"""Failed regeneration preserves accepted frontage, exact cuts and exclusions."""
import copy
from pathlib import Path
import pickle
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import automatic_sites
from buildgen.topology import Footprint
from test_buildgen_facades import building


def flat(points):
    return np.zeros(len(points))


def roads():
    return [(np.array([[-50., -25.], [150., -25.]]), 3., 'residential', False)]


def item(seed='atomic', fp=None):
    spec = building(40, 20, fp=fp, **{'class': 'supermarket', 'height': 6.,
                     'roof_shape': 'flat', 'seed_id': seed, 'facade_material': 'concrete'})
    spec.gring = flat(spec.ring)
    result = (spec, 0., 0.)
    b.doors([result], roads(), 0., 0., ground=flat)
    return result


def installed():
    result = item()
    neighbor = (5., 8., .002)
    walks = [dict(pts=np.array([[-50., -20.75, 0.], [150., -20.75, 0.]]), side=1, w=2.5,
                  driveways=[neighbor], commercial_driveway_owners={'unrelated-neighbor': (neighbor,)})]
    raw = copy.deepcopy(walks)
    raw[0]['pts'][:, 2] += 7.25  # Native raw walks precede terrain draping.
    records = automatic_sites.resolve([result], roads(), 0., 0., ground=flat, walks=walks, raw_walks=raw)
    return result, walks, raw, records


class AutomaticAtomicTests(unittest.TestCase):
    def assert_retained(self, before, spec):
        self.assertEqual(spec.access.solids, before.solids)
        self.assertEqual(spec.access.landscape, before.landscape)
        self.assertEqual(spec.access.site_layout.markings, before.site_layout.markings)
        self.assertEqual(spec.access.site_layout.parking, before.site_layout.parking)
        self.assertIn('automatic_replan_retained_previous', spec.access.site_layout.diagnostics)

    def assert_same_records(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for a, b in zip(actual, expected):
            self.assertEqual(a['bne_commercial_owner'], b['bne_commercial_owner'])
            self.assertAlmostEqual(a['w'], b['w'])
            np.testing.assert_allclose(a['n'], b['n'], atol=1e-8)
            self.assertTrue(a['bne_access_only'])

    def test_success_then_unknown_ground_keeps_neighbor_cuts_and_exact_road_mouth(self):
        result, walks, raw, records = installed()
        spec = result[0]
        self.assertGreater(spec.access.site_layout.parking, 0)
        self.assertEqual(len(records), 1)
        self.assertEqual(len(walks[0]['driveways']), 2)
        before = spec.access
        saved_walks = pickle.dumps((walks, raw))
        kept = automatic_sites.resolve([result], roads(), 0., 0.,
                    ground=lambda xy: np.full(len(xy), np.nan), walks=walks, raw_walks=raw)
        self.assert_retained(before, spec)
        self.assertEqual(pickle.dumps((walks, raw)), saved_walks)
        self.assert_same_records(kept, records)
        self.assertAlmostEqual(kept[0]['n'][-1][1], -22.)

    def test_failed_connector_does_not_replace_connected_parking_with_service_pavement(self):
        result, walks, raw, records = installed()
        before = result[0].access
        saved_walks = pickle.dumps((walks, raw))
        with patch('sitegen.commercial_access.propose_access', return_value=None):
            kept = automatic_sites.resolve([result], roads(), 0., 0., ground=flat, walks=walks, raw_walks=raw)
        self.assert_retained(before, result[0])
        self.assertEqual(pickle.dumps((walks, raw)), saved_walks)
        self.assert_same_records(kept, records)

    def test_failed_prior_owner_prevents_new_batch_geometry_from_publishing(self):
        result, walks, raw, records = installed()
        second = item('new', Footprint(((45, 0), (85, 0), (85, 20), (45, 20))))
        before, new_before = result[0].access, second[0].access
        saved_walks = pickle.dumps((walks, raw))
        real_core = automatic_sites._resolve_staged
        observed = []
        def core(*args, **kwargs):
            output = real_core(*args, **kwargs)
            observed.extend(s.access for s, _, _ in args[0] if s.evidence.source_id == second[0].evidence.source_id)
            return output
        def terrain(xy):
            return np.where(np.asarray(xy)[:, 0] < 41., np.nan, 0.)
        with patch.object(automatic_sites, '_resolve_staged', side_effect=core):
            kept = automatic_sites.resolve([result, second], roads(), 0., 0.,
                            ground=terrain, walks=walks, raw_walks=raw)
        self.assertTrue(observed)
        self.assertTrue(any(automatic_sites._accepted_automatic(a) for a in observed))
        self.assert_retained(before, result[0])
        self.assertIs(second[0].access, new_before)
        self.assertEqual(pickle.dumps((walks, raw)), saved_walks)
        self.assert_same_records(kept, records)

    def test_failed_bare_road_regeneration_reconstructs_original_access_exclusion(self):
        result = item()
        records = automatic_sites.resolve([result], roads(), 0., 0., ground=flat)
        before = result[0].access
        self.assertGreater(before.site_layout.parking, 0)
        kept = automatic_sites.resolve([result], [], 0., 0., ground=flat)
        self.assert_retained(before, result[0])
        self.assert_same_records(kept, records)

    def test_successful_replacement_publishes_once_preserving_walk_dictionary_identity(self):
        result, walks, raw, records = installed()
        walk, raw_walk = walks[0], raw[0]
        before = result[0].access
        rebuilt = automatic_sites.resolve([result], roads(), 0., 0., ground=flat, walks=walks, raw_walks=raw)
        self.assertEqual(result[0].access, before)
        self.assertIs(walks[0], walk)
        self.assertIs(raw[0], raw_walk)
        self.assertEqual(len(walks[0]['driveways']), 2)
        self.assertEqual(walks[0]['driveways'], raw[0]['driveways'])
        self.assert_same_records(rebuilt, records)

    def test_losing_shallow_entry_link_retains_previous_usable_frontage(self):
        result = item()
        streets = [(np.array([[-50., -9.], [150., -9.]]), 3., 'residential', False)]
        walks = [dict(pts=np.array([[-50., -4.75, 0.], [150., -4.75, 0.]]), side=1, w=2.5)]
        b.doors([result], streets, 0., 0., ground=flat, walks=walks)
        automatic_sites.resolve([result], streets, 0., 0., ground=flat, walks=walks)
        before = result[0].access
        self.assertEqual(before.site_layout.parking, 0)
        self.assertTrue(any(s.kind == 'site_walk' for s in before.solids))
        with patch.object(automatic_sites, '_entry_link', return_value=None):
            kept = automatic_sites.resolve([result], streets, 0., 0., ground=flat, walks=walks)
        self.assert_retained(before, result[0])
        self.assertEqual(kept, [])


if __name__ == '__main__':
    unittest.main()
