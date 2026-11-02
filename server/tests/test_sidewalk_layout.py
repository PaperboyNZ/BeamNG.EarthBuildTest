"""Whole-width clearance, continuity, edge fallback and regional paving contracts."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from shapely.geometry import LineString, Polygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import islands
import cdae
import junctions
import roads
import sidewalk_details as details
import sidewalks as sw
import streetscape
from sidewalk_layout import CarriagewayGuard


def run(a=0., b=20., y=5., **kwargs):
    return dict(pts=np.array([[a, y, 0.], [b, y, 0.]]), side=1, w=2.5, fid=str(a),
                j=(False, False), open=(True, True), **kwargs)


class ContinuityTests(unittest.TestCase):
    def test_duplicate_vertices_do_not_collapse_profile_width(self):
        points = np.array([[0., 0., 0.], [10., 0., 0.], [10., 0., 0.], [20., 10., 0.]])
        c, out = sw.run_geometry(points, 1, 2.5)
        self.assertTrue((np.linalg.norm(out, axis=1) >= 1 - 1e-12).all())
        np.testing.assert_array_equal(out[1], out[2])
        b = sw.Builder((0, 0, 0), collision=True)
        b.add_run(c, out, 2.5)
        self.assertTrue(np.isfinite(b.arrays()[0]).all())

    def test_sub_30cm_and_coincident_seams_join(self):
        for gap in (0., .02, .2):
            result = roads.join_walk_ends([run(0, 10), run(10 + gap, 20)], [])
            self.assertEqual(len(result), 1, gap)
            self.assertEqual(result[0]['pts'][0, 0], 0)
            self.assertEqual(result[0]['pts'][-1, 0], 20)
            self.assertTrue((np.diff(result[0]['pts'][:, 0]) > 0).all())

    def test_reversed_run_then_third_chain_retains_both_ends(self):
        first = run(10, 0); first['side'] = -1
        result = roads.join_walk_ends([first, run(10.1, 20), run(20.2, 30)], [])
        self.assertEqual(len(result), 1)
        np.testing.assert_allclose(result[0]['pts'][[0, -1], 0], [0, 30])

    def test_median_metadata_survives_and_cannot_join_pedestrian_walk(self):
        self.assertEqual(len(roads.join_walk_ends([run(0, 10, median=True), run(10.1, 20)], [])), 2)
        result = roads.join_walk_ends([run(0, 10, median=True), run(10.1, 20, median=True)], [])
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]['median'])

    def test_different_levels_and_driveway_gaps_do_not_join(self):
        a, b = run(0, 10), run(10.1, 20)
        b['pts'][:, 2] = 2
        self.assertEqual(len(roads.join_walk_ends([a, b], [])), 2)
        barrier = (np.array([[11., 0.], [11., 10.]]), .5)
        self.assertEqual(len(roads.join_walk_ends([a, run(12, 20)], [barrier])), 2)


class ClearanceTests(unittest.TestCase):
    def test_curved_source_street_does_not_use_coarse_decal_simplification(self):
        from test_roads import FRAME, features, flat
        t = np.linspace(0, np.pi / 2, 46)
        centre = np.array([128., 128.])
        arc = centre + 40 * np.c_[np.cos(t), np.sin(t)]
        f = features([arc.tolist()], ['residential'])
        walks, source = [], []
        roads.build_tile(FRAME, 0, 0, [f], flat, lambda la, lo: np.ones(np.shape(la), bool),
                         walks=walks, roads_out=source)
        self.assertEqual(len(walks), 2)
        for wk in walks:
            curb, _ = sw.run_geometry(wk['pts'], wk['side'], wk['w'])
            xy = np.vstack((curb[:, :2], (curb[:-1, :2] + curb[1:, :2]) / 2))
            _, spec, points, lon = source[0]
            reference = next(line for look, width, line in roads.extras(spec, points, lon)
                             if look['m'] == roads.SIDEWALK['m'] and look['side'] == wk['side'])
            expected, _ = sw.run_geometry(reference, wk['side'], wk['w'])
            self.assertLess(junctions._seg_dist(xy, expected[:, :2]).max(), .03)

    def test_ordinary_road_keeps_full_walk(self):
        guard = CarriagewayGuard([(np.array([[-10., 0.], [30., 0.]]), 3.)])
        original = run()
        self.assertIs(guard.trim(original)[0], original)

    def test_adjacent_carriageway_cannot_be_narrowed_by_sidewalk(self):
        line = np.array([[-10., 7.], [30., 7.]])
        guard = CarriagewayGuard([(line, 1.5)])
        original = line.copy()
        self.assertEqual(guard.trim(run()), [])
        np.testing.assert_array_equal(line, original)

    def test_skew_intersection_protects_entire_width_and_rear_slope(self):
        line = np.array([[5., -10.], [20., 20.]])
        guard = CarriagewayGuard([(line, 2.)])
        result = guard.trim(run(0, 40))
        self.assertEqual(len(result), 2)
        for piece in result:
            c, out = sw.run_geometry(piece['pts'], 1, 2.5)
            rear = 2.5 + sw.BACK_RUN * (.18 + 2.5 * sw.CROSS_SLOPE + sw.SINK)
            self.assertTrue(guard.clear(np.vstack((c[:, :2], (c[:, :2] + out * rear)[::-1]))))

    def test_small_corner_gets_a_chamfer_instead_of_a_gap(self):
        spec = roads.Spec(6., 'paved', True, 'residential', False)
        rs = [('east', spec, np.array([[0., 0., 0.], [4.4, 0., 0.]]), 0.),
              ('north', spec, np.array([[0., 0., 0.], [0., 4.4, 0.]]), 0.)]
        corners = junctions.find(rs, roads.has_sidewalks, None)[0]
        self.assertEqual(len(corners), 1)
        self.assertEqual(corners[0]['edge_style'], 'chamfer')
        guard = CarriagewayGuard([(p, s.width / 2) for _, s, p, _ in rs])
        self.assertTrue(guard.clear(np.vstack((corners[0]['arc'], corners[0]['outer']))))

    def test_island_smoothing_cannot_enter_wide_approach(self):
        t = np.linspace(0, 2 * np.pi, 65)
        poly = np.c_[16 * np.cos(t), 16 * np.sin(t)]
        loop = (poly, 3.)
        entry = (np.array([[11., 0.], [35., 0.]]), 4.)
        ring = islands._island_ring(poly[:-1], [loop], 0., carriageways=[loop, entry])
        self.assertIsNotNone(ring)
        shape = Polygon(ring[:, :2])
        self.assertLess(shape.intersection(LineString(entry[0]).buffer(entry[1], cap_style=2)).area, 1e-8)


class DetailAndRegionalTests(unittest.TestCase):
    def test_tile_export_keeps_selected_corner_and_run_finishes(self):
        corner = dict(arc=np.array([[0., 0., 0.], [1., 1., 0.], [2., 1., 0.]]),
                      inward=np.tile([0., 1.], (3, 1)), outer=[[2., 4., 0.], [0., 4., 0.]])
        wk = dict(pts=np.array([[10., 0., 0.], [30., 0., 0.]]), side=1, w=2.5, caps=(True, True), brick=True)
        with tempfile.TemporaryDirectory() as d:
            path, _ = roads.write_tile(d, '/vfs', 1, 0, 0, [], [dict(corner=corner, pavement='stone'), wk])
            import json
            data = json.loads((Path(d) / Path(path).name).read_text())
            shape = cdae.read(str(Path(d) / Path(data['walk']['shape']).name))
        names = {m['name'] for m in shape['materials']}
        self.assertIn(sw.MATERIALS[sw.STONE], names)
        self.assertIn(sw.MATERIALS[sw.BRICK], names)

    def test_utility_patch_preserves_atlas_and_clear_corridor(self):
        b = sw.Builder((0, 0, 0), collision=True)
        curb = np.c_[np.arange(0., 41., 2), np.zeros(21), np.zeros(21)]
        b.add_run(curb, np.tile([0., 1.], (len(curb), 1)), 2.5, ramps=[(30., 34.)])
        P, T, UV, M = b.arrays()
        self.assertIn(details.MATERIAL, M)
        for tri in T[M == details.MATERIAL]:
            p = P[tri]
            self.assertGreaterEqual(p[:, 1].min(), sw.CURB_W + details.EDGE_MARGIN_M - 1e-8)
            self.assertGreaterEqual(2.5 - p[:, 1].max(), details.CLEAR_WALK_M)
            self.assertTrue(np.all((p[:, 0] < 30 - sw.RAMP_FLARE - details.END_MARGIN_M) |
                                   (p[:, 0] > 34 + sw.RAMP_FLARE + details.END_MARGIN_M)))
            self.assertTrue(np.all((UV[tri] >= 0) & (UV[tri] <= 1)))
        self.assertNotIn(details.MATERIAL, b.col.arrays()[3])

    def test_narrow_and_verge_walks_cannot_get_cover_in_walking_strip(self):
        for width, verge in ((1.5, False), (2.5, True)):
            b = sw.Builder((0, 0, 0))
            b.add_run(np.array([[0., 0., 0.], [40., 0., 0.]]), np.tile([0., 1.], (2, 1)), width, verge=verge)
            self.assertNotIn(details.MATERIAL, b.arrays()[3])

    def test_paver_corners_and_crossings_keep_their_regional_finish(self):
        arc = np.array([[0., 0., 0.], [1., 1., 0.], [2., 1., 0.]])
        for finish in (sw.BRICK, sw.STONE):
            b = sw.Builder((0, 0, 0), collision=True)
            b.add_corner(arc, np.tile([0., 1.], (3, 1)), [[2., 4., 0.], [0., 4., 0.]], slab=finish)
            b.add_run(np.array([[10., 0., 0.], [30., 0., 0.]]), np.tile([0., 1.], (2, 1)),
                      2.5, slab=finish, driveways=[(6., 9.)])
            self.assertIn(finish, b.arrays()[3])
            self.assertNotIn(1, b.arrays()[3])

    def test_international_selection_and_reannotation_clear_stale_finish(self):
        import geodesy
        cases = [(-36.85, 174.76, 'precast_channel', 'slab'), (40.7, -74., 'concrete_channel', 'slab'),
                 (52.37, 4.9, 'paved_edge', 'brick'), (41.9, 12.5, 'paved_edge', 'stone'),
                 (59.91, 10.75, 'cold_climate', 'slab'), (1.29, 103.85, 'deep_channel', 'slab'),
                 (35.68, 139.69, 'compact_precast', 'slab')]
        walk = run(); walk['fid'] = 'source'
        for lat, lon, style, pavement in cases:
            streetscape.annotate([walk], geodesy.EnuFrame(lat, lon),
                                 source_locations={'source': (lat, lon)}, road_classes={'source': 'residential'})
            self.assertEqual(walk['curb_style'], style, (lat, lon))
            self.assertEqual(walk['pavement'], pavement)
            self.assertEqual(walk['brick'], pavement == 'brick')


if __name__ == '__main__':
    unittest.main()
