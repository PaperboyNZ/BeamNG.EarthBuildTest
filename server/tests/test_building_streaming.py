"""Fast travel changes optional visual work, never physical/access geometry."""
import json
import tempfile
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import Future
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
import blockworker
import geodesy
import geotiles
import roads
from buildgen import progressive
from test_buildgen_progressive import ProgressiveTests


class BuildingStreamingTests(unittest.TestCase):
    def test_graphics_settings_validate_without_world_startup(self):
        from earthd import Connection
        c=SimpleNamespace(lod_scale=1.,tree_scale=1.,building_scale=1.,
            veg=SimpleNamespace(send_m=1300),bldfar=SimpleNamespace(send_m=1600),
            s=SimpleNamespace(base_px=2048),view_cap=None,active=None)
        Connection.set_graphics(c,dict(buildingQuality='adaptive',buildingDetailM=500))
        Connection.set_graphics(c,dict(buildingQuality='unknown',buildingDetailM=float('nan')))
        self.assertEqual(c.building_quality,'adaptive');self.assertEqual(c.building_detail_m,500)
        Connection.set_graphics(c,dict(buildingQuality='lite',buildingDetailM=99999))
        self.assertEqual(c.building_quality,'lite');self.assertEqual(c.building_detail_m,640)
        Connection.set_graphics(c,dict(buildingDetailM=-1))
        self.assertEqual(c.building_detail_m,100)

    def test_speed_hysteresis_and_explicit_quality(self):
        t=roads.GeoTracker();c=SimpleNamespace(building_quality='adaptive')
        self.assertEqual(t.building_detail(c,0),'full')
        self.assertEqual(t.building_detail(c,67.056),'lite')  # 150 mph
        self.assertEqual(t.building_detail(c,18),'lite')
        self.assertEqual(t.building_detail(c,12),'full')
        self.assertEqual(t.building_detail(c,18),'full')
        c.building_quality='full';self.assertEqual(t.building_detail(c,67.056),'full')
        c.building_quality='lite';self.assertEqual(t.building_detail(c,0),'lite')
        self.assertEqual(t.building_detail(SimpleNamespace(),67.056),'full','older client remains compatible')

    def test_150mph_then_slow_refines_without_downgrading_finished_full_tiles(self):
        frame=geodesy.EnuFrame(0,0);key=geotiles.tile_of(0,0)
        t=roads.GeoTracker();submitted=[];messages=[]
        def submit(pool,fn,*args):
            f=Future();submitted.append((fn,args,f));return f
        loop=SimpleNamespace(run_in_executor=submit)
        with tempfile.TemporaryDirectory() as folder,patch.object(roads,'geo_wanted',return_value={key:0}), \
             patch.object(geotiles,'tiles_near',return_value=[(*key,0)]):
            c=SimpleNamespace(building_quality='adaptive',building_progress=True,send=messages.append,
                              s=SimpleNamespace(out_dir=folder))
            def pose(speed):t.on_pose(c,1,0,0,loop,lambda *a,**kw:None,vel=(speed,0),frame=frame)
            try:
                pose(67.056)
                self.assertEqual(submitted[-1][0].keywords['building_detail'],'lite')
                submitted[-1][2].set_result(dict(content=('/lite.json',0,{'h':'lite','parts':{},'buildingDetail':'lite'},[])))
                t.skins.add(key);t.need[(key,1)]={}
                pose(18);self.assertEqual(len(submitted),1)
                pose(0);self.assertEqual(submitted[-1][0].keywords['building_detail'],'full')
                token=submitted[-1][0].keywords['progress_token']
                pose(67.056)
                self.assertTrue(progressive.manifest_path(folder,token).with_name(f'bp_{token}.lite.tmp').exists())
                submitted[-1][2].set_result(dict(content=('/full.json',0,{'h':'full','parts':{},'buildingDetail':'full'},[])))
                pose(67.056);self.assertEqual(len(submitted),2,'completed full tiles are retained')
            finally:t.close()

    def test_lite_omits_full_facade_work_and_preserves_collision(self):
        items=ProgressiveTests().items(2)
        full=b.road_tile(None,0,0,None,None,items=items)
        state=progressive.DETAIL.set('lite')
        try:
            with patch.object(b,'build_parts',side_effect=AssertionError('full facade generated')):
                lite=b.road_tile(None,0,0,None,None,items=items)
        finally:progressive.DETAIL.reset(state)
        self.assertLess(sum(len(m[0]) for m in lite[0]),sum(len(m[0]) for m in full[0])/2)
        self.assertEqual(lite[1],full[1])
        import numpy as np
        for a,c in zip(lite[2][:4],full[2][:4]):np.testing.assert_array_equal(a,c)

    def test_acceleration_downgrades_between_groups_and_reuses_lite_as_final(self):
        items=ProgressiveTests().items(progressive.GROUP_SIZE+1)
        with tempfile.TemporaryDirectory() as folder:
            p=progressive.Publisher(folder,'/vfs',None,'b'*32)
            def publish(group,stage,meshes,names=None):
                if stage==2:progressive.limit_detail(folder,p.token)
            with patch.object(p,'publish',side_effect=publish),patch.object(b,'build_parts',wraps=b.build_parts) as build:
                meshes,groups=p.build(items)
            self.assertEqual(build.call_count,1,'second group skips full facade work after acceleration')
            self.assertEqual(p.detail,'lite')
            self.assertEqual(len(groups),len(p.partition(items)))
            self.assertEqual(sum(len(g['visual']) for g in groups),len(meshes))

    def test_quality_cache_keys_are_distinct(self):
        args=('g17_1_1',14,True,False,False,False,0,None,None)
        full=blockworker._geo_content_key(*args,md={},building_detail='full')
        lite=blockworker._geo_content_key(*args,md={},building_detail='lite')
        self.assertNotEqual(full,lite)

    def test_downgraded_full_job_cannot_populate_full_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            p=progressive.Publisher(folder,'/vfs',None,'c'*32);p.detail='lite'
            state=progressive.ACTIVE.set(p)
            try:
                import revisit
                with patch.object(blockworker,'_s',SimpleNamespace(cache_dir=folder)), \
                     patch.object(blockworker,'_md_versions',return_value={}), \
                     patch.object(revisit,'load',return_value=None),patch.object(revisit,'ON',True), \
                     patch.object(revisit,'faults',return_value=0),patch.object(revisit,'store') as store, \
                     patch.object(blockworker,'_frame_grader',return_value=None), \
                     patch.object(blockworker,'_tile_parts',return_value=SimpleNamespace(fuel_pads=[])), \
                     patch.object(blockworker,'_write_geo_content',return_value=('/vfs/test.json',0,{'parts':{}})):
                    blockworker._geo_content(65536,65536,14,folder,'/vfs',True,False,False,False,0,None,None)
                store.assert_not_called()
            finally:progressive.ACTIVE.reset(state)

    def test_obsolete_completion_is_cached_without_sending_game_objects(self):
        t=roads.GeoTracker();key=(65536,65536);t.aid=1
        f=Future();t.building.add(key);t.futs[key]=f;t.obsolete_buildings.add(key)
        messages=[];c=SimpleNamespace(send=messages.append)
        f.set_result(dict(content=('/old.json',0,{'h':'old','parts':{}},[])))
        t._built(c,1,key,f,True,True,'auto')
        self.assertFalse(messages)
        self.assertNotIn(key,t.sent)
        self.assertNotIn(key,t.building)

    @patch.dict('os.environ', {'BNE_BUILDING_GENERATOR': 'v2'})
    def test_quality_content_hash_changes_but_physical_hash_does_not(self):
        items=ProgressiveTests().items(1);tile=geotiles.geobox(*geotiles.tile_of(0,0))
        results=[]
        with tempfile.TemporaryDirectory() as folder,patch.object(b,'V2_IMPORT_VERTS',600):
            for detail in ('full','lite'):
                state=progressive.DETAIL.set(detail)
                try:
                    p=SimpleNamespace(chunks=[],ctx=None,walks_raw=[],dmesh=None,
                        bld=b.road_tile(None,0,0,None,None,items=items),props=None,wires=None,park=None,
                        tmesh=None,fuel=None,rmesh=None,guardrail_rows=None,garage_sound=(),wells=None)
                    path,n,info=blockworker._write_geo_content(folder,'/vfs',tile,p)
                    data=json.loads((Path(folder)/Path(path).name).read_text())
                    self.assertEqual(info['buildingDetail'],detail)
                    results.append(data)
                finally:progressive.DETAIL.reset(state)
        self.assertNotEqual(results[0]['h'],results[1]['h'])
        self.assertGreater(len(results[0]['buildingChunks']['visual']),len(results[1]['buildingChunks']['visual']))
        self.assertEqual(results[0]['physicalHash'],results[1]['physicalHash'])


if __name__=='__main__':unittest.main()
