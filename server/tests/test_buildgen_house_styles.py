"""House mixtures retain geography, evidence, physical envelopes and stable identity."""
from collections import Counter
from dataclasses import replace
from pathlib import Path
import pickle
import sys
import unittest
from unittest.mock import patch
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import house_styles as styles, regional_architecture as regional, freeze_items
from buildgen import facades, materials, roof_colours
from buildgen.context import Context
from buildgen.topology import Footprint
import codefiles

FP=Footprint(((0.,0.),(12.,0.),(12.,9.),(0.,9.)))


def seed_for(variant, alternate=None):
    for i in range(10000):
        sid='house-mix-test-'+str(i)
        choice=styles.select('nz_temperate',sid,'residential','house',2,8.,108.)
        if choice.variant==variant and (alternate is None or choice.alternate==alternate):
            return sid
    raise AssertionError('missing style')


def building(sid, fp=FP, context=None, **attrs):
    values=dict(seed_id=sid,_footprint=fp,_context=context or Context(location=(-36.9141,174.90925)),
                **{'class':'house','height':8.,'num_floors':2})
    values.update(attrs)
    spec=b.plan(np.asarray(fp.outer),values)
    spec.gring=np.zeros(len(fp.outer));spec.front=0;spec.door=(0,2.3)
    return spec


class HouseStyleTests(unittest.TestCase):
    def test_ratios_and_foreign_profiles_across_all_64_regions(self):
        donors=set()
        for region in regional.catalogue():
            counts=Counter()
            for i in range(3000):
                choice=styles.select(region,f'{region}-house-{i}','residential','house',2,8.,108.)
                counts[choice.variant]+=1
                if choice.variant=='global':
                    self.assertNotEqual(choice.profile,region)
                    self.assertIsNotNone(regional.profile(choice.profile))
                    donors.add(choice.profile)
            self.assertAlmostEqual(counts['regional']/3000,.70,delta=.03,msg=region)
            self.assertAlmostEqual(counts['contemporary']/3000,.20,delta=.03,msg=region)
            self.assertAlmostEqual(counts['global']/3000,.10,delta=.02,msg=region)
        self.assertEqual(donors,set(regional.catalogue()))

    def test_five_contemporary_families_compile_without_changing_geography(self):
        self.assertEqual(len(styles.CONTEMPORARY),5)
        signatures=set()
        for alternate in styles.CONTEMPORARY:
            spec=building(seed_for('contemporary',alternate))
            self.assertEqual(spec.inference.selection.environment.region,'nz_temperate')
            self.assertEqual(spec.inference.house_style.alternate,alternate)
            frozen=freeze_items([(spec,0.,0.)])
            for mesh in (b.build(frozen),b.build(frozen,lite=True),b.collision_mesh(frozen)):
                self.assertTrue(np.isfinite(mesh[0]).all())
                self.assertLess(mesh[2].max(),len(mesh[0]))
            signatures.add((spec.facade,repr(frozen[0][0].facades)))
        self.assertEqual(len(signatures),5)

    def test_mapped_and_sampled_evidence_wins_in_every_variant(self):
        measured=roof_colours.Sample((.25,.34,.43),'fixture','geometry','image',.5)
        for variant in ('regional','contemporary','global'):
            sid=seed_for(variant)
            attrs=dict(roof_shape='hipped',roof_material='metal',facade_material='stone',
                       facade_color='#778899',roof_color='#aa4411',roof_height=1.5)
            spec=building(sid,**attrs)
            self.assertEqual(spec.inference.selection.environment.region,'nz_temperate')
            self.assertEqual(spec.roof,'hipped')
            self.assertEqual(spec.height,6.5)
            self.assertEqual(b.LOOKS[spec.facade][1],b.parse_color('#778899'))
            self.assertEqual(b.LOOKS[spec.roof_mat][1],b.parse_color('#aa4411'))
            sampled=building(sid,context=Context(location=(-36.9141,174.90925),roof_colour=measured),**attrs)
            self.assertEqual(b.LOOKS[sampled.roof_mat][1],measured.rgb)
            self.assertEqual(sampled.inference.roof_colour.source,'imagery:fixture')

    def test_style_survives_translation_pickle_and_near_lite(self):
        shifted=Footprint(tuple((x+1000,y-300) for x,y in FP.outer))
        for variant in ('regional','contemporary','global'):
            sid=seed_for(variant)
            a,c=building(sid),building(sid,shifted)
            self.assertEqual(a.inference.house_style,c.inference.house_style)
            self.assertEqual((a.facade,a.roof,a.pitch,a.roof_mat),(c.facade,c.roof,c.pitch,c.roof_mat))
            frozen=freeze_items([(a,0.,0.)]);restored=pickle.loads(pickle.dumps(frozen))
            self.assertEqual(frozen[0][0].inference.house_style,restored[0][0].inference.house_style)
            for lite in (False,True):
                left,right=b.build(frozen,lite=lite),b.build(restored,lite=lite)
                for field in (0,1,2,3,5):np.testing.assert_array_equal(left[field],right[field])

    def test_mixture_does_not_change_mapped_envelope_or_collision(self):
        sid='same-physical-building';meshes=[]
        choices=[styles.HouseStyle('regional','nz_temperate'),
                 styles.HouseStyle('contemporary','',alternate='mixed_infill'),
                 styles.HouseStyle('global','italy_regional')]
        for choice in choices:
            with patch.object(styles,'select',return_value=choice):
                spec=building(sid,roof_shape='hipped',roof_height=1.5)
            np.testing.assert_array_equal(spec.ring,FP.outer)
            self.assertEqual(spec.height,6.5)
            meshes.append(b.collision_mesh(freeze_items([(spec,0.,0.)])))
        for mesh in meshes[1:]:
            for field in (0,2):np.testing.assert_array_equal(mesh[field],meshes[0][field])

    def test_nonhouses_unknown_geography_and_parts_are_not_randomized(self):
        sid=seed_for('global')
        for kw in (dict(cls='office',use='commercial'),dict(cls='apartments'),
                   dict(floors=6),dict(height=30.),dict(area=1000.),dict(part=True),
                   dict(region=''),dict(identity=None)):
            args=dict(region='nz_temperate',identity=sid,use='residential',cls='house',floors=2,height=8.,area=108.)
            args.update(kw)
            self.assertEqual(styles.select(**args).variant,'unmixed')

    def test_broader_roof_and_wall_colours_are_actual_compiler_output(self):
        roofs=set();walls=set();families=set()
        for i in range(160):
            spec=building('colour-mix-'+str(i))
            roofs.add(b.LOOKS[spec.roof_mat][1]);walls.add(b.LOOKS[spec.facade][1])
            families.add(spec.inference.facade.value)
        self.assertGreaterEqual(len(roofs),15)
        self.assertGreaterEqual(len(walls),10)
        self.assertTrue({'brick','wood','render'}<=families)
        self.assertTrue(any(r>g*1.4 and r>bl*1.4 for r,g,bl in roofs),'red roofs')
        self.assertTrue(any(g>r*1.15 and g>bl*1.1 for r,g,bl in roofs),'green roofs')

    def test_new_style_rules_participate_in_cache_identity(self):
        self.assertIn('buildgen/house_styles.py',codefiles.source_files(Path(__file__).resolve().parents[1]))


if __name__=='__main__':unittest.main()
