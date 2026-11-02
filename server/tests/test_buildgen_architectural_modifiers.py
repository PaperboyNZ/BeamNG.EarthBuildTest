"""Regional associations, spawn diversity, source precedence and visible geometry."""
from dataclasses import replace
from pathlib import Path
import pickle
import json
import sys
import unittest
from unittest.mock import patch
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import architectural_modifiers as modifiers, regional_architecture, house_styles, freeze_items
from buildgen import regional_roof_details, regional_supports, facades, roof_edges
from buildgen.context import Context
from buildgen.environments import Environment
from buildgen.topology import Footprint
from buildgen.geometry import sky_vertex_count
from buildgen.access import resolve as resolve_access


def fixture(key, **overrides):
    row=modifiers.catalogue()[key];region=row['regions'][0]
    example=regional_architecture.catalogue()[region]['example']
    fp=Footprint(((0.,0.),(12.,0.),(12.,10.),(0.,10.)))
    if key=='stepped_gable':fp=Footprint(((0.,0.),(6.,0.),(6.,11.),(0.,11.)))
    attrs={'class':'house','height':9.,'num_floors':2,'roof_height':3.,
           'roof_shape':'flat' if key in ('roof_terrace','water_tanks') else 'gabled',
           '_footprint':fp,'seed_id':'architecture-'+key,
           '_context':Context(location=(example['lat'],example['lon']),land_use=(('rural',1.),))}
    if key in ('mansard','stepped_gable'):attrs.pop('roof_shape')
    if key=='stilts':attrs.update(height=None,num_floors=1)
    attrs.update(overrides)
    with patch('buildgen.architectural_modifiers.select',return_value=(key,)), \
         patch('buildgen.house_styles.select',return_value=house_styles.HouseStyle('regional',region)), \
         patch('buildgen.environments.resolve',return_value=Environment(region=region)):
        spec=b.plan(np.asarray(fp.outer),attrs)
    spec.gring=np.zeros(len(spec.ring));spec.front=0;spec.door=(0,6.)
    if key in ('front_porch','veranda','stilts'):
        resolve_access([(spec,0.,0.,8.,['door',6.,0.,0.,0.,1.,2.,0.])],[(spec,0.,0.)],ground=lambda xy:np.zeros(len(xy)))
    return spec


class ModifierTests(unittest.TestCase):
    def test_all_25_features_have_nonuniversal_rates_and_registered_regions(self):
        self.assertEqual(len(modifiers.catalogue()),25)
        for key,row in modifiers.catalogue().items():
            self.assertTrue(0.<row['chance']<1.,key)
            self.assertTrue(set(row['regions'])<=set(regional_architecture.catalogue()),key)
            region=row['regions'][0];ctx=Context(land_use=(('rural',1.),))
            draws=[key in modifiers.select(region,ctx,str(i),'residential',2,120.) for i in range(2000)]
            self.assertTrue(any(draws) and not all(draws),key)
            if not row.get('family'):
                self.assertAlmostEqual(sum(draws)/len(draws),row['chance'],delta=.04,msg=key)

    def test_country_and_rural_gates(self):
        self.assertIn('mansard',modifiers.eligible('low_countries',Context(location=(50.85,4.35))))
        self.assertNotIn('mansard',modifiers.eligible('low_countries',Context(location=(52.37,4.90))))
        self.assertIn('half_timber',modifiers.eligible('eu_atlantic',Context(location=(51.5,-.12))))
        self.assertNotIn('half_timber',modifiers.eligible('eu_atlantic',Context(location=(55.95,-3.19))))
        self.assertNotIn('thatch',modifiers.eligible('central_europe',Context()))
        self.assertIn('thatch',modifiers.eligible('central_europe',Context(land_use=(('rural',1.),))))

    def test_every_modifier_compiles_and_serializes_with_correct_sky_count(self):
        for key in modifiers.catalogue():
            with self.subTest(key=key):
                spec=fixture(key);items=freeze_items([(spec,0.,0.)])
                restored=pickle.loads(pickle.dumps(items))
                self.assertEqual(restored[0][0].inference.modifiers,(key,))
                for mesh in (b.build(items),b.build(items,lite=True),b.collision_mesh(items),b._sky_mesh(items)):
                    self.assertIsNotNone(mesh)
                    self.assertTrue(np.isfinite(mesh[0]).all())
                    self.assertTrue(np.isfinite(mesh[1]).all())
                    self.assertLess(mesh[2].max(),len(mesh[0]))
                self.assertEqual(len(b._sky_mesh(items)[0]),sky_vertex_count(items[0][0]))

    def test_required_geometry_is_emitted(self):
        for key in ('stepped_gable','large_chimneys','roof_terrace','water_tanks'):
            self.assertTrue(regional_roof_details.plan(fixture(key)),key)
        for key in ('front_porch','stilts'):
            self.assertTrue(regional_supports.plan(fixture(key)),key)
        for key,assembly in (('bay_windows','regional_bay'),('iron_balconies','regional_iron_balcony'),
                             ('timber_balconies','regional_timber_balcony'),('veranda','regional_veranda')):
            spec=fixture(key);layout=facades.plan(spec,0.,0.)
            self.assertTrue(any(o.assembly==assembly for e in layout.elevations for o in e.openings),key)
        spec=fixture('deep_eaves');deep=roof_edges.treatment(spec)
        spec.inference=replace(spec.inference,modifiers=())
        self.assertGreater(deep.eave,roof_edges.treatment(spec).eave)

    def test_materials_and_mapped_facts_win(self):
        for key,row in modifiers.catalogue().items():
            if row.get('family'):
                spec=fixture(key)
                field=spec.inference.facade if row['family']=='facade' else spec.inference.roof_material
                self.assertEqual(field.value,row['material'])
            spec=fixture(key,height=8.,roof_shape='flat',roof_height=0.,roof_material='metal',facade_material='stone')
            self.assertEqual(spec.roof,'flat')
            self.assertEqual(spec.inference.height.value,8.)
            self.assertEqual(spec.inference.facade.value,'stone')
            self.assertEqual(spec.inference.roof_material.value,'metal')
            self.assertEqual(spec.min_h,0.)

    def test_porch_uses_only_clear_landings_and_stilts_fall_back_without_stairs(self):
        for key in ('front_porch','stilts'):
            spec=fixture(key);spec.access=None
            resolve_access([(spec,0.,0.,.6,['door',6.,0.,0.,0.,1.,2.,0.])],[(spec,0.,0.)],ground=lambda xy:np.zeros(len(xy)))
            self.assertFalse(regional_supports.plan(spec),key)

    def test_stepped_gable_has_broad_continuous_masonry_and_no_front_roof_rake(self):
        spec=fixture('stepped_gable')
        self.assertEqual(roof_edges.treatment(spec).rake,0.)
        rows=[faces for kind,_,faces in regional_roof_details.plan(spec) if kind=='stepped_gable']
        self.assertEqual(len(rows),2)
        for faces in rows:
            heights={round(p[2],5) for face in faces for p in face if p[2]>.01}
            self.assertLessEqual(len(heights),7)
            self.assertTrue(any(len(face)==3 for face in faces))
        caps=[faces for kind,_,faces in regional_roof_details.plan(spec) if kind=='gable_coping']
        self.assertTrue(caps)
        self.assertAlmostEqual(max(p[2] for faces in caps for face in faces for p in face),spec.inference.roof_rise)
        self.assertTrue(all(max(p[2] for face in faces for p in face)-min(p[2] for face in faces for p in face)<.101 for faces in caps))

    def test_roof_fittings_and_projected_bays_are_covered_by_physics_bounds(self):
        for key in ('water_tanks','bay_windows','front_porch','stilts','stepped_gable'):
            spec=fixture(key);items=freeze_items([(spec,0.,0.)])
            collision=b.collision_mesh(items)[0];bounds=b.collider_boxes(items,0.,0.)
            self.assertLessEqual(float(collision[:,2].max()),max(row[5] for row in bounds)+1e-4)
            for axis in (0,1):
                self.assertGreaterEqual(float(collision[:,axis].min()),min(row[axis] for row in bounds)-.001)
                self.assertLessEqual(float(collision[:,axis].max()),max(row[axis+3] for row in bounds)+.001)

    def test_stepped_gables_require_narrow_steep_proportions_without_breaking_height_caps(self):
        for width in (4.,6.,8.,10.,12.):
            for floors in (1,2,3):
                fp=Footprint(((0.,0.),(width,0.),(width,14.),(0.,14.)))
                spec=fixture('stepped_gable',_footprint=fp,height=None,num_floors=floors,roof_height=None)
                rise=spec.inference.roof_rise
                self.assertLessEqual(rise,min(3.,.6*spec.height)+1e-6)
                accepted='stepped_gable' in spec.inference.modifiers
                self.assertEqual(accepted,4.<=width<=8. and rise>=1.65 and 2.*rise/width>=.75)
                self.assertEqual(bool(regional_roof_details.plan(spec)),accepted)
                if not accepted:self.assertGreater(roof_edges.treatment(spec).rake,0.)
        spec=fixture('stepped_gable',roof_height=1.2)
        self.assertNotIn('stepped_gable',spec.inference.modifiers)
        self.assertAlmostEqual(spec.inference.roof_rise,1.2)
        self.assertAlmostEqual(spec.inference.height.value,9.)

    def test_thatch_asset_is_registered_and_bundled(self):
        from PIL import Image
        root=Path(__file__).resolve().parents[2]
        art=root/'mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth'
        row=json.loads((art/'architectural_details.materials.json').read_text())[b.ROOF_THATCH]
        self.assertIn(b.ROOF_THATCH,b.MATERIALS)
        for name in ('baseColorMap','normalMap'):
            p=art/Path(row['Stages'][0][name]).name
            with Image.open(p) as im:self.assertEqual(im.size,(512,512))


if __name__=='__main__':unittest.main()
