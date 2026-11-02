"""Aggregate existing-pool work is bounded and leaves essential/coverage reserve."""
from pathlib import Path
import sys,threading,unittest
from unittest.mock import patch
from concurrent.futures import Future
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from budget import WorkAdmission,Backpressure
import pools


class FakeExecutor:
    def __init__(self,*a,**kw):self.futures=[]
    def submit(self,*a,**kw):
        f=Future();self.futures.append(f);return f
    def shutdown(self,*a,**kw):pass


class AdmissionTests(unittest.TestCase):
    def test_reserves_and_oversized_owner_are_independent(self):
        a=WorkAdmission(jobs=16,bytes_limit=1024,essential_bytes=256,coverage_bytes=128)
        optional=[]
        while (lease:=a.acquire('background','optional',64)) is not None:optional.append(lease)
        self.assertEqual(len(optional),8) # per-complex admission, never truncate its descriptors
        while (lease:=a.acquire('other','optional',64)) is not None:optional.append(lease)
        self.assertEqual(len(optional),10)
        essential=a.acquire('near','essential',256);coverage=a.acquire('far','coverage',128)
        self.assertIsNotNone(essential);self.assertIsNotNone(coverage)
        self.assertEqual(a.snapshot()['admitted_estimate_bytes'],1024)
        self.assertIsNone(a.acquire('huge','essential',1025))
        for lease in optional+[essential,coverage]:self.assertTrue(a.release(lease));self.assertFalse(a.release(lease))
        self.assertEqual(a.snapshot()['active_jobs'],0)

    def test_concurrent_admission_has_no_hidden_queue(self):
        a=WorkAdmission(jobs=6,bytes_limit=1000,essential_bytes=0,coverage_bytes=0)
        barrier=threading.Barrier(30);leases=[];lock=threading.Lock()
        def enter(i):
            barrier.wait();lease=a.acquire('owner-'+str(i),'essential',100)
            with lock:leases.append(lease)
        threads=[threading.Thread(target=enter,args=(i,)) for i in range(30)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(sum(x is not None for x in leases),6)
        self.assertEqual(a.snapshot()['peak_jobs'],6)

    def test_shared_pools_release_on_completion_failure_cancellation_and_submit_failure(self):
        a=WorkAdmission(jobs=2,bytes_limit=512<<20,essential_bytes=0,coverage_bytes=0)
        with patch.object(pools,'ProcessPoolExecutor',FakeExecutor):
            p=pools.RespawningPool('road',1,admission=a)
            q=pools.RespawningPool('far',1,admission=a,work_class='coverage')
            first=p.submit(abs,-1);second=q.submit(abs,-2)
            with self.assertRaises(Backpressure):q.submit(abs,-3).result()
            self.assertEqual(len(q._pool.futures),1)
            first.set_result(1);second.cancel()
            self.assertEqual(a.snapshot()['active_jobs'],0)
            third=p.submit(abs,-4);third.set_exception(OSError('dead worker'))
            self.assertEqual(a.snapshot()['active_jobs'],0)
            with patch.object(p._pool,'submit',side_effect=OSError('cannot submit')):
                with self.assertRaises(OSError):p.submit(abs,-5)
            self.assertEqual(a.snapshot()['active_jobs'],0)
            self.assertEqual(p.inflight,0);self.assertEqual(q.inflight,0)


if __name__=='__main__':unittest.main()
