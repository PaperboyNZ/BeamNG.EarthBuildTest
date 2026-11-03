"""Far-service roof reuse is bounded, quality-specific and released with scope."""
from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from buildgen import roofs,minimum_roofs,progressive
from buildgen.topology import Footprint


def rectangle():return Footprint(((0.,0.),(12.,0.),(12.,8.),(0.,8.)))


def result(label='test'):
    # Cache ownership/budget tests do not need a geometry solver invocation.
    return roofs.Envelope((),(),(),(),(),(0.,0.),1.,label)


class ServiceCacheTests(unittest.TestCase):
    def test_inference_then_mesh_lookup_survives_more_than_process_lru_capacity(self):
        fp=rectangle()
        token=progressive.DETAIL.set('full')
        try:
            with roofs.service_cache():
                first=roofs.envelope(fp,'gabled')
                for i in range(260):roofs.envelope(fp.translated(20.*(i+1),0.),'gabled')
                spec=SimpleNamespace(footprint=fp,roof='gabled',inference=None,church=False,roof_outline=None)
                with patch.object(roofs,'_resolve_envelope',side_effect=AssertionError('recomputed inference roof')):
                    self.assertIs(roofs.for_spec(spec),first)
            self.assertEqual(roofs._envelope.cache_parameters()['maxsize'],256)
        finally:progressive.DETAIL.reset(token)

    def test_minimum_compact_precedes_full_and_quality_keys_cannot_alias(self):
        fp=rectangle();compact=result('compact');full=result('full')
        token=progressive.DETAIL.set('full')
        try:
            with patch.object(minimum_roofs,'envelope',return_value=compact) as low,\
                 patch.object(roofs,'_envelope',return_value=full) as high,roofs.service_cache():
                self.assertIs(roofs.envelope(fp,'gabled'),full)
                minimum=progressive.DETAIL.set('minimum')
                try:
                    self.assertIs(roofs.envelope(fp,'gabled'),compact)
                    self.assertIs(roofs.envelope(fp,'gabled'),compact)
                finally:progressive.DETAIL.reset(minimum)
                self.assertIs(roofs.envelope(fp,'gabled'),full)
                self.assertEqual(high.call_count,1);self.assertEqual(low.call_count,1)
        finally:progressive.DETAIL.reset(token)

    def test_kind_and_variant_are_independent_keys(self):
        fp=rectangle()
        with patch.object(roofs,'_resolve_envelope',side_effect=lambda fp,kind,variant:result(kind+variant)) as solve,roofs.service_cache():
            a=roofs.envelope(fp,'gabled');b=roofs.envelope(fp,'hipped');c=roofs.envelope(fp,'gabled','shed')
            self.assertIsNot(a,b);self.assertIsNot(a,c)
            self.assertIs(roofs.envelope(fp,'gabled'),a)
            self.assertIs(roofs.envelope(fp,'hipped'),b)
            self.assertIs(roofs.envelope(fp,'gabled','shed'),c)
            self.assertEqual(solve.call_count,3)

    def test_entry_budget_rejects_first_overflow_without_eviction_or_admission(self):
        fp=Footprint(((0.,0.),(2.,0.),(0.,2.)))
        with patch.object(roofs,'_resolve_envelope',side_effect=lambda *a:result()) as solve,roofs.service_cache():
            first=roofs.envelope(fp,'gabled','0')
            for i in range(1,2048):roofs.envelope(fp,'gabled',str(i))
            state=roofs._SERVICE_CACHE.get()
            self.assertEqual(len(state.values),2048);self.assertEqual(state.vertices,6144)
            for _ in range(2):roofs.envelope(fp,'gabled','overflow')
            self.assertEqual(solve.call_count,2050)
            self.assertIs(roofs.envelope(fp,'gabled','0'),first)
            self.assertEqual(len(state.values),2048)

    def test_vertex_budget_rejects_first_overflow_and_retries_next_time(self):
        fp=Footprint(((0.,0.),(2.,0.),(3.,1.),(3.,2.),(2.,3.),(0.,3.),(-1.,2.),(-1.,1.)))
        with patch.object(roofs,'_resolve_envelope',side_effect=lambda *a:result()) as solve,roofs.service_cache():
            for i in range(1024):roofs.envelope(fp,'gabled',str(i))
            state=roofs._SERVICE_CACHE.get()
            self.assertEqual(state.vertices,8192);self.assertEqual(len(state.values),1024)
            for _ in range(2):roofs.envelope(rectangle(),'gabled')
            self.assertEqual(solve.call_count,1026)
            self.assertEqual(state.vertices,8192);self.assertEqual(len(state.values),1024)

    def test_exception_and_non_envelope_values_are_not_admitted(self):
        fp=rectangle();roof=result()
        with patch.object(roofs,'_resolve_envelope',side_effect=[ValueError('failed'),roof]) as solve,roofs.service_cache():
            with self.assertRaisesRegex(ValueError,'failed'):roofs.envelope(fp,'gabled')
            self.assertEqual(roofs._SERVICE_CACHE.get().vertices,0)
            self.assertIs(roofs.envelope(fp,'gabled'),roof)
            self.assertIs(roofs.envelope(fp,'gabled'),roof)
            self.assertEqual(solve.call_count,2)
        for value in (None,object()):
            with patch.object(roofs,'_resolve_envelope',return_value=value) as solve,roofs.service_cache():
                for _ in range(2):self.assertIs(roofs.envelope(fp,'gabled'),value)
                self.assertEqual(solve.call_count,2)
                self.assertEqual(roofs._SERVICE_CACHE.get().values,{})

    def test_nested_scopes_release_and_restore_parent_without_sharing(self):
        fp=rectangle()
        with patch.object(roofs,'_resolve_envelope',side_effect=lambda *a:result()) as solve:
            with roofs.service_cache():
                parent=roofs._SERVICE_CACHE.get();first=roofs.envelope(fp,'gabled')
                with roofs.service_cache():
                    child=roofs._SERVICE_CACHE.get();second=roofs.envelope(fp,'gabled')
                    self.assertIsNot(first,second)
                self.assertTrue(child.closed);self.assertEqual(child.values,{});self.assertEqual(child.vertices,0)
                self.assertIs(roofs._SERVICE_CACHE.get(),parent)
                self.assertIs(roofs.envelope(fp,'gabled'),first)
                self.assertEqual(solve.call_count,2)
                with self.assertRaisesRegex(RuntimeError,'nested abort'):
                    with roofs.service_cache():
                        aborted=roofs._SERVICE_CACHE.get();roofs.envelope(fp,'gabled')
                        raise RuntimeError('nested abort')
                self.assertTrue(aborted.closed);self.assertEqual(aborted.values,{});self.assertEqual(aborted.vertices,0)
                self.assertIs(roofs._SERVICE_CACHE.get(),parent)
                self.assertIs(roofs.envelope(fp,'gabled'),first)
                self.assertEqual(solve.call_count,3)
            self.assertTrue(parent.closed);self.assertEqual(parent.values,{});self.assertEqual(parent.vertices,0)
            self.assertIsNone(roofs._SERVICE_CACHE.get())

    def test_exception_exit_closes_state_even_for_copied_context(self):
        fp=rectangle()
        with patch.object(roofs,'_resolve_envelope',side_effect=lambda *a:result()) as solve:
            with self.assertRaisesRegex(RuntimeError,'abort'):
                with roofs.service_cache():
                    state=roofs._SERVICE_CACHE.get();first=roofs.envelope(fp,'gabled');copied=copy_context()
                    raise RuntimeError('abort')
            self.assertTrue(state.closed);self.assertEqual(state.values,{});self.assertEqual(state.vertices,0)
            self.assertIsNone(roofs._SERVICE_CACHE.get())
            self.assertIsNot(copied.run(roofs.envelope,fp,'gabled'),first)
            self.assertEqual(solve.call_count,2)
            self.assertEqual(state.values,{})

    def test_copied_context_in_another_thread_bypasses_live_owner_state(self):
        fp=rectangle()
        with patch.object(roofs,'_resolve_envelope',side_effect=lambda *a:result()) as solve,roofs.service_cache():
            state=roofs._SERVICE_CACHE.get();first=roofs.envelope(fp,'gabled');copied=copy_context()
            with ThreadPoolExecutor(max_workers=1) as pool:
                second=pool.submit(copied.run,roofs.envelope,fp,'gabled').result()
            self.assertIsNot(first,second);self.assertEqual(solve.call_count,2)
            self.assertEqual(len(state.values),1);self.assertFalse(state.closed)
            self.assertIs(roofs.envelope(fp,'gabled'),first)

    def test_non_footprint_bypasses_scoped_cache_and_near_publisher_is_preserved(self):
        fp=object();roof=result()
        with patch.object(roofs,'_resolve_envelope',return_value=roof) as solve,roofs.service_cache():
            for _ in range(2):self.assertIs(roofs.envelope(fp,'gabled'),roof)
            self.assertEqual(solve.call_count,2);self.assertEqual(roofs._SERVICE_CACHE.get().values,{})
        publisher=progressive.Publisher('unused','/vfs',None,'a'*32)
        token=progressive.ACTIVE.set(publisher);detail=progressive.DETAIL.set('full')
        try:
            real_fp=rectangle()
            with patch.object(roofs,'_envelope',return_value=roof) as solve:
                self.assertIs(roofs.envelope(real_fp,'gabled'),roof)
                self.assertIs(roofs.envelope(real_fp,'gabled'),roof)
                self.assertEqual(solve.call_count,1)
                self.assertEqual(publisher.roof_cache_vertices,4)
                with roofs.service_cache():
                    self.assertIs(progressive.ACTIVE.get(),publisher)
                    self.assertIs(roofs.envelope(real_fp,'gabled'),roof)
            self.assertEqual(len(publisher.roof_cache),1)
        finally:progressive.DETAIL.reset(detail);progressive.ACTIVE.reset(token)


if __name__=='__main__':unittest.main()
