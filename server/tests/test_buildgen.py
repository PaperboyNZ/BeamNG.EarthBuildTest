"""The v2 compatibility boundary: immutable plans and unchanged legacy geometry."""
import dataclasses
import pickle
import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as bld
from buildgen import BuildingPlan, freeze_items
from buildgen.evidence import normalise_attributes


def rectangle(w=12, d=8):
    return np.array([(0, 0), (w, 0), (w, d), (0, d)], np.float64)


class PlanTest(unittest.TestCase):
    def test_snapshot_is_detached_and_deeply_immutable(self):
        spec = bld.plan(rectangle(), {"class": "house", "seed_id": "house-1"})
        spec.gring = np.array([1., 2., 2., 1.])
        spec.door = [0, 4.0]
        spec.ship = {"parts": [rectangle()], "profile": {"heights": [1.0, 2.0]}}
        plan = BuildingPlan.from_spec(spec)
        spec.ring[0, 0] = 99
        spec.gring[0] = 99
        spec.door[1] = 99
        spec.ship["parts"][0][0, 0] = 99
        spec.ship["profile"]["heights"][0] = 99
        self.assertEqual(plan.ring[0, 0], 0)
        self.assertEqual(plan.gring[0], 1)
        self.assertEqual(plan.door, (0, 4.0))
        self.assertEqual(plan.ship["parts"][0][0, 0], 0)
        self.assertEqual(plan.ship["profile"]["heights"], (1., 2.))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            plan.roof = "flat"
        with self.assertRaises(ValueError):
            plan.ring[0, 0] = 1
        with self.assertRaises(ValueError):
            plan.ring.setflags(write=True)
        with self.assertRaises(TypeError):
            plan.ship["profile"] = None
        self.assertIs(BuildingPlan.from_spec(plan), plan)

    def test_pickling_keeps_worker_plans_immutable(self):
        spec = bld.plan(rectangle(), {"ship": True, "name": "generic liner"})
        plan = pickle.loads(pickle.dumps(BuildingPlan.from_spec(spec)))
        np.testing.assert_array_equal(plan.ring, spec.ring)
        self.assertEqual(plan.ship["profile"]["navy"], spec.ship["profile"]["navy"])
        with self.assertRaises(ValueError):
            plan.ring.setflags(write=True)
        with self.assertRaises(TypeError):
            plan.ship["parts"] = []

    def test_invalid_geometry_rejected_at_boundary(self):
        for ring in (np.zeros((2, 2)), np.zeros((4, 3)), [[0, 0], [1, 0], [0, np.nan]]):
            with self.subTest(ring=ring), self.assertRaises(ValueError):
                BuildingPlan(ring=ring)
        with self.assertRaises(ValueError):
            BuildingPlan(ring=rectangle(), gring=[1, 2])

    def test_contract_covers_every_legacy_field(self):
        self.assertEqual(set(bld.Spec.__slots__), {f.name for f in dataclasses.fields(BuildingPlan)})


class EvidenceTest(unittest.TestCase):
    def test_unknown_invalid_and_zero_are_distinct(self):
        evidence = normalise_attributes({"height": np.nan, "min_height": 0, "roof_height": -2,
                                         "roof_direction": 0, "num_floors": "many"})
        self.assertEqual(evidence.get("height").status, "unknown")
        self.assertEqual(evidence.get("min_height").value, 0)
        self.assertEqual(evidence.get("min_height").status, "observed")
        self.assertEqual(evidence.get("roof_direction").status, "observed")
        self.assertEqual(evidence.get("roof_height").status, "invalid")
        self.assertEqual(evidence.get("roof_height").value, -2)
        self.assertEqual(evidence.get("num_floors").status, "invalid")
        self.assertEqual(evidence.get("num_floors").value, "many")
        self.assertEqual(evidence.get("facade_material").status, "unknown")

    def test_source_specific_height_and_mapped_roof_direction_survive(self):
        attrs = {"seed_id": "building-A", "src_dataset": "OpenStreetMap", "src_record": "way/1",
                 "height_src": "survey", "height": 12, "roof_direction": 230,
                 "roof_orientation": "along", "roof_shape": "gabled", "class": "house"}
        plan = BuildingPlan.from_spec(bld.plan(rectangle(), attrs))
        self.assertEqual(plan.evidence.source_id, "building-A")
        self.assertEqual(plan.evidence.source_record, "way/1")
        self.assertEqual(plan.evidence.get("height").source, "survey")
        self.assertEqual(plan.evidence.get("class").source, "OpenStreetMap")
        self.assertEqual(plan.evidence.get("roof_direction").value, 230)
        self.assertEqual(plan.evidence.get("roof_orientation").value, "along")
        attrs["height"] = 100
        self.assertEqual(plan.evidence.get("height").value, 12)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            plan.evidence.get("height").value = 15

    def test_estimated_height_is_not_promoted_to_an_observation(self):
        plan = BuildingPlan.from_spec(bld.plan(rectangle(), {"class": "house"}))
        self.assertGreater(plan.height, 0)
        self.assertEqual(plan.evidence.get("height").status, "unknown")

    def test_invalid_infinities_and_directions_are_not_observed(self):
        for value in (float("inf"), -30, 720):
            with self.subTest(value=value):
                self.assertEqual(normalise_attributes({"roof_direction": value}).get("roof_direction").status,
                                 "invalid")


class CompilerTest(unittest.TestCase):
    def assertMeshEqual(self, a, b):
        if a is None or b is None:
            self.assertIs(a, b)
            return
        self.assertEqual(len(a), len(b))
        for left, right in zip(a, b):
            np.testing.assert_array_equal(left, right)

    def test_specialised_and_ordinary_geometry_is_preserved(self):
        examples = [
            {"class": "house", "roof_shape": "gabled"},
            {"class": "house", "roof_shape": "hipped", "facade_material": "wood"},
            {"class": "terrace", "height": 9},
            {"class": "retail", "height": 9},
            {"class": "industrial", "height": 12},
            {"class": "office", "height": 80},
            {"class": "parking", "height": 12, "num_floors": 4},
            {"class": "bridge_structure", "height": 25},
            {"class": "", "ship": True, "name": "generic liner"},
            {"class": "", "pier": True},
        ]
        for attrs in examples:
            with self.subTest(attrs=attrs):
                spec = bld.plan(rectangle(40, 20), dict(attrs, seed_id="stable-id"))
                spec.gring = np.array([1., 1., 2., 2.])
                original = [(spec, 1., 2.)]
                frozen = freeze_items(original)
                for lite in (False, True):
                    self.assertMeshEqual(bld.build(original, lite), bld.build(frozen, lite))
                self.assertMeshEqual(bld.collision_mesh(original), bld.collision_mesh(frozen))

    def test_near_lite_and_collision_share_the_same_snapshot(self):
        spec = bld.plan(rectangle(), {"class": "house", "seed_id": "house-2"})
        compiled = []
        original_build, original_collision = bld.build, bld.collision_mesh

        def build(items, lite=False):
            self.assertIsInstance(items[0][0], BuildingPlan)
            compiled.append(items[0][0])
            return original_build(items, lite)

        def collision(items):
            self.assertIs(compiled[0], items[0][0])
            return original_collision(items)

        with mock.patch.object(bld, "build", side_effect=build), \
                mock.patch.object(bld, "collision_mesh", side_effect=collision):
            got = bld.road_tile(None, 0, 0, None, None, items=[(spec, 0., 0.)])
        self.assertIsNotNone(got)
        self.assertEqual(len(compiled), 2)
        self.assertIs(compiled[0], compiled[1])

    def test_door_resolution_precedes_snapshot(self):
        spec = bld.plan(rectangle(), {"class": "house"})

        def resolve_doors(items, lines, x0, y0):
            items[0][0].door = (0, 3.)
            return []

        with mock.patch.object(bld, "doors", side_effect=resolve_doors), \
                mock.patch.object(bld, "build_parts", wraps=bld.build_parts) as build:
            bld.road_tile(None, 0, 0, None, None, lines=["road"], props=[], items=[(spec, 0., 0.)])
        self.assertEqual(build.call_args.args[0][0][0].door, (0, 3.))

    def test_skyline_does_not_change_later_near_geometry(self):
        ring = np.array([(0, 0), (12, 0), (12, 4), (6, 4), (6, 8), (0, 8)], float)
        spec = bld.plan(ring, {"class": "house", "roof_shape": "gabled"})
        # Use a resolved pitched plan even though the legacy planner falls back
        # to flat on some concave footprints; skyline must not rewrite it.
        spec.roof = "gabled"
        spec.door = (0, 3.)
        spec.stoop = (0, 3.)
        original = [(spec, 0., 0.)]
        before = bld.build(original)
        md = mock.Mock()
        md.has.return_value = True
        md.cell.return_value.layers = {}
        with mock.patch.object(bld, "tile_buildings", return_value=original), \
                mock.patch.object(bld, "far_lamps", return_value=[]):
            picked, _ = bld.sky_items(None, (0, 0, 256, 256), ["cell"], md, None)
        self.assertIsInstance(picked[0][0], BuildingPlan)
        self.assertIsNotNone(bld._sky_mesh(picked))
        self.assertEqual(len(bld._sky_ring(picked[0][0])), 4)
        np.testing.assert_array_equal(spec.ring, ring)
        self.assertEqual(spec.roof, "gabled")
        self.assertEqual(spec.door, (0, 3.))
        self.assertMeshEqual(before, bld.build(original))


if __name__ == "__main__":
    unittest.main()
