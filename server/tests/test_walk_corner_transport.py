"""Curved rear stations survive draping, worker frames and native meshing."""
import copy
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import blockworker
import geodesy
import roads
import sidewalks
from test_walk_geometry import circular
from walk_geometry import corner_rear


def fixture(radius=8., widths=(1.2, 3.1)):
    arc, inward, start, end = circular(radius, widths)
    rear = corner_rear(arc, inward, *widths, start, end)
    return {'corner': dict(arc=arc, inward=inward, outer=rear.outer,
                          outer_widths=rear.widths, outer_stations=rear.stations,
                          merged_inner=rear.merged_inner)}


class CornerTransportTests(unittest.TestCase):
    def test_nonlinear_drape_uses_every_corresponding_curb_station(self):
        walk = fixture()
        before = copy.deepcopy(walk['corner'])
        ground = lambda x, y: .03*x*x + .02*y
        roads.drape_walks(None, None, [walk], ground)
        c = walk['corner']
        expected = ground(c['arc'][:, 0], c['arc'][:, 1])
        np.testing.assert_array_equal(c['arc'][:, 2], expected)
        np.testing.assert_allclose(np.asarray(c['outer'])[:, 2], expected[::-1], atol=1e-12)
        np.testing.assert_array_equal(c['outer_stations'], before['outer_stations'])
        np.testing.assert_array_equal(np.asarray(c['outer'])[:, :2], before['outer'][:, :2])
        # Native's fixed 2.5 m datum and each real width are applied once.
        corrected = sidewalks.corner_outer(c)
        expected_top = expected[::-1] + sidewalks.CURB_H + c['outer_widths']*sidewalks.CROSS_SLOPE
        np.testing.assert_allclose(corrected[:, 2] + sidewalks.CURB_H + 2.5*sidewalks.CROSS_SLOPE,
                                   expected_top, atol=1e-12)
        for collision in (False, True):
            builder = sidewalks.Builder((100., -200., 12.), collision=collision)
            builder.add_corner(c['arc'], c['inward'], corrected, outer_stations=c['outer_stations'])
            mesh = builder.col.arrays() if collision else builder.arrays()
            referenced = mesh[0][np.unique(mesh[1])] + builder.origin
            for xy, height in zip(corrected[:, :2], expected_top):
                self.assertLess(np.linalg.norm(referenced - [*xy, height], axis=1).min(), 1e-8)

    def test_merged_corner_drape_keeps_one_rear_point(self):
        walk = fixture(3., (4., 4.))
        self.assertTrue(walk['corner']['merged_inner'])
        self.assertEqual(len(walk['corner']['outer']), 1)
        roads.drape_walks(None, None, [walk], lambda x, y: .1*x + .2*y)
        c = walk['corner']
        self.assertEqual(len(c['outer']), 1)
        self.assertAlmostEqual(c['outer'][0][2], np.mean(c['arc'][[0, -1], 2]))

    def test_worker_frame_remaps_stations_without_mutating_source(self):
        walk = fixture()
        before = copy.deepcopy(walk['corner'])
        src = geodesy.EnuFrame(-36.914235, 174.910092, 0.)
        dst = geodesy.EnuFrame(-36.814235, 174.810092, 0.)
        mapped = blockworker._map_walks(src, dst, [walk])[0]['corner']
        stations = np.r_[0., np.cumsum(np.linalg.norm(np.diff(mapped['arc'][:, :2], axis=0), axis=1))]
        np.testing.assert_allclose(mapped['outer_stations'], stations[::-1], atol=1e-10)
        for key in ('arc', 'inward', 'outer', 'outer_stations', 'outer_widths'):
            np.testing.assert_array_equal(walk['corner'][key], before[key])


if __name__ == '__main__':
    unittest.main()
