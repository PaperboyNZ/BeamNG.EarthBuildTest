"""Site geometry, connected surfaces, evidence, bounded work and persistence."""
from dataclasses import replace
import json
import os
from pathlib import Path
import pickle
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from shapely.geometry import Polygon, Point

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import freeze_items, site_data, site_layout, commercial
from buildgen.site_data import Site, Port
from buildgen.topology import Footprint
from test_buildgen_commercial import fixture
from test_buildgen_facades import road


def example(width=60.,boundary=None,exclusions=(),rise=1.1):
    s,lo,hi=fixture('warehouse',width,25,seed='A')
    x=s.door[1]
    s.site=Site('property','survey-1',boundary or Footprint(((-15,-40),(width+15,-40),(width+15,60),(-15,60))),exclusions,
        (Port('service',(width/2-3,60,.04),(width/2+3,60,.04)),
         Port('parking',(width*.65-3,-40,.04),(width*.65+3,-40,.04)),
         Port('pedestrian',(x-.7,-40,.04),(x+.7,-40,.04))),rise)
    return s,lo,hi


class SiteTests(unittest.TestCase):
    def test_parking_uses_continuous_front_with_the_same_accepted_door(self):
        from test_buildgen_commercial_foundation import set_world_door
        original=example()
        s=original[0]
        edge,along=s.door
        a=s.ring[edge];c=s.ring[(edge+1)%len(s.ring)]
        point=a+(c-a)*along/np.linalg.norm(c-a)
        dense=Footprint(((0,0),(20,0),(40,0),(60,0),(60,25),(0,25)))
        split=fixture('warehouse',60,25,seed='A',fp=dense)
        split[0].site=s.site
        set_world_door(split[0],point)
        split[0].access=s.access
        commercial.resolve([split],road(),lambda p:np.zeros(len(p)),0,0)
        for item in (original,split):
            site_layout.resolve([item],lambda p:np.zeros(len(p)),0,0)
        self.assertGreater(original[0].access.site_layout.parking,0)
        self.assertEqual(original[0].access.site_layout.parking,split[0].access.site_layout.parking)
        self.assertEqual(original[0].access.site_layout.connections,split[0].access.site_layout.connections)
        self.assertEqual(original[0].access.solids,split[0].access.solids)

    def test_loading_court_uses_continuous_facade_across_source_vertices(self):
        original=example()
        dense=Footprint(((0,0),(60,0),(60,25),(48,25),(0,25)))
        split=fixture('warehouse',60,25,seed='A',fp=dense)
        split[0].site=original[0].site
        for item in (original,split):
            site_layout.resolve([item],lambda p:np.zeros(len(p)),0,0)
        self.assertGreater(split[0].access.site_layout.docks,0)
        self.assertEqual(original[0].access.solids,split[0].access.solids)
        self.assertEqual(original[0].access.site_layout.connections,split[0].access.site_layout.connections)
        docks=[]
        for item in (original,split):
            s=item[0]
            docks.append(tuple((tuple(s.ring[e.edge]),e.length,e.openings)
                for e in s.facades.elevations if e.role=='loading_docks'))
            for mesh in (b.build([item]),b.build([item],lite=True),b.collision_mesh([item])):
                self.assertTrue(np.isfinite(mesh[0]).all())
        self.assertEqual(docks[0],docks[1])

    def test_docks_parking_and_pedestrians_fit_property_and_connect(self):
        s,lo,hi=example()
        site_layout.resolve([(s,lo,hi)],lambda p:np.zeros(len(p)),0,0)
        r=s.access.site_layout
        self.assertGreater(r.docks,0);self.assertGreater(r.parking,0)
        self.assertEqual(set(r.connections),{'service','parking','pedestrian'})
        shapes=[]
        for solid in s.access.solids:
            if not solid.kind.startswith('site_'):continue
            p=Polygon([v[:2] for v in solid.top]);shapes.append((solid,p))
            self.assertTrue(s.site.boundary.shape().buffer(1e-7).covers(p))
            self.assertLess(p.intersection(s.footprint.shape()).area,1e-7)
        for port in s.site.ports:
            for q in (port.a,port.b):
                self.assertTrue(any(p.distance(Point(q[:2]))<1e-6 for _,p in shapes))
        walk=next(p for solid,p in shapes if solid.kind=='site_path')
        self.assertTrue(any(p.distance(walk)<1e-6 for solid,p in shapes if solid.kind=='site_walk'))
        self.assertLessEqual(r.terrain_points,site_layout.MAX_POINTS)

    def test_surface_joins_do_not_overlap_or_jump_in_height(self):
        s,lo,hi=example()
        site_layout.resolve([(s,lo,hi)],lambda p:np.zeros(len(p)),0,0)
        solids=[v for v in s.access.solids if v.kind.startswith('site_') and v.kind not in ('site_dock','site_bumper')]
        for i,a in enumerate(solids):
            pa=Polygon([p[:2] for p in a.top])
            for c in solids[i+1:]:
                pc=Polygon([p[:2] for p in c.top])
                self.assertLess(pa.intersection(pc).area,1e-6)
                shared=pa.boundary.intersection(pc.boundary)
                if shared.length<.01:continue
                point=np.asarray(shared.centroid.coords[0])
                def height(s):
                    p=np.asarray(s.top);coef=np.linalg.lstsq(np.c_[p[:,:2],np.ones(4)],p[:,2],rcond=None)[0]
                    return np.r_[point,1.]@coef
                self.assertAlmostEqual(height(a),height(c),places=6)

    def test_irregular_boundary_and_exclusions_reduce_parking(self):
        full=example();cut=example(exclusions=(Footprint(((8,-18),(31,-18),(31,-4),(8,-4))),))
        for item in (full,cut):site_layout.resolve([item],lambda p:np.zeros(len(p)),0,0)
        self.assertLess(cut[0].access.site_layout.parking,full[0].access.site_layout.parking)
        fp=Footprint(((-10,-40),(35,-40),(75,-20),(75,60),(-10,60)))
        s,lo,hi=example(boundary=fp)
        site_layout.resolve([(s,lo,hi)],lambda p:np.zeros(len(p)),0,0)
        for solid in s.access.solids:
            if solid.kind.startswith('site_'):
                self.assertTrue(fp.shape().buffer(1e-7).covers(Polygon([p[:2] for p in solid.top])))

    def test_missing_or_rough_terrain_never_leaves_floating_sites(self):
        for ground in (lambda p:np.full(len(p),np.nan),lambda p:p[:,0]*.3,
                       lambda p:np.sin(p[:,0]*.8)*.4):
            s,lo,hi=example();original=s.facades
            site_layout.resolve([(s,lo,hi)],ground,0,0)
            self.assertEqual(s.access.site_layout.docks,0)
            self.assertEqual(s.access.site_layout.parking,0)
            self.assertEqual(s.facades,original)

    def test_no_boundary_no_site_no_mapped_floor_no_docks(self):
        s,lo,hi=fixture();before=s.access
        site_layout.resolve([(s,lo,hi)],lambda p:np.zeros(len(p)),0,0)
        self.assertEqual(s.access,before)
        s,lo,hi=example(rise=None)
        site_layout.resolve([(s,lo,hi)],lambda p:np.zeros(len(p)),0,0)
        self.assertEqual(s.access.site_layout.docks,0)

    def test_repeated_generation_and_prop_pass_preserve_site(self):
        s,lo,hi=example()
        ground=lambda p:np.zeros(len(p))
        site_layout.resolve([(s,lo,hi)],ground,0,0)
        before=(s.facades,s.access)
        # Normal full pipeline rebuilds commercial facade before resolving site.
        commercial.resolve([(s,lo,hi)],road(),ground,0,0)
        site_layout.resolve([(s,lo,hi)],ground,0,0)
        self.assertEqual((s.facades,s.access),before)
        b.doors([(s,lo,hi)],road(),0,0)
        self.assertEqual((s.facades,s.access),before)
        site_layout.resolve([(s,lo,hi)],lambda p:np.full(len(p),np.nan),0,0)
        self.assertFalse(any(e.role=='loading_docks' for e in s.facades.elevations))
        self.assertEqual(s.access.site_layout.docks,0)

    def test_worker_and_mesh_tiers_keep_physical_sites(self):
        item=example();site_layout.resolve([item],lambda p:np.zeros(len(p)),0,0)
        frozen=freeze_items([item]);copy=pickle.loads(pickle.dumps(frozen))
        self.assertEqual(frozen[0][0].site,copy[0][0].site)
        self.assertEqual(frozen[0][0].access,copy[0][0].access)
        for mesh in (b.build(copy),b.build(copy,lite=True),b.collision_mesh(copy)):
            self.assertTrue(np.isfinite(mesh[0]).all())
            tri=mesh[0][mesh[2]]
            self.assertTrue((np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)>1e-9).all())
        self.assertTrue(any(v.kind=='site_bumper' for v in copy[0][0].access.solids))

    def test_sampling_is_bounded_and_batched_per_site(self):
        for width in (24.,45.,60.,150.,1000.):
            s,lo,hi=example(width);calls=[]
            def ground(p):calls.append(len(p));return np.zeros(len(p))
            site_layout.resolve([(s,lo,hi)],ground,0,0)
            self.assertLessEqual(len(calls),1)
            self.assertLessEqual(sum(calls),site_layout.MAX_POINTS)

    def test_no_parking_without_accepted_pedestrian_connection(self):
        s,lo,hi=example()
        s.site=replace(s.site,ports=tuple(p for p in s.site.ports if p.kind!='pedestrian'))
        site_layout.resolve([(s,lo,hi)],lambda p:np.zeros(len(p)),0,0)
        self.assertEqual(s.access.site_layout.parking,0)
        self.assertGreater(s.access.site_layout.docks,0)

    def test_trade_service_lane_meets_existing_shutter_without_crossing_staff_entries(self):
        s,lo,hi=fixture('workshop',60,25,seed='A')
        elevation=next(e for e in s.facades.elevations if e.role=='trade')
        op=next(o for o in elevation.openings if o.kind=='service')
        x=(op.left+op.right)/2
        boundary=Footprint(((-15,-40),(75,-40),(75,60),(-15,60)))
        s.site=Site('trade','1',boundary,(),(Port('service',(x-2,-40,.04),(x+2,-40,.04)),))
        before=s.facades
        site_layout.resolve([(s,lo,hi)],lambda p:np.zeros(len(p)),0,0)
        self.assertEqual(s.access.site_layout.connections,('service',))
        self.assertEqual(s.access.site_layout.docks,0)
        self.assertEqual(s.facades,before)
        lane=next(v for v in s.access.solids if v.kind=='site_service')
        lane_shape=Polygon([p[:2] for p in lane.top])
        for step in s.access.solids:
            if step.kind in ('threshold','ci_threshold'):
                self.assertLess(lane_shape.intersection(Polygon([p[:2] for p in step.top])).area,1e-7)
        self.assertAlmostEqual(max(p[2] for p in lane.top),op.bottom-.01,places=6)

    def test_conflicting_parking_and_footpath_levels_omit_parking(self):
        s,lo,hi=example()
        s.site=replace(s.site,ports=tuple(Port(p.kind,(*p.a[:2],.12),(*p.b[:2],.12))
            if p.kind=='parking' else p for p in s.site.ports))
        site_layout.resolve([(s,lo,hi)],lambda p:np.zeros(len(p)),0,0)
        self.assertEqual(s.access.site_layout.parking,0)
        self.assertIn('pedestrian',s.access.site_layout.connections)
        self.assertIn('site_parking_connection_level_conflict',s.access.site_layout.diagnostics)

    def test_shifted_anchor_and_building_preserve_counts(self):
        original=example();shifted=example()
        offset=np.array([1234.,-500.])
        s,lo,hi=shifted
        site=s.site
        from test_buildgen_facades import building
        s=building(fp=s.footprint.translated(*offset),**{'class':'warehouse','height':6.,'roof_shape':'flat',
                                                       'seed_id':'A','facade_material':'concrete'})
        s.site=replace(site,boundary=site.boundary.translated(*offset),ports=tuple(Port(p.kind,
            (*(np.asarray(p.a[:2])+offset),p.a[2]),(*(np.asarray(p.b[:2])+offset),p.b[2])) for p in site.ports))
        b.doors([(s,lo,hi)],[(p+offset,*rest) for p,*rest in road()],0,0,ground=lambda p:np.zeros(len(p)))
        site_layout.resolve([original],lambda p:np.zeros(len(p)),0,0)
        self.assertEqual(s.access.site_layout.parking,original[0].access.site_layout.parking)
        self.assertEqual(s.access.site_layout.docks,original[0].access.site_layout.docks)

    def test_catalogue_provenance_and_projection(self):
        import geodesy
        frame=geodesy.EnuFrame(-43.5,172.6,0)
        def ll(points):
            p=np.asarray(points,float);lat,lon,h=frame.enu_to_geodetic(p[:,0],p[:,1],p[:,2])
            return np.c_[lon,lat,h].tolist()
        ring=ll([[-15,-40,0],[75,-40,0],[75,60,0],[-15,60,0],[-15,-40,0]])
        props=dict(site_id='S',owner_id='B',source='synthetic fixture',release='1',obstacles_complete=True,
                   ports=[dict(kind='service',coordinates=ll([[27,60,.04],[33,60,.04]]))],dock_rise=1.1)
        data=dict(type='FeatureCollection',features=[dict(type='Feature',geometry=dict(type='Polygon',coordinates=[[p[:2] for p in ring]]),properties=props)])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'sites.geojson';path.write_text(json.dumps(data))
            with patch.dict(os.environ,{'BNE_BUILDING_SITES':str(path)}):
                site_data.catalogue.cache_clear()
                try:
                    site=site_data.project('B',frame)
                    self.assertEqual(site.id,'S')
                    self.assertTrue(np.allclose(site.ports[0].a,(27,60,.04),atol=.001))
                    digest=site.revision
                    props['release']='2';path.write_text(json.dumps(data));site_data.catalogue.cache_clear()
                    self.assertNotEqual(site_data.catalogue()[0],digest)
                    props['obstacles_complete']=False;path.write_text(json.dumps(data));site_data.catalogue.cache_clear()
                    with self.assertRaises(ValueError):site_data.catalogue()
                finally:site_data.catalogue.cache_clear()

    def test_tile_ingestion_attaches_only_single_component_site_owner(self):
        from test_buildgen_topology import FlatFrame,features,rect
        site=example()[0].site
        shapes=([[(rect(0,0,60,25),)]], [[(rect(0,0,60,25),),(rect(80,0,10,10),)]])
        with patch.dict(os.environ,{'BNE_BUILDING_GENERATOR':'v2'}), \
             patch.object(site_data,'catalogue',return_value=('test',{'B0':{}})):
            for polygons,expected in zip(shapes,(1,0)):
                layer=features(polygons,height=[6.],**{'class':['warehouse']})
                with patch.object(site_data,'project',return_value=site) as project:
                    items=b.tile_buildings(FlatFrame(),-20,-50,150,100,[layer],lambda lat,lon:np.zeros(np.shape(lat)))
                    self.assertEqual(project.call_count,expected)
                    self.assertEqual(sum(s.site is not None for s,_,_ in items),expected)
                    from sitegen.adapters import LegacySiteAdapter
                    self.assertTrue(all(isinstance(s.site, LegacySiteAdapter) for s,_,_ in items if s.site is not None))

    def test_infrastructure_cut_does_not_duplicate_property_layout(self):
        from test_buildgen_topology import planned
        s,_,_=example()
        site=replace(s.site,owner_footprint=s.footprint)
        cut=Footprint(((0,0),(20,0),(20,25),(0,25)))
        self.assertIsNone(planned(cut,_site=site).site)
        self.assertIsNotNone(planned(s.footprint,_site=site).site)

    def test_site_revision_changes_generated_cache_key(self):
        import revisit
        with patch.dict(os.environ,{'BNE_BUILDING_GENERATOR':'v2'}),patch.object(revisit,'_code',[]):
            keys=[]
            for digest in ('site-one','site-two'):
                revisit._code.clear()
                with patch.object(site_data,'catalogue',return_value=(digest,{})):
                    keys.append(revisit.code_key())
            self.assertNotEqual(*keys)


if __name__=='__main__':unittest.main()
