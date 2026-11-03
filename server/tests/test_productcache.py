"""Accepted products survive workers; corruption and storage failure remain misses."""
from pathlib import Path
import sys,tempfile,threading,time,unittest,zipfile,json
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from productcache import Store,Codec,identity
from buildgen import freeze_items
from test_buildgen_regions import building


class ProductCacheTests(unittest.TestCase):
    def test_detached_building_plan_and_binary_physical_products_round_trip(self):
        from buildgen.plan import BuildingPlan
        value={'plans':freeze_items([(building('jp_temperate'),0.,0.)]),'shape':b'compiled native bytes',
               'topology':np.arange(12,dtype=np.int64).reshape(4,3),'names':('visual','collision')}
        key=identity({'source':'mapped-feature','revision':'r1','terrain':'t1','street':'s1'})
        with tempfile.TemporaryDirectory() as folder:
            saved=Store(folder).put('plans',key,value)
            self.assertEqual(saved.status,'ready')
            loaded=Store(folder).load('plans',key)
            self.assertEqual(loaded.status,'ready')
            self.assertEqual(saved.revision,loaded.revision)
            self.assertIsInstance(loaded.value['plans'][0][0],BuildingPlan)
            self.assertFalse(loaded.value['plans'][0][0].ring.flags.writeable)
            self.assertEqual(loaded.value['shape'],value['shape'])
            np.testing.assert_array_equal(loaded.value['topology'],value['topology'])
            self.assertEqual(loaded.value['plans'][0][0].facades,value['plans'][0][0].facades)

    def test_corruption_incompatibility_and_absence_are_distinct(self):
        key=identity({'id':1})
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);self.assertEqual(store.load('plans',key).status,'absent')
            self.assertEqual(store.put('plans',key,np.arange(8)).status,'ready')
            path=store.path('plans',key)
            with zipfile.ZipFile(path) as archive:blobs={n:archive.read(n) for n in archive.namelist()}
            blobs['a0.bin']=b'x'*len(blobs['a0.bin'])
            with zipfile.ZipFile(path,'w') as archive:
                for n,data in blobs.items():archive.writestr(n,data)
            self.assertEqual(store.load('plans',key).status,'corrupt')
            store.put('plans',key,{'value':1})
            with zipfile.ZipFile(path) as archive:meta=json.loads(archive.read('meta.json'))
            meta['version']=100
            with zipfile.ZipFile(path,'w') as archive:archive.writestr('meta.json',json.dumps(meta))
            self.assertEqual(store.load('plans',key).status,'incompatible')

    def test_quota_atomic_failure_and_invalid_layout_do_not_damage_accepted_product(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder,quota=7000)
            for i in range(5):store.put('physical',identity({'id':i}),b'a'*2000)
            self.assertLessEqual(sum(p.stat().st_size for p in store.root.glob('*/*.zip')),7000)
            key=identity({'retained':1});store.put('plans',key,{'value':'accepted'})
            with patch('productcache.os.replace',side_effect=OSError('disk full')):
                self.assertEqual(store.put('plans',key,{'value':'replacement'}).status,'unavailable')
            self.assertEqual(store.load('plans',key).value['value'],'accepted')
            self.assertFalse(list(store.root.glob('*/*.tmp')))
        codec=Codec();codec.blobs['a0.bin']=b'12345678'
        with self.assertRaises(ValueError):codec.decode({'array':'a0.bin','dtype':'<f8','shape':[10**10]})
        with self.assertRaises(ValueError):codec.decode({'record':'subprocess:Popen','fields':{}})

    def test_equivalent_requests_coalesce_and_cancelled_result_is_not_published(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);key=identity({'shared':1});calls=[];results=[]
            def build():calls.append(1);time.sleep(.15);return {'resolved':True}
            threads=[threading.Thread(target=lambda:results.append(store.get_or_build('plans',key,build))) for _ in range(3)]
            for thread in threads:thread.start()
            for thread in threads:thread.join()
            self.assertEqual(len(calls),1)
            self.assertTrue(all(r.value=={'resolved':True} for r in results))
            other=identity({'cancelled':1})
            result=store.get_or_build('plans',other,lambda:{'safe_physical':True},valid=lambda:False)
            self.assertEqual(result.status,'unpublished')
            self.assertEqual(result.value,{'safe_physical':True})
            self.assertEqual(store.load('plans',other).status,'absent')

    def test_small_products_are_also_bounded_by_entry_count(self):
        with tempfile.TemporaryDirectory() as folder,patch('productcache.MAX_ENTRIES',3):
            store=Store(folder)
            for i in range(12):
                self.assertEqual(store.put('plans',identity({'small':i}),i).status,'ready')
                self.assertLessEqual(len(list(store.root.glob('*/*.zip'))),3)

    def test_dead_producer_is_recovered_without_waiting_for_stale_timeout(self):
        import xproc
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);key=identity({'dead-producer':1})
            lock=Path(str(store.path('plans',key))+'.lock');lock.parent.mkdir(parents=True)
            lock.write_text('1 0 123456789')
            with patch.object(xproc,'alive',return_value=False):
                result=store.get_or_build('plans',key,lambda:{'replacement':True},wait_s=.1)
            self.assertEqual(result.status,'ready')
            self.assertFalse(lock.exists())


if __name__=='__main__':unittest.main()
