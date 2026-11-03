"""Terrain-aware entrances, shared collision and batched terrain sampling."""
from dataclasses import FrozenInstanceError
from pathlib import Path
import pickle
import sys
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import freeze_items
from buildgen import access, facades
from test_buildgen_facades import building, road


class AccessTest(unittest.TestCase):
    def make(self, height, ground=None, setback=12.):
        spec = building()
        spec.gring = np.array([0., 0., height, height])
        rows = b.doors([(spec, 0., height)], road(-setback), 0., 0., [],
                       ground=ground or (lambda xy: np.zeros(len(xy))))
        return spec, next(r for r in rows if r[0] == "door")

    def test_high_rear_ground_does_not_float_doors_or_garages(self):
        spec, row = self.make(3.)
        self.assertAlmostEqual(row[3], access.SURFACE_LIFT)
        self.assertAlmostEqual(spec.access.garage_z, access.SURFACE_LIFT)
        self.assertIn("entrance_lowered_to_local_ground", spec.access.diagnostics)
        layout = facades.plan(spec, 0., 3.)
        openings = [op for e in layout.elevations for op in e.openings]
        self.assertAlmostEqual(next(op.bottom for op in openings if op.kind == "door") + 3., row[3])
        self.assertAlmostEqual(next(op.bottom for op in openings if op.kind == "garage") + 3., access.SURFACE_LIFT)

    def test_moderate_slope_gets_usable_steps_to_the_floor(self):
        spec, row = self.make(.9)
        steps = [s for s in spec.access.solids if s.kind == "step"]
        self.assertGreater(len(steps), 1)
        self.assertEqual(row[3], .9)
        levels = [s.top[0][2] for s in steps] + [access.SURFACE_LIFT]
        self.assertTrue(all(0 < a-c <= access.MAX_RISE for a, c in zip(levels, levels[1:])))
        self.assertEqual(steps[0].top[0][2], spec.access.door_z)
        self.assertLessEqual(-steps[-1].top[1][1], 12.-3.-.4)

    def test_short_setback_lowers_threshold_instead_of_stairs_in_road(self):
        spec, row = self.make(1.2, setback=4.)
        self.assertFalse(any(s.kind == "step" for s in spec.access.solids))
        self.assertAlmostEqual(row[3], access.SURFACE_LIFT)

    def test_apron_meets_horizontal_garage_and_sloping_ground(self):
        terrain = lambda xy: .12*xy[:, 0] + .07*xy[:, 1]
        spec, _ = self.make(3., terrain)
        apron = next(s for s in spec.access.solids if s.kind == "apron")
        p = np.asarray(apron.top)
        self.assertEqual(p[0, 2], spec.access.garage_z)
        self.assertEqual(p[3, 2], spec.access.garage_z)
        np.testing.assert_allclose(p[[1, 2], 2], terrain(p[[1, 2], :2])+access.SURFACE_LIFT)

    def test_visual_and_collision_have_same_access_surfaces_and_occupancy(self):
        spec, _ = self.make(.9)
        plan = freeze_items([(spec, 0., .9)])[0][0]
        meshes = []
        for collision in (False, True):
            mesh = b.Mesh(); access.draw(mesh, plan, collision)
            meshes.append(mesh.arrays())
        np.testing.assert_array_equal(meshes[0][0][:len(meshes[1][0])], meshes[1][0])
        np.testing.assert_array_equal(meshes[0][2][:len(meshes[1][2])], meshes[1][2])
        self.assertEqual(len(meshes[0][2])-len(meshes[1][2]),2*len(plan.access.landscape))
        p, _, t, _, _ = meshes[0]
        self.assertTrue(np.isfinite(p).all())
        self.assertTrue(np.all(np.linalg.norm(np.cross(p[t[:, 1]]-p[t[:, 0]], p[t[:, 2]]-p[t[:, 0]]), axis=1) > 1e-8))
        boxes = b.collider_boxes([(plan, 0., .9)], 100., 200.)
        self.assertEqual(len(boxes), 1+len(plan.access.solids))
        self.assertTrue(any(box[1] < 200. for box in boxes))
        self.assertEqual(pickle.loads(pickle.dumps(plan)).access, plan.access)
        with self.assertRaises(FrozenInstanceError):
            plan.access.door_z = 99.

    def test_projection_does_not_enter_neighbour_or_courtyard_wall(self):
        one = building()
        other = building(width=12., depth=2.)
        other.ring[:, 1] -= 2.
        from buildgen.topology import Footprint
        other.footprint = Footprint(tuple(map(tuple, other.ring)))
        b.doors([(one, 0., .9), (other, 0., 0.)], road(), 0., 0., ground=lambda xy: np.zeros(len(xy)))
        self.assertFalse(one.access.solids)
        self.assertIn("entrance_projection_omitted_clearance", one.access.diagnostics)

    def test_terrain_is_batched_and_repeated_prop_calls_keep_resolved_access(self):
        items = [(building(seed_id=f"house-{i}"), 0., .9) for i in range(30)]
        sampler = mock.Mock(side_effect=lambda xy: np.zeros(len(xy)))
        b.doors(items, road(), 0., 0., ground=sampler)
        self.assertEqual(sampler.call_count, 1)
        plans = [s.access for s, _, _ in items]
        rows = b.doors(items, road(), 0., 0.)
        self.assertEqual([s.access for s, _, _ in items], plans)
        self.assertTrue(all(abs(r[3] - plans[0].door_z) < .01 for r in rows if r[0] == "door"))

    def test_corner_road_clearance_and_anchor_coordinates_are_respected(self):
        spec = building()
        # Resolve the frontage first, then add a crossing lane beside the door.
        b.doors([(spec, 0., .9)], road(), 0., 0.)
        along = spec.door[1]
        lines = road() + [(np.array([(along, -50.), (along, -.1)]), .6, "service", False)]
        origin = np.array([100., 200.])
        shifted = [(p+origin, *rest) for p, *rest in lines]
        sampler = mock.Mock(side_effect=lambda xy: np.zeros(len(xy)))
        b.doors([(spec, 0., .9)], shifted, *origin, ground=sampler)
        self.assertGreater(float(sampler.call_args.args[0][:, 0].min()), 100.)
        self.assertFalse(any(s.kind in ("step", "threshold") for s in spec.access.solids))


if __name__ == "__main__":
    unittest.main()
