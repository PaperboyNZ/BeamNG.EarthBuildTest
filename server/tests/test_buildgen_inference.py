"""Evidence conflicts, conservative fallback and renderer agreement for v2."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import pickle
import sys
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import BuildingPlan
from buildgen.context import Context, ContextManifest, Neighbour
from buildgen.evidence import normalise_attributes
from buildgen.topology import Footprint


FP = Footprint(((0., 0.), (12., 0.), (12., 8.), (0., 8.)))
MANIFEST = ContextManifest("test-observed-v1", "14/1/1", (("source", "v1"),), "digest")


def context(classes=("house",) * 3, **attrs):
    ns = tuple(Neighbour(f"N{i}", 20. + i * 30., 100., normalise_attributes(dict(attrs, **{"class": cls})))
               for i, cls in enumerate(classes))
    return Context(MANIFEST, ns)


def planned(attrs=None, ctx=None, fp=FP):
    at = dict(attrs or {}, seed_id="B1", _footprint=fp, _context=ctx)
    return b.plan(np.asarray(fp.outer), at)


class InferenceTest(unittest.TestCase):
    def test_area_alone_never_establishes_industrial_use(self):
        fp = Footprint(((0, 0), (100, 0), (100, 100), (0, 100)))
        unknown = planned(fp=fp).inference
        self.assertEqual(unknown.use.value, "unknown")
        commercial = planned({"class": "commercial"}, fp=fp).inference
        self.assertEqual(commercial.use.value, "commercial")
        self.assertEqual(commercial.use.status, "observed")
        self.assertEqual(commercial.facade.value, "render")

    def test_observed_use_blocks_conflicting_neighbourhood(self):
        ctx = replace(context(("industrial",) * 4), land_use=(("industrial", 1.),))
        result = planned({"class": "house"}, ctx).inference
        self.assertEqual(result.use.value, "residential")
        self.assertIn("mapped_use_overrides_neighbourhood", result.diagnostics)
        self.assertEqual(result.candidates[0].use, "industrial")

    def test_conflicting_tags_and_equal_land_use_remain_unknown(self):
        result = planned({"class": "house", "subtype": "industrial"}, context()).inference
        self.assertEqual((result.use.value, result.use.status), ("unknown", "conflict"))
        ctx = Context(MANIFEST, land_use=(("industrial", 1.), ("commercial", 1.)))
        self.assertEqual(planned(ctx=ctx).inference.use.value, "unknown")

    def test_neighbour_consensus_requires_multiple_observations(self):
        self.assertEqual(planned(ctx=context(("house",) * 2)).inference.use.value, "unknown")
        result = planned(ctx=context()).inference
        self.assertEqual((result.use.value, result.use.status), ("residential", "inferred"))
        self.assertEqual(result.height.status, "fallback")

    def test_mapped_materials_roof_and_colours_override_local_and_climate(self):
        ctx = replace(context(facade_material="brick", roof_material="tile", roof_shape="gabled"), climate=22)
        attrs = {"class": "house", "facade_material": "wood", "roof_shape": "flat", "roof_material": "metal",
                 "facade_color": "#123456", "roof_color": "#cc6633"}
        spec = planned(attrs, ctx)
        result = spec.inference
        self.assertEqual((result.facade.value, result.roof.value, result.roof_material.value), ("wood", "flat", "metal"))
        self.assertEqual(result.architecture.value, "timber_punched")
        self.assertEqual(spec.facade.split("|")[0], b.SIDING)
        self.assertEqual(spec.roof_mat.split("|")[0], b.ROOF_METAL)
        np.testing.assert_allclose(b.LOOKS[spec.facade][1], np.array([0x12, 0x34, 0x56]) / 255.)

    def test_observed_local_architecture_overrides_climate_prior(self):
        ctx = replace(context(facade_material="stone", roof_shape="hipped", roof_material="tile"), climate=4)
        result = planned({"class": "house"}, ctx).inference
        self.assertEqual((result.facade.value, result.roof.value, result.roof_material.value), ("stone", "hipped", "tile"))
        self.assertEqual(result.facade.support, ("N0", "N1", "N2"))
        self.assertEqual(result.architecture.value, "masonry_punched")

    def test_materials_only_borrow_from_comparable_observed_buildings(self):
        ctx = context(("industrial",) * 3, facade_material="metal", height=25.)
        result = planned({"class": "house"}, ctx).inference
        self.assertEqual(result.facade.status, "fallback")
        self.assertNotEqual(result.facade.value, "metal")
        self.assertEqual(result.height.status, "fallback")
        ctx = context(facade_material="brick", height=12.)
        ctx = replace(ctx, neighbours=tuple(replace(n, area_m2=10000) for n in ctx.neighbours))
        self.assertEqual(planned({"class": "house"}, ctx).inference.height.status, "fallback")

    def test_neighbour_height_uses_median_and_never_becomes_a_source_observation(self):
        ctx = context(height=10., min_height=2., facade_material="brick")
        extra = Neighbour("outlier", 30., 100., normalise_attributes({"class": "house", "height": 400.}))
        spec = planned({"class": "house", "roof_shape": "flat"}, replace(ctx, neighbours=ctx.neighbours + (extra,)))
        self.assertEqual(spec.height, 8.)
        self.assertEqual(spec.inference.height.source, "observed_neighbour_heights")
        self.assertEqual(spec.evidence.get("height").status, "unknown")

    def test_measured_total_height_and_roof_height_match_mesh(self):
        spec = planned({"class": "house", "height": 10., "num_floors": 2, "roof_height": 3., "roof_shape": "gabled"})
        self.assertAlmostEqual(spec.height, 7.)
        self.assertAlmostEqual(spec.floor_h, 3.5)
        self.assertAlmostEqual(spec.inference.height.value, 10.)
        mesh = b.build([(spec, 0., 0.)])
        collision = b.collision_mesh([(spec, 0., 0.)])
        self.assertAlmostEqual(float(mesh[0][:, 2].max()), 10., places=5)
        self.assertAlmostEqual(float(collision[0][:, 2].max()), 10., places=5)

    def test_impossible_dimensions_are_diagnosed_without_expanding_measured_top(self):
        spec = planned({"class": "house", "height": 5., "num_floors": 4, "roof_height": 6., "roof_shape": "gabled"})
        self.assertEqual(spec.roof, "flat")
        self.assertEqual(spec.height, 5.)
        self.assertIn("roof_height_conflicts_with_envelope", spec.diagnostics)
        self.assertIn("height_storey_conflict", spec.diagnostics)
        self.assertEqual(spec.floors, 2)
        self.assertEqual(spec.evidence.get("num_floors").value, 4)

    def test_roof_height_with_only_mapped_floors_adds_to_the_inferred_body(self):
        spec = planned({"class": "house", "num_floors": 1, "roof_height": 4., "roof_shape": "gabled"})
        self.assertEqual((spec.height, spec.inference.height.value), (3., 7.))
        self.assertEqual(spec.inference.roof_rise, 4.)

    def test_short_observed_neighbour_height_cannot_make_the_body_negative(self):
        spec = planned({"class": "house", "roof_shape": "gabled"}, context(height=2.3))
        self.assertGreater(spec.height, 0.)
        self.assertAlmostEqual(spec.inference.height.value, 2.3)
        self.assertAlmostEqual(spec.height + spec.inference.roof_rise, 2.3)

    def test_unsupported_roof_and_complex_outline_keep_evidence_and_total_height(self):
        fp = Footprint(((0, 0), (20, 0), (20, 5), (5, 5), (5, 20), (0, 20)))
        spec = planned({"height": 12., "roof_shape": "gabled"}, fp=fp)
        self.assertEqual(spec.roof, "gabled")
        self.assertAlmostEqual(spec.height + spec.inference.roof_rise, 12.)
        self.assertEqual(spec.evidence.get("roof_shape").value, "gabled")
        self.assertIn("clipped_pitched_roof_envelope", spec.diagnostics)
        spec = planned({"roof_shape": "dome", "height": 12.})
        self.assertIn("unsupported_mapped_roof_flat_fallback", spec.diagnostics)

    def test_invalid_dimensions_are_explicit_and_generated_results_stay_finite(self):
        spec = planned({"height": float("inf"), "num_floors": -3, "roof_height": -2})
        self.assertTrue(np.isfinite(spec.height) and spec.height > 0)
        self.assertTrue({"invalid_height", "invalid_num_floors", "invalid_roof_height"} <= set(spec.diagnostics))

    def test_tile_density_country_boxes_and_source_order_do_not_change_architecture(self):
        ctx = context(height=9., facade_material="brick", roof_shape="gabled")
        at = {"seed_id": "A", "_footprint": FP, "_context": ctx, "class": "house"}
        with mock.patch.object(b, "region_style", side_effect=AssertionError("legacy geography used")):
            a = b.plan(np.asarray(FP.outer), at, neighbours=0, lat=1, lon=1, town=True)
            other = dict(at, _context=replace(ctx, neighbours=tuple(reversed(ctx.neighbours))))
            z = b.plan(np.asarray(FP.outer), other, neighbours=8, lat=70, lon=50, dense=True, west_town=True, alpine=True)
        self.assertEqual(a.inference, z.inference)
        self.assertEqual(a.facade, z.facade)
        self.assertEqual(a.roof_mat, z.roof_mat)

    def test_frozen_inference_survives_worker_boundary_and_mapped_colours_render(self):
        spec = planned({"facade_material": "brick", "facade_color": "#123456"}, context())
        expected = b._Looks(spec.seed)[spec.facade]
        key = spec.facade
        plan = pickle.loads(pickle.dumps(BuildingPlan.from_spec(spec)))
        with mock.patch.dict(b.LOOKS):
            del b.LOOKS[key]
            actual = b._Looks(plan.seed)[plan.facade]
            self.assertEqual(actual, expected)
        self.assertEqual(plan.inference, spec.inference)
        with self.assertRaises(FrozenInstanceError):
            plan.inference.use.value = "industrial"
        self.assertEqual(plan.inference.context, MANIFEST)


if __name__ == "__main__":
    unittest.main()
