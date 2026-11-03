"""Live one-owner record dispatch; shared-site production is deliberately separate."""
from dataclasses import FrozenInstanceError, replace
import json
import os
from pathlib import Path
import pickle
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
import geodesy
import productcache
from buildgen import freeze_items, site_data, site_layout
from buildgen.topology import Footprint
from sitegen.adapters import LegacySiteAdapter, adapt_validated_legacy_site
from sitegen.identity import GeographicFrame, SourceIdentity
from sitegen.plan import EntityRef, FrameContext, ResourceRecord
import test_buildgen_sites as fixtures


def adapt(site):
    return adapt_validated_legacy_site(site,
        owner=EntityRef(SourceIdentity('fixture', 'owner'), 'building'),
        frame=FrameContext('legacy_projected_xy', GeographicFrame(172.6, -43.5, 30), 1000, -300),
        source_namespace='fixture')


class RuntimeRecordsTests(unittest.TestCase):
    def test_live_fitter_and_all_emitters_preserve_legacy_geometry(self):
        old = fixtures.example()
        current = fixtures.example()
        current[0].site = adapt(current[0].site)
        for item in (old, current):
            site_layout.resolve([item], lambda p: np.zeros(len(p)), 0, 0)
        self.assertEqual(old[0].access, current[0].access)
        self.assertEqual(old[0].facades, current[0].facades)
        self.assertGreater(current[0].access.site_layout.parking, 0)
        self.assertGreater(current[0].access.site_layout.docks, 0)
        for compile in (b.build, lambda p: b.build(p, lite=True), b.collision_mesh):
            a, c = compile([old]), compile([current])
            for left, right in zip(a, c):
                if isinstance(left, np.ndarray):
                    np.testing.assert_array_equal(left, right)
                else:
                    self.assertEqual(left, right)

    def test_record_ports_control_fitting_without_mutating_source(self):
        item = fixtures.example()
        original = adapt(item[0].site)
        # Removing a measured parking interface must remove its generated lot.
        plan = replace(original.plan, interfaces=tuple(i for i in original.plan.interfaces if i.kind != 'parking'))
        item[0].site = replace(original, plan=plan)
        site_layout.resolve([item], lambda p: np.zeros(len(p)), 0, 0)
        self.assertEqual(item[0].access.site_layout.parking, 0)
        self.assertIn('parking', {i.kind for i in original.plan.interfaces})
        self.assertEqual(original.plan.surface_validation, 'unresolved')

    def test_unsupported_contract_cannot_enter_one_owner_fitter(self):
        record = adapt(fixtures.example()[0].site)
        interface = record.plan.interfaces[0]
        for status in ('proposed', 'rejected', 'connected', 'crossing_only', 'pedestrian_only'):
            with self.assertRaises(ValueError):
                replace(record, plan=replace(record.plan, interfaces=(replace(interface, status=status),)))
        resource = ResourceRecord('common', 'shared_circulation', record.evidence.ref,
                                  (record.evidence.memberships[0].member,))
        with self.assertRaises(ValueError):
            replace(record, plan=replace(record.plan, resources=(resource,)))

    def test_frozen_worker_and_typed_cache_retain_records_and_identical_collision(self):
        item = fixtures.example()
        item[0].site = adapt(item[0].site)
        site_layout.resolve([item], lambda p: np.zeros(len(p)), 0, 0)
        plans = freeze_items([item])
        self.assertIsInstance(plans[0][0].site, LegacySiteAdapter)
        with self.assertRaises(FrozenInstanceError):
            plans[0][0].site.plan = None
        codec = productcache.Codec()
        encoded = codec.encode(plans)
        for decoded in (pickle.loads(pickle.dumps(plans)), codec.decode(encoded)):
            self.assertEqual(decoded[0][0].site, plans[0][0].site)
            for left, right in zip(b.collision_mesh(plans), b.collision_mesh(decoded)):
                if isinstance(left, np.ndarray): np.testing.assert_array_equal(left, right)
                else: self.assertEqual(left, right)

    def test_infrastructure_cut_clears_record_site_just_like_legacy(self):
        from test_buildgen_topology import planned
        item = fixtures.example()
        record = adapt(replace(item[0].site, owner_footprint=item[0].footprint))
        cut = Footprint(((0, 0), (20, 0), (20, 25), (0, 25)))
        self.assertIsNone(planned(cut, _site=record).site)
        self.assertEqual(planned(item[0].footprint, _site=record).site, record)

    def test_project_record_uses_original_frame_and_validated_catalogue(self):
        frame = geodesy.EnuFrame(-43.5, 172.6, 30)
        geometry = dict(type='Polygon', coordinates=[[[172.6, -43.5], [172.601, -43.5],
            [172.601, -43.499], [172.6, -43.499], [172.6, -43.5]]])
        props = dict(site_id='survey-site', owner_id='building', source='survey', release='1',
                     obstacles_complete=True)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'sites.json'
            with patch.dict(os.environ, {'BNE_BUILDING_SITES': str(path)}):
                try:
                    path.write_text(json.dumps(dict(type='FeatureCollection', features=[
                        dict(type='Feature', geometry=geometry, properties=props)])))
                    site_data.catalogue.cache_clear()
                    old = site_data.project('building', frame, 1000, -300)
                    record = site_data.project_record('building', frame, 1000, -300)
                    self.assertEqual(record.to_legacy_site(), old)
                    self.assertEqual(record.evidence.frame,
                        FrameContext('legacy_projected_xy', GeographicFrame(172.6, -43.5, 30), 1000, -300))
                    self.assertEqual(record.evidence.memberships[0].member.identity.feature_id, 'building')
                    self.assertIsNone(site_data.project_record('missing', frame))
                    props['obstacles_complete'] = False
                    path.write_text(json.dumps(dict(type='FeatureCollection', features=[
                        dict(type='Feature', geometry=geometry, properties=props)])))
                    site_data.catalogue.cache_clear()
                    with self.assertRaises(ValueError):
                        site_data.project_record('building', frame)
                finally:
                    site_data.catalogue.cache_clear()

    def test_legacy_identifier_outside_record_budget_keeps_physical_input(self):
        site = replace(fixtures.example()[0].site, id='site-'+'x'*512)
        with patch.object(site_data, 'project', return_value=site), self.assertLogs('buildgen.site_data', 'WARNING'):
            self.assertIs(site_data.project_record('owner', geodesy.EnuFrame(-43.5, 172.6)), site)


if __name__ == '__main__': unittest.main()
