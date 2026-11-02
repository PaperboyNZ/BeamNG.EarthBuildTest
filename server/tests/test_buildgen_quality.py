"""Quality ceilings, identity, cache isolation and adaptive recovery contracts."""
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
sys.path[:0]=[str(Path(__file__).resolve().parents[1])]
import buildings as b
import blockworker as bw
import geodesy,geotiles,roads
from buildgen import freeze_items,quality,products
from buildgen import progressive as p
from test_buildgen_regions import building
from test_buildgen_city import make as city
import test_buildgen_products as product_fixtures
import test_buildgen_progressive as stage_fixtures


@contextmanager
def tier(name):
    token=p.DETAIL.set(name)
    try:yield
    finally:p.DETAIL.reset(token)


class QualityTests(unittest.TestCase):
    def test_all_six_have_bounded_adaptive_settings(self):
        for rank,name in enumerate(quality.NAMES):
            q=quality.PROFILES[name]
            self.assertEqual(q.rank,rank)
            self.assertLess(q.fast_exit,q.fast_enter)
            self.assertGreater(q.settle_s,0)
            self.assertLessEqual(quality.rank(q.fallback),rank)
        self.assertEqual(quality.rank('full'),5)
        self.assertEqual(quality.rank('lite'),1)
        self.assertEqual(quality.rank(None),-1)

    def test_geometry_is_finite_nested_cost_and_collision_independent(self):
        for spec in (building('nz_temperate'),building('jp_temperate'),city()[0]):
            items=freeze_items([(spec,0.,0.)])
            original=b.collision_mesh(items)
            counts=[]
            for name in quality.NAMES:
                with tier(name):
                    mesh=b.build(items)
                    collision=b.collision_mesh(items)
                self.assertTrue(np.isfinite(mesh[0]).all(),name)
                self.assertTrue(np.isfinite(mesh[1]).all(),name)
                self.assertLess(int(mesh[2].max()),len(mesh[0]))
                self.assertAlmostEqual(mesh[0][:,2].max(),b.build(items)[0][:,2].max(),places=5)
                for index in (0,1,2,3,5):np.testing.assert_array_equal(collision[index],original[index])
                counts.append(len(mesh[2]))
            self.assertEqual(counts,sorted(counts))
            self.assertLess(counts[0],counts[-1])

    def test_every_tier_keeps_architectural_window_rows(self):
        spec=building('nz_temperate');items=freeze_items([(spec,0.,0.)])
        def rows(mesh):
            triangles=mesh[2][mesh[3]==b._Looks(spec.seed)['bne_bld_fac_white'][0]]
            return np.unique(mesh[0][triangles.ravel(),2])
        expected=rows(b.build(items))
        self.assertGreater(len(expected),0)
        for name in quality.NAMES:
            with tier(name):mesh=b.build(items)
            np.testing.assert_array_equal(rows(mesh),expected)
        with tier('very_low'):self.assertIs(freeze_items(items)[0][0],items[0][0])

    def test_ultra_equals_legacy_full_for_both_representations(self):
        items=freeze_items([(building('jp_temperate'),0.,0.),(city()[0],0.,0.)])
        for lite in (False,True):
            with tier('full'):expected=b.build(items,lite=lite)
            with tier('ultra'):actual=b.build(items,lite=lite)
            for index in (0,1,2,3,5):np.testing.assert_array_equal(actual[index],expected[index])

    def test_context_does_not_leak_between_workers(self):
        def worker(name):
            with tier(name):return quality.current().name
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(worker,quality.NAMES)),list(quality.NAMES))
        self.assertEqual(p.DETAIL.get(),'full')

    def test_adaptive_recovery_hysteresis_and_ceiling_at_every_tier(self):
        for name in quality.NAMES:
            q=quality.PROFILES[name];tracker=SimpleNamespace();conn=SimpleNamespace(building_quality=name)
            def choose(speed,now,**kw):return quality.adaptive_target(tracker,conn,speed,now=now,**kw)
            self.assertEqual(choose(0,0),name)
            self.assertEqual(choose(40,1),q.fallback)
            self.assertEqual(choose(q.fast_exit+1,2),q.fallback)
            self.assertEqual(choose(0,3),q.fallback)
            self.assertEqual(choose(0,3+q.settle_s),name)
            self.assertEqual(choose(0,20,busy=True),q.fallback)
            self.assertEqual(choose(0,20+q.settle_s-.01),q.fallback)
            self.assertEqual(choose(0,21+q.settle_s),name)
            conn.building_adaptive=False
            self.assertEqual(choose(100,30,busy=True),name)

    def test_free_camera_is_not_throttled_by_an_unrelated_fast_car(self):
        t=SimpleNamespace();c=SimpleNamespace(building_quality='ultra')
        self.assertEqual(quality.adaptive_target(t,c,80,now=1,free_camera=True),'ultra')
        self.assertEqual(quality.adaptive_target(t,c,80,now=2,free_camera=True),'ultra')

    def test_explicit_lowering_and_automatic_recovery_are_distinct(self):
        self.assertFalse(quality.needs_rebuild('ultra','low','ultra'))
        self.assertTrue(quality.needs_rebuild('ultra','low','high'))
        self.assertTrue(quality.needs_rebuild('low','high','high'))
        self.assertFalse(quality.needs_rebuild('high','high','high'))

    def test_low_publishes_final_once_without_duplicate_lite_encoding(self):
        items=stage_fixtures.ProgressiveTests().items(13)
        for name in ('very_low','low'):
            with tempfile.TemporaryDirectory() as folder,tier(name):
                pub=p.Publisher(folder,'/vfs',None,'a'*32);events=[]
                with patch.object(pub,'publish',side_effect=lambda g,s,m,names=None:events.append((g,s))),\
                     patch.object(b,'build',wraps=b.build) as build:
                    pub.shells(items);meshes,groups=pub.build(items)
                self.assertEqual([stage for g,stage in events],[0]*len(groups)+[2]*len(groups))
                self.assertEqual(build.call_count,len(groups))
                self.assertTrue(all(len(m[0])<=b.V2_IMPORT_VERTS for m in meshes))
                self.assertLessEqual(max(map(len,pub.partition(items))),quality.PROFILES[name].group_size)

    def test_progressive_downgrade_keeps_selected_cache_unpoisoned(self):
        items=stage_fixtures.ProgressiveTests().items(15)
        with tempfile.TemporaryDirectory() as folder,tier('ultra'):
            pub=p.Publisher(folder,'/vfs',None,'b'*32)
            p.limit_detail(folder,pub.token)
            with patch.object(pub,'publish'):meshes,_=pub.build(items)
            self.assertEqual(pub.detail,'low')
            self.assertEqual(p.DETAIL.get(),'ultra')
            self.assertTrue(meshes)

    def test_scheduler_upgrades_and_lowers_visuals_without_auto_downgrade(self):
        key=geotiles.tile_of(0,0);frame=geodesy.EnuFrame(0,0)
        tracker=roads.GeoTracker();submitted=[]
        def submit(pool,fn,*args):
            f=Future();submitted.append((fn,f));return f
        loop=SimpleNamespace(run_in_executor=submit)
        with tempfile.TemporaryDirectory() as folder,patch.object(roads,'geo_wanted',return_value={key:0}),\
             patch.object(geotiles,'tiles_near',return_value=[(*key,0)]):
            conn=SimpleNamespace(building_quality='high',building_adaptive=False,building_progress=True,
                                 send=lambda msg:None,s=SimpleNamespace(out_dir=folder))
            def pose(speed=0):tracker.on_pose(conn,1,0,0,loop,lambda *a,**kw:None,vel=(speed,0),frame=frame)
            def done(name):
                submitted[-1][1].set_result(dict(content=('/q',0,dict(h=name,parts={},buildingDetail=name),[])))
                tracker.skins.add(key);tracker.need[(key,1)]={}
            try:
                pose();self.assertEqual(submitted[-1][0].keywords['building_detail'],'high');done('high')
                conn.building_quality='ultra';pose()
                self.assertEqual(submitted[-1][0].keywords['building_detail'],'ultra');done('ultra')
                conn.building_adaptive=True;pose(80)
                self.assertEqual(len(submitted),2)
                conn.building_quality='very_low';pose()
                self.assertEqual(submitted[-1][0].keywords['building_detail'],'very_low')
            finally:tracker.close()

    def test_graphics_accepts_six_names_and_boolean_adaptation_only(self):
        from earthd import Connection
        conn=SimpleNamespace(lod_scale=1.,tree_scale=1.,building_scale=1.,veg=SimpleNamespace(send_m=1300),
                             bldfar=SimpleNamespace(send_m=1600),s=SimpleNamespace(base_px=2048),view_cap=None,active=None)
        for name in quality.NAMES:
            Connection.set_graphics(conn,dict(buildingQuality=name,buildingAdaptive=False))
            self.assertEqual(conn.building_quality,name);self.assertFalse(conn.building_adaptive)
        Connection.set_graphics(conn,dict(buildingQuality='bad',buildingAdaptive='true'))
        self.assertEqual(conn.building_quality,'ultra');self.assertFalse(conn.building_adaptive)

    def test_all_quality_cache_keys_are_unique(self):
        args=('g',15,True,False,False,False,0.,None,None)
        keys=[bw._geo_content_key(*args,md={},building_detail=name) for name in quality.NAMES]
        self.assertEqual(len(set(keys)),6)

    def test_full_profiler_reports_building_stages_without_changing_mesh(self):
        import runtimeprofiler as profiler
        import ioprofiler
        items=freeze_items([(building('nz_temperate'),0.,0.)])
        expected=b.build(items)
        context=dict(mode='full',stack=[],steps={})
        token=profiler._context.set(context)
        try:
            with patch.object(ioprofiler.monitor,'mode','full'):
                actual=b.build(items)
                with tempfile.TemporaryDirectory() as folder:b.write(str(Path(folder)/'test.cdae'),actual)
        finally:profiler._context.reset(token)
        for name in ('Building visual mesh','Building facade geometry','Building roof solution',
                     'Building rainwater detail','Building surface aging','Building shape export'):
            self.assertIn(name,context['steps'])
            self.assertGreaterEqual(context['steps'][name]['totalMs'],0)
        self.assertEqual(context['stack'],[])
        for index in (0,1,2,3,5):np.testing.assert_array_equal(actual[index],expected[index])


class QualityProductTests(unittest.TestCase):
    def test_all_six_deepen_then_lower_using_one_physical_product(self):
        fixture=product_fixtures.IndependentProductsTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        folder,before=fixture.retain_lite()
        for name in (*quality.NAMES,'very_low'):
            out=fixture.root/('tier-'+name)
            out.mkdir(exist_ok=True)
            with tier(name),patch.object(bw,'_tile_parts',side_effect=AssertionError('replanned')),\
                 patch.object(b,'collision_mesh',side_effect=AssertionError('rebuilt collision')),\
                 patch.object(b,'doors',side_effect=AssertionError('rebuilt access')):
                result=products.refine(bw,fixture.tile,fixture.key,str(out),'/tier',name)
            self.assertIsNotNone(result)
            data=json.loads((out/bw.geo_names(fixture.tile.key)['json']).read_text())
            self.assertEqual(data['buildingDetail'],name)
            self.assertEqual(data['physicalHash'],before['physicalHash'])
            for what in before['buildingChunks']['collision']:
                fn=bw.geo_names(fixture.tile.key,parts={what:{}})[what]
                self.assertEqual((out/fn).read_bytes(),(folder/fn).read_bytes())


if __name__=='__main__':unittest.main()
