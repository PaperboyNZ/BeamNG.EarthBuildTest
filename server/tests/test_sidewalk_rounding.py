"""Plan-view arcs, bounded coarse profiles and accepted-outline physics."""
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from shapely.geometry import Point, Polygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sidewalks as sw
import sidewalk_outline as outline
import sidewalk_rounding as rounding


def builder(quality='minimum', width=2.5, caps=(True, True), **options):
    ground = options.pop('ground', None)
    b = sw.Builder((100., 200., 0.), collision=True, quality=quality, ground=ground)
    curb = np.array([[100., 200., 2.], [110., 200., 2.1], [120., 203., 2.2]])
    b.add_run(curb, sw._normals_2d(curb[:, :2]), width, caps=caps, **options)
    return b


def same_mesh(test, a, b):
    for x, y in zip(a, b):
        np.testing.assert_array_equal(x, y)


class RoundedSidewalkTest(unittest.TestCase):
    def assert_valid(self, mesh):
        p, t, uv, m = mesh
        self.assertTrue(np.isfinite(p).all() and np.isfinite(uv).all())
        self.assertEqual(len(m), len(t))
        self.assertGreaterEqual(t.min(), 0)
        self.assertLess(t.max(), len(p))
        area = np.linalg.norm(np.cross(p[t[:, 1]]-p[t[:, 0]], p[t[:, 2]]-p[t[:, 0]]), axis=1)
        self.assertTrue((area > 1e-13).all(), 'degenerate faces')
        vertices = np.unique(t[m == 0])
        self.assertTrue((uv[vertices, 1] >= sw.V_BAND_LOW-1e-8).all())
        self.assertTrue((uv[vertices, 1] <= sw.V_BAND_TOP+1e-8).all())

    def test_higher_tiers_share_rounded_physics_but_use_cheaper_lower_profiles(self):
        physical = builder('low').col.arrays()
        counts = []
        for quality in ('very_low', 'low', 'medium', 'high', 'very_high', 'ultra'):
            b = builder(quality)
            self.assert_valid(b.arrays())
            same_mesh(self, physical, b.col.arrays())
            counts.append(len(b.arrays()[1]))
        self.assertEqual(counts[:2], [counts[0]]*2)
        self.assertLess(counts[1], counts[2])
        self.assertLess(counts[2], counts[3])
        self.assertNotEqual(len(physical[1]), len(builder().col.arrays()[1]))

    def test_minimum_and_default_remain_original(self):
        a = builder()
        b = sw.Builder(a.origin, collision=True)
        piece = a.pieces[0]
        b.add_run(piece[1], piece[2], piece[5])
        same_mesh(self, a.arrays(), b.arrays())
        self.assertFalse(any(a.round_flags))

    def test_outline_rounds_all_four_rectangle_corners_without_expansion(self):
        p = np.array([[0., 0., 0.], [20., 0., 0.]])
        n = np.array([[0., 1.], [0., 1.]])
        c, outward, _, mapping = outline.run(p, n, 2.5, (True, True), [], 'low')
        shape = Polygon(np.vstack((c[:, :2], (c[:, :2]+outward*2.5)[::-1])))
        self.assertTrue(shape.is_valid)
        self.assertTrue(Polygon([(0, 0), (20, 0), (20, 2.5), (0, 2.5)]).covers(shape))
        for corner in ((.01, .01), (.01, 2.49), (19.99, .01), (19.99, 2.49)):
            self.assertFalse(shape.covers(Point(corner)), corner)
        self.assertTrue(shape.covers(Point(0., 1.25)))
        np.testing.assert_allclose(np.linalg.norm(c[:5, :2]-[.6, .6], axis=1), .6, atol=1e-8)
        self.assertEqual(len(c), 2+2*outline.ARC_SPANS)

    def test_cap_flags_keep_tile_and_continuous_driveway_joins_exact(self):
        p = np.array([[0., 0., 0.], [20., 0., 0.]])
        n = np.tile([0., 1.], (2, 1))
        c, normal, ramps, mapping = outline.run(p, n, 2.5, (True, False), [], 'low')
        np.testing.assert_array_equal(c[-1], p[-1])
        np.testing.assert_array_equal(normal[-1], n[-1])
        result = outline.run(p, n, 2.5, (False, False), [], 'low')
        self.assertIs(result[0], p)
        self.assertIs(result[1], n)
        self.assertIsNone(result[3])

    def test_driveway_gap_receives_rounded_corners_on_both_exposed_sides(self):
        b = sw.Builder((0, 0, 0), quality='low', collision=True)
        for a, z in ((0., 8.), (12., 20.)):
            b.add_run(np.array([[a, 0., 0.], [z, 0., 0.]]), np.tile([0., 1.], (2, 1)), 2.5)
        for piece in b.pieces:
            c, n, w = piece[1], piece[2], piece[5]
            self.assertGreater(c[0, 1], 0.)
            self.assertGreater(c[-1, 1], 0.)
            self.assertLess((c[:, :2]+n*w)[:, 1].max(), 2.51)
        self.assert_valid(b.arrays())

    def test_coarse_chamfer_uses_one_native_sweep_and_no_straight_path_subdivision(self):
        for quality in ('very_low', 'low'):
            b = sw.Builder((0, 0, 0), collision=True, quality=quality)
            b.add_run(np.array([[0., 0., 0.], [20., 0., 0.]]), np.tile([0., 1.], (2, 1)),
                      2.5, caps=(False, False))
            self.assertEqual(len(b.pieces[0][1]), 2)
            with patch.object(sw, 'native_mesh', wraps=sw.native_mesh) as native, \
                 patch.object(rounding, 'native_visual', side_effect=AssertionError('low-tier smoothing pass')):
                mesh = b.arrays()
                b.col.arrays()
            self.assertEqual(native.call_count, 1)
            self.assertEqual(np.count_nonzero(mesh[3] != 5), 14)  # unchanged native profile
            self.assertEqual(rounding.spans(quality), 1)

    def test_over_budget_piece_falls_back_completely_without_losing_ends(self):
        count = outline.limits('low')[0]+1
        p = np.c_[np.linspace(0, 100, count), np.zeros(count), np.zeros(count)]
        n = np.tile([0., 1.], (count, 1))
        pair = []
        for quality in ('minimum', 'low'):
            b = sw.Builder((0, 0, 0), quality=quality, collision=True)
            b.add_run(p, n, 2.5)
            pair.append(b)
        self.assertFalse(pair[1].round_flags[0])
        same_mesh(self, pair[0].arrays(), pair[1].arrays())
        same_mesh(self, pair[0].col.arrays(), pair[1].col.arrays())

    def test_ramps_narrow_bands_verges_and_driveways_share_physical_outline(self):
        for width in (.3, .6, 1.2, 2.5, 4.):
            for options in ({'ramps': [(0., 1.), (8., 10.)]}, {'driveways': [(6., 9.)]},
                            {'verge': True, 'driveways': [(6., 9.)]}, {'slab': sw.BRICK}, {'slab': sw.STONE}):
                with self.subTest(width=width, options=options):
                    a, b = builder('low', width=width, **options), builder('high', width=width, **options)
                    self.assert_valid(a.arrays())
                    self.assert_valid(b.arrays())
                    same_mesh(self, a.col.arrays(), b.col.arrays())

    def test_terrain_and_garden_clearance_use_same_accepted_outline(self):
        garden = {'ring': [[105., 201., 0.], [106., 201., 0.], [106., 202., 0.], [105., 202., 0.]]}
        ground = lambda x, y: np.full_like(x, 2.22)
        a, b = builder('low', ground=ground, gardens=[garden]), builder('high', ground=ground, gardens=[garden])
        same_mesh(self, a.col.arrays(), b.col.arrays())
        self.assert_valid(a.arrays())

    def test_terrain_physics_reuses_native_sweep_instead_of_generating_twice(self):
        ground = lambda x, y: np.full_like(x, 2.22)
        b = builder('low', ground=ground)
        with patch.object(sw, 'native_mesh', wraps=sw.native_mesh) as native:
            b.arrays()
            b.col.arrays()
        self.assertEqual(native.call_count, 1)

    def test_topology_has_no_open_upper_cap_edges(self):
        p, t, _, m = builder('low').arrays()
        welded, inverse = np.unique(np.round(p, 8), axis=0, return_inverse=True)
        faces = inverse[t[m != 5]]
        edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
        edge, count = np.unique(edges, axis=0, return_counts=True)
        self.assertFalse(np.any(count > 2))
        boundary = welded[edge[count == 1]]
        self.assertTrue((boundary[:, :, 2] <= 2.1+1e-8).all())

    def test_paving_retains_actual_metric_grid_through_rounded_tips(self):
        b = sw.Builder((0, 0, 0), quality='low')
        b.add_run(np.array([[0., 0., 0.], [20., 0., 0.]]), np.tile([0., 1.], (2, 1)), 2.5)
        p, t, uv, m = b.arrays()
        ids = np.unique(t[m == 1])
        np.testing.assert_allclose(uv[ids], p[ids, :2]/sw.SLAB_TILE_M, atol=1e-8)

    def test_station_paired_corners_survive_ramps_reflection_and_transport(self):
        from test_walk_surfaces import corner
        for transpose in (False, True):
            for ramps in (False, True):
                origin = np.array([119., -85., 3.])
                arc, inward, outer, stations, _ = corner(widths=(1.1, 3.4), angle=.61,
                                                         transpose=transpose, ramps=ramps, origin=origin)
                length = np.linalg.norm(np.diff(arc[:, :2], axis=0), axis=1).sum()
                lowered = [(.35*length, .6*length)] if ramps else []
                pair = []
                for quality in ('minimum', 'low'):
                    b = sw.Builder(origin, collision=True, quality=quality)
                    b.add_corner(arc, inward, outer, outer_stations=stations, ramps=lowered)
                    pair.append(b)
                self.assert_valid(pair[1].arrays())
                same_mesh(self, pair[0].col.arrays(), pair[1].col.arrays())

    def test_road_writer_uses_grounds_not_buildings_and_changes_collision_with_outline(self):
        import roads
        from buildgen import grounds_quality as grounds, quality
        walk = {'pts': np.array([[0., 3., 0.], [20., 3., 0.]]), 'side': 1,
                'w': 2.5, 'caps': (True, True)}
        digests = []
        with tempfile.TemporaryDirectory() as directory:
            for building, ground in (('ultra', 'minimum'), ('minimum', 'low'), ('ultra', 'low')):
                quality.run(building, grounds.run, ground, roads.write_tile,
                            directory, '/fixture', 1, 0, 0, [], walks=[walk])
                digests.append(tuple(hashlib.sha256((Path(directory)/name).read_bytes()).hexdigest()
                                     for name in ('walks_1_0_0.cdae', 'walkcol_1_0_0.cdae')))
        self.assertNotEqual(digests[0][0], digests[1][0])
        self.assertNotEqual(digests[0][1], digests[1][1])
        self.assertEqual(digests[1], digests[2])

    def test_closed_island_corners_trim_inside_original_and_keep_height_and_winding(self):
        ring = np.array([[0., 0., 1.], [20., 0., 2.], [20., 10., 3.], [0., 10., 2.]])
        original = Polygon(ring[:, :2])
        for source in (ring, ring[::-1]):
            result = outline.island_ring(source, 1.2, 'low')
            self.assertEqual(len(result), 4*(outline.ARC_SPANS+1)+1)
            self.assertTrue(original.buffer(1e-7).covers(Polygon(result[:, :2])))
            self.assertFalse(Polygon(result[:, :2]).covers(Point(.01, .01)))
            self.assertTrue(np.isfinite(result).all())
        self.assertIs(outline.island_ring(ring, 1.2, 'minimum'), ring)

    def test_invalid_or_over_budget_ring_has_whole_original_fallback(self):
        small = np.array([[0., 0., 0.], [1., 0., 0.], [1., 1., 0.], [0., 1., 0.]])
        self.assertIs(outline.island_ring(small, 1.2, 'low'), small)
        theta = np.linspace(0., 2*np.pi, 200, endpoint=False)
        ring = np.c_[10*np.cos(theta), 10*np.sin(theta), np.zeros(len(theta))]
        self.assertIs(outline.island_ring(ring, 1.2, 'low'), ring)

    def test_densified_straight_island_edges_do_not_hide_ninety_degree_corners(self):
        corners = np.array([[0., 0., 0.], [20., 0., 0.], [20., 10., 0.], [0., 10., 0.]])
        dense = np.concatenate([a+(b-a)*np.linspace(0., 1., 12, endpoint=False)[:, None]
                                for a, b in zip(corners, np.roll(corners, -1, axis=0))])
        rounded = outline.island_ring(dense, 1.2, 'very_low')
        self.assertEqual(len(rounded), 21)
        self.assertFalse(Polygon(rounded[:, :2]).covers(Point(.01, .01)))

    def test_actual_closed_native_island_band_has_matching_start_end_sections(self):
        import roads
        ring = np.array([[0., 0., 0.], [20., 0., 0.], [20., 10., 0.], [0., 10., 0.]])
        rounded = outline.island_ring(ring, 1.2, 'low')
        band = roads.offset_polyline(np.vstack([rounded[-1:], rounded, rounded[:2]]), .6)[1:-1]
        curb, normal = sw.run_geometry(band, 1, 1.2)
        np.testing.assert_allclose(curb[0], curb[-1], atol=1e-8)
        np.testing.assert_allclose(normal[0], normal[-1], atol=1e-8)
        b = sw.Builder((0, 0, 0), quality='low', collision=True)
        b.add_run(curb, normal, 1.2, caps=(False, False))
        self.assert_valid(b.arrays())

    def test_both_geometry_and_profile_recipe_changes_invalidate_road_cache(self):
        import blockworker
        from buildgen import grounds_quality as grounds
        def key():
            return grounds.run('low', blockworker._geo_content_key, 'tile', 15, True,
                               False, False, False, 0., None, None, md={})
        original = key()
        with patch.object(outline, 'REVISION', 'different-outline'):
            geometry_changed = key()
        with patch.object(rounding, 'REVISION', 'different-profile'):
            profile_changed = key()
        self.assertEqual(len({original, geometry_changed, profile_changed}), 3)


if __name__ == '__main__':
    unittest.main()
