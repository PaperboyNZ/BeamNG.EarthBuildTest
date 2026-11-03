"""Occupied building area stays consistent across ingestion, render LODs and physics."""
import dataclasses
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
import mapgeom
from buildgen import BuildingPlan, freeze_items
from buildgen.geometry import sky_vertex_count
from buildgen.topology import Footprint, InvalidFootprint, component_key, triangles


def rect(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def courtyard():
    return Footprint(rect(10, 10, 80, 80), (rect(30, 30, 40, 40),))


class FlatFrame:
    """Identity frame for exact geometric assertions (lat=y, lon=x)."""
    lat0 = 0.
    lon0 = 0.
    h0 = 0.

    def geodetic_to_enu(self, lat, lon, height):
        return np.asarray(lon), np.asarray(lat), np.asarray(height)

    def enu_to_geodetic(self, x, y, z):
        return np.asarray(y), np.asarray(x), np.asarray(z)


def features(polygons, ids=None, **attrs):
    points, parts, rings, coords = [], [0], [0], [0]
    for components in polygons:
        for component in components:
            for r in component:
                p = np.asarray(r).tolist()
                if p[0] != p[-1]:
                    p.append(p[0])
                points.extend(p)
                coords.append(len(points))
            rings.append(len(coords) - 1)
        parts.append(len(rings) - 1)
    ids = ids if ids is not None else [f"B{i}" for i in range(len(polygons))]
    attrs.setdefault("src_dataset", ["OpenStreetMap"] * len(ids))
    return mapgeom.Features("buildings", np.array(ids), np.full(len(ids), 3, np.uint8), np.array(parts),
                            np.array(rings), np.array(coords), np.asarray(points, np.float64),
                            attrs={k: np.asarray(v) for k, v in attrs.items()})


def planned(fp, **attrs):
    values = {"class": "apartments", "height": 15., "roof_shape": "flat", "seed_id": "test", "_footprint": fp}
    values.update(attrs)
    return b.plan(np.asarray(fp.outer), values)


class TopologyTest(unittest.TestCase):
    def test_canonical_rings_holes_and_identity(self):
        fp = courtyard()
        outer = list(fp.outer)
        hole = list(fp.holes[0])
        reordered = Footprint(outer[2:] + outer[:2] + [outer[2]], (hole[::-1],))
        self.assertEqual(fp, reordered)
        self.assertEqual(component_key((outer, hole)), component_key((outer[::-1], hole[::-1])))
        self.assertGreater(b._area2(np.asarray(fp.outer)), 0)
        self.assertLess(b._area2(np.asarray(fp.holes[0])), 0)
        self.assertEqual(fp.area, 4800.)
        self.assertEqual(fp, pickle.loads(pickle.dumps(fp)))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            fp.outer = ()

    def test_triangles_cover_only_occupied_area(self):
        shapes = [courtyard(), Footprint([(0, 0), (20, 0), (20, 5), (5, 5), (5, 20), (0, 20)]),
                  Footprint(rect(0, 0, 80, 50), (rect(5, 5, 10, 10), rect(40, 20, 20, 20)))]
        for fp in shapes:
            with self.subTest(fp=fp):
                tt = [Polygon(t) for t in triangles(fp)]
                self.assertTrue(all(fp.shape().covers(t) for t in tt))
                self.assertAlmostEqual(sum(t.area for t in tt), fp.area)
                self.assertAlmostEqual(unary_union(tt).symmetric_difference(fp.shape()).area, 0.)

    def test_invalid_source_geometry_is_rejected_without_repair(self):
        invalid = [([(0, 0), (4, 4), (0, 4), (4, 0)], ()),
                   (rect(0, 0, 10, 10), (rect(12, 2, 3, 3),)),
                   (rect(0, 0, 10, 10), (rect(1, 1, 5, 5), rect(3, 3, 5, 5))),
                   ([(0, 0), (1, 0), (2, 0)], ()),
                   ([(0, 0), (1, 1), (np.nan, 4)], ())]
        for outer, holes in invalid:
            with self.subTest(outer=outer, holes=holes), self.assertRaises(InvalidFootprint):
                Footprint(outer, holes)

    def test_halfplane_can_return_disconnected_pieces(self):
        fp = Footprint([(0, 0), (30, 0), (30, 30), (20, 30), (20, 10), (10, 10), (10, 30), (0, 30)])
        pieces = fp.half((0, 15), (0, 1))
        self.assertEqual(len(pieces), 2)
        self.assertEqual(sum(p.area for p in pieces), 300.)
        self.assertTrue(all(fp.shape().covers(p.shape()) for p in pieces))

    def test_road_in_courtyard_has_no_occupied_length(self):
        fp = courtyard()
        ring = np.asarray(fp.outer)
        inside = [np.array([(35., 50), (65., 50)])]
        crossing = [np.array([(0., 50), (100., 50)])]
        self.assertEqual(b.road_through(ring, inside, footprint=fp), 0.)
        self.assertEqual(b.road_through(ring, crossing, footprint=fp), 40.)


class GeometryTest(unittest.TestCase):
    def assertLids(self, mesh, footprint, z, down=False):
        p, _, t = mesh[:3]
        t = p[t]
        t = t[np.all(np.isclose(t[:, :, 2], z, atol=1e-6), axis=1)]
        self.assertGreater(len(t), 0)
        polygons = [Polygon(tri[:, :2]) for tri in t]
        self.assertTrue(all(footprint.shape().covers(poly) for poly in polygons))
        self.assertAlmostEqual(sum(poly.area for poly in polygons), footprint.area, places=6)
        cross = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])[:, 2]
        self.assertTrue(np.all(cross < 0 if down else cross > 0))

    def test_courtyard_lids_and_walls_match_all_representations(self):
        fp = courtyard()
        spec = planned(fp)
        items = freeze_items([(spec, 0., 0.)])
        meshes = [b.build(items), b.build(items, lite=True), b.collision_mesh(items), b._sky_mesh(items)]
        for mesh in meshes:
            self.assertLids(mesh, fp, spec.height)
            self.assertTrue(np.isfinite(mesh[0]).all())
            self.assertTrue(np.isfinite(mesh[1]).all())
        self.assertEqual(sky_vertex_count(items[0][0]), len(meshes[-1][0]))
        collision = meshes[2][0][meshes[2][2]]
        for t in collision:
            n = np.cross(t[1] - t[0], t[2] - t[0])
            if abs(n[2]) > 1e-6:
                continue
            n = n[:2] / np.linalg.norm(n[:2])
            c = t[:, :2].mean(0)
            self.assertFalse(fp.shape().contains(Point(c + n * .01)), "wall normal points into air")
            self.assertTrue(fp.shape().contains(Point(c - n * .01)), "wall backs onto building")

    def test_elevated_underside_and_collision_hold_volume(self):
        fp = courtyard()
        spec = planned(fp)
        spec.min_h = 8.
        items = freeze_items([(spec, 1., 2.)])
        for mesh in [b.build(items), b.build(items, True), b.collision_mesh(items), b._sky_mesh(items)]:
            self.assertLids(mesh, fp, 10., down=True)
            self.assertLids(mesh, fp, 10. + spec.height)
        box = b.collider_boxes(items, 100., 200.)[0]
        self.assertEqual(box[:6], [110., 210., 10., 190., 290., 25.])
        self.assertEqual(box[6][0][0], [110., 210.])
        self.assertEqual(len(box[6]), 2)

    def test_complex_pitched_roof_keeps_outline_and_mapped_top(self):
        fp = Footprint([(0, 0), (20, 0), (20, 5), (5, 5), (5, 20), (0, 20)])
        spec = planned(fp, roof_shape="gabled")
        self.assertEqual(spec.roof, "gabled")
        self.assertIn("clipped_pitched_roof_envelope", spec.diagnostics)
        self.assertEqual(spec.evidence.get("roof_shape").value, "gabled")
        for mesh in [b.build([(spec, 0., 0.)]), b.collision_mesh([(spec, 0., 0.)])]:
            self.assertAlmostEqual(float(mesh[0][:, 2].max()), 15.)
        np.testing.assert_array_equal(b.drawn_ring(spec), fp.outer)

    def test_rectangular_pitched_roof_is_supported(self):
        fp = Footprint(rect(0, 0, 12, 8))
        spec = planned(fp, roof_shape="gabled", **{"class": "house"})
        self.assertEqual(spec.roof, "gabled")
        for mesh in [b.build([(spec, 0., 0.)]), b.collision_mesh([(spec, 0., 0.)])]:
            self.assertGreater(mesh[0][:, 2].max(), spec.height)

    def test_plan_rejects_misaligned_topology_and_door_ring(self):
        spec = planned(courtyard())
        spec.ring = np.roll(spec.ring, 1, axis=0)
        with self.assertRaisesRegex(ValueError, "canonical footprint"):
            BuildingPlan.from_spec(spec)

    def test_small_source_bevel_does_not_leave_a_wall_crack(self):
        fp = Footprint([(0., .02), (.02, 0.), (20., 0.), (20., 20.), (0., 20.)])
        spec = planned(fp)
        for mesh in (b.build([(spec, 0., 0.)]), b.build([(spec, 0., 0.)], lite=True)):
            p = mesh[0]
            faces = p[mesh[2]]
            bevel = np.all(np.isclose(faces[:, :, 0] + faces[:, :, 1], .02), axis=1)
            self.assertEqual(int(bevel.sum()), 2)

    def test_specialised_structures_keep_existing_compilers(self):
        for attrs in ({"class": "parking", "num_floors": 4}, {"class": "bridge_structure"}, {"ship": True}, {"pier": True}):
            spec = planned(Footprint(rect(0, 0, 80, 30)), **attrs)
            if spec.deck:
                self.assertEqual(spec.footprint,Footprint(rect(0,0,80,30)))
                self.assertIsNotNone(b.deck_plan(spec,0.,0.))
            else:
                self.assertIsNone(spec.footprint)
            self.assertIn("specialised_structure_legacy_geometry", spec.diagnostics)
            self.assertIsNotNone(b.build(freeze_items([(spec, 0., 0.)])))


class IngestTest(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.dict(os.environ, {"BNE_BUILDING_GENERATOR": "v2"})
        patch.start()
        self.addCleanup(patch.stop)

    def tile(self, layers, box=(0., 0., 256., 256.), **kwargs):
        elev = kwargs.pop("elev", lambda lat, lon: np.zeros(np.shape(lat)))
        return b.tile_buildings(FlatFrame(), *box, layers, elev, **kwargs)

    def test_multipolygons_holes_and_duplicate_cells(self):
        fp = courtyard()
        small = rect(150, 10, 20, 10)
        layer = features([[(fp.outer, *fp.holes), (small,)]], height=[15.])
        items = self.tile([layer, layer])
        self.assertEqual(len(items), 2)
        self.assertEqual(sum(s.footprint.area for s, _, _ in items), 5000.)
        self.assertEqual({s.evidence.source_id for s, _, _ in items}, {"B0"})
        self.assertEqual(len({s.seed for s, _, _ in items}), 1)
        self.assertEqual(self.tile([layer], skip={"B0"}), [])
        self.assertEqual(b.coverage(items, 100.), .5)

    def test_component_order_winding_and_tile_origin_do_not_change_ownership(self):
        left, right = rect(20, 20, 20, 10), rect(270, 20, 20, 10)
        a = features([[(left,), (right,)]], height=[10.])
        c = features([[(right[::-1],), (left[2:] + left[:2],)]], height=[10.])
        for lo in (0., 256.):
            ia = self.tile([a], box=(lo, 0., lo + 256., 256.))
            ic = self.tile([c], box=(lo, 0., lo + 256., 256.))
            self.assertEqual(len(ia), len(ic))
            for x, y in zip(ia, ic):
                self.assertEqual(x[0].footprint, y[0].footprint)
                self.assertEqual(x[0].seed, y[0].seed)
        first = self.tile([a])
        second = self.tile([a], box=(256., 0., 512., 256.))
        all_items = first + second
        self.assertEqual(len(all_items), 2)
        shifted = self.tile([a], box=(-10., -10., 512., 256.))
        for before, after in zip(all_items, shifted):
            delta = 10. if first else 266.
            np.testing.assert_array_equal(before[0].ring + [delta, 10.], after[0].ring)
            self.assertEqual(before[0].seed, after[0].seed)
        self.assertEqual({s.evidence.source_id for s, _, _ in shifted}, {"B0"})

    def test_mapped_parts_preserve_all_components_and_courtyards_once(self):
        fp = courtyard()
        parent = features([[(rect(0, 0, 100, 100),), (rect(140, 0, 30, 30),)]], ids=["parent"], height=[25.])
        parts = features([[(fp.outer, *fp.holes), (rect(150, 10, 10, 10),)]], ids=["part"],
                         building_id=["parent"], height=[25.], min_height=[10.])
        items = self.tile([parent, parent], part_layers=[parts, parts])
        self.assertEqual(len(items), 2)
        self.assertEqual(sum(s.footprint.area for s, _, _ in items), 4900.)
        for s, _, _ in items:
            self.assertEqual((s.height, s.min_h), (15., 10.))
            self.assertEqual(s.evidence.source_id, "part")
            self.assertEqual(s.evidence.parent_id, "parent")
            self.assertEqual(s.evidence.get("height").value, 25.)

    def test_courtyard_terrain_samples_and_water_probe(self):
        fp = courtyard()
        layer = features([[(fp.outer, *fp.holes)]], height=[15.])
        def ground(lat, lon):
            return np.where((lat == 30.) & (lon == 30.), -4., 0.)
        items = self.tile([layer], elev=ground, water=lambda lat, lon: 30 < lat < 70 and 30 < lon < 70)
        self.assertEqual(len(items), 1)
        spec, lo, hi = items[0]
        self.assertEqual((lo, hi), (-4., 0.))
        np.testing.assert_array_equal(spec.gring, [0.] * 4)
        freeze_items(items)

    def test_courtyard_road_does_not_raise_building(self):
        fp = courtyard()
        layer = features([[(fp.outer, *fp.holes)]], height=[15.])
        road = np.array([(35., 50.), (65., 50.)])
        items = self.tile([layer], roads_xy=[road], bridges_xy=[road], decks=[(road, np.array([8., 8.]), 6.)])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][0].min_h, 0.)
        self.assertEqual(items[0][0].footprint, fp)

    def test_passage_slicing_does_not_fill_courtyards(self):
        fp = courtyard()
        layer = features([[(fp.outer, *fp.holes)]], height=[30.])
        road = np.array([(0., 50.), (100., 50.)])
        items = self.tile([layer], decks=[(road, np.array([5., 5.]))])
        self.assertGreater(len(items), 1)
        for s, _, _ in items:
            self.assertTrue(fp.shape().covers(s.footprint.shape()))
            self.assertEqual(s.footprint.shape().intersection(Polygon(fp.holes[0])).area, 0.)
            if s.min_h < 10. and s.min_h + s.height > 5.:
                self.assertEqual(s.footprint.road_length([road]), 0.)
        self.assertIsNotNone(b.collision_mesh(freeze_items(items)))

    def test_invalid_component_is_reported_and_other_component_survives(self):
        layer = features([[([(0, 0), (10, 10), (0, 10), (10, 0)],), (rect(20, 20, 10, 10),)]], height=[10.])
        with self.assertLogs("buildgen.ingest", level="WARNING") as logs:
            items = self.tile([layer])
        self.assertEqual(len(items), 1)
        self.assertIn("B0", logs.output[0])

    def test_legacy_default_stays_available(self):
        fp = courtyard()
        layer = features([[(fp.outer, *fp.holes), (rect(150, 10, 10, 10),)]], height=[15.])
        with mock.patch.dict(os.environ, {"BNE_BUILDING_GENERATOR": "legacy"}):
            items = self.tile([layer])
        self.assertEqual(len(items), 1)
        self.assertIsNone(items[0][0].footprint)

    def test_real_geodetic_projection_keeps_one_owner_for_disconnected_wings(self):
        import geotiles
        gx, gy = geotiles.tile_of(51.5, -.1)
        frame = geotiles.geobox(gx, gy).frame
        def lonlat(ring):
            p = np.asarray(ring)
            lat, lon, _ = frame.enu_to_geodetic(p[:, 0], p[:, 1], 0.)
            return np.c_[lon, lat].tolist()
        main = (lonlat(rect(-50, -50, 100, 100)), lonlat(rect(-20, -20, 40, 40)))
        wing = (lonlat(rect(180, -20, 20, 40)),)
        layer = features([[main, wing]], height=[15.])
        reverse = features([[wing, main]], height=[15.])
        owners = []
        for x in range(gx - 1, gx + 2):
            for y in range(gy - 1, gy + 2):
                tile = geotiles.geobox(x, y)
                args = (tile.frame, *tile.box)
                items = b.tile_buildings(*args, [layer], lambda la, lo: np.zeros(np.shape(la)), own=tile.box)
                other = b.tile_buildings(*args, [reverse], lambda la, lo: np.zeros(np.shape(la)), own=tile.box)
                self.assertEqual(len(items), len(other))
                if items:
                    owners.append(tile.key)
                    self.assertEqual(len(items), 2)
                    self.assertEqual(sum(len(s.footprint.holes) for s, _, _ in items), 1)
                    for a, c in zip(items, other):
                        np.testing.assert_array_equal(a[0].ring, c[0].ring)
                        self.assertEqual(a[0].seed, c[0].seed)
                    self.assertIsNotNone(b.collision_mesh(freeze_items(items)))
        self.assertEqual(len(owners), 1)


if __name__ == "__main__":
    unittest.main()
