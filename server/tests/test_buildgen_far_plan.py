"""Distant products reuse accepted near plans; cold coverage remains available."""
from concurrent.futures import Future
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import blockworker as bw
import buildings as b
import earthd
import geotiles
from buildgen import products
from buildgen.progressive import DETAIL
from productcache import Store
import test_buildgen_products as product_tests


class FarPlanProductsTests(unittest.TestCase):
    parts=product_tests.IndependentProductsTests.parts
    retain_lite=product_tests.IndependentProductsTests.retain_lite

    def setUp(self):
        product_tests.IndependentProductsTests.setUp(self)
        self.addCleanup(self.close_index)
        bw._s.md.cell=lambda *a,**kw:SimpleNamespace(layers={'roads':None})
        self.retain_lite()
        self.store=Store(str(self.cache))
        self.saved=self.store.load('accepted-plan',self.key)
        self.ref=dict(key=self.key,revision=self.saved.revision)

    def close_index(self):
        # Revisit keeps a process-wide append descriptor. Close this fixture's
        # own handle before TemporaryDirectory cleanup on Windows.
        import revisit
        descriptor=revisit._where.pop(str(self.cache),None)
        if descriptor is not None:os.close(descriptor)

    def far(self,name,ref=None):
        out=self.root/name;out.mkdir(exist_ok=True)
        result=bw.far_geo('bldfar',self.gx,self.gy,15,str(out),'/'+name,plan_ref=self.ref if ref is None else ref)
        data=json.loads((out/Path(result[0]).name).read_text())
        return result,data,out

    def test_far_worker_reuses_exact_plan_without_building_or_physical_planning(self):
        with patch.object(b,'far_items',side_effect=AssertionError('replanned distant buildings')),\
             patch.object(b,'plan',side_effect=AssertionError('resolved architecture again')),\
             patch.object(b,'doors',side_effect=AssertionError('replanned accepted access')),\
             patch.object(b,'collision_mesh',side_effect=AssertionError('regenerated physics')),\
             patch.object(bw,'_tile_parts',side_effect=AssertionError('combined pipeline')),\
             patch.object(bw,'_frame_grader',side_effect=AssertionError('terrain fitting')):
            result,data,out=self.far('accepted')
        expected=out/'expected.cdae';b.write(str(expected),b.build(self.plans,lite=True,texture_facades=True))
        self.assertEqual((out/result[4]['shape']).read_bytes(),expected.read_bytes())
        self.assertEqual(data['acceptedPlan']['revision'],self.ref['revision'])
        self.assertEqual(data['acceptedPlan']['physicalRevision'],self.saved.value['physical_revision'])
        self.assertEqual(result[1],len(self.plans))
        self.assertIn(self.ref['revision'][:24],result[4]['shape'])
        self.assertEqual(data['pos'],[float(v) for v in self.tile.box[:2]]+[0.])

    def test_cached_far_representation_survives_a_worker_boundary(self):
        first,data,out=self.far('first')
        with patch.object(bw,'_far_geo_build',side_effect=AssertionError('rebuilt cached representation')):
            second,again,other=self.far('second')
        self.assertEqual((out/first[4]['shape']).read_bytes(),(other/second[4]['shape']).read_bytes())
        self.assertEqual(data['h'],again['h'])

    def test_lite_full_upgrade_reports_same_accepted_plan_reference(self):
        out=self.root/'upgrade';out.mkdir()
        token=DETAIL.set('full')
        try:result=products.refine(bw,self.tile,self.key,str(out),'/upgrade','full')
        finally:DETAIL.reset(token)
        self.assertEqual(result[2]['acceptedPlan'],self.ref)

    def test_revision_changes_publish_distinct_paths_and_preserve_old_bytes(self):
        first,data,out=self.far('same')
        old={name:(out/name).read_bytes() for name in (Path(first[0]).name,first[4]['shape'])}
        plan,low,high=self.saved.value['plans'][0]
        newer=products.plan_record(((replace(plan,seed=plan.seed+.0001),low,high),),
            self.saved.value['physical_revision'],self.saved.value['dependencies'],self.saved.value['inputs'])
        updated=self.store.put('accepted-plan',self.key,newer)
        newref=dict(key=self.key,revision=updated.revision)
        second,after,_=self.far('same',newref)
        self.assertNotEqual(first[0],second[0]);self.assertNotEqual(first[4],second[4])
        self.assertNotEqual(data['h'],after['h'])
        for name,blob in old.items():self.assertEqual((out/name).read_bytes(),blob)

    def test_stale_revision_changed_input_wrong_tile_and_corruption_use_cold_fallback(self):
        fallback=(self.plans,[],self.tile.box)
        with patch.object(b,'far_items',return_value=fallback) as cold:
            for label,ref in (('wrong-revision',dict(self.ref,revision='f'*64)),
                              ('malformed',dict(key='../other',revision='0'*64))):
                _,data,_=self.far(label,ref)
                self.assertNotIn('acceptedPlan',data)
            self.assertEqual(cold.call_count,1,'equivalent cold fallback is reusable')
            self.source.write_text('changed terrain or street source')
            _,data,_=self.far('changed-source')
            self.assertNotIn('acceptedPlan',data)
            self.assertIsNone(products.load_accepted(self.store,self.tile,self.key))
            self.store.path('accepted-plan',self.key).write_bytes(b'incomplete archive')
            _,data,_=self.far('corrupt')
            self.assertNotIn('acceptedPlan',data)
        other=geotiles.geobox(self.gx+1,self.gy)
        self.store.put('accepted-plan',self.key,self.saved.value)
        self.assertIsNone(products.load_accepted(self.store,other,self.key))

    def test_fallback_cache_cannot_poison_later_accepted_revision(self):
        with patch.object(b,'far_items',return_value=(self.plans,[],self.tile.box)):
            _,cold,_=self.far('cold',dict(self.ref,revision='f'*64))
        with patch.object(b,'far_items',side_effect=AssertionError('fell back despite accepted plan')):
            _,warm,_=self.far('warm')
        self.assertNotIn('acceptedPlan',cold)
        self.assertEqual(warm['acceptedPlan']['revision'],self.ref['revision'])
        self.assertNotEqual(cold['shape'].split('/')[-1],warm['shape'].split('/')[-1])

    def test_generator_and_frame_dependency_mismatch_is_a_miss(self):
        with patch('revisit.code_key',return_value='different-generator'):
            self.assertIsNone(products.load_accepted(self.store,self.tile,self.key))
        for field,value in (('source','invalid'),('frame',{})):
            deps=dict(self.saved.value['dependencies'],**{field:value})
            from productcache import identity
            key=identity(deps)
            self.store.put('accepted-plan',key,dict(self.saved.value,dependencies=deps))
            self.assertIsNone(products.load_accepted(self.store,self.tile,key))

    def test_malformed_semantic_product_is_a_miss_after_checksum_validation(self):
        for field,value in (('inputs','not file stamps'),('inputs',(('path','bad stamp'),)),
                            ('plans',(('not a BuildingPlan',0.,0.),)),('physical_revision','unknown')):
            with self.subTest(field=field,value=value):
                self.store.put('accepted-plan',self.key,dict(self.saved.value,**{field:value}))
                self.assertIsNone(products.load_accepted(self.store,self.tile,self.key))

    def test_server_memo_and_connection_builder_follow_near_plan_revisions(self):
        calls=[]
        class Pool:
            def submit(inner,fn,*args,**kwargs):
                calls.append(kwargs.get('plan_ref'))
                future=Future();future.set_result(fn(*args,**kwargs));return future
        server=object.__new__(earthd.Server)
        server.far_bld_pool=Pool();server.mapdata=bw._s.md
        out=self.root/'server';out.mkdir()
        server.out_dir=str(out);server.vfs_dir='/server';server.geo_rules=lambda *a:(False,False,0.,None,None,15)
        conn=SimpleNamespace(s=server,roads=SimpleNamespace(info={(self.gx,self.gy):{'acceptedPlan':self.ref}}))
        build=earthd.Connection.build_far_geo(conn,'bldfar')
        first=build(self.gx,self.gy);self.assertEqual(calls,[self.ref])
        self.assertEqual(build(self.gx,self.gy),first);self.assertEqual(len(calls),1)
        plan,lo,hi=self.saved.value['plans'][0]
        newer=products.plan_record(((replace(plan,seed=plan.seed+.01),lo,hi),),
            self.saved.value['physical_revision'],self.saved.value['dependencies'],self.saved.value['inputs'])
        saved=self.store.put('accepted-plan',self.key,newer)
        updated=dict(key=self.key,revision=saved.revision)
        conn.roads.info[(self.gx,self.gy)]={'acceptedPlan':updated}
        second=build(self.gx,self.gy)
        self.assertEqual(calls[-1],updated);self.assertEqual(len(calls),2)
        self.assertNotEqual(first[0],second[0])


if __name__=='__main__':unittest.main()
