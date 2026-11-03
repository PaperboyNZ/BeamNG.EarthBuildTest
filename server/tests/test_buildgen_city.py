"""City source constraints, descriptive authoring isolation and bounded meshes."""
from dataclasses import asdict, replace, FrozenInstanceError
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import pickle
import sys
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'server'),str(ROOT/'tools')]
import buildings as b
from buildgen import city, facades, freeze_items, regional_architecture, regional_blocks
from buildgen.context import Context
from buildgen.environments import Environment
from buildgen.topology import Footprint
from compile_city_regions import compile_records


def make(cls='office',material='concrete',floors=16,fp=None,offset=(0.,0.),party=(),region=None):
    fp = fp or Footprint(((0,0),(30,0),(30,24),(0,24)))
    fp = fp.translated(*offset)
    attrs = dict(_footprint=fp,seed_id='stable-city',height=floors*3.4,num_floors=floors,
                 roof_shape='flat',facade_material=material,_party_walls=party)
    attrs['class'] = cls
    attrs['_context'] = Context(location=(40.73,-73.99))
    if region is None:
        s=b.plan(np.asarray(fp.outer),attrs)
    else:
        with patch('buildgen.environments.resolve',return_value=Environment('city_centre',region)):
            s=b.plan(np.asarray(fp.outer),attrs)
    s.gring=np.zeros(len(s.ring))
    roads=[(np.array([(-50.,-12.),(80.,-12.)])+offset,3.,'residential',False)]
    props=b.doors([(s,0.,0.)],roads,0.,0.,ground=lambda xy:np.zeros(len(xy)))
    return s,props


def geometry(s,lite=False):
    return b.build(freeze_items([(s,0.,0.)]),lite=lite)


class CityTests(unittest.TestCase):
    def test_tall_glass_middle_tier_preserves_panes_with_meaningful_simplification(self):
        spec,_=make(material='glass',floors=80)
        close=geometry(spec);middle=geometry(spec,True)
        self.assertLess(len(middle[0]),len(close[0])*.60)
        glass=b.MATERIALS.index(b.OFFICE)
        def pattern(mesh):
            vertices=mesh[2][mesh[3]==glass].ravel()
            return sorted(tuple(row) for row in np.column_stack((mesh[0][vertices,2],mesh[1][vertices])))
        self.assertEqual(pattern(close),pattern(middle))

    def test_all_64_descriptive_ids_and_compiler_isolation(self):
        env=json.loads((ROOT/'server/buildgen/catalog/environments.json').read_text())['regions']
        brief=(ROOT/'docs/CITY_REGIONAL_DESIGN_BRIEFS.md').read_text(encoding='utf-8')
        expected=compile_records(env,brief)
        stored=json.loads(city.PATH.read_text())
        self.assertEqual(expected,stored)
        changed=copy.deepcopy(env)
        for p in changed.values():
            p.update(facade=[['glass',9999]],roof=[['metal',9999]],runtime_profile='unrelated',status='proposed')
        self.assertEqual(compile_records(changed,brief),expected)
        changed['us_northeast']['coverage']+=' Local revised scope.'
        new=compile_records(changed,brief)
        self.assertNotEqual(new['regions']['us_northeast']['source_digest'],expected['regions']['us_northeast']['source_digest'])
        self.assertEqual(new['regions']['nz_temperate'],expected['regions']['nz_temperate'])

    def test_each_region_has_city_or_neutral_result(self):
        for key in city.catalogue():
            with self.subTest(region=key):
                s,_=make(region=key)
                self.assertEqual(s.city.region.id,key)
                self.assertEqual(s.city.region.source_digest,city.catalogue()[key]['source_digest'])
                self.assertEqual(s.city.region.status,'neutral_fallback' if key=='antarctic_stations' else 'text_based_proposal')
                self.assertTrue(np.isfinite(geometry(s)[0]).all())

    def test_city_never_reads_existing_style_parameters(self):
        fail=AssertionError('Defined regional styles reached the city path')
        with patch.object(regional_architecture,'profile',side_effect=fail), \
             patch.object(regional_architecture,'wall_colour',side_effect=fail), \
             patch.object(regional_architecture,'roof_colour',side_effect=fail), \
             patch.object(regional_blocks,'catalogue',side_effect=fail):
            for cls,material,floors in (('office','glass',30),('office','concrete',16),('hotel','render',8)):
                s,_=make(cls,material,floors)
                for lite in (False,True):
                    self.assertTrue(len(geometry(s,lite)[0]))
                mesh=b.Mesh();from buildgen.geometry import sky
                sky(mesh,s,0.,0.)
                self.assertGreater(mesh.n,0)

    def test_five_material_compatible_families_and_source_dimensions(self):
        families=[]
        for cls,mat,expected in (('office','glass','office_curtain'),('office','concrete','office_panel'),
                                  ('office','brick','office_masonry'),('hotel','render','hotel_contemporary'),
                                  ('hotel','stone','hotel_masonry')):
            s,_=make(cls,mat)
            families.append(s.city.family)
            self.assertEqual(s.city.family,expected)
            self.assertEqual(s.inference.facade.value,mat)
            self.assertEqual(s.inference.facade.status,'observed')
            self.assertAlmostEqual(s.city.programme.datums[-1].top,16*3.4)
            self.assertEqual(s.roof,'flat')
            self.assertEqual(s.city.programme.era.status,'unknown')
        self.assertEqual(len(set(families)),5)

    def test_specialists_low_offices_motels_and_hostels_keep_existing_paths(self):
        for cls,floors in (('office',3),('motel',6),('hostel',6),('warehouse',1),('airport_terminal',2),('church',1)):
            with self.subTest(cls=cls):
                s,_=make(cls,floors=floors)
                self.assertIsNone(s.city)

    def test_frozen_plan_roundtrip_and_translation(self):
        s,_=make('hotel','brick',8)
        frozen=freeze_items([(s,0.,0.)])
        restored=pickle.loads(pickle.dumps(frozen))
        self.assertEqual(frozen[0][0].city,restored[0][0].city)
        with self.assertRaises(FrozenInstanceError):
            restored[0][0].city.family='other'
        shifted,_=make('hotel','brick',8,offset=(128.,-256.))
        self.assertEqual(s.city.region,shifted.city.region)
        self.assertEqual(s.city.runs,shifted.city.runs)
        self.assertEqual(s.city.expression,shifted.city.expression)
        # Compare facades only: site coordinates have separate ownership/frames.
        for item in (s,shifted):
            item.access=None;item.facades=None;item.door=None
        a,c=geometry(s),geometry(shifted)
        np.testing.assert_allclose(a[0],c[0]-[128.,-256.,0.],atol=2e-5)
        np.testing.assert_array_equal(a[2],c[2])

    def test_city_and_baseline_have_identical_physical_geometry(self):
        s,_=make('hotel','brick',8)
        first=b.collision_mesh(freeze_items([(s,0.,0.)]))
        with patch.object(city,'plan',return_value=None):
            old,_=make('hotel','brick',8)
        second=b.collision_mesh(freeze_items([(old,0.,0.)]))
        np.testing.assert_array_equal(first[0],second[0])
        np.testing.assert_array_equal(first[2],second[2])
        self.assertEqual(s.door,old.door)
        self.assertEqual(s.access.door_z,old.access.door_z)
        self.assertEqual([(v.kind,v.top) for v in s.access.solids],[(v.kind,v.top) for v in old.access.solids])

    def test_party_wall_has_no_windows_or_entry(self):
        s,props=make(party=((0,0),))
        run=s.city.programme.run(0,0)
        self.assertTrue(run.party_wall)
        layout=facades.plan(s,0.,0.)
        e=next(e for e in layout.elevations if e.boundary==0 and e.edge==run.edge)
        self.assertEqual(e.openings,())
        self.assertTrue(s.door is None or s.door[0]!=0)

    def test_courtyard_holes_and_finite_nondegenerate_meshes(self):
        fp=Footprint(((0,0),(40,0),(40,32),(0,32)),(((12,10),(28,10),(28,22),(12,22)),))
        s,_=make('hotel','stone',12,fp=fp)
        from shapely.geometry import Polygon,Point
        hole=Polygon(fp.holes[0]).buffer(-.1)
        for mesh in (geometry(s),geometry(s,True),b.collision_mesh(freeze_items([(s,0.,0.)]))):
            self.assertTrue(np.isfinite(mesh[0]).all())
            tris=mesh[0][mesh[2]]
            areas=np.linalg.norm(np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]),axis=1)
            self.assertTrue((areas>1e-9).all())
            horiz=tris[np.ptp(tris[:,:,2],axis=1)<1e-5]
            self.assertFalse(any(hole.contains(Point(t[:2])) for t in horiz.mean(axis=1)))

    def test_120_storey_budget_preserves_every_floor_and_chunk(self):
        fp=Footprint(((0,0),(300,0),(300,200),(0,200)))
        s,_=make('office','glass',120,fp=fp)
        self.assertEqual(s.city.mode,'bands')
        self.assertEqual(len(s.city.programme.datums),120)
        self.assertEqual(len(s.city.runs),4)
        frozen=freeze_items([(s,0.,0.)])
        full=b.build(frozen)
        self.assertLess(len(full[0]),15000)
        self.assertAlmostEqual(full[0][:,2].max(),s.height,places=4)
        with patch.dict(os.environ,{'BNE_BUILDING_GENERATOR':'v2'}):
            chunks=b.build_parts(frozen,max_verts=2000,with_lod=True)
        self.assertTrue(all(len(m[0])<=2000 for m in chunks))
        self.assertEqual(sum(len(m[2]) for m in chunks),len(full[2]))

    def test_street_clipping_refits_city_runs_and_preserves_party_segments(self):
        from buildgen.road_conflicts import filter_items
        s,_=make('hotel','brick',8,party=((0,3),))
        road=('street',SimpleNamespace(cls='residential',width=6.),
              np.array([[-50.,1.,0.],[100.,1.,0.]]),None)
        kept=filter_items([(s,0.,0.)],roads=[road],ground=lambda xy:np.zeros(len(xy)))
        changed=kept[0][0]
        self.assertIsNot(changed,s)
        self.assertEqual(changed.city.region,s.city.region)
        self.assertIsNone(changed.access)
        self.assertGreaterEqual(changed.ring[:,1].min(),4.35-1e-7)
        for run in changed.city.programme.runs:
            self.assertGreaterEqual(min(run.start[1],run.end[1]),4.35-1e-7)
            if run.start[0]==run.end[0]==0.:
                self.assertTrue(run.party_wall)
            if run.start[1]==run.end[1]:
                self.assertFalse(run.party_wall)
        for lite in (False,True):
            mesh=geometry(changed,lite)
            self.assertGreaterEqual(mesh[0][:,1].min(),4.34)

    def test_lite_retains_aperture_positions_with_lower_vertex_cost(self):
        s,_=make('hotel','brick',16)
        near,lite=geometry(s),geometry(s,True)
        self.assertLess(len(lite[0]),len(near[0])*.65)
        self.assertEqual(s.city.mode,'modules')
        # Pier-mask boundaries in lite equal the near pane corners.
        for run,desc in zip(s.city.programme.runs,s.city.runs):
            if run.boundary==0 and run.start==(0.,0.) and run.end[1]==0.:
                xs=lite[0][np.abs(lite[0][:,1])<.01,0]
                for i in range(desc.columns):
                    edge=desc.margin+(i+.5)*desc.pitch-desc.window_width/2
                    self.assertTrue(np.any(np.isclose(xs,edge,atol=1e-4)))


if __name__=='__main__':
    unittest.main()
