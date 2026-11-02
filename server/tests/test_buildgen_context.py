"""Fixed source neighbourhoods, complete data and the three rendering entry points."""
from concurrent.futures import ThreadPoolExecutor
import copy
import os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
import geodesy
import mapcells
from buildgen.context import ContextPending, LAYERS, Provider, halo
from test_buildgen_topology import features, rect


FRAME = geodesy.EnuFrame(45., 9., 0.)


def geographic(polygons, ids=None, **attrs):
    def convert(ring):
        xy = np.asarray(ring)
        la, lo, _ = FRAME.enu_to_geodetic(xy[:, 0], xy[:, 1], 0.)
        return np.column_stack((lo, la))
    return features([[[convert(r) for r in part] for part in pp] for pp in polygons], ids, **attrs)


def scene():
    pp = [[[rect(-6, -4, 12, 8)]], [[rect(35, 0, 12, 8)]], [[rect(0, 35, 12, 8)]],
          [[rect(-45, 0, 12, 8)]], [[rect(330, 0, 12, 8)]]]
    buildings = geographic(pp, ["target", "N1", "N2", "N3", "distant"],
                           **{"class": ["", "house", "house", "house", "industrial"],
                              "height": [np.nan, 9., 9., 9., 60.],
                              "facade_material": ["", "brick", "brick", "brick", "metal"]})
    land = geographic([[[rect(-100, -100, 200, 200)]]], ["zone"], **{"class": ["residential"]})
    return buildings, land


class MapData:
    """All cells intentionally repeat features, as unclipped Overture buildings do."""
    def __init__(self, buildings=None, land=None):
        self.buildings, self.land = scene() if buildings is None else (buildings, land)
        self.available = True
        self.revision = "test-release-1"
        self.calls, self.prefetched = [], []
        self.failures = 0

    def versions(self):
        return {"overture": self.revision, "pipeline": 1}

    def has(self, key, layer):
        return self.available

    def prefetch(self, key, layers):
        self.prefetched.append((key, layers))

    def cell(self, key, layers, kind):
        self.calls.append((key, tuple(layers), kind))
        if self.failures:
            self.failures -= 1
            raise OSError("simulated source outage")
        return SimpleNamespace(key=key, layers={name: self.buildings if name == "buildings" else
                                                self.land if name == "land_use" else None for name in layers})


class ContextTest(unittest.TestCase):
    def test_self_and_duplicate_cells_excluded_and_radius_is_fixed(self):
        md = MapData()
        ctx = Provider(md).query(md.buildings, 0)
        self.assertEqual([n.source_id for n in ctx.neighbours], ["N1", "N2", "N3"])
        self.assertTrue(all(n.evidence.get("height").status == "observed" for n in ctx.neighbours))
        self.assertEqual(ctx.land_use, (("residential", 1.),))
        self.assertTrue(ctx.manifest.digest)
        self.assertTrue(all(layers == LAYERS for _, layers, _ in md.calls))
        expected = set(halo(mapcells.cell_of(45., 9.)))
        self.assertEqual({key for key, _, _ in md.calls}, expected)

    def test_order_and_source_winding_do_not_change_context_identity(self):
        md = MapData()
        original = Provider(md).query(md.buildings, 0)
        source = md.buildings
        order = [4, 3, 2, 1, 0]
        reordered = features([[[r[::-1] for r in pp] for pp in source.parts(i)] for i in order],
                             source.ids[order], **{k: v[order] for k, v in source.attrs.items()})
        actual = Provider(MapData(reordered, md.land)).query(reordered, 4)
        self.assertEqual(original, actual)

    def test_missing_required_layer_fails_and_later_request_retries(self):
        md = MapData()
        p = Provider(md)
        md.failures = 1
        with self.assertRaisesRegex(OSError, "outage"):
            p.query(md.buildings, 0)
        self.assertEqual(len(p.query(md.buildings, 0).neighbours), 3)
        missing = MapData(md.buildings, None)
        with self.assertRaisesRegex(ValueError, "required land_use"):
            Provider(missing).query(md.buildings, 0)

    def test_background_fetch_defers_instead_of_planning_from_partial_data(self):
        md = MapData()
        md.available = False
        p = Provider(md)
        with self.assertRaises(ContextPending):
            p.query(md.buildings, 0, background=True)
        self.assertFalse(md.calls)
        self.assertTrue(md.prefetched)
        md.available = True
        self.assertEqual(len(p.query(md.buildings, 0, background=True).neighbours), 3)
        self.assertTrue(all(kind == "background" for _, _, kind in md.calls))

    def test_revision_change_invalidates_cached_evidence(self):
        md = MapData()
        p = Provider(md)
        old = p.query(md.buildings, 0)
        count = len(md.calls)
        self.assertEqual(p.query(md.buildings, 0), old)
        self.assertEqual(len(md.calls), count)
        md.revision = "test-release-2"
        new = p.query(md.buildings, 0)
        self.assertNotEqual(new.manifest.digest, old.manifest.digest)
        self.assertEqual(new.neighbours, old.neighbours)
        self.assertGreater(len(md.calls), count)

    def test_cell_content_and_climate_fingerprints_participate_in_identity(self):
        md = MapData()
        before = Provider(md).query(md.buildings, 0)
        changed = copy.deepcopy(md.buildings)
        changed.attrs["height"][1] = 15.
        after = Provider(MapData(changed, md.land)).query(changed, 0)
        self.assertNotEqual(before.manifest.digest, after.manifest.digest)
        with mock.patch("buildgen.context.climate_identity", return_value="different-grid"):
            climate = Provider(md).query(md.buildings, 0)
        self.assertNotEqual(before.manifest.digest, climate.manifest.digest)

    def test_land_use_holes_and_overlapping_duplicates_do_not_create_false_coverage(self):
        buildings, _ = scene()
        land = geographic([[[rect(-100, -100, 200, 200), rect(-10, -10, 20, 20)]]], ["zone"],
                          **{"class": ["industrial"]})
        ctx = Provider(MapData(buildings, land)).query(buildings, 0)
        self.assertEqual(ctx.land_use, ())

    def test_underground_buildings_do_not_supply_height_or_use_priors(self):
        md = MapData()
        md.buildings.attrs["is_underground"] = np.array([False, True, False, False, False])
        ctx = Provider(md).query(md.buildings, 0)
        self.assertEqual([n.source_id for n in ctx.neighbours], ["N2", "N3"])

    def test_duplicate_geometry_with_different_ids_cannot_inflate_consensus(self):
        buildings = geographic([[[rect(-6, -4, 12, 8)]], [[rect(35, 0, 12, 8)]],
                                [[rect(35, 0, 12, 8)]], [[rect(35, 0, 12, 8)]]],
                               ["target", "N1", "N2", "N3"], **{"class": ["", "house", "house", "house"]})
        _, land = scene()
        ctx = Provider(MapData(buildings, land)).query(buildings, 0)
        self.assertEqual([n.source_id for n in ctx.neighbours], ["N1"])

    def test_large_disconnected_target_cannot_use_partial_land_use_overlap(self):
        buildings = geographic([[[rect(-6, -4, 12, 8)], [rect(10000, 0, 12, 8)]]], ["target"])
        _, land = scene()
        ctx = Provider(MapData(buildings, land)).query(buildings, 0)
        self.assertFalse(ctx.land_use)
        self.assertIn("land_use_target_exceeds_context_extent", ctx.diagnostics)

    def test_halo_wraps_at_dateline_and_extends_at_high_latitudes(self):
        for lat, lon in ((0., 179.9999), (85., -179.9999), (-85., 20.)):
            key = mapcells.cell_of(lat, lon)
            keys = set(halo(key))
            self.assertIn(key, keys)
            self.assertTrue(all(0 <= k.x < k.n and 0 <= k.y < k.n for k in keys))
            if lon > 179:
                self.assertTrue(any(k.x == 0 for k in keys))
            if lon < -179:
                self.assertTrue(any(k.x == k.n - 1 for k in keys))

    def test_concurrent_requests_share_a_complete_bundle(self):
        md = MapData()
        started, proceed = threading.Event(), threading.Event()
        cell = md.cell

        def waiting(key, layers, kind):
            started.set()
            if not proceed.wait(5):
                raise TimeoutError("test barrier")
            return cell(key, layers, kind)

        md.cell = waiting
        p = Provider(md)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(p.query, md.buildings, 0)
            self.assertTrue(started.wait(5))
            second = pool.submit(p.query, md.buildings, 0)
            with self.assertRaises(ContextPending):
                p.query(md.buildings, 0, background=True)
            proceed.set()
            self.assertEqual(first.result(), second.result())
        self.assertEqual(len(md.calls), len(halo(mapcells.cell_of(45., 9.))))

    def test_near_far_and_skyline_share_observed_inference(self):
        import roads
        md = MapData()
        ground = lambda la, lo: np.zeros(np.broadcast(la, lo).shape)
        # One source appears in differently sized render requests. Neither the
        # tile coverage nor its shared-wall count may change its use or material.
        with mock.patch.dict(os.environ, {"BNE_BUILDING_GENERATOR": "v2"}), \
                mock.patch.object(roads, "tile_bbox", return_value=(-20., -20., 20., 20.)), \
                mock.patch.object(roads, "cells_of_tile", return_value=[mapcells.cell_of(45., 9.)]):
            near = b.road_tile_items(FRAME, 0, 0, md, ground)
            far, _, _ = b.far_items(FRAME, 0, 0, md, ground)
            sky, _ = b.sky_items(FRAME, (-200., -200., 200., 200.), [mapcells.cell_of(45., 9.)], md, ground)
        n, f = near[0][0], far[0][0]
        s = next(item[0] for item in sky if item[0].evidence.source_id == "target")
        self.assertEqual(n.inference, f.inference)
        self.assertEqual(n.inference, s.inference)
        self.assertEqual((n.facade, n.roof_mat), (s.facade, s.roof_mat))
        self.assertEqual(n.inference.use.value, "residential")
        self.assertEqual(n.inference.facade.value, "brick")

    def test_rebased_frames_keep_identical_inference_and_roof_top(self):
        md = MapData()
        p = Provider(md)
        ground = lambda la, lo: np.zeros(np.broadcast(la, lo).shape)
        plans = []
        with mock.patch.dict(os.environ, {"BNE_BUILDING_GENERATOR": "v2"}):
            for lon in (9., 9.01, 9.19):
                frame = geodesy.EnuFrame(45., lon, 0.)
                x, y, _ = frame.geodetic_to_enu(45., 9., 0.)
                items = b.tile_buildings(frame, x-20, y-20, x+20, y+20, [md.buildings], ground, context_for=p.query)
                plans.append(items[0][0])
        for plan in plans[1:]:
            self.assertEqual(plan.inference, plans[0].inference)
            self.assertEqual((plan.height, plan.facade, plan.roof_mat),
                             (plans[0].height, plans[0].facade, plans[0].roof_mat))

    def test_parts_keep_original_heights_and_identify_inherited_materials(self):
        parent = geographic([[[rect(-20, -20, 40, 40)]]], ["target"],
                            **{"height": [20.], "class": ["office"], "facade_material": ["stone"]})
        parts = geographic([[[rect(-15, -5, 12, 8)]], [[rect(5, -5, 12, 8)]]], ["part1", "part2"],
                           building_id=["target", "target"], height=[12., np.nan], min_height=[3., 0.],
                           num_floors=[3., 2.], roof_shape=["gabled", ""], roof_height=[2., np.nan])
        _, land = scene()
        md = MapData(parent, land)
        ground = lambda la, lo: np.zeros(np.broadcast(la, lo).shape)
        with mock.patch.dict(os.environ, {"BNE_BUILDING_GENERATOR": "v2"}):
            items = b.tile_buildings(FRAME, -25., -25., 25., 25., [parent], ground,
                                    part_layers=[parts], context_for=Provider(md).query)
        plans = {s.evidence.source_id: s for s, _, _ in items}
        one, two = plans["part1"], plans["part2"]
        self.assertEqual(one.evidence.get("height").value, 12.)
        self.assertEqual(one.evidence.get("min_height").value, 3.)
        self.assertEqual(one.inference.height.value, 9.)
        self.assertAlmostEqual(one.min_h + one.height + one.inference.roof_rise, 12.)
        self.assertEqual(one.inference.use.source, "parent:mapped_use")
        self.assertEqual(one.inference.facade.source, "parent:mapped:facade_material")
        self.assertEqual(one.inference.context, two.inference.context)
        self.assertEqual(two.inference.height.status, "inferred")
        self.assertEqual(two.inference.roof.source, "unmapped_part_roof")

    def test_impossible_mapped_height_range_is_not_turned_into_an_extra_slab(self):
        f = geographic([[[rect(-6, -4, 12, 8)]]], ["invalid"], height=[10.], min_height=[12.])
        with mock.patch.dict(os.environ, {"BNE_BUILDING_GENERATOR": "v2"}), \
                self.assertLogs("buildgen.ingest", level="WARNING") as logs:
            items = b.tile_buildings(FRAME, -20., -20., 20., 20., [f], lambda la, lo: np.zeros_like(la))
        self.assertFalse(items)
        self.assertIn("invalid", logs.output[0])


if __name__ == "__main__":
    unittest.main()
