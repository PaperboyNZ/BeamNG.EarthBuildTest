"""Telemetry must describe current behavior without changing emitted geometry."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import generation_baseline as baseline
from buildgen.diagnostics import DrivewayAudit


class BaselineTests(unittest.TestCase):
    def test_observation_preserves_meshes_access_and_work(self):
        for case in ('connected', 'no_footpath', 'no_garage', 'narrow', 'pedestrian_ramp',
                     'obstructed', 'missing_terrain', 'steep', 'no_roads'):
            with self.subTest(case=case):
                enabled = baseline.access_case(case)
                disabled = baseline.access_case(case, audit_enabled=False)
                enabled.pop('audit')
                disabled.pop('audit')
                self.assertEqual(enabled, disabled)

    def test_success_has_one_outcome_and_one_crossing(self):
        result = baseline.access_case('connected')
        counts = result['audit']['counts']
        self.assertEqual(counts['eligibility'], {'eligible': 1})
        self.assertEqual(counts['outcomes'], {'driveway_connected': 1})
        self.assertEqual(counts['crossings'], {'connected': 1, 'selected_before_internal_fit': 1})
        self.assertEqual(counts['work']['terrain_calls'], 1)
        self.assertLessEqual(counts['work']['terrain_points'], 4*37)

    def test_ineligible_is_not_a_failed_driveway(self):
        counts = baseline.access_case('no_garage')['audit']['counts']
        self.assertEqual(counts['eligibility'], {'no_garage_opening': 1})
        self.assertEqual(counts['outcomes'], {})
        self.assertEqual(counts['candidates'], {})

    def test_narrow_path_and_protected_ramp_have_distinct_reasons(self):
        for case, reason in (('narrow', 'footpath_width'), ('pedestrian_ramp', 'pedestrian_ramp')):
            result = baseline.access_case(case)
            counts = result['audit']['counts']
            self.assertGreater(counts['candidate_rejections'][reason], 0)
            self.assertEqual(result['emitted_crossings'], 0)
            self.assertEqual(sum(counts['outcomes'].values()), 1)

    def test_internal_failure_does_not_claim_a_usable_crossing(self):
        result = baseline.access_case('steep')
        counts = result['audit']['counts']
        self.assertEqual(result['audit']['crossing_only_feasibility'], 'not_evaluated')
        self.assertEqual(result['emitted_crossings'], 0)
        self.assertEqual(counts['crossings']['internal_route_failed_receiving_area_untested'], 1)
        self.assertNotIn('connected', counts['crossings'])

    def test_skipped_resolver_is_not_reported_as_ineligible(self):
        counts = baseline.access_case('no_roads')['audit']['counts']
        self.assertEqual(counts['resolver_skipped'], {'no_roads': 1})
        self.assertEqual(counts['eligibility'], {})
        self.assertEqual(counts['outcomes'], {})

    def test_rebase_preserves_counters_and_local_meshes(self):
        self.assertEqual(baseline.access_case('connected'),
                         baseline.access_case('connected', offset=(1000., -2000.)))

    def test_snapshot_is_detached_json_and_aggregates_without_history(self):
        audit = DrivewayAudit()
        audit.record('eligibility', 'eligible')
        before = audit.snapshot()
        audit.record('eligibility', 'eligible', 10000)
        self.assertEqual(before['counts']['eligibility'], {'eligible': 1})
        after = json.loads(json.dumps(audit.snapshot(), allow_nan=False))
        self.assertEqual(after['counts']['eligibility'], {'eligible': 10001})
        self.assertLess(len(json.dumps(after)), 600)


if __name__ == '__main__':
    unittest.main()
