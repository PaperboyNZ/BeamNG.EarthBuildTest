"""Mixed skyline products preserve accepted plans, source ownership and frames."""
from dataclasses import replace
import gc
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import weakref

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
import blockworker as bw
import earthd
import geotiles
import inputwatch
import roads
from buildgen import distant,products,freeze_items
from buildgen.geometry import sky_vertex_count
from buildgen.topology import Footprint
from productcache import Store
from test_buildgen_facades import building
from test_buildgen_topology import features


class SkylinePlanTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'BNE_BUILDING_GENERATOR':'v2'});self.env.start();self.addCleanup(self.env.stop)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.cache=self.root/'cache';self.store=Store(str(self.cache))
        self.parent=geotiles.geobox(*geotiles.tile_of(-36.91,174.90,geotiles.SKY_Z),geotiles.SKY_Z)
        self.keys=sorted(geotiles.children(self.parent.gx,self.parent.gy,self.parent.z,geotiles.Z))
        self.source=self.root/'input';self.source.write_text('revision1')
        self.inputs=inputwatch.snapshot({'files':{str(self.source)},'overflow':False})
        self.items={};self.values={};self.refs={}
        self.md=SimpleNamespace(cell=lambda *a,**kw:SimpleNamespace(layers={'roads':None,'buildings':None,'building_parts':None}),
                                has=lambda *a:True,prefetch=lambda *a,**kw:None,versions=lambda:{'buildings':'fixture1'})
        self.state=patch.object(bw,'_s',SimpleNamespace(cache_dir=str(self.cache),md=self.md,airports=None,sea=None,
                               dem=SimpleNamespace(sample=lambda la,lo,z:np.zeros_like(np.asarray(la,float)))))
        self.state.start();self.addCleanup(self.state.stop)
        self.addCleanup(self.close_index)
        for i,key in enumerate(self.keys):
            fp=Footprint(((60.,60.),(90.,60.),(90.,85.),(60.,85.)))
            if i%3==1:fp=Footprint(fp.outer,(((68.,68.),(68.,77.),(81.,77.),(81.,68.)),))
            if i%3==2:fp=Footprint(((60.,60.),(90.,60.),(90.,70.),(78.,70.),(78.,85.),(60.,85.)))
            spec=building(fp=fp,seed_id='accepted-'+str(i),height=12.+i,num_floors=3,
                          roof_shape=('gabled','hipped','flat')[i%3],roof_height=2.)
            self.items[key]=freeze_items([(spec,0.,0.)])
            child=geotiles.geobox(*key);address,deps=products.address(child,'sky-fixture-'+child.key)
            value=products.plan_record(self.items[key],'a'*16,deps,self.inputs)
            saved=self.store.put('accepted-plan',address,value)
            self.values[key]=value;self.refs[key]=dict(key=address,revision=saved.revision)

    def close_index(self):
        import revisit
        descriptor=revisit._where.pop(str(self.cache),None)
        if descriptor is not None:os.close(descriptor)

    def sky(self,refs=None):
        return distant.skyline(self.parent,self.refs if refs is None else refs,str(self.cache),self.md,
                               lambda la,lo:np.zeros_like(np.asarray(la,float)))

    def source_features(self):
        def polygon(key,offset=(0.,0.)):
            child=geotiles.geobox(*key)
            xy=np.array([[-20.,-20.],[20.,-20.],[20.,20.],[-20.,20.]])+offset
            lat,lon,_=geotiles.world_to_geodetic(child.frame,np.c_[xy,np.zeros(4)])
            return [list(zip(lon,lat))]
        source=features([[polygon(self.keys[0])],[polygon(self.keys[0],(60.,60.))],
                         [polygon(self.keys[1])]],ids=['accepted-source','suppressed-canopy','cold-source'],
                         height=[18.,18.,18.],num_floors=[3.,3.,3.],roof_shape=['flat']*3)
        self.md.cell=lambda *a,**kw:SimpleNamespace(layers={'roads':None,'buildings':source,'building_parts':None})
        return source

    def background_context(self):
        return patch('buildgen.context.provider',return_value=SimpleNamespace(query=lambda *a,**kw:None))

    def test_all_accepted_children_skip_source_planning_and_preserve_exact_emitted_geometry(self):
        with patch.object(b,'sky_items',side_effect=AssertionError('replanned accepted children')),\
             patch.object(b,'plan',side_effect=AssertionError('resolved architecture again')),\
             patch.object(b,'doors',side_effect=AssertionError('replanned access')),\
             patch.object(b,'collision_mesh',side_effect=AssertionError('rebuilt physics')):
            mesh,lamps,n,revision,metadata=self.sky()
        expected=[]
        ordered=sorted(self.keys,key=lambda k:(-(self.items[k][0][0].height or 0.),str(self.items[k][0][0].seed),geotiles.key(*k)))
        for key in ordered:
            child=geotiles.geobox(*key);source=b._sky_mesh(self.items[key])
            points=source[0]+np.r_[child.box[:2],0.]
            # Independent conversion through geodetic coordinates instead of
            # modifying/rebasing the architectural plan.
            lat,lon,height=geotiles.world_to_geodetic(child.frame,points)
            xyz=np.column_stack(geotiles.geodetic_to_world(self.parent.frame,lat,lon,height))-np.r_[self.parent.box[:2],0.]
            expected.append((xyz,*source[1:]))
        expected=b._concat(expected)
        np.testing.assert_allclose(mesh[0],expected[0],atol=1e-7,rtol=0.)
        for index in (1,2,3,5):np.testing.assert_array_equal(mesh[index],expected[index])
        self.assertEqual(n,16);self.assertEqual(lamps,[])
        self.assertEqual(metadata['acceptedSectors'],16)
        self.assertEqual(metadata['revision'],distant.reference_revision(self.refs))
        self.assertEqual(len(revision),64)
        self.assertLessEqual(len(mesh[0]),b.MAX_MESH_VERTS)

    def test_only_one_cached_plan_survives_between_child_loads(self):
        original=products.load_accepted;last=[]
        def load(*args,**kw):
            gc.collect()
            self.assertTrue(not last or last[-1]() is None,'previous complete plan released before another load')
            result=original(*args,**kw)
            if result is not None:last.append(weakref.ref(result.value['plans'][0][0].ring))
            return result
        with patch.object(products,'load_accepted',side_effect=load):self.sky()
        gc.collect();self.assertTrue(all(ref() is None for ref in last))
        self.assertEqual(len(last),16)

    def test_mixed_source_filter_runs_before_clipping_or_architecture_planning(self):
        self.source_features();planned=[];original=b.plan
        def plan(ring,attrs,*a,**kw):
            planned.append(attrs.get('seed_id'));return original(ring,attrs,*a,**kw)
        with self.background_context(),patch.object(b,'plan',side_effect=plan):
            mesh,_,n,_,metadata=self.sky({self.keys[0]:self.refs[self.keys[0]]})
        self.assertEqual(planned,['cold-source'])
        self.assertEqual(n,2);self.assertEqual(metadata['acceptedSectors'],1)
        self.assertEqual(metadata['consideredBuildings'],2)
        self.assertTrue(np.isfinite(mesh[0]).all())

    def test_corrupt_child_falls_back_and_cannot_claim_all_accepted_identity(self):
        self.source_features();refs={key:self.refs[key] for key in self.keys[:2]}
        self.store.path('accepted-plan',refs[self.keys[1]]['key']).write_bytes(b'incomplete')
        with self.background_context():before=self.sky(refs)
        self.assertEqual(before[4]['acceptedSectors'],1);self.assertEqual(before[4]['requestedSectors'],2)
        self.assertNotEqual(before[4]['revision'],distant.reference_revision(refs))
        restored=self.store.put('accepted-plan',refs[self.keys[1]]['key'],self.values[self.keys[1]])
        self.assertEqual(restored.revision,refs[self.keys[1]]['revision'])
        with self.background_context():after=self.sky(refs)
        self.assertEqual(after[4]['acceptedSectors'],2)
        self.assertNotEqual(before[3],after[3])
        self.assertEqual(after[2],2)

    def test_pending_cold_source_publishes_no_partial_replacement(self):
        self.source_features();self.md.has=lambda *a:False
        refs={self.keys[0]:self.refs[self.keys[0]]}
        with self.background_context():self.assertIsNone(self.sky(refs))
        out=self.root/'pending';out.mkdir()
        with self.background_context():
            result=bw.far_geo('bldsky',self.parent.gx,self.parent.gy,15,str(out),'/pending',plan_refs=refs)
        self.assertIsNone(result);self.assertFalse(list(out.iterdir()))

    def test_runtime_publishes_distinct_hybrid_paths_and_never_poisoned_revisit_identity(self):
        self.source_features();out=self.root/'runtime';out.mkdir()
        refs={self.keys[0]:self.refs[self.keys[0]]}
        with self.background_context(),patch('revisit.store',side_effect=AssertionError('hybrid stored under incomplete dependency key')):
            first=bw.far_geo('bldsky',self.parent.gx,self.parent.gy,15,str(out),'/runtime',plan_refs=refs)
        previous={p.name:p.read_bytes() for p in out.iterdir()}
        refs[self.keys[1]]=self.refs[self.keys[1]]
        with self.background_context():
            second=bw.far_geo('bldsky',self.parent.gx,self.parent.gy,15,str(out),'/runtime',plan_refs=refs)
        self.assertNotEqual(first[0],second[0]);self.assertNotEqual(first[4]['shape'],second[4]['shape'])
        for name,blob in previous.items():self.assertEqual((out/name).read_bytes(),blob)
        data=json.loads((out/Path(second[0]).name).read_text())
        self.assertEqual(data['acceptedPlan']['acceptedSectors'],2)
        self.assertIn(data['representationRevision'][:24],second[4]['shape'])

    def test_reference_inventory_is_complete_bounded_and_parent_specific(self):
        self.assertEqual(distant.references(self.parent,self.refs),self.refs)
        variants=[{**self.refs,(0,0):next(iter(self.refs.values()))},
                  {self.keys[0]:{'key':'../path','revision':'a'*64}},
                  {('wrong','key'):self.refs[self.keys[0]]},
                  {self.keys[0]:self.refs[self.keys[1]]}]
        for values in variants[:3]:self.assertFalse(distant.references(self.parent,values))
        # A well-formed reference to another child passes envelope validation,
        # but complete source/frame validation rejects it before exclusion.
        with patch.object(b,'sky_items',return_value=([],[])):
            result=self.sky(variants[3])
        self.assertEqual(result[4]['acceptedSectors'],0)

    def test_source_ownership_masks_edges_and_vector_inputs_consistently(self):
        excluded={self.keys[0],self.keys[5]};owner=distant.SourceOwners(self.parent,excluded)
        rng=np.random.default_rng(31)
        points=[]
        for key in self.keys:
            corners=geotiles.quad(self.parent.frame,*key)
            points.extend(np.vstack([corners+rng.normal(0.,.02,corners.shape) for _ in range(20)]))
        xy=np.asarray(points)
        lat,lon,_=geotiles.world_to_geodetic(self.parent.frame,np.c_[xy,np.zeros(len(xy))])
        gx,gy=geotiles.tile_of(lat,lon)
        expected=np.asarray(self.parent.owns(xy[:,0],xy[:,1]))
        for a,c in excluded:expected &= ~((gx==a)&(gy==c))
        np.testing.assert_array_equal(owner.owns(xy[:,0],xy[:,1]),expected)
        for i in range(0,len(xy),39):self.assertEqual(owner.owns(*xy[i]),bool(expected[i]))

    def test_tallest_first_budget_is_order_independent_and_never_slices_buildings(self):
        items=[]
        source=geotiles.geobox(*self.keys[0])
        for i in range(20):
            original=self.items[self.keys[i%16]][0]
            spec=replace(original[0],height=10.+i,seed=.01*i)
            items.append((spec,original[1],original[2]))
        limit=230
        expected=[];used=0
        for item in sorted(items,key=lambda it:(-it[0].height,str(it[0].seed))):
            cost=max(sky_vertex_count(item[0]),len(b._sky_mesh((item,))[0]))
            if used+cost>limit:break
            expected.append(item[0].height);used+=cost
        for order in (list(range(20)),list(reversed(range(20))),np.random.default_rng(17).permutation(20)):
            prefix=distant.SkylinePrefix(self.parent);prefix.limit=limit
            for i in order:prefix.add(items[i],source,int(i))
            self.assertEqual([-rank[0] for rank in prefix.ranks],expected)
            self.assertLessEqual(len(prefix.result()[0]),limit)
            self.assertTrue(prefix.budget_limited)

    def test_small_distant_visibility_filter_does_not_modify_near_plan_or_physics(self):
        key=self.keys[0]
        tiny=building(fp=Footprint(((30.,30.),(33.,30.),(33.,33.),(30.,33.))),roof_shape='flat')
        self.items[key]=freeze_items([*self.items[key],(tiny,0.,0.)])
        value=products.plan_record(self.items[key],'a'*16,self.values[key]['dependencies'],self.inputs)
        saved=self.store.put('accepted-plan',self.refs[key]['key'],value)
        self.refs[key]=dict(self.refs[key],revision=saved.revision)
        before={key:b.collision_mesh(items) for key,items in self.items.items()}
        shapes={key:items[0][0].footprint for key,items in self.items.items()}
        result=self.sky()
        self.assertEqual(result[2],16,'subpixel small building stays in near physics but need not enter skyline')
        for key,items in self.items.items():
            self.assertIs(items[0][0].footprint,shapes[key])
            after=b.collision_mesh(items)
            for i in (0,1,2,3,5):np.testing.assert_array_equal(after[i],before[key][i])

    def test_aggregate_lamps_keep_the_parent_bound_and_exact_child_frames(self):
        glow=[[float(i%20),float(i//20),8.] for i in range(400)]
        with patch.object(b,'built_squares',return_value={(0,0)}),patch.object(b,'far_lamps',return_value=glow):
            _,lamps,_,_,metadata=self.sky()
        self.assertEqual(len(lamps),b.FAR_LAMP_MAX)
        self.assertTrue(metadata['lampBudgetLimited'])
        child=geotiles.geobox(*self.keys[0])
        points=geotiles.world_map(self.parent.frame,child.frame,np.asarray(lamps[:400]))
        np.testing.assert_allclose(points,glow,atol=1e-7,rtol=0.)

    def test_unresolved_source_dependencies_change_representation_identity(self):
        self.source_features();original=self.md.cell
        cold_input=self.root/'cold-source-input';cold_input.write_text('revision1')
        def cell(*a,**kw):
            inputwatch.paths([cold_input]);return original(*a,**kw)
        self.md.cell=cell;refs={self.keys[0]:self.refs[self.keys[0]]}
        with self.background_context():before=self.sky(refs)
        cold_input.write_text('longer revision2')
        with self.background_context():after=self.sky(refs)
        for i in (0,1,2,3,5):np.testing.assert_array_equal(before[0][i],after[0][i])
        self.assertNotEqual(before[3],after[3])

    def test_connection_inventory_and_server_memo_follow_partial_parent_revisions(self):
        from concurrent.futures import Future
        calls=[]
        class Pool:
            def submit(inner,fn,*args,**kwargs):
                calls.append(kwargs.get('plan_refs'))
                future=Future();future.set_result(fn(*args,**kwargs));return future
        server=object.__new__(earthd.Server)
        server.far_bld_pool=Pool();server.mapdata=self.md
        out=self.root/'memo';out.mkdir()
        server.out_dir=str(out);server.vfs_dir='/memo';server.geo_rules=lambda *a:(False,False,0.,None,None,15)
        near=roads.GeoTracker();near.remember_plan(self.keys[0],self.refs[self.keys[0]])
        conn=SimpleNamespace(s=server,roads=near)
        build=earthd.Connection.build_far_geo(conn,'bldsky')
        first=build(self.parent.gx,self.parent.gy)
        self.assertEqual(calls,[{self.keys[0]:self.refs[self.keys[0]]}])
        self.assertEqual(build(self.parent.gx,self.parent.gy),first)
        self.assertEqual(len(calls),1)
        near.remember_plan(self.keys[1],self.refs[self.keys[1]])
        second=build(self.parent.gx,self.parent.gy)
        self.assertEqual(len(calls),2);self.assertEqual(len(calls[-1]),2)
        self.assertNotEqual(first[0],second[0])


if __name__=='__main__':unittest.main()
