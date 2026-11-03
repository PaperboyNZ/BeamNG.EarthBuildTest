"""Source semantics, environment weighting and inferred-house garage regression."""
import json
from pathlib import Path
import sys
import unittest
import tempfile
import subprocess
from dataclasses import replace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import environments, zone_adapters, presets, zones
from buildgen.context import Context
from buildgen.topology import Footprint
from test_buildgen_inference import planned, context
from test_buildgen_facades import road


def feature(**props):
    return dict(type='Feature',properties=props,geometry=dict(type='Polygon',coordinates=[
        [[172.,-43.],[172.01,-43.],[172.01,-42.99],[172.,-42.99],[172.,-43.]]]))


def ctx(environment,use='residential',meaning='statutory',region='nz_temperate'):
    z=zones.Zone('fixture','v1','fixture','R',meaning,(use,),1.,environment=environment,region=region)
    return Context(zones=(z,))


class EnvironmentTests(unittest.TestCase):
    def test_packed_zone_roundtrip_preserves_holes_and_rejects_bad_offsets(self):
        from shapely.geometry import shape
        data=zone_adapters.normalize(dict(type='FeatureCollection',features=[
            feature(DPZoneID=1,Code='RS',LegalStatus='Operative',RemovedByPlanChangeIdentifier=None)]),
            'christchurch','test')
        data['features'][0]['geometry']['coordinates'].append([
            [172.002,-42.998],[172.002,-42.992],[172.008,-42.992],[172.008,-42.998],[172.002,-42.998]])
        root=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'zones.json';packed=Path(tmp)/'zones.npz'
            source.write_text(json.dumps(data))
            result=subprocess.run([sys.executable,str(root/'tools/compile_building_zones.py'),str(source),str(packed)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(zones.load(source)[1][0][0].wkb,zones.load(packed)[1][0][0].wkb)
            self.assertEqual(zones.load(source)[1][0][1],zones.load(packed)[1][0][1])
            with np.load(packed,allow_pickle=False) as f:arrays={k:f[k] for k in f.files}
            arrays['offsets'][0]=1
            np.savez_compressed(packed,**arrays)
            with self.assertRaises(ValueError):zones.load(packed)

    def test_projected_zone_cache_is_bounded_and_revision_specific(self):
        import geodesy
        from shapely.geometry import box
        frame=geodesy.EnuFrame(-43.,172.,0.)
        polygon=box(172.,-43.,172.01,-42.99)
        first=zones._projected(frame,'v1',0,polygon)
        self.assertIs(zones._projected(frame,'v1',0,polygon),first)
        second=zones._projected(frame,'v2',0,box(172.,-43.,172.02,-42.99))
        self.assertGreater(second.area,first.area*1.9)
        for index in range(100):zones._projected(frame,'v2',index,polygon)
        _,cache,count=frame._building_zones
        self.assertLessEqual(len(cache),64)
        self.assertLessEqual(count[0],zones.PROJECTED_COORDINATE_BUDGET)

    def test_ccc_removed_operative_and_proposed_are_not_current(self):
        data=dict(type='FeatureCollection',features=[
            feature(DPZoneID=1,Code='RS',LegalStatus='Operative',RemovedByPlanChangeIdentifier=None),
            feature(DPZoneID=2,Code='RS',LegalStatus='Operative',RemovedByPlanChangeIdentifier='PC14'),
            feature(DPZoneID=3,Code='RS',LegalStatus='Proposed')])
        out=zone_adapters.normalize(data,'christchurch','test')
        self.assertEqual(len(out['features']),1)
        self.assertEqual(out['excluded_nonoperative'],2)
        p=out['features'][0]['properties']
        self.assertEqual((p['meaning'],p['environment']),('statutory','low_density_residential'))
        self.assertEqual(p['raw_attributes']['DPZoneID'],1)

    def test_unmapped_code_fails_and_pluto_mixed_vacant_stay_distinct(self):
        with self.assertRaises(ValueError):
            zone_adapters.normalize(dict(type='FeatureCollection',features=[feature(BBL=1,LandUse=99)]),'nyc_pluto','v1')
        data=dict(type='FeatureCollection',features=[feature(BBL=1,LandUse=4),feature(BBL=2,LandUse=11)])
        a,b_=zone_adapters.normalize(data,'nyc_pluto','v1')['features']
        self.assertEqual(a['properties']['uses'],['mixed'])
        self.assertEqual(b_['properties']['uses'],['unknown'])
        self.assertEqual(b_['properties']['environment'],'vacant')

    def test_environment_does_not_invent_use_height_or_special_class(self):
        z=ctx('high_density_residential')
        self.assertEqual(planned(ctx=z).inference.use.value,'unknown')
        actual=planned({'class':'house','height':6.,'num_floors':1},z)
        self.assertEqual(actual.inference.height.value,6.)
        self.assertEqual(actual.inference.selection.preset.id,'detached_house')
        school=planned({'class':'residential'},ctx('education','civic'))
        self.assertNotEqual(school.inference.selection.preset.id,'school')

    def test_environment_changes_compatible_generic_pool(self):
        specs=[planned({'class':'residential'},ctx(e)) for e in ('low_density_residential','medium_density_residential')]
        pools=[{s.inference.selection.preset.id,*s.inference.selection.alternatives} for s in specs]
        self.assertIn('suburban_lowrise_home',pools[0])
        self.assertNotIn('suburban_lowrise_home',pools[1])
        self.assertIn('compact_lowrise_home',pools[1])

    def test_regional_priors_never_override_mapped_materials(self):
        s=planned({'class':'house','roof_material':'slate','facade_material':'stone'},ctx('low_density_residential'))
        self.assertEqual(s.inference.roof_material.value,'slate')
        self.assertEqual(s.inference.facade.value,'stone')
        default=planned({'class':'house'},ctx('low_density_residential')).inference
        self.assertIn('nz_temperate',default.facade.source)
        unknown=environments.Environment('low_density_residential','unregistered_region')
        self.assertEqual(environments.material_prior(unknown,'residential','roof','id','slate'),'slate')

    def test_overlapping_regions_do_not_assign_arbitrary_local_style(self):
        a=ctx('low_density_residential').zones[0]
        b_=replace(a,source_id='other',region='us_northeast')
        e=environments.resolve(Context(zones=(a,b_)),'residential')
        self.assertEqual(e.region,'')

    def test_inferred_detached_home_retains_garage_eligibility(self):
        neighbourhood=context()
        neighbourhood=replace(neighbourhood,neighbours=tuple(replace(n,distance_m=20.+i*10.)
                              for i,n in enumerate(neighbourhood.neighbours)))
        spec=planned(ctx=neighbourhood)
        self.assertEqual(spec.inference.selection.preset.id,'residential_lowrise')
        self.assertEqual(spec.inference.morphology.value,'detached_lowrise')
        b.doors([(spec,0.,0.)],road(),0.,0.)
        self.assertIsNotNone(spec.garage_opening)
        from buildgen.facades import plan
        self.assertTrue(any(op.kind=='garage' for e in plan(spec,0.,0.).elevations for op in e.openings))

    def test_narrow_frontage_fits_single_garage_without_entry_overlap(self):
        fp=Footprint(((0.,0.),(7.,0.),(7.,12.),(0.,12.)))
        spec=planned({'class':'house','roof_shape':'flat','height':3.},fp=fp)
        b.doors([(spec,0.,0.)],road(),0.,0.)
        self.assertIsNotNone(spec.garage_opening)
        self.assertEqual(spec.garage_opening[2],2.8)
        self.assertGreater(abs(spec.door[1]-spec.garage_opening[1]),spec.garage_opening[2]/2+.5)
        compact=planned({'class':'apartments','height':6.,'num_floors':2},fp=fp)
        b.doors([(compact,0.,0.)],road(),0.,0.)
        self.assertIsNone(compact.garage_opening)

    def test_small_mapped_garage_gets_shutter_without_overlaid_pedestrian_door(self):
        from buildgen.facades import plan
        fp=Footprint(((0.,0.),(3.6,0.),(3.6,6.),(0.,6.)))
        spec=planned({'class':'garage','height':2.8,'num_floors':1,'roof_shape':'flat'},fp=fp)
        props=b.doors([(spec,0.,0.)],road(),0.,0.)
        self.assertIsNotNone(spec.garage_opening)
        self.assertEqual(props,[])
        opening=[op for e in plan(spec,0.,0.).elevations for op in e.openings]
        self.assertEqual([op.kind for op in opening],['garage'])


if __name__=='__main__':unittest.main()
