"""Bounded low-tier work and roof failures must not abort physical coverage."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
import buildings as b
from buildgen import context, compiler, roofs, quality
from buildgen.topology import Footprint, InvalidFootprint
from test_buildgen_context import MapData, geographic, rect


class LowPlanningTests(unittest.TestCase):
    def test_complete_context_does_not_index_distant_source_cell_geometry(self):
        import mapcells
        f = geographic([[[rect(0.,0.,12.,8.)]], [[rect(30000.,0.,12.,8.)]]],
                       ['target', 'irrelevant'], height=[8.,200.])
        md = MapData(f, MapData().land)
        key = mapcells.cell_of(45.,9.)
        cds = [md.cell(k,context.LAYERS,'demand') for k in context.halo(key)]
        bundle = context._Bundle(key,cds,'bounded-test')
        self.assertEqual([sid for sid,_,_ in bundle.buildings], ['target'])

    def test_low_tiers_never_fetch_neighbourhood_cells(self):
        md = MapData()
        for tier in ('minimum', 'very_low', 'low'):
            with patch.object(md, 'cell', side_effect=AssertionError('halo IO on low tier')):
                got = quality.run(tier, context.Provider(md).query, md.buildings, 0)
            self.assertEqual(got.manifest.profile, 'source-local-low-v1')
            self.assertFalse(got.neighbours)
            self.assertIn('low_quality_neighbourhood_inference_omitted', got.diagnostics)
            self.assertIsNotNone(got.location)

    def test_mapped_top_and_floors_survive_every_low_tier(self):
        fp = Footprint(((0.,0.),(10.,0.),(10.,8.),(0.,8.)))
        attrs = dict(_footprint=fp, seed_id='observed', height=12., num_floors=3,
                     roof_shape='gabled', **{'class':'house'})
        for tier in ('minimum', 'very_low', 'low'):
            with patch('buildgen.roofs._envelope', side_effect=AssertionError('full roof solver')):
                spec = quality.run(tier, b.plan, np.asarray(fp.outer), attrs)
            self.assertEqual(spec.floors, 3)
            self.assertAlmostEqual(spec.height + spec.inference.roof_rise, 12.)
            self.assertEqual(spec.footprint, fp)

    def test_low_complex_roof_keeps_holes_and_mapped_height(self):
        fp = Footprint(((0.,0.),(12.,0.),(12.,10.),(0.,10.)),
                       (((3.,3.),(3.,6.),(6.,6.),(6.,3.)),))
        attrs = dict(_footprint=fp, seed_id='courtyard', height=10., roof_shape='hipped')
        spec = quality.run('minimum', b.plan, np.asarray(fp.outer), attrs)
        self.assertEqual(spec.roof, 'hipped')
        self.assertEqual(spec.inference.roof_solver, 'fast')
        self.assertEqual(spec.footprint, fp)
        self.assertAlmostEqual(spec.height + spec.inference.roof_rise, 10.)

    def test_bad_regional_roof_falls_back_to_valid_standard_envelope(self):
        fp = Footprint(((0.,0.),(12.,0.),(12.,8.),(0.,8.)))
        with patch('buildgen.regional_roofs.envelope', side_effect=InvalidFootprint('bad decorative band')):
            roofs._envelope.cache_clear()
            got = quality.run('full', roofs.envelope, fp, 'hipped', 'flared_hip')
        area = sum(abs((t[1][0]-t[0][0])*(t[2][1]-t[0][1])-
                       (t[1][1]-t[0][1])*(t[2][0]-t[0][0]))*.5 for t in got.triangles)
        self.assertAlmostEqual(area, fp.area)
        self.assertTrue(np.isfinite(np.asarray(got.triangles)).all())

    def test_unrecoverable_roof_is_flattened_during_planning(self):
        fp = Footprint(((0.,0.),(12.,0.),(12.,8.),(0.,8.)))
        attrs = dict(_footprint=fp, seed_id='fallback', height=10., roof_shape='gabled', roof_height=2.)
        with patch.object(roofs, 'envelope', side_effect=InvalidFootprint('bad roof')):
            spec = quality.run('full', b.plan, np.asarray(fp.outer), attrs)
        self.assertEqual(spec.roof, 'flat')
        self.assertEqual(spec.height, 10.)
        self.assertEqual(spec.footprint, fp)
        self.assertTrue(any('roof_geometry_flat_fallback' in s for s in spec.diagnostics))


if __name__ == '__main__':
    unittest.main()
