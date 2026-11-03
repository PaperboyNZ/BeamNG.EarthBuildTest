"""Only building far-cache miss work owns the temporary roof cache."""
from contextlib import ExitStack
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import blockworker as bw
import geotiles
import revisit
from buildgen import distant,minimum,products,roofs
from buildgen.topology import Footprint


class FarGeoRoofServiceTests(unittest.TestCase):
    def setUp(self):
        stack=ExitStack();self.addCleanup(stack.close);self.stack=stack
        self.tile=SimpleNamespace(key='g17_1_2',frame=SimpleNamespace(lat0=1.,lon0=2.))
        self.fp=Footprint(((0.,0.),(4.,0.),(4.,3.),(0.,3.)))
        self.roof=roofs.Envelope((),(),(),(),(),(0.,0.),1.)
        self.enter=stack.enter_context(patch.object(roofs,'service_cache',wraps=roofs.service_cache))
        stack.enter_context(patch.object(roofs,'_resolve_envelope',return_value=self.roof))
        stack.enter_context(patch.object(bw,'_s',SimpleNamespace(cache_dir='unused-test-cache')))
        stack.enter_context(patch.object(bw,'_md_versions',return_value={}))
        stack.enter_context(patch.object(bw,'_far_geo_stats',{'built':0,'hits':0}))
        stack.enter_context(patch.object(bw,'far_geo_names',return_value={'json':'tile.json','shape':'tile.cdae'}))
        stack.enter_context(patch.object(geotiles,'geobox',return_value=self.tile))
        stack.enter_context(patch.object(revisit,'key',return_value='test-key'))
        self.load=stack.enter_context(patch.object(revisit,'load',return_value=None))
        stack.enter_context(patch.object(revisit,'faults',return_value=0))
        stack.enter_context(patch.object(revisit,'ON',False))
        stack.enter_context(patch.object(distant,'references',return_value=None))
        stack.enter_context(patch.object(minimum,'enabled',return_value=False))
        self.write=stack.enter_context(patch.object(bw,'_write_bytes',side_effect=self.write_after_scope))

    def write_after_scope(self,*args):self.assertIsNone(roofs._SERVICE_CACHE.get())

    def call(self,kind,**kwargs):return bw.far_geo(kind,1,2,15,'unused-out','/vfs',**kwargs)

    def check_closed(self,state):
        self.assertTrue(state.closed);self.assertEqual(state.values,{});self.assertEqual(state.vertices,0)
        self.assertIsNone(roofs._SERVICE_CACHE.get())

    def test_source_and_accepted_building_misses_have_one_scope_only_during_build(self):
        for kind,accepted in (('bldfar',None),('bldfar',SimpleNamespace(revision='a'*64)),('bldsky',None)):
            with self.subTest(kind=kind,accepted=accepted is not None),ExitStack() as stack:
                seen=[];count=self.enter.call_count
                if accepted is not None:
                    stack.enter_context(patch.object(products,'valid_reference',return_value=True))
                    stack.enter_context(patch('productcache.Store',return_value=object()))
                    stack.enter_context(patch.object(products,'load_accepted',return_value=accepted))
                def build(*args):
                    state=roofs._SERVICE_CACHE.get();self.assertIsNotNone(state);self.assertFalse(state.closed)
                    self.assertIs(args[6],accepted)
                    seen.append(state);self.assertIs(roofs.envelope(self.fp,'gabled'),self.roof)
                    self.assertEqual(len(state.values),1)
                    return {'pivot':3.}, {}, 2
                with patch.object(bw,'_far_geo_build',side_effect=build):
                    ref={'key':'accepted','revision':'a'*64} if accepted is not None else None
                    self.assertIsNotNone(self.call(kind,plan_ref=ref))
                self.assertEqual(self.enter.call_count,count+1);self.check_closed(seen[0])

    def test_none_and_exception_misses_release_cache(self):
        for raises in (False,True):
            with self.subTest(raises=raises):
                seen=[]
                def build(*args):
                    state=roofs._SERVICE_CACHE.get();seen.append(state)
                    roofs.envelope(self.fp,'gabled')
                    if raises:raise RuntimeError('aborted build')
                    return None
                with patch.object(bw,'_far_geo_build',side_effect=build):
                    if raises:
                        with self.assertRaisesRegex(RuntimeError,'aborted build'):self.call('bldfar')
                    else:self.assertIsNone(self.call('bldfar'))
                self.check_closed(seen[0])

    def test_revisit_hit_and_bridge_miss_never_enter_service_scope(self):
        for kind in ('bldfar','bldsky','brfar'):
            with self.subTest(hit=kind):
                self.load.return_value=({'tile.json':b'{}'},{'n':1,'shapes':{}})
                with patch.object(bw,'_far_geo_build',side_effect=AssertionError('built revisit hit')):
                    self.assertIsNotNone(self.call(kind))
                self.assertEqual(self.enter.call_count,0)
        self.load.return_value=None
        def bridge(*args):
            self.assertIsNone(roofs._SERVICE_CACHE.get())
            return {'pivot':0.},{},0
        with patch.object(bw,'_far_geo_build',side_effect=bridge):self.assertIsNotNone(self.call('brfar'))
        self.assertEqual(self.enter.call_count,0)


if __name__=='__main__':unittest.main()
