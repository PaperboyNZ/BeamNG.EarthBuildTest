"""Accepted-plan refreshes use the existing far queue and retain prior coverage."""
from concurrent.futures import Future
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import geodesy
import geotiles
import vegetation
import roads
import test_sitegen_progress_lifecycle as near_tests


class Loop:
    def __init__(self):self.jobs=[]
    def run_in_executor(self,pool,fn,*args):
        f=Future();self.jobs.append((fn,args,f));return f


class FarPlanLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tracker=vegetation.Tracker(100,200,1,'bldfar',geo=True)
        self.addCleanup(self.tracker.close)
        self.frame=geodesy.EnuFrame(0.,0.)
        self.key=geotiles.tile_of(0.,0.);self.other=(self.key[0]+1,self.key[1])
        self.want=[self.key];self.distance=0.
        self.loop=Loop();self.messages=[]
        self.conn=SimpleNamespace(send=self.messages.append)
        self.clock=patch.object(vegetation.time,'monotonic',return_value=10.);self.now=self.clock.start();self.addCleanup(self.clock.stop)
        near=patch.object(geotiles,'tiles_near',side_effect=lambda *a,**kw:[(*k,0.) for k in self.want])
        near.start();self.addCleanup(near.stop)
        dist=patch.object(self.tracker,'_geo_dist',side_effect=lambda *a,**kw:self.distance)
        dist.start();self.addCleanup(dist.stop)

    def pose(self):
        self.tracker.on_pose(self.conn,1,0.,0.,self.loop,lambda *a:None,frame=self.frame)

    def finish(self,result=True):
        _,args,f=self.loop.jobs[-1]
        if isinstance(result,Exception):f.set_exception(result)
        elif result is None:f.set_result(None)
        else:f.set_result(('/vfs/far.json',1,geotiles.centre(*args),0.,{}))

    def test_cold_inflight_refresh_missing_first_and_latest_coalescing(self):
        self.pose();self.tracker.refine(self.key,'accepted-1')
        self.finish();self.assertIn(self.key,self.tracker.sent)
        self.assertEqual(self.tracker.refinements,{self.key:'accepted-1'})
        self.want=[self.key,self.other];self.pose()
        self.assertEqual(self.loop.jobs[-1][1],self.other,'missing coverage precedes optional refinement')
        self.finish();self.pose()
        self.assertEqual(self.loop.jobs[-1][1],self.key)
        self.assertIn(self.key,self.tracker.sent,'accepted far coverage stays sent during replacement')
        for i in range(2,101):self.tracker.refine(self.key,'accepted-'+str(i))
        self.assertEqual(len(self.tracker.refinements),1)
        self.assertEqual(len(self.loop.jobs),3,'supersession cannot start additional workers')
        self.finish();self.assertEqual(self.tracker.refinements,{self.key:'accepted-100'})
        self.pose();self.finish();self.assertFalse(self.tracker.refinements)
        jobs=len(self.loop.jobs)
        self.tracker.refine(self.key,'accepted-100');self.pose()
        self.assertEqual(len(self.loop.jobs),jobs,'repeated accepted reference does not rebuild distant content')

    def test_failed_refresh_retains_coverage_and_retries_without_busy_loop(self):
        self.pose();self.finish();self.tracker.refine(self.key,'accepted')
        self.pose();before=len(self.messages);self.finish(OSError('worker failed'))
        self.assertIn(self.key,self.tracker.sent)
        self.assertEqual(len(self.messages),before)
        self.pose();self.assertEqual(len(self.loop.jobs),2,'failed optional refresh waits for retry interval')
        self.now.return_value=12.;self.pose();self.finish(None)
        self.assertIn(self.key,self.tracker.sent)
        self.now.return_value=14.;self.pose();self.finish()
        self.assertFalse(self.tracker.refinements)
        self.assertFalse(any(m['type'].endswith('_drop') for m in self.messages))

    def test_drop_during_refresh_cannot_resurrect_far_tile_or_desired_revision(self):
        self.pose();self.finish();self.tracker.refine(self.key,'accepted');self.pose()
        self.want=[];self.distance=1000.;self.pose()
        self.assertNotIn(self.key,self.tracker.sent)
        before=len(self.messages);self.finish()
        self.assertEqual(len(self.messages),before)
        self.assertFalse(self.tracker.refinements);self.assertFalse(self.tracker.refined)
        self.assertFalse(self.tracker.refinement_jobs)
        self.want=[self.key];self.distance=0.;self.pose();self.finish()
        self.assertIn(self.key,self.tracker.sent,'revisit can build clean coverage after retirement')

    def test_reversal_cancels_inert_refresh_but_reverses_an_inflight_one(self):
        self.pose();self.finish();self.tracker.refine(self.key,'A');self.pose();self.finish()
        self.tracker.refine(self.key,'B');self.tracker.refine(self.key,'A')
        jobs=len(self.loop.jobs);self.pose();self.assertEqual(len(self.loop.jobs),jobs)
        self.tracker.refine(self.key,'B');self.pose();self.tracker.refine(self.key,'A');self.finish()
        self.assertEqual(self.tracker.refinements,{self.key:'A'})
        self.pose();self.finish();self.assertFalse(self.tracker.refinements)

    def test_stale_future_and_close_cannot_publish_refresh(self):
        self.pose();active=self.loop.jobs[-1][2]
        stale=Future();stale.set_result(('/stale.json',1,(0.,0.),0.,{}))
        self.tracker._built_geo(self.conn,self.key,stale)
        self.assertIs(self.tracker.futs[self.key],active)
        self.assertFalse(self.messages)
        self.tracker.close();active.set_result(('/closed.json',1,(0.,0.),0.,{}))
        self.assertFalse(self.messages);self.assertFalse(self.tracker.refinements)
        jobs=len(self.loop.jobs);self.pose();self.assertEqual(len(self.loop.jobs),jobs)

    def test_compact_plan_references_survive_near_retirement_and_are_bounded(self):
        near=roads.GeoTracker()
        ref={'key':'a'*64,'revision':'b'*64}
        near.info[self.key]={'acceptedPlan':ref};near.remember_plan(self.key,ref)
        near.info.pop(self.key)
        self.assertEqual(near.plan_reference(self.key),ref)
        detached=near.plan_reference(self.key);detached['revision']='c'*64
        self.assertEqual(near.plan_reference(self.key),ref)
        for i in range(near.PLAN_REFS_KEPT+10):near.remember_plan((i,1),ref)
        self.assertEqual(len(near.plan_refs),near.PLAN_REFS_KEPT)
        near.remember_plan((0,1),ref);near.remember_plan((0,1),None)
        self.assertIsNone(near.plan_reference((0,1)))

    def test_live_near_completion_records_reference_and_coalesces_far_refresh(self):
        fixture=near_tests.ProgressLifecycleTests('test_close_signals_every_active_token')
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        near,_,conn,future,_,_=fixture.launch()
        conn.bldfar=self.tracker;self.tracker.sent.add(fixture.key)
        ref={'key':'a'*64,'revision':'b'*64}
        result={'content':('/vfs/near.json',1,{'h':'accepted','parts':{},'acceptedPlan':ref},[])}
        with patch('roads.staging.inline_json',return_value=None):future.set_result(result)
        self.assertEqual(near.plan_reference(fixture.key),ref)
        self.assertEqual(self.tracker.refinements,{fixture.key:ref['revision']})

    def test_live_near_completion_refreshes_the_parent_skyline_inventory(self):
        from buildgen.distant import reference_revision
        fixture=near_tests.ProgressLifecycleTests('test_close_signals_every_active_token')
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        near,_,conn,future,_,_=fixture.launch()
        parent=geotiles.parent(*fixture.key,geotiles.Z,geotiles.SKY_Z)
        sky=vegetation.Tracker(100,200,1,'bldsky',geo=True,z=geotiles.SKY_Z)
        self.addCleanup(sky.close);sky.sent.add(parent);conn.bldsky=sky
        ref={'key':'a'*64,'revision':'b'*64}
        result={'content':('/vfs/near.json',1,{'h':'accepted','parts':{},'acceptedPlan':ref},[])}
        with patch('roads.staging.inline_json',return_value=None):future.set_result(result)
        self.assertEqual(sky.refinements,{parent:reference_revision({fixture.key:ref})})

    def test_safe_partial_fallback_acknowledges_attempted_parent_without_busy_loop(self):
        self.pose();self.finish();self.tracker.refine(self.key,'desired-all-children');self.pose()
        conn=SimpleNamespace(send=self.messages.append,s=SimpleNamespace(out_dir='/fixture'))
        data={'acceptedPlan':{'revision':'available-subset'}}
        future=self.loop.jobs[-1][2]
        with patch('vegetation.staging.inline_json',return_value=data):
            # Invoke the real captured callback, using this connection so the
            # aggregate's actual accepted subset is visible to the tracker.
            self.conn.s=conn.s
            future.set_result(('/vfs/hybrid.json',1,geotiles.centre(*self.key),0.,{}))
        self.assertFalse(self.tracker.refinements)
        jobs=len(self.loop.jobs);self.pose();self.assertEqual(len(self.loop.jobs),jobs)

    def test_pending_refresh_crosses_rebase_without_duplicate_job(self):
        self.pose();self.finish();self.tracker.refine(self.key,'accepted');self.pose()
        jobs=len(self.loop.jobs)
        self.tracker.on_pose(self.conn,2,0.,0.,self.loop,lambda *a:None,frame=geodesy.EnuFrame(.001,.001))
        self.assertEqual(len(self.loop.jobs),jobs)
        self.finish()
        self.assertEqual(self.messages[-1]['anchorId'],2)
        self.assertFalse(self.tracker.refinements)


if __name__=='__main__':unittest.main()
