"""Early publication, reuse of facade LODs and safe staged delivery."""
from pathlib import Path
import copy,io,sys,json,tempfile,unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import progressive
from buildgen.topology import Footprint
from test_buildgen_facades import building,road


class ProgressiveTests(unittest.TestCase):
    def test_spilled_lite_cache_reuses_exact_meshes_and_cleans_up(self):
        items=self.items(17)
        with tempfile.TemporaryDirectory() as folder:
            p=progressive.Publisher(folder,'/vfs',None,'a'*32)
            with patch.object(p,'publish'),patch.object(b,'build',wraps=b.build) as build, \
                 patch.object(progressive,'LITE_MEMORY_BYTES',0):
                actual,mapping=p.build(items)
            self.assertEqual(sum(bool(c.kwargs.get('lite')) for c in build.call_args_list),len(items))
            self.assertFalse(list(p.path.parent.glob('building-lite-*')))
            expected=[m for g in p.partition(items) for m in b.build_parts(g,max_verts=b.V2_IMPORT_VERTS,with_lod=True)]
            for a,c in zip(actual,expected):
                np.testing.assert_array_equal(a[0],c[0]);np.testing.assert_array_equal(a[6][0],c[6][0])
            self.assertEqual(len(actual),len(expected))

    def test_spatial_cost_groups_preserve_every_building(self):
        items=self.items(30);items=list(reversed(items))
        p=progressive.Publisher('unused','/vfs',None,'a'*32)
        groups=p.partition(items)
        self.assertEqual({id(i[0]) for g in groups for i in g},{id(i[0]) for i in items})
        self.assertEqual(sum(map(len,groups)),len(items))
        for g in groups:
            self.assertLessEqual(len(g),progressive.GROUP_SIZE)
            centres=[i[0].ring.mean(axis=0) for i in g]
            self.assertLessEqual(max(np.linalg.norm(a-c) for a in centres for c in centres),progressive.GROUP_SPAN)

    def items(self,n=9):
        items=[]
        for i in range(n):
            x=i*20.
            s=building(fp=Footprint(((x,0),(x+12,0),(x+12,10),(x,10))),seed_id=str(i))
            items.append((s,0.,0.))
        b.doors(items,road(),0.,0.,ground=lambda xy:np.zeros(len(xy)))
        return items

    def test_shell_preserves_bounds_colour_and_courtyard(self):
        s=self.items(1)[0]
        shell=progressive.shell([s]);near=b.build([s])
        self.assertEqual(len(shell),6)
        self.assertLess(len(shell[0]),len(near[0])/3)
        self.assertTrue(np.isfinite(shell[0]).all())
        self.assertEqual(shell[5].shape,(len(shell[0]),4))
        self.assertAlmostEqual(shell[0][:,2].max(),near[0][:,2].max(),places=4)

    def test_groups_publish_before_full_completion_and_reuse_lods(self):
        count=progressive.GROUP_SIZE*2+1
        items=self.items(count);events=[]
        p=progressive.Publisher('unused','/vfs',None,'a'*32)
        with patch.object(p,'publish',side_effect=lambda g,s,m,names=None:events.append((g,s,len(m)))), \
             patch.object(b,'build',wraps=b.build) as build:
            p.shells(items)
            meshes,groups=p.build(items)
        self.assertEqual([s for g,s,n in events],[0]*len(groups)+[1]*len(groups)+[2]*len(groups))
        self.assertEqual(sum(bool(c.kwargs.get('lite')) for c in build.call_args_list),count)
        self.assertEqual(len({w for g in groups for w in g['visual']}),len(meshes))
        self.assertTrue(all(len(m[0])<=b.V2_IMPORT_VERTS for m in meshes))
        self.assertTrue(all(len(m)==7 and m[6] is not None for m in meshes))

    def test_atomic_manifest_and_coalesced_delivery(self):
        import geotiles
        with tempfile.TemporaryDirectory() as folder:
            tile=geotiles.geobox(100,100)
            tracker=SimpleNamespace(aid=1);token=progressive.begin(tracker,(100,100))
            p=progressive.Publisher(folder,'/vfs',tile,token)
            p.total=2
            mesh=progressive.shell(self.items(1))
            p.publish(0,0,[mesh]);p.publish(0,1,[mesh]);p.publish(1,0,[mesh])
            messages=[];conn=SimpleNamespace(s=SimpleNamespace(out_dir=folder),send=messages.append)
            progressive.poll(tracker,conn,1,(100,100),limit=1)
            self.assertEqual(len(messages),1);self.assertEqual(messages[0]['stage'],1)
            progressive.poll(tracker,conn,1,(100,100));progressive.poll(tracker,conn,1,(100,100))
            self.assertEqual(len(messages),2)
            self.assertEqual(progressive.finish(tracker,conn,0,(100,100),False),None)
            self.assertIn((100,100),tracker._building_progress)
            self.assertEqual(progressive.finish(tracker,conn,1,(100,100),True),token)
            self.assertFalse(tracker._building_progress)

    def test_oversized_mesh_retains_complete_disjoint_lod(self):
        item=self.items(1)[0]
        near=b.build([item]);lite=b.build([item],lite=True)
        chunks=b.split_with_lod(near,lite,300)
        self.assertGreater(len(chunks),1)
        self.assertTrue(all(len(m[0])<=300 and len(m)==8 and len(m[6][2]) for m in chunks))
        self.assertEqual(sum(len(m[2]) for m in chunks),len(near[2]))
        self.assertEqual(sum(len(m[6][2]) for m in chunks),len(lite[2]))
        import cdae
        with tempfile.TemporaryDirectory() as folder:
            encoded=[]
            for i,m in enumerate(chunks):
                path=Path(folder)/f'{i}.cdae';b.write(str(path),m);encoded.append(cdae.read(path))
            self.assertTrue(all(d['bounds']==encoded[0]['bounds'] and d['radius']==encoded[0]['radius']
                                for d in encoded))

    def test_detail_only_chunks_encode_native_empty_lod(self):
        import cdae
        item=self.items(1)[0]
        near=b.build([item]);lite=progressive.shell([item])
        chunks=b.split_with_lod(near,lite,60)
        empty=[m for m in chunks if not len(m[6][2])]
        self.assertTrue(empty)
        self.assertEqual(sum(len(m[2]) for m in chunks),len(near[2]))
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'detail.cdae';b.write(str(path),empty[0])
            data=cdae.read(path)
            self.assertEqual(len(data['meshes']),2)
            self.assertEqual(data['meshes'][1]['type'],4)

    def test_roof_solutions_survive_process_lru_eviction_within_job(self):
        from buildgen import roofs
        p=progressive.Publisher('unused','/vfs',None,'a'*32)
        fp=self.items(1)[0][0].footprint
        token=progressive.ACTIVE.set(p)
        try:
            first=roofs.envelope(fp,'hipped')
            roofs._envelope.cache_clear()
            with patch.object(roofs,'_envelope',side_effect=AssertionError('recomputed')):
                self.assertIs(roofs.envelope(fp,'hipped'),first)
            p.roof_cache_vertices=8192
            roofs.envelope(fp.translated(20,0),'hipped')
            self.assertEqual(len(p.roof_cache),1)
        finally:progressive.ACTIVE.reset(token)

    def test_final_writer_reuses_published_bytes_and_group_mapping(self):
        import roads,os
        mesh=b.build_parts(self.items(1),with_lod=True)[0]
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'BNE_BUILDING_GENERATOR':'v2'}):
            path=Path(folder)/'published.cdae';b.write(str(path),mesh)
            groups=[dict(group='0',visual=['bld'])]
            with patch.object(b,'write',side_effect=AssertionError('encoded twice')):
                roads.write_tile(folder,'/vfs',1,0,0,[],bld=([mesh],[],None,groups,{'bld':str(path)}))
            data=json.loads((Path(folder)/'roads_1_0_0.json').read_text())
            self.assertEqual(data['buildingGroups'],groups)
            self.assertEqual((Path(folder)/'bld_1_0_0.cdae').read_bytes(),path.read_bytes())

    def test_tracker_delivers_stages_before_worker_future_completes(self):
        import roads,geodesy,geotiles
        from concurrent.futures import Future
        frame=geodesy.EnuFrame(0,0);key=geotiles.tile_of(0,0)
        future=Future();submitted=[];messages=[]
        def submit(pool,fn,*args):submitted.append((fn,args));return future
        tracker=roads.GeoTracker()
        try:
            with tempfile.TemporaryDirectory() as folder, \
                 patch.object(roads,'geo_wanted',return_value={key:0}), \
                 patch.object(geotiles,'tiles_near',return_value=[(*key,0)]):
                conn=SimpleNamespace(building_progress=True,send=messages.append,s=SimpleNamespace(out_dir=folder))
                loop=SimpleNamespace(run_in_executor=submit)
                tracker.on_pose(conn,1,0,0,loop,lambda *a,**kw:None,frame=frame)
                token=submitted[0][0].keywords['progress_token']
                p=progressive.Publisher(folder,'/vfs',geotiles.geobox(*key),token)
                p.total=1
                p.publish(0,0,[progressive.shell(self.items(1))])
                tracker.on_pose(conn,1,0,0,loop,None,frame=frame)
                self.assertFalse(future.done())
                self.assertEqual(messages[-1]['type'],'building_progress')
                future.set_result(dict(content=('/vfs/final.json',0,{'h':'test','parts':{}},[])))
                final=next(m for m in messages if m['type']=='roads_tile')
                self.assertEqual(final['buildingProgressToken'],token)
                self.assertFalse(tracker._building_progress)
                self.assertFalse(p.path.exists())
        finally:tracker.close()

    def test_worker_resets_progress_context_on_failure(self):
        import blockworker
        seen=[]
        def fail(*args):
            seen.append(progressive.ACTIVE.get())
            raise RuntimeError('fixture')
        with patch.object(blockworker,'_geo_content',side_effect=fail),patch.object(blockworker,'_stack_watch'):
            with self.assertRaisesRegex(RuntimeError,'fixture'):
                blockworker.roads_geo(1,0,0,15,65536,65536,15,'unused','/vfs',True,0,True,
                                      False,False,0,False,skin=False,progress_token='a'*32)
        self.assertIsInstance(seen[0],progressive.Publisher)
        self.assertIsNone(progressive.ACTIVE.get())

    def manifest_fixture(self,folder,key=(100,100)):
        import geotiles
        tracker=SimpleNamespace(aid=1)
        token=progressive.begin(tracker,key)
        messages=[]
        conn=SimpleNamespace(s=SimpleNamespace(out_dir=folder),send=messages.append)
        position=[float(v) for v in geotiles.geobox(*key).box[:2]]+[0.]
        part=dict(shape=f'/vfs/bp_{token}_0_0_0.cdae',pos=position,pivot=0.,relief=10.)
        data=dict(v=progressive.VERSION,token=token,key=geotiles.key(*key),frame=list(geotiles.centre(*key)),
                  sequence=1,total=1,groups=[dict(group='0',stage=0,parts={'p0':part})])
        return tracker,conn,token,messages,data

    def test_cancel_before_worker_start_skips_shells_and_preserves_final_geometry(self):
        import roads,geotiles
        items=self.items(3)
        def equal(a,c):
            if isinstance(a,np.ndarray):np.testing.assert_array_equal(a,c)
            elif isinstance(a,(list,tuple)):
                self.assertEqual(len(a),len(c))
                for x,y in zip(a,c):equal(x,y)
            else:self.assertEqual(a,c)
        with tempfile.TemporaryDirectory() as folder:
            tile=geotiles.geobox(*geotiles.tile_of(0,0))
            baseline=progressive.Publisher(folder,'/vfs',tile,'a'*32)
            state=progressive.ACTIVE.set(baseline)
            try:
                with patch.object(baseline,'publish'):
                    expected=b.road_tile(None,0,0,None,None,items=items)
            finally:progressive.ACTIVE.reset(state)
            self.assertTrue(progressive.cancel(folder,'b'*32))
            cancelled=progressive.Publisher(folder,'/vfs',tile,'b'*32)
            with patch.object(progressive,'shell',side_effect=AssertionError('cancelled shell ran')):
                cancelled.shells(items)
            state=progressive.ACTIVE.set(cancelled)
            try:
                with patch.object(cancelled,'publish',side_effect=AssertionError('cancelled preview published')):
                    actual=b.road_tile(None,0,0,None,None,items=items)
            finally:progressive.ACTIVE.reset(state)
            equal(expected,actual)
            self.assertFalse(cancelled.path.exists())
            # Cancellation skipped only transient writes. The normal final tile
            # writer still receives and encodes every final mesh and collider.
            with patch.dict('os.environ',{'BNE_BUILDING_GENERATOR':'v2'}):
                roads.write_tile(folder,'/vfs',1,0,0,[],bld=actual)
            final=json.loads((Path(folder)/'roads_1_0_0.json').read_text())
            self.assertEqual(final['buildingGroups'],actual[3])
            self.assertTrue((Path(folder)/'bld_1_0_0.cdae').exists())

    def test_cancellation_between_shell_groups_stops_next_group(self):
        items=self.items(progressive.GROUP_SIZE+1)
        with tempfile.TemporaryDirectory() as folder:
            p=progressive.Publisher(folder,'/vfs',None,'c'*32)
            with patch.object(progressive,'shell',wraps=progressive.shell) as shell, \
                 patch.object(p,'publish',side_effect=lambda *a,**k:progressive.cancel(folder,p.token)) as publish:
                p.shells(items)
            self.assertEqual(shell.call_count,1)
            self.assertEqual(publish.call_count,1)

    def test_cancellation_during_encoding_prevents_manifest_and_next_mesh(self):
        import geotiles
        with tempfile.TemporaryDirectory() as folder:
            p=progressive.Publisher(folder,'/vfs',geotiles.geobox(*geotiles.tile_of(0,0)),'d'*32)
            p.total=1
            mesh=progressive.shell(self.items(1))
            write=b.write
            def cancel_after_write(path,mesh):
                write(path,mesh)
                progressive.cancel(folder,p.token)
            with patch.object(b,'write',side_effect=cancel_after_write) as encoded:
                self.assertFalse(p.publish(0,0,[mesh,mesh]))
            self.assertEqual(encoded.call_count,1)
            self.assertFalse(p.path.exists())

    def test_failed_finish_signals_worker_and_expected_token_guards_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            tracker,conn,old,messages,_=self.manifest_fixture(folder)
            replacement=progressive.begin(tracker,(100,100))
            self.assertIsNone(progressive.finish(tracker,conn,1,(100,100),False,token=old))
            self.assertEqual(tracker._building_progress[(100,100)]['token'],replacement)
            self.assertFalse(progressive.cancellation_path(folder,replacement).exists())
            self.assertEqual(progressive.finish(tracker,conn,1,(100,100),False,token=replacement),replacement)
            self.assertTrue(progressive.cancellation_path(folder,replacement).exists())
            self.assertTrue(messages[-1]['cancel'])
            self.assertEqual(messages[-1]['token'],replacement)

    def test_cancelled_token_is_not_delivered_even_with_cached_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            tracker,conn,token,messages,data=self.manifest_fixture(folder)
            path=progressive.manifest_path(folder,token)
            data['total']=2
            second=copy.deepcopy(data['groups'][0]);second['group']='1'
            second['parts']['p0']['shape']=f'/vfs/bp_{token}_1_0_0.cdae'
            data['groups'].append(second)
            path.write_text(json.dumps(data))
            progressive.poll(tracker,conn,1,(100,100),limit=0)
            self.assertEqual(messages,[])
            progressive.poll(tracker,conn,1,(100,100),limit=1)
            self.assertEqual(len(messages),1)
            self.assertIn('data',tracker._building_progress[(100,100)])
            self.assertTrue(progressive.cancel(folder,token))
            progressive.poll(tracker,conn,1,(100,100))
            self.assertEqual(len(messages),1)
            # Sticky worker observation prevents accidental resurrection if a
            # later cleanup removes the tombstone while this publisher exists.
            p=progressive.Publisher(folder,'/vfs',None,token)
            self.assertFalse(p.checkpoint())
            progressive.cancellation_path(folder,token).unlink()
            self.assertFalse(p.checkpoint())

    def test_invalid_manifest_envelopes_are_ignored_before_delivery(self):
        with tempfile.TemporaryDirectory() as folder:
            tracker,conn,token,messages,valid=self.manifest_fixture(folder)
            bad=[]
            for field,value in (('v',True),('v',2),('token','f'*32),('key','g17_101_100'),
                                ('sequence',False),('frame',[float('nan'),0.]),('frame',[0.,0.]),('total',0),
                                ('groups',{})):
                data=copy.deepcopy(valid);data[field]=value;bad.append(data)
            for field,value in (('stage',3),('group','00'),('group','999'),('parts',[])):
                data=copy.deepcopy(valid);data['groups'][0][field]=value;bad.append(data)
            for field,value in (('shape','/vfs/../bp_'+token+'_0_0_0.cdae'),
                                ('shape','/vfs/bp_'+'f'*32+'_0_0_0.cdae'),
                                ('pos',[0.,True,0.]),('pos',[10**400,0.,0.]),('pos',[1e7,0.,0.]),('relief',-1.)):
                data=copy.deepcopy(valid);data['groups'][0]['parts']['p0'][field]=value;bad.append(data)
            data=copy.deepcopy(valid);data['groups'].append(copy.deepcopy(data['groups'][0]));bad.append(data)
            path=progressive.manifest_path(folder,token)
            for i,data in enumerate(bad):
                with self.subTest(case=i):
                    path.write_text(json.dumps(data))
                    progressive.poll(tracker,conn,1,(100,100))
                    self.assertEqual(messages,[])
            path.write_text(json.dumps(valid))
            with patch.object(Path,'read_bytes',side_effect=AssertionError('unbounded read')):
                progressive.poll(tracker,conn,1,(100,100))
            self.assertEqual(len(messages),1)

    def test_manifest_read_is_bounded_even_if_file_grows_after_stat(self):
        with tempfile.TemporaryDirectory() as folder:
            tracker,conn,token,messages,_=self.manifest_fixture(folder)
            path=progressive.manifest_path(folder,token)
            path.write_bytes(b'x'*(progressive.MAX_MANIFEST_BYTES+1))
            with patch.object(Path,'open',side_effect=AssertionError('oversized file opened')):
                progressive.poll(tracker,conn,1,(100,100))
            path.write_bytes(b'{}')
            reads=[]
            class GrowingFile(io.BytesIO):
                def read(self,size=-1):
                    reads.append(size)
                    return super().read(size)
            stream=GrowingFile(b'x'*(progressive.MAX_MANIFEST_BYTES+10))
            with patch.object(Path,'open',return_value=stream):
                progressive.poll(tracker,conn,1,(100,100))
            self.assertEqual(reads,[progressive.MAX_MANIFEST_BYTES+1])
            self.assertEqual(messages,[])

    def test_duplicate_json_fields_and_regressed_sequence_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            tracker,conn,token,messages,data=self.manifest_fixture(folder)
            path=progressive.manifest_path(folder,token)
            encoded=json.dumps(data)
            path.write_text(encoded[:-1]+',"v":1}')
            progressive.poll(tracker,conn,1,(100,100))
            self.assertEqual(messages,[])
            path.write_text(encoded)
            progressive.poll(tracker,conn,1,(100,100))
            self.assertEqual(len(messages),1)
            data['groups'][0]['stage']=1
            data['groups'][0]['parts']['p0']['shape']=f'/vfs/bp_{token}_0_1_0.cdae'
            path.write_text(json.dumps(data))
            progressive.poll(tracker,conn,1,(100,100))
            self.assertEqual(len(messages),1)
            data['sequence']=2
            path.write_text(json.dumps(data))
            progressive.poll(tracker,conn,1,(100,100))
            self.assertEqual(len(messages),2)

    def test_preview_metadata_limit_preserves_all_final_meshes(self):
        items=self.items(progressive.GROUP_SIZE+1)
        with tempfile.TemporaryDirectory() as folder:
            p=progressive.Publisher(folder,'/vfs',None,'e'*32)
            groups=p.partition(items)
            expected=[m for group in groups for m in b.build_parts(group,max_verts=b.V2_IMPORT_VERTS,with_lod=True)]
            with patch.object(progressive,'MAX_MANIFEST_GROUPS',1):
                actual,mapping=p.build(items)
            self.assertEqual(len(mapping),len(groups))
            self.assertEqual(len(actual),len(expected))
            for a,c in zip(actual,expected):np.testing.assert_array_equal(a[0],c[0])
            self.assertEqual(p.final_files,{})
            self.assertFalse(p.path.exists())

    def test_optional_preview_io_failures_stop_previews_and_keep_final_meshes(self):
        import blockworker,geotiles
        items=self.items(3)
        with tempfile.TemporaryDirectory() as folder:
            tile=geotiles.geobox(*geotiles.tile_of(0,0))
            baseline=progressive.Publisher(folder,'/vfs',tile,'1'*32)
            with patch.object(baseline,'publish'):
                expected,mapping=baseline.build(items)
            failures=(lambda:patch.object(Path,'mkdir',side_effect=PermissionError('preview mkdir')),
                      lambda:patch.object(b,'write',side_effect=PermissionError('preview shape')),
                      lambda:patch.object(blockworker,'_shape_info',side_effect=OSError('preview read')),
                      lambda:patch.object(blockworker,'_write_bytes',side_effect=PermissionError('preview manifest')),
                      lambda:patch.object(progressive,'shell',side_effect=OSError('preview shell')))
            for i,failure in enumerate(failures):
                with self.subTest(failure=i):
                    publisher=progressive.Publisher(folder,'/vfs',tile,str(i+2)*32)
                    with failure():publisher.shells(items)
                    self.assertFalse(publisher.checkpoint())
                    with patch.object(publisher,'publish',side_effect=AssertionError('preview retried')):
                        actual,actual_mapping=publisher.build(items)
                    self.assertEqual(actual_mapping,mapping)
                    self.assertEqual(len(actual),len(expected))
                    for a,c in zip(actual,expected):
                        np.testing.assert_array_equal(a[0],c[0])
                        np.testing.assert_array_equal(a[2],c[2])
                        np.testing.assert_array_equal(a[6][0],c[6][0])

    def test_lite_and_detail_manifest_io_failures_preserve_final_geometry(self):
        import blockworker,geotiles
        items=self.items(3)
        with tempfile.TemporaryDirectory() as folder:
            tile=geotiles.geobox(*geotiles.tile_of(0,0))
            baseline=progressive.Publisher(folder,'/vfs',tile,'7'*32)
            with patch.object(baseline,'publish'):
                expected,mapping=baseline.build(items)
            original=blockworker._write_bytes
            for stage in (1,2):
                with self.subTest(stage=stage):
                    publisher=progressive.Publisher(folder,'/vfs',tile,str(stage+7)*32)
                    def fail_manifest(path,data):
                        if json.loads(data)['groups'][-1]['stage']==stage:
                            raise PermissionError('optional manifest')
                        return original(path,data)
                    with patch.object(blockworker,'_write_bytes',side_effect=fail_manifest):
                        actual,actual_mapping=publisher.build(items)
                    self.assertFalse(publisher.checkpoint())
                    self.assertEqual(actual_mapping,mapping)
                    self.assertEqual(len(actual),len(expected))
                    for a,c in zip(actual,expected):np.testing.assert_array_equal(a[0],c[0])

    def test_programmer_errors_in_optional_publication_are_not_hidden(self):
        import geotiles
        with tempfile.TemporaryDirectory() as folder:
            p=progressive.Publisher(folder,'/vfs',geotiles.geobox(*geotiles.tile_of(0,0)),'f'*32)
            p.total=1
            mesh=progressive.shell(self.items(1))
            with patch.object(b,'write',side_effect=RuntimeError('encoder bug')):
                with self.assertRaisesRegex(RuntimeError,'encoder bug'):p.publish(0,0,[mesh])
            with patch.object(progressive,'shell',side_effect=RuntimeError('shell bug')):
                with self.assertRaisesRegex(RuntimeError,'shell bug'):p.shells(self.items(1))

if __name__=='__main__':unittest.main()
