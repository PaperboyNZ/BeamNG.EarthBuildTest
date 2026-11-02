"""Global routing, evidence precedence, deterministic style and bounded geometry."""
from dataclasses import replace
import json
import math
from pathlib import Path
import pickle
import sys
import unittest
from unittest.mock import patch

import numpy as np
from shapely import STRtree
from shapely.geometry import box, Polygon

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
import codefiles
from buildgen import freeze_items
from buildgen import environments, regional_architecture as architecture, regional_geography as geography, facades
from buildgen.context import Context
from buildgen.topology import Footprint
from buildgen.zones import Zone

FP=Footprint(((0.,0.),(12.,0.),(12.,9.),(0.,9.)))


def building(theme, *, fp=FP, seed='regional-fixture', **attrs):
    example=architecture.catalogue()[theme]['example']
    values=dict(seed_id=seed,_footprint=fp,_context=Context(location=(example['lat'],example['lon'])),
                **{'class':'house','height':8.,'num_floors':2})
    values.update(attrs)
    spec=b.plan(np.asarray(fp.outer),values)
    spec.gring=np.zeros(len(fp.outer));spec.door=(0,2.3);spec.front=0
    return spec


class GeographyTests(unittest.TestCase):
    def test_all_64_reviewed_examples_route_to_their_theme(self):
        self.assertEqual(len(architecture.catalogue()),64)
        for key,p in architecture.catalogue().items():
            with self.subTest(theme=key):
                self.assertTrue(all(r.get('image_viewed') for r in p['references']))
                self.assertEqual(environments.catalogue()['regions'][key]['status'],'active')
                e=p['example'];self.assertEqual(geography.locate(e['lat'],e['lon']).theme,key)

    def test_independent_cities_islands_and_country_boundaries(self):
        cases=[(21.3069,-157.8583,'pacific_islands'),(-18.1416,178.4419,'pacific_islands'),
               (51.0447,-114.0719,'canada_prairie'),(50.6745,-120.3273,'canada_prairie'),
               (49.2827,-123.1207,'canada_pacific'),(47.6062,-122.3321,'us_pacific'),
               (31.7619,-106.485,'us_southwest'),(32.7767,-96.797,'us_southeast'),
               (28.6139,77.209,'indus_gangetic'),(12.9716,77.5946,'india_peninsular'),
               (29.652,91.1721,'tibetan_plateau'),(43.8256,87.6168,'central_asia_oases'),
               (-31.9523,115.8613,'au_southeast'),(-12.4634,130.8456,'au_tropical_arid'),
               (-77.846,166.676,'antarctic_stations'),(-68.5763,77.9688,'antarctic_stations')]
        for lat,lon,theme in cases:
            with self.subTest(point=(lat,lon)):
                self.assertEqual(geography.locate(lat,lon).theme,theme)
        for point in ((0.,0.),(30.,-40.),(math.nan,0.),(91.,0.)):
            self.assertEqual(geography.locate(*point).theme,'')
        self.assertEqual(geography.locate(-17.7,178.1),geography.locate(-17.7,538.1))

    def test_shoreline_does_not_choose_foreign_province_over_nearer_country(self):
        metadata=({'theme':'first','priority':0,'source':'A','name':'A','jurisdiction':'A'},
                  {'theme':'second','priority':10,'source':'B','name':'B','jurisdiction':'B'})
        with patch.object(geography,'_index',return_value=(STRtree([box(-.01,-.01,-.001,.01),box(.002,-.01,.01,.01)]),metadata)):
            geography.locate.cache_clear()
            self.assertEqual(geography.locate(0.,0.).method,'ambiguous_shoreline')
        geography.locate.cache_clear()

    def test_high_latitude_shore_distance_uses_metric_not_degree_nearest_point(self):
        # Diagonal coast at 80N: horizontal degrees are much shorter than vertical.
        polygon=Polygon(((.018,79.998),(.04,80.006),(.05,80.02),(.018,80.02)))
        metadata=({'theme':'polar','priority':0,'source':'X','name':'X','jurisdiction':'X'},)
        with patch.object(geography,'_index',return_value=(STRtree([polygon]),metadata)):
            geography.locate.cache_clear()
            self.assertEqual(geography.locate(80.,0.).theme,'polar')
        geography.locate.cache_clear()

    def test_local_overlay_wins_and_conflicting_overlays_stay_unresolved(self):
        z=Zone('local','v1','test','R','statutory',('residential',),1.,region='jp_temperate')
        ctx=Context(zones=(z,),location=(-43.5321,172.6362))
        self.assertEqual(environments.resolve(ctx,'residential').region,'jp_temperate')
        ctx=replace(ctx,zones=(z,replace(z,source_id='conflict',region='arid_warm')))
        self.assertEqual(environments.resolve(ctx,'residential').region,'')


class RegionalGeometryTests(unittest.TestCase):
    def test_every_theme_changes_the_actual_plan_and_compiles_near_lite_collision(self):
        signatures=set()
        for key in architecture.catalogue():
            with self.subTest(theme=key):
                spec=building(key)
                plan=freeze_items([(spec,0.,0.)])[0][0]
                self.assertEqual(plan.inference.selection.environment.region,key)
                self.assertIn('regional_architecture:'+key,plan.facades.diagnostics)
                windows=[o for e in plan.facades.elevations for o in e.openings if o.kind=='window']
                signatures.add((plan.facade,plan.roof,round(plan.pitch,5),tuple((round(o.right-o.left,4),round(o.top-o.bottom,4)) for o in windows)))
                self.assertEqual(plan.facades,pickle.loads(pickle.dumps(plan)).facades)
                for mesh in (b.build([(plan,0.,0.)]),b.build([(plan,0.,0.)],lite=True),b.collision_mesh([(plan,0.,0.)])):
                    self.assertIsNotNone(mesh)
                    self.assertTrue(np.isfinite(mesh[0]).all())
                    self.assertTrue(np.isfinite(mesh[1]).all())
                    self.assertLess(int(mesh[2].max()),len(mesh[0]))
        self.assertEqual(len(signatures),64)

    def test_mapped_materials_colour_roof_height_and_storeys_win_in_all_themes(self):
        for key in architecture.catalogue():
            with self.subTest(theme=key):
                spec=building(key,roof_shape='flat',roof_material='metal',facade_material='stone',facade_color='#778899',roof_color='#88aa55')
                result=spec.inference
                self.assertEqual(result.roof.value,'flat')
                self.assertEqual(result.roof_material.value,'metal')
                self.assertEqual(result.facade.value,'stone')
                self.assertEqual(result.height.value,8.)
                self.assertEqual(result.floors.value,2)
                self.assertEqual(spec.facade,b.custom_look(b.STONE,b.parse_color('#778899')))
                self.assertEqual(spec.roof_mat,b.custom_look(b.ROOF_METAL,b.parse_color('#88aa55')))

    def test_detail_budgets_and_door_clearances_all_themes(self):
        for key in architecture.catalogue():
            spec=building(key,seed='detail-review')
            layout=facades.plan(spec,0.,0.);p=architecture.for_spec(spec)
            count=0
            for elevation in layout.elevations:
                rows=architecture.components(spec,elevation,p,architecture.MAX_COMPONENTS-count)
                count+=len(rows)
                self.assertLessEqual(len(rows),architecture.MAX_PER_ELEVATION)
                for row in rows:
                    self.assertGreaterEqual(row.left,0.)
                    self.assertLessEqual(row.right,elevation.length)
                    self.assertLessEqual(row.top,spec.height)
                    if not row.overlay:
                        a=facades.Opening('detail',0,row.left,row.right,row.bottom,row.top)
                        self.assertTrue(all(not a.overlaps(o) for o in elevation.openings),(key,row))
            self.assertLessEqual(count,architecture.MAX_COMPONENTS)

    def test_disabled_and_unknown_themes_do_not_apply_any_profile(self):
        catalog=json.loads(json.dumps(environments.catalogue()))
        catalog['regions']['jp_temperate']['status']='proposed'
        with patch.object(environments,'catalogue',return_value=catalog):
            self.assertIsNone(architecture.profile('jp_temperate'))
            self.assertEqual(architecture.roof_default('jp_temperate','residential',True,1,'flat'),'flat')
        self.assertIsNone(architecture.profile('not_a_region'))

    def test_fixed_source_location_wins_over_render_frame_and_translation(self):
        attrs=dict(seed_id='stable',_footprint=FP,_context=Context(location=(35.68,139.76)),**{'class':'house','height':8.})
        a=b.plan(np.asarray(FP.outer),attrs,lat=-43.,lon=172.)
        shifted=Footprint(tuple((x+1000,y-300) for x,y in FP.outer))
        c=b.plan(np.asarray(shifted.outer),dict(attrs,_footprint=shifted),lat=51.,lon=-.1)
        self.assertEqual(a.inference.selection.environment,c.inference.selection.environment)
        self.assertEqual(a.inference.selection.environment.region,'jp_temperate')
        self.assertEqual((a.roof,a.pitch,a.facade),(c.roof,c.pitch,c.facade))

    def test_runtime_data_participates_in_cache_and_package_inputs(self):
        root=Path(__file__).resolve().parents[2]
        files=codefiles.source_files(root/'server')
        for name in ('regional_geography.json','regional_profiles.json','environments.json'):
            self.assertIn('buildgen/catalog/'+name,files)


if __name__=='__main__':unittest.main()
