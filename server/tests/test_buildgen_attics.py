"""Attic details fit the actual roof and survive all persistent representations."""
from dataclasses import replace
from pathlib import Path
import pickle
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import attics, freeze_items, house_styles, roofs, roof_edges
from buildgen.geometry import sky_vertex_count
from buildgen.topology import Footprint
from building_fixtures import transform


def house(rise=3., region='us_northeast', kind='gabled', angle=0., variant='standard'):
    fp = Footprint(transform(((-9., -5.), (9., -5.), (9., 5.), (-9., 5.)), angle, offset=(2300., -1200.)))
    spec = b.plan(np.asarray(fp.outer), {'class': 'house', 'num_floors': 2,
                  'roof_height': rise, 'roof_shape': kind, '_footprint': fp, 'seed_id': 'attic-test'})
    spec.inference = replace(spec.inference, house_style=house_styles.HouseStyle('regional', region), roof_variant=variant,
                             modifiers=('dormers',) if region!='jp_temperate' else ())
    spec.gring = np.zeros(len(fp.outer))
    return spec


class AtticTests(unittest.TestCase):
    def test_low_roofs_and_non_houses_have_no_attic_details(self):
        spec = house(1.8)
        self.assertEqual(attics.plan(spec), ((), ()))
        for changes in ({'windows': False}, {'plain': True}, {'floors': 5}):
            s = house()
            for key, value in changes.items(): setattr(s, key, value)
            self.assertEqual(attics.plan(s), ((), ()))
        spec = house()
        spec.inference = replace(spec.inference, use=replace(spec.inference.use, value='industrial'))
        self.assertEqual(attics.plan(spec), ((), ()))

    def test_attic_windows_fit_gables_and_do_not_appear_on_hips(self):
        for angle in (0., 31., 89.):
            spec = house(angle=angle, region='jp_temperate')
            windows, dormers = attics.plan(spec)
            self.assertEqual(len(windows), 2)
            self.assertFalse(dormers)
            roof = roofs.for_spec(spec)
            for w in windows:
                for side in (-.5, .5):
                    xy = np.array(w.centre) + np.array(w.direction) * w.width * side
                    self.assertGreater(roof_edges.height(roof, xy) * spec.inference.roof_rise, w.bottom + w.height)
        self.assertFalse(attics.plan(house(kind='hipped', region='jp_temperate'))[0])

    def test_dormers_fit_single_planes_and_keep_the_original_peak(self):
        for region in ('us_northeast', 'us_midwest'):
            for angle in (0., 31., 89.):
                spec = house(region=region, angle=angle)
                with patch('buildgen.attics.materials.unit', return_value=.1):
                    attics._plan.cache_clear()
                    windows, dormers = attics.plan(spec)
                self.assertTrue(dormers, (region, angle))
                self.assertLessEqual(len(dormers), 2)
                roof = roofs.for_spec(spec)
                for dormer in dormers:
                    self.assertGreaterEqual(dormer.window.width, 1.35)
                    self.assertGreaterEqual(dormer.window.height, 1.25)
                    self.assertGreaterEqual(np.linalg.norm(np.subtract(dormer.walls[0][1], dormer.walls[0][0])), 2.6 - 1e-7)
                    for face in (*dormer.walls, *dormer.caps):
                        for x, y, z in face:
                            self.assertLessEqual(z, spec.inference.roof_rise)
                            self.assertGreaterEqual(z + 1e-6, roof_edges.height(roof, (x, y)) * spec.inference.roof_rise)
                    self.assertGreater(dormer.window.bottom, roof_edges.height(roof, dormer.window.centre) * spec.inference.roof_rise)

    def test_dormer_solids_match_near_lite_collision_sky_and_pickle(self):
        spec = house()
        # Find an eligible stable identity without overriding runtime selection.
        for seed in np.linspace(.01, .99, 40):
            spec.seed = float(seed)
            if attics.plan(spec)[1]: break
        self.assertTrue(attics.plan(spec)[1])
        items = freeze_items([(spec, 0., 0.)])
        restored = pickle.loads(pickle.dumps(items))
        self.assertEqual(attics.plan(items[0][0]), attics.plan(restored[0][0]))
        vertices = [np.array(p) + (0., 0., spec.height) for dormer in attics.plan(spec)[1]
                    for face in dormer.caps for p in face]
        for mesh in (b.build(items), b.build(items, lite=True), b.collision_mesh(items), b._sky_mesh(items)):
            self.assertTrue(np.isfinite(mesh[0]).all())
            self.assertAlmostEqual(float(mesh[0][:, 2].max()), spec.height + spec.inference.roof_rise, places=5)
            for p in vertices:
                self.assertLess(np.min(np.linalg.norm(mesh[0] - p, axis=1)), .001)
        self.assertEqual(len(b._sky_mesh(items)[0]), sky_vertex_count(items[0][0]))

    def test_small_or_unsuitable_faces_decline_dormers(self):
        for variant in ('shed', 'cross_gable', 'flared_hip', 'broad_eave'):
            self.assertFalse(attics.plan(house(variant=variant))[1])
        spec = house()
        spec.footprint = Footprint(((0., 0.), (18., 0.), (18., 18.), (0., 18.)),
                                  (((4., 4.), (4., 14.), (14., 14.), (14., 4.)),))
        self.assertEqual(attics.plan(spec), ((), ()))


if __name__ == '__main__': unittest.main()
