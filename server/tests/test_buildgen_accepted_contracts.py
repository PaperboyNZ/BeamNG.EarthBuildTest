"""Acceptance fingerprints survive storage and reject implicit plan revisions."""
from dataclasses import replace
import tempfile
import threading
import unittest
from unittest.mock import patch

from buildgen import accepted_contracts as contracts, freeze_items, products
from buildgen.presentation_contracts import ComponentProduct
from productcache import Store
from test_buildgen_facades import building
import test_buildgen_products as fixtures


class AcceptedContractTests(unittest.TestCase):
    def setUp(self):
        self.items = freeze_items([(building(), 0., 0.)])
        self.deps = dict(frame={'lon0':174., 'lat0':-36.}, building_site_policy=2,
                         plan_schema=30)
        sem, phy = contracts.capture(self.items, 'a'*16, self.deps['frame'], 2)
        self.value = dict(plans=self.items, physical_revision='a'*16,
                          semantic_plan=sem, physical_plan=phy)

    def test_capture_never_plans_or_compiles_and_survives_product_store(self):
        with patch('buildgen.facades.plan', side_effect=AssertionError('eager layout')):
            sem, phy = contracts.capture(self.items, 'a'*16, self.deps['frame'], 2)
        self.assertEqual(sem, self.value['semantic_plan'])
        self.assertEqual(phy, self.value['physical_plan'])
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            store.put('accepted-plan', 'a'*64, self.value)
            restored = store.load('accepted-plan', 'a'*64)
            self.assertEqual(restored.status, 'ready')
            self.assertTrue(contracts.valid(restored.value, self.deps))

    def test_mutating_identity_physics_frame_or_schema_needs_acceptance(self):
        spec, lo, hi = self.items[0]
        for change in (dict(seed=spec.seed+.01), dict(height=spec.height+1),
                       dict(door=(0, 2.)), dict(gring=[1.]*len(spec.ring))):
            newer = dict(self.value, plans=((replace(spec, **change), lo, hi),))
            self.assertFalse(contracts.valid(newer, self.deps), change)
        self.assertFalse(contracts.valid(dict(self.value, physical_revision='b'*16), self.deps))
        self.assertFalse(contracts.valid(self.value, dict(self.deps, frame={'lat0':0.,'lon0':0.})))
        self.assertFalse(contracts.valid(self.value, dict(self.deps, plan_schema=29)))
        self.assertFalse(contracts.valid({k:v for k,v in self.value.items() if k!='semantic_plan'}, self.deps))

    def test_weather_only_changes_leave_both_accepted_revisions_unchanged(self):
        spec, lo, hi = self.items[0]
        changed = ((replace(spec, weather_exposure=(.3,.8), diagnostics=('presentation',)), lo, hi),)
        expected = contracts.capture(self.items, 'a'*16, self.deps['frame'], 2)
        self.assertEqual(expected, contracts.capture(changed, 'a'*16, self.deps['frame'], 2))


class StoredComponentTests(unittest.TestCase):
    # Exercise the real publication, store and independent physical fixtures.
    setUp = fixtures.IndependentProductsTests.setUp
    parts = fixtures.IndependentProductsTests.parts
    retain_lite = fixtures.IndependentProductsTests.retain_lite

    def test_refinement_is_a_versioned_immutable_component_with_resource_cost(self):
        self.retain_lite()
        out = self.root/'component'; out.mkdir()
        self.assertIsNotNone(products.refine(__import__('blockworker'), self.tile, self.key,
                                            str(out), '/component', 'full'))
        store = Store(str(self.cache))
        paths = list((store.root/'presentation-component').glob('*.zip'))
        self.assertEqual(len(paths), 1)
        result = store.load('presentation-component', paths[0].stem)
        product = result.value
        self.assertIsInstance(product, ComponentProduct)
        self.assertEqual(product.component.key(), paths[0].stem)
        self.assertEqual(product.cost.encoded_bytes, sum(len(v) for _,v in product.files))
        self.assertGreater(product.cost.vertices, 0)
        self.assertGreater(product.cost.primitives, 0)
        self.assertEqual(product.component.system, 'legacy_building')
        self.assertEqual(product.component.physical_revision,
                         store.load('accepted-plan', self.key).value['physical_revision'])
        publication = product.publication()
        publication['entries'].clear(); publication['files'].clear()
        self.assertTrue(product.publication()['entries'])
        self.assertTrue(product.files)

    def test_stale_fingerprints_cannot_refine_or_be_used_for_far_coverage(self):
        self.retain_lite()
        store = Store(str(self.cache)); saved = store.load('accepted-plan', self.key)
        spec,lo,hi = saved.value['plans'][0]
        value = dict(saved.value, plans=((replace(spec, seed=spec.seed+.01),lo,hi),))
        store.put('accepted-plan', self.key, value)
        self.assertIsNone(products.load_accepted(store, self.tile, self.key))
        self.assertIsNone(products.refine(__import__('blockworker'), self.tile, self.key,
                                         str(self.root), '/stale', 'full'))

    def test_late_cold_producer_cannot_overwrite_accepted_physics_or_identity(self):
        import blockworker as bw
        self.retain_lite()
        store=Store(str(self.cache)); before=store.load('accepted-plan',self.key)
        spec,lo,hi=self.plans[0]
        self.plans=((replace(spec,seed=spec.seed+.01),lo,hi),)
        out=self.root/'late';out.mkdir();P=self.parts('full')
        _,n,info=bw._write_geo_content(str(out),'/late',self.tile,P)
        self.assertFalse(products.retain(bw,self.tile,self.key,self.dependencies,P,str(out),'/late',n,info,self.watched))
        self.assertEqual(store.load('accepted-plan',self.key).revision,before.revision)
        self.assertIsNotNone(products.refine(bw,self.tile,self.key,str(out),'/late','full'))

    def test_acceptance_lock_does_not_fall_back_to_unlocked_writes(self):
        store=Store(str(self.cache)); acquired=[]
        with products._acceptance_lock(store,self.key) as first:
            self.assertTrue(first)
            def compete():
                with products._acceptance_lock(store,self.key,wait_s=.01) as held:
                    acquired.append(held)
            thread=threading.Thread(target=compete);thread.start();thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(acquired,[False])
        with patch('buildgen.products.os.open',side_effect=PermissionError('unavailable cache')):
            with products._acceptance_lock(store,self.key) as held:self.assertFalse(held)
