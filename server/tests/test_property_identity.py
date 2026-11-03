import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import property_identity as pi
import mapgeom


class Frame:
    def enu_to_geodetic(self, e, n, u):
        return np.asarray(n)/100000, np.asarray(e)/100000, u
    def geodetic_to_enu(self, lat, lon, h):
        return np.asarray(lon)*100000, np.asarray(lat)*100000, h


def places(rows):
    n = len(rows)
    f = mapgeom.Features('places', np.array([r[0] for r in rows]), np.ones(n, np.uint8),
                         np.arange(n+1), np.arange(n+1), np.arange(n+1),
                         np.array([[r[1]/100000, r[2]/100000] for r in rows]),
                         attrs={'name': np.array([r[3] for r in rows]),
                                'basic_category': np.array([r[4] for r in rows]),
                                'confidence': np.full(n, np.nan),
                                'src_dataset': np.array(['OpenStreetMap']*n),
                                'src_record': np.array(['source:1']*n)})
    return f


def box(x, y, width=20, height=20):
    return np.array([[x,y], [x+width,y], [x+width,y+height], [x,y+height]])


class PropertyIdentityTest(unittest.TestCase):
    def test_explicit_use_thresholds_and_unknown_area(self):
        for width, expected, modifier in [(19, 'grocery_store', None), (20, 'supermarket', None),
                                          (50, 'supermarket', 'large')]:
            result = pi.resolve(box(0, 0, width, width), {'class':'grocery_store', 'num_floors':1}, Frame())
            self.assertEqual((result['kind'],result['size_modifier']), (expected,modifier))
            self.assertEqual(result['area_basis'], 'exclusive_single_storey_footprint_proxy')
        result = pi.resolve(box(0,0,50,50), {'class':'grocery_store'}, Frame())
        self.assertEqual(result['kind'], 'food_retail_size_unresolved')
        self.assertIsNone(result['premises_area'])

    def test_containment_does_not_change_host_or_name(self):
        f = places([('a', 4, 4, 'Hôpital Māori', 'hospital'), ('b', 6, 6, 'Cafe', 'cafe')])
        result = pi.resolve(box(0,0), {'class':'apartments', 'name':'The Building'}, Frame(), layers=[f])
        self.assertIsNone(result['kind'])
        self.assertEqual(result['display_name'], 'The Building')
        self.assertEqual(result['status'], 'ambiguous')
        self.assertEqual(result['occupants'][0]['name'], 'Hôpital Māori')
        self.assertIsNone(result['occupants'][0]['confidence'])
        self.assertEqual(result['occupants'][0]['source_record'], 'source:1')
        self.assertIsNone(pi.resolve(box(30,0), {'class':'apartments'}, Frame(), layers=[f]))
        self.assertIs(pi.index(f), pi.index(f))

    def test_mapped_hospital_host_survives_ambiguous_occupants(self):
        f = places([('a', 4, 4, 'Physio', 'physical_therapy'),
                    ('b', 6, 6, 'Gift shop', 'gift_shop')])
        result = pi.resolve(box(0,0), {'class':'hospital', 'name':'Hôpital Māori'}, Frame(), layers=[f])
        self.assertEqual((result['kind'], result['display_name'], result['status']),
                         ('hospital', 'Hôpital Māori', 'supported'))
        self.assertEqual(result['occupant_association'], 'ambiguous')
        self.assertTrue(all(o['association'] == 'contained' for o in result['occupants']))
        retail = pi.resolve(box(0,0), {'class':'retail'}, Frame(), layers=[f])
        self.assertIsNone(retail['kind'])
        self.assertIsNone(retail['display_name'])
        self.assertEqual((retail['status'], retail['occupant_association']), ('ambiguous', 'ambiguous'))

    def test_mixed_occupants_do_not_establish_exclusive_area(self):
        f = places([('a', 4, 4, 'Grocery', 'grocery_store'), ('b', 6, 6, 'Clinic', 'clinic')])
        result = pi.resolve(box(0,0,50,50), {'class':'grocery_store', 'num_floors':1}, Frame(), layers=[f])
        self.assertIsNone(result['premises_area'])
        self.assertEqual(result['kind'], 'food_retail_size_unresolved')

    def test_non_grocery_tenant_does_not_establish_exclusive_area(self):
        f = places([('a', 4, 4, 'Clinic', 'clinic')])
        result = pi.resolve(box(0,0,50,50), {'class':'grocery_store', 'num_floors':1}, Frame(), layers=[f])
        self.assertEqual(result['kind'], 'food_retail_size_unresolved')
        self.assertIsNone(result['premises_area'])

    def test_compatible_subtype_and_inherited_part(self):
        for cls, sub, expected in [('commercial', 'grocery_store', 'supermarket'),
                                    ('industrial', 'trade_units', 'trade_units'),
                                    ('civic', 'hospital', 'hospital'),
                                    ('residential', 'hospital', None),
                                    ('commercial', 'hospital', None)]:
            result = pi.resolve(box(0, 0), {'class': cls, 'subtype': sub, 'num_floors': 1}, Frame())
            self.assertEqual(result['kind'] if result else None, expected)
        part = {'class': 'hospital', '_part': True, '_inherited_fields': ('class',)}
        self.assertIsNone(pi.resolve(box(0, 0), part, Frame()))
        self.assertEqual(pi.resolve(box(0, 0), {'class': 'clinic', 'name': 'Clinic A'}, Frame())['display_name'], 'Clinic A')

    def test_provider_without_cache_adapter_never_fetches(self):
        md = SimpleNamespace(cell=Mock())
        self.assertEqual(pi.cached_layers(md, ['key']), [])
        md.cell.assert_not_called()

    def test_no_network_when_cache_missing(self):
        md = SimpleNamespace(path=lambda *args: 'missing-file-for-property-identity',
                             _mem_lock=__import__('threading').Lock(), _mem={}, cell=Mock())
        import inputwatch
        with inputwatch.capture() as watch:
            self.assertEqual(pi.cached_layers(md, ['key']), [])
        self.assertEqual(len(watch['files']), 1)
        self.assertTrue(next(iter(watch['files'])).endswith('missing-file-for-property-identity'))
        md.cell.assert_not_called()

    def test_cached_layer_is_decoded_once_without_network(self):
        f = places([('one', 4, 4, 'Shop', 'grocery_store')])
        md = SimpleNamespace(path=lambda *args: 'cached-places.npz',
                             _mem_lock=__import__('threading').Lock(), _mem={},
                             _load=Mock(return_value=f.to_arrays('')), cell=Mock())
        with patch.object(pi.os, 'stat', return_value=SimpleNamespace(st_mtime_ns=1, st_size=10)):
            first = pi.cached_layers(md, ['key'])
            second = pi.cached_layers(md, ['key'])
        self.assertIs(first[0], second[0])
        self.assertEqual(md._load.call_count, 1)
        md.cell.assert_not_called()
        result = pi.resolve(box(0, 0), {'class':'retail'}, Frame(), layers=first)
        self.assertEqual(result['occupants'][0]['name'], 'Shop')

    def test_500_building_indexed_batch(self):
        f = places([(str(i), (i%25)*30+10, (i//25)*30+10, f'Unit {i}', 'grocery_store')
                    for i in range(500)])
        pi.index(f)
        start = time.perf_counter()
        rings = [box((i%25)*30, (i//25)*30) for i in range(500)]
        attrs = [{'class':'retail'} for _ in rings]
        results = pi.resolve_many(rings, attrs, Frame(), layers=[f])
        self.assertEqual(results[:20], [pi.resolve(r, a, Frame(), layers=[f])
                                        for r, a in zip(rings[:20], attrs[:20])])
        elapsed = time.perf_counter()-start
        self.assertTrue(all(len(r['occupants']) == 1 for r in results))
        self.assertLess(elapsed, 5.0, f'500 indexed buildings took {elapsed:.3f}s')


if __name__ == '__main__':
    unittest.main()
