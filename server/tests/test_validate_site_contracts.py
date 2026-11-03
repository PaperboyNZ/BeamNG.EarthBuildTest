"""Offline M1 export must retain the validated one-owner legacy boundary."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'server'))
sys.path.insert(0, str(ROOT / 'tools'))
import validate_building_sites as validator
from buildgen import site_data
from sitegen.adapters import adapt_validated_legacy_site
from sitegen.plan import SiteGraph


def feature(name='site-a', owner='building-a', longitude=172.6):
    def polygon(west, south, east, north):
        return dict(type='Polygon', coordinates=[[[west, south], [east, south], [east, north],
                                                  [west, north], [west, south]]])
    exclusion = polygon(longitude + .0003, -43.4998, longitude + .0004, -43.4997)
    return dict(type='Feature', geometry=polygon(longitude, -43.5, longitude + .001, -43.499),
                properties=dict(site_id=name, owner_id=owner, source='fixture-survey', release='release-1',
                                obstacles_complete=True, exclusions=[exclusion, exclusion], dock_rise=1.1,
                                ports=[dict(kind='parking', coordinates=[
                                    [longitude + .0001, -43.5, 30.], [longitude + .00015, -43.5, 30.]])]))


class ValidateSiteContractsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(site_data.catalogue.cache_clear)
        self.directory = Path(self.tmp.name)
        self.catalogue = self.directory / 'sites.geojson'
        self.output = self.directory / 'records' / 'sites.json'

    def write(self, features, path=None):
        path = path or self.catalogue
        path.write_text(json.dumps(dict(type='FeatureCollection', features=features)), encoding='utf-8')
        return path

    def export(self, **kwargs):
        return validator.validate(self.catalogue, records_out=self.output,
                                  site_namespace='survey:sites', owner_namespace='overture:buildings', **kwargs)

    def test_existing_helper_and_cli_summary_are_preserved_without_export(self):
        self.write([feature()])
        expected = dict(valid=True, properties=1, sha256=hashlib.sha256(self.catalogue.read_bytes()).hexdigest(),
                        note='Geometry/evidence validation only; runtime terrain and building fit still apply.')
        with mock.patch.dict(os.environ, {'BNE_BUILDING_SITES': 'previous-catalogue'}):
            self.assertEqual(validator.validate(self.catalogue), expected)
            self.assertEqual(os.environ['BNE_BUILDING_SITES'], 'previous-catalogue')
        stdout = StringIO()
        with redirect_stdout(stdout):
            validator.main([str(self.catalogue)])
        self.assertEqual(json.loads(stdout.getvalue()), expected)
        self.assertFalse(self.output.exists())

    def test_export_preserves_projection_and_declares_pending_work(self):
        self.write([feature()])
        original = self.catalogue.read_bytes()
        summary = self.export()
        payload = self.output.read_text(encoding='utf-8')
        graph = SiteGraph.from_json(payload)
        self.assertEqual(graph.to_json() + '\n', payload)
        self.assertEqual(summary['records_schema_version'], 1)
        self.assertEqual(summary['record_sites'], 1)
        self.assertEqual(summary['physical_surface_validation'], 'pending')
        self.assertEqual(summary['canonical_migration'], 'pending')
        self.assertEqual(self.catalogue.read_bytes(), original)
        evidence = graph.sites[0].evidence
        self.assertEqual(evidence.identity.namespace, 'survey:sites')
        self.assertEqual(evidence.memberships[0].member.identity.namespace, 'overture:buildings')
        self.assertEqual(evidence.memberships[0].member.identity.feature_id, 'building-a')
        self.assertEqual(evidence.frame.kind, 'legacy_projected_xy')
        self.assertEqual((evidence.frame.frame.longitude, evidence.frame.frame.latitude, evidence.frame.frame.height),
                         (172.6, -43.5, 0.))
        self.assertEqual((evidence.frame.x0, evidence.frame.y0), (0., 0.))
        self.assertEqual(len(evidence.exclusions), 2)
        self.assertEqual(evidence.physical_extents, ())
        self.assertEqual(graph.sites[0].surface_validation, 'unresolved')
        with self.assertRaises(ValueError):
            evidence.frame.require_canonical()

    def test_namespaces_are_required_for_helper_and_cli(self):
        self.write([feature()])
        for namespaces in ({}, {'site_namespace': 'survey'}, {'owner_namespace': 'buildings'}):
            with self.subTest(namespaces=namespaces), self.assertRaisesRegex(ValueError, 'explicit'):
                validator.validate(self.catalogue, records_out=self.output, **namespaces)
        stderr = StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as exc:
            validator.main([str(self.catalogue), '--records-out', str(self.output)])
        self.assertEqual(exc.exception.code, 2)
        self.assertIn('--site-namespace and --owner-namespace', stderr.getvalue())
        self.assertFalse(self.output.exists())
        # Empty inputs must not evade namespace validation by skipping adapters.
        self.write([])
        with self.assertRaises(ValueError):
            validator.validate(self.catalogue, records_out=self.output,
                               site_namespace=' padded ', owner_namespace='buildings')

    def test_reusable_helper_does_not_keep_stale_catalogues(self):
        self.write([feature()])
        second = self.write([feature(), feature('site-b', 'building-b', 172.61)], self.directory / 'other.geojson')
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('BNE_BUILDING_SITES', None)
            self.assertEqual(validator.validate(self.catalogue)['properties'], 1)
            self.assertNotIn('BNE_BUILDING_SITES', os.environ)
            self.assertEqual(validator.validate(second)['properties'], 2)
            # Changing content at the same path also requires a fresh catalogue.
            self.write([])
            self.assertEqual(validator.validate(self.catalogue)['properties'], 0)
            self.assertEqual(site_data.catalogue.cache_info().currsize, 0)

    def test_invalid_legacy_inputs_still_fail_before_export(self):
        missing_inventory = feature()
        missing_inventory['properties'].pop('obstacles_complete')
        bad_port = feature()
        bad_port['properties']['ports'][0]['coordinates'][1][0] = 172.600101
        cases = ([missing_inventory], [feature(), feature('overlap', 'other-owner')], [bad_port])
        self.output.parent.mkdir()
        for features in cases:
            with self.subTest(features=features):
                self.write(features)
                self.output.write_bytes(b'existing output')
                with self.assertRaises(ValueError):
                    validator.validate(self.catalogue)
                with self.assertRaises(ValueError):
                    self.export()
                self.assertEqual(self.output.read_bytes(), b'existing output')

    def test_all_project_validation_finishes_before_any_adapter(self):
        bad_port = feature('site-b', 'building-b', 172.61)
        bad_port['properties']['ports'][0]['coordinates'][1][0] = 172.610101
        self.write([feature(), bad_port])
        with mock.patch('sitegen.adapters.adapt_validated_legacy_site', wraps=adapt_validated_legacy_site) as adapt:
            with self.assertRaises(ValueError):
                self.export()
            adapt.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_export_is_deterministic_under_catalogue_enumeration_order(self):
        self.write([feature('site-z', 'building-z', 172.61), feature('site-a', 'building-a')])
        self.export()
        first = self.output.read_bytes()
        original_catalogue = site_data.catalogue

        def reverse_rows():
            digest, rows = original_catalogue()
            return digest, dict(reversed(tuple(rows.items())))

        reverse_rows.cache_clear = original_catalogue.cache_clear
        with mock.patch.object(site_data, 'catalogue', reverse_rows):
            self.export()
        self.assertEqual(first, self.output.read_bytes())
        graph = SiteGraph.from_json(first)
        self.assertEqual(sorted(p.evidence.identity.feature_id for p in graph.sites), ['site-a', 'site-z'])

    def test_input_catalogue_cannot_be_used_as_output(self):
        self.write([feature()])
        original = self.catalogue.read_bytes()
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            validator.validate(self.catalogue, records_out=self.catalogue,
                               site_namespace='survey', owner_namespace='buildings')
        self.assertEqual(self.catalogue.read_bytes(), original)

    def test_adapter_roundtrip_mismatch_prevents_output(self):
        self.write([feature()])

        def corrupt(*args, **kwargs):
            adapter = adapt_validated_legacy_site(*args, **kwargs)
            return mock.Mock(plan=adapter.plan, to_legacy_site=lambda: None)

        with mock.patch('sitegen.adapters.adapt_validated_legacy_site', side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, 'changed legacy site output'):
                self.export()
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
