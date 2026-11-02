"""Street-level visual regressions: openings, garage access, materials and roofs."""
from dataclasses import FrozenInstanceError
import math
import os
from pathlib import Path
import pickle
import sys
import unittest
from unittest import mock

import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import freeze_items
from buildgen import facades, roofs, materials as recipes
from buildgen.geometry import sky_vertex_count
from buildgen.topology import Footprint
from test_buildgen_topology import rect


def building(width=12., depth=10., fp=None, **attrs):
    fp = fp or Footprint(rect(0, 0, width, depth))
    values = {"class": "house", "num_floors": 1, "seed_id": "house", "_footprint": fp}
    values.update(attrs)
    return b.plan(np.asarray(fp.outer), values)


def road(y=-12.):
    return [(np.array([(-50., y), (100., y)]), 3., "residential", False)]


class FacadesTest(unittest.TestCase):
    def test_front_door_face_is_clear_in_every_facade_lod(self):
        from buildgen import progressive, quality

        spec = building(8., 10., seed_id="off-centre")
        rows = b.doors([(spec, 0., 0.)], road(-6.), 0., 0.)
        self.assertEqual(sum(row[0] == "door" for row in rows), 1)
        spec = freeze_items([(spec, 0., 0.)])[0][0]
        elevation = next(e for e in spec.facades.elevations
                         if e.boundary == 0 and e.edge == spec.door[0])
        door = next(op for op in elevation.openings if op.kind == "door")
        ring = np.asarray(spec.footprint.outer)
        origin = ring[elevation.edge]
        along = (ring[(elevation.edge + 1) % len(ring)] - origin) / elevation.length
        outward = np.array([along[1], -along[0]])
        base = b.base_z(spec, 0., 0.)
        # The stock prop's panel sits 6.9 cm behind its origin. A facade
        # surrogate at 2.5 cm can cover or fight it after placement rounding.
        panel_depth = b.DOOR_OUT_M - .069
        for name in quality.NAMES:
            token = progressive.DETAIL.set(name)
            try:
                for lite in (False, True):
                    with self.subTest(quality=name, lite=lite):
                        mesh = b.Mesh()
                        facades.draw(mesh, spec, 0., 0., -b.SKIRT_M, lite)
                        positions, _, triangles, _, _ = mesh.arrays()
                        local = positions[:, :2] - origin
                        projected = np.column_stack((local @ along, positions[:, 2] - base))
                        depths = local @ outward
                        for height in (.75, 1.25):
                            sample = Point((door.left + door.right) / 2., door.bottom + height)
                            backing = [tri for tri in triangles
                                       if Polygon(projected[tri]).area > 1e-8
                                       and Polygon(projected[tri]).covers(sample)
                                       and np.ptp(depths[tri]) < 1e-5]
                            self.assertTrue(backing, "Door needs an opaque wall behind the prop")
                            self.assertLess(max(float(depths[tri].max()) for tri in backing),
                                            panel_depth - .005)
            finally:
                progressive.DETAIL.reset(token)

    def test_off_centre_door_reserves_its_actual_window_interval(self):
        spec = building(8., 10., seed_id="off-centre")
        props = b.doors([(spec, 0., 0.)], road(-6.), 0., 0.)
        self.assertEqual(props[0][0], "door")
        self.assertAlmostEqual(spec.door[1] / 8., .22 if b._hash01(spec.seed, "door") < .5 else .78)
        layout = facades.plan(spec, 0., 0.)
        front = next(e for e in layout.elevations if e.boundary == 0 and e.edge == spec.door[0])
        door = next(op for op in front.openings if op.kind == "door")
        windows = [op for op in front.openings if op.kind == "window"]
        self.assertTrue(windows)
        self.assertTrue(all(not op.overlaps(door, facades.OPENING_GAP) for op in windows))
        # The old kernel put a window at 2 or 6 m, overlapping this off-centre door.
        self.assertLess(min(abs(spec.door[1] - x) for x in (2., 6.)), .5)

    def test_only_the_entrance_elevation_loses_a_window(self):
        spec = building(5., 9.)
        spec.door = (0, 2.5)
        layout = facades.plan(spec, 0., 0.)
        front, back = layout.elevations[0], layout.elevations[2]
        self.assertFalse(any(op.kind == "window" for op in front.openings))
        self.assertTrue(any(op.kind == "window" for op in back.openings))

    def test_window_heads_fit_short_storeys_and_align_across_each_floor(self):
        spec = building(height=5.2, num_floors=2, roof_shape="flat")
        layout = facades.plan(spec, 0., 0.)
        windows = [op for e in layout.elevations for op in e.openings if op.kind == "window"]
        self.assertTrue(windows)
        for floor in range(2):
            group = [op for op in windows if op.floor == floor]
            self.assertEqual(len({op.top for op in group}), 1)
            self.assertTrue(all(op.top <= (floor + 1) * spec.floor_h - .39 for op in group))

    def test_garage_entry_windows_and_driveway_form_one_layout(self):
        spec = building()
        drives = []
        rows = b.doors([(spec, 0., 0.)], road(), 0., 0., drives)
        self.assertTrue(spec.garage_opening)
        self.assertEqual(len(drives), 1)
        self.assertAlmostEqual(drives[0]["n"][0][0], spec.garage_opening[1], places=3)
        self.assertGreaterEqual(drives[0]["w"], spec.garage_opening[2])
        self.assertEqual(rows[0][0], "door")
        layout = facades.plan(spec, 0., 0.)
        front = next(e for e in layout.elevations if e.boundary == 0 and e.edge == spec.door[0])
        for i, op in enumerate(front.openings):
            self.assertGreater(op.left, .4)
            self.assertLess(op.right, front.length - .4)
            for other in front.openings[i+1:]:
                self.assertFalse(op.overlaps(other, .15))

    def test_upper_parts_and_shallow_setbacks_do_not_receive_garage_entries(self):
        spec = building()
        spec.min_h = 4.
        self.assertEqual(b.doors([(spec, 0., 0.)], road(), 0., 0.), [])
        self.assertIsNone(spec.garage_opening)
        spec = building()
        b.doors([(spec, 0., 0.)], road(-5.), 0., 0.)
        self.assertIsNone(spec.garage_opening)

    def test_frozen_layout_and_worker_roundtrip_preserve_openings(self):
        spec = building()
        b.doors([(spec, 0., 0.)], road(), 0., 0.)
        plan = freeze_items([(spec, 0., 0.)])[0][0]
        copy = pickle.loads(pickle.dumps(plan))
        self.assertEqual(plan.facades, copy.facades)
        self.assertEqual(plan.garage_opening, copy.garage_opening)
        with self.assertRaises(FrozenInstanceError):
            copy.facades.elevations[0].length = 8.
        spec.door = (1, 3.)
        self.assertNotEqual(spec.door, plan.door)

    def test_independent_near_and_far_requests_keep_source_entrances(self):
        import roads
        from test_buildgen_context import FRAME, MapData, geographic
        from test_roads import features as road_features
        houses = geographic([[[rect(-7, 0, 14, 12)]]], ["target"],
                            **{"class": ["house"], "num_floors": [1.]})
        streets = road_features([[(-50., -13.), (50., -13.)]], ["residential"], widths=[(0, 6.)])
        la, lo, _ = FRAME.enu_to_geodetic(np.array([-50., 50.]), np.array([-13., -13.]), 0.)
        streets.lonlat = np.column_stack((lo, la))
        md = MapData(houses, geographic([[[rect(-100, -100, 200, 200)]]], ["land"], **{"class": ["residential"]}))
        original_cell = md.cell

        def cell(*args, **kwargs):
            result = original_cell(*args, **kwargs)
            result.layers["roads"] = streets
            return result

        ground = lambda la, lo: np.zeros(np.broadcast(la, lo).shape)
        with mock.patch.dict(os.environ, {"BNE_BUILDING_GENERATOR": "v2"}), \
                mock.patch.object(md, "cell", side_effect=cell), \
                mock.patch.object(roads, "tile_bbox", return_value=(-20., -20., 20., 20.)), \
                mock.patch.object(roads, "cells_of_tile", return_value=[(0, 0)]):
            near = b.road_tile_items(FRAME, 0, 0, md, ground)
            far, _, _ = b.far_items(FRAME, 0, 0, md, ground)
        n, f = near[0][0], far[0][0]
        self.assertIsNotNone(n.garage_opening)
        self.assertEqual(n.door, f.door)
        self.assertEqual(n.garage_opening, f.garage_opening)
        # A closer rendered service lane must not move the independently
        # resolved front door or replace the garage with a window.
        b.doors(near, road(-12.) + [(np.array([(10., -50.), (10., 50.)]), 2., "service", False)], -20., -20.)
        frozen = freeze_items(near)[0][0]
        self.assertEqual(frozen.facades, f.facades)

    def test_front_fence_leaves_the_full_garage_driveway_clear(self):
        spec = building(20., 10.)
        b.doors([(spec, 0., 0.)], road(), 0., 0.)
        edge, centre, width, _ = spec.garage_opening
        self.assertEqual(edge, 0)
        rows = b._front_fence(spec, np.array([0., 0.]), np.array([1., 0.]), 20., spec.door[1]/20.,
                              np.array([-50., -12.]), np.array([150., 0.]), 150.**2, 3., 0., True)
        self.assertTrue(rows)
        for row in rows:
            self.assertGreaterEqual(abs(row[1] - centre), b.FENCE_SEG_M/2. + (width+.3)/2. - .01)

    def test_near_lite_share_panes_and_close_mesh_has_recesses(self):
        spec = building()
        b.doors([(spec, 0., 0.)], road(), 0., 0.)
        spec = freeze_items([(spec, 0., 0.)])[0][0]
        meshes = []
        for lite in (False, True):
            mesh = b.Mesh()
            facades.draw(mesh, spec, 0., 0., -b.SKIRT_M, lite)
            meshes.append(mesh.arrays())
        window_index = b.MATERIALS.index(b.FACADE)
        expected = sum(op.columns * 2 for e in spec.facades.elevations for op in e.openings if op.kind == "window")
        for p, uv, tris, mats, colors in meshes:
            self.assertEqual(int((mats == window_index).sum()), expected)
            self.assertTrue(np.isfinite(p).all())
            self.assertTrue(np.all(np.linalg.norm(np.cross(p[tris[:, 1]]-p[tris[:, 0]], p[tris[:, 2]]-p[tris[:, 0]]), axis=1) > 1e-10))
        front = spec.facades.elevations[0]
        window = next(op for op in front.openings if op.kind == "window")
        near = meshes[0][0]
        self.assertTrue(np.any(np.isclose(near[:, 1], facades.REVEAL) & np.isclose(near[:, 2], window.bottom)))
        self.assertGreater(len(meshes[0][0]), len(meshes[1][0]))

    def test_wall_partition_excludes_apertures_without_losing_opaque_wall(self):
        spec = building()
        b.doors([(spec, 0., 0.)], road(), 0., 0.)
        for e in facades.plan(spec, 0., 0.).elevations:
            openings = [op for op in e.openings if op.kind != "door"]
            cells = [Polygon(rect(x0, z0, x1-x0, z1-z0)) for x0, x1, z0, z1 in facades.wall_cells(e.length, -3., spec.height, openings)]
            apertures = [Polygon(rect(op.left, op.bottom, op.right-op.left, op.top-op.bottom)) for op in openings]
            wall = unary_union(cells)
            self.assertAlmostEqual(sum(p.area for p in cells), wall.area)
            self.assertAlmostEqual(wall.area + sum(p.area for p in apertures), e.length * (spec.height + 3.))
            self.assertTrue(all(wall.intersection(p).area < 1e-8 for p in apertures))

    def test_courtyard_openings_never_inherit_the_exterior_door(self):
        fp = Footprint(rect(0, 0, 24, 20), (rect(6, 6, 12, 8),))
        spec = building(fp=fp, roof_shape="flat")
        spec.door = (0, 3.)
        layout = facades.plan(spec, 0., 0.)
        self.assertEqual(sum(op.kind == "door" for e in layout.elevations for op in e.openings), 1)
        inner = [op for e in layout.elevations if e.boundary == 1 for op in e.openings]
        self.assertTrue(inner)
        self.assertTrue(all(op.kind == "window" for op in inner))

    def test_data_poor_houses_have_multiple_coherent_material_and_roof_families(self):
        specs = [building(seed_id=f"house-{i}") for i in range(60)]
        self.assertGreaterEqual(len({s.inference.facade.value for s in specs}), 3)
        self.assertGreaterEqual(len({s.facade for s in specs}), 12)
        self.assertEqual({s.roof for s in specs}, {"gabled", "hipped"})
        self.assertTrue(all(s.inference.facade.status == "fallback" for s in specs))
        self.assertGreater(sum(s.roof == "hipped" for s in specs), 25)

    def test_skyline_recovers_exact_palette_after_a_worker_boundary(self):
        spec = building(facade_material="wood", facade_color="#345678")
        expected = b._sky_colour(spec.facade, 1.)
        with mock.patch.dict(b.LOOKS):
            del b.LOOKS[spec.facade]
            self.assertEqual(b._sky_colour(spec.facade, 1.), expected)


class RoofEnvelopeTest(unittest.TestCase):
    def shapes(self):
        return [Footprint(((0, 0), (20, 0), (20, 6), (8, 6), (8, 16), (0, 16))),
                Footprint(rect(0, 0, 30, 24), (rect(8, 8, 14, 8),)),
                Footprint(((0, 0), (20, .2), (19.8, 12), (.1, 11.8)))]

    def test_supported_planes_cover_exactly_the_source_footprint(self):
        for fp in self.shapes():
            for kind in ("gabled", "hipped"):
                with self.subTest(kind=kind, footprint=fp):
                    roof = roofs.envelope(fp, kind)
                    tiles = [Polygon([p[:2] for p in tri]) for tri in roof.triangles]
                    self.assertAlmostEqual(sum(p.area for p in tiles), fp.area, places=6)
                    self.assertLess(unary_union(tiles).symmetric_difference(fp.shape()).area, 1e-6)
                    self.assertAlmostEqual(max(p[2] for tri in roof.triangles for p in tri), 1.)
                    self.assertTrue(all(0. <= p[2] <= 1. + 1e-8 for tri in roof.triangles for p in tri))

    def test_visual_collision_and_skyline_preserve_mapped_roof_top(self):
        for fp in self.shapes():
            for kind in ("gabled", "hipped"):
                spec = building(fp=fp, roof_shape=kind, height=8., roof_height=2.)
                items = freeze_items([(spec, 0., 0.)])
                meshes = [b.build(items), b.build(items, lite=True), b.collision_mesh(items), b._sky_mesh(items)]
                for mesh in meshes:
                    self.assertAlmostEqual(float(mesh[0][:, 2].max()), 8.)
                self.assertEqual(sky_vertex_count(items[0][0]), len(meshes[-1][0]))

    def test_roof_triangles_are_nondegenerate_and_textures_keep_physical_scale(self):
        for fp in self.shapes() + [Footprint(rect(0, 0, 12, 12)), Footprint(rect(0, 0, 14, 12))]:
            for kind in ("gabled", "hipped"):
                spec = building(fp=fp, roof_shape=kind, facade_material="brick", roof_material="slate")
                mesh = b.Mesh()
                roofs.draw(mesh, spec, spec.height, b._Looks(spec.seed), overhang=True)
                p, uv, tris, materials, _ = mesh.arrays()
                cross = np.cross(p[tris[:, 1]]-p[tris[:, 0]], p[tris[:, 2]]-p[tris[:, 0]])
                self.assertTrue(np.all(np.linalg.norm(cross, axis=1) > 1e-8))
                roof_triangles = tris[materials == b.MATERIALS.index(b.ROOF_SLATE)]
                for tri in roof_triangles:
                    lengths = np.linalg.norm(p[tri] - np.roll(p[tri], 1, axis=0), axis=1)
                    tex_lengths = np.linalg.norm((uv[tri] - np.roll(uv[tri], 1, axis=0))*recipes.roof_scale("slate"), axis=1)
                    np.testing.assert_allclose(lengths, tex_lengths, atol=2e-5)
                # Gable and courtyard upper-wall UVs continue the facade's run
                # and storey height instead of sampling a single flat texel.
                body = tris[materials != b.MATERIALS.index(b.ROOF_SLATE)]
                if len(body):
                    np.testing.assert_allclose(uv[body, 1], p[body, 2]/2.4, atol=1e-5)

    def test_complexity_limit_retains_a_diagnosed_flat_fallback(self):
        angles = np.linspace(0., 2 * math.pi, roofs.MAX_ROOF_VERTICES + 1, endpoint=False)
        fp = Footprint(tuple((float(20 * math.cos(t)), float(20 * math.sin(t))) for t in angles))
        spec = building(fp=fp, roof_shape="hipped", height=9.)
        self.assertEqual(spec.roof, "flat")
        self.assertIn("pitched_roof_complexity_limit_flat_fallback", spec.diagnostics)
        self.assertEqual(spec.evidence.get("roof_shape").value, "hipped")

    def test_roof_v_runs_uphill_and_coplanar_triangles_share_texture_frame(self):
        # The former triangle-normal projection ran V downhill. Thin triangles
        # could also acquire a different texture frame on the same roof plane.
        outline = np.array([(0, 0), (20, .000001), (20, 12), (12, 12), (12, 12.000001), (0, 12)])
        angle = math.radians(37)
        rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
        fp = Footprint(tuple(map(tuple, outline @ rotation.T + [8100., -6300.])))
        spec = building(fp=fp, roof_shape="hipped", roof_material="metal")
        mesh = b.Mesh(); roofs.draw(mesh, spec, spec.height, b._Looks(spec.seed))
        p, uv, tris, mid, _ = mesh.arrays()
        tris = tris[mid == b.MATERIALS.index(b.ROOF_METAL)]
        shared = {}
        for tri, plane in zip(tris, roofs.envelope(fp, spec.roof).triangle_planes):
            for i, j in ((0, 1), (1, 2), (2, 0)):
                dz = p[tri[i], 2]-p[tri[j], 2]
                dv = uv[tri[i], 1]-uv[tri[j], 1]
                self.assertGreaterEqual(dz*dv, -1e-8)
            for idx in tri:
                key = (plane, *np.round(p[idx], 6))
                if key in shared:
                    np.testing.assert_allclose(uv[idx], shared[key], atol=1e-6)
                shared[key] = uv[idx]

    def test_covering_scale_does_not_depend_on_roof_size(self):
        for family in ("metal", "slate", "shingle"):
            scale = recipes.roof_scale(family)
            self.assertLess(scale[0], 6.)
            for width in (8., 14., 32.):
                spec = building(width, 12., roof_shape="gabled", roof_material=family)
                mesh = b.Mesh(); roofs.draw(mesh, spec, spec.height, b._Looks(spec.seed))
                p, uv, tris, _, _ = mesh.arrays()
                for tri in tris[:len(roofs.envelope(spec.footprint, spec.roof).triangles)]:
                    lengths = np.linalg.norm(p[tri]-np.roll(p[tri], 1, axis=0), axis=1)
                    measured = np.linalg.norm((uv[tri]-np.roll(uv[tri], 1, axis=0))*scale, axis=1)
                    np.testing.assert_allclose(lengths, measured, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
