"""Property-family selection remains evidence-gated and deterministic."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from buildgen import inference, property_programme
from buildgen.topology import Footprint


class PropertyProgrammeTests(unittest.TestCase):
    def setUp(self):
        self.fp = Footprint(((0, 0), (30, 0), (30, 20), (0, 20)))

    def resolve(self, cls, identity=None):
        attrs = {'class': cls, 'height': 6., 'num_floors': 1, 'seed_id': 'fixture'}
        if identity is not None:
            attrs['_property_identity'] = identity
        return inference.resolve(attrs, self.fp, 10.)

    def test_supported_families_select_recipe_and_keep_use(self):
        for kind, cls, expected in (
            ('grocery_store', 'commercial', 'commercial'), ('supermarket', 'commercial', 'commercial'),
            ('strip_shops', 'commercial', 'commercial'), ('trade_units', 'industrial', 'industrial'),
            ('clinic', 'clinic', 'civic'), ('hospital', 'hospital', 'civic')):
            with self.subTest(kind=kind):
                identity = {'kind': kind, 'status': 'supported'}
                result = self.resolve(cls, identity)
                self.assertEqual(result.use.value, expected)
                self.assertEqual(result.selection.preset.id, property_programme.PRESETS[kind])

    def test_explicit_health_classes_select_distinct_presets(self):
        for kind in ('clinic', 'hospital'):
            self.assertEqual(self.resolve(kind).selection.preset.id, property_programme.PRESETS[kind])

    def test_ambiguous_or_incompatible_association_cannot_reclassify_host(self):
        for status in ('ambiguous', 'unmatched', 'closed'):
            identity = {'kind': 'supermarket', 'status': status}
            self.assertNotEqual(self.resolve('commercial', identity).selection.preset.id, 'ci_supermarket')
        identity = {'kind': 'hospital', 'status': 'supported'}
        result = self.resolve('house', identity)
        self.assertEqual(result.use.value, 'residential')
        self.assertNotEqual(result.selection.preset.id, 'ci_hospital')

    def test_unresolved_food_size_uses_no_specific_scale(self):
        identity = {'kind': 'food_retail_size_unresolved', 'status': 'supported',
                    'premises_area': None, 'area_basis': None}
        for cls in ('supermarket', 'grocery_store'):
            result = self.resolve(cls, identity)
            self.assertEqual(result.use.value, 'commercial')
            self.assertNotIn(result.selection.preset.id, ('ci_grocery_store', 'ci_supermarket'))
            self.assertIsNone(property_programme.for_spec(SimpleNamespace(inference=result, seed='x', property_identity=identity)))

    def test_explicit_supported_classes_reach_correct_use(self):
        for cls, expected in (('grocery_store', 'commercial'), ('convenience_store', 'commercial'),
                              ('strip_shops', 'commercial'), ('shopping_parade', 'commercial'),
                              ('trade_units', 'industrial'), ('clinic', 'civic'), ('hospital', 'civic')):
            with self.subTest(cls=cls):
                self.assertEqual(self.resolve(cls).use.value, expected)

    def test_programme_determinism_and_bounded_modifiers(self):
        identity = {'kind': 'supermarket', 'status': 'supported', 'size_modifier': 'large'}
        result = self.resolve('commercial', identity)
        spec = SimpleNamespace(inference=result, seed='stable', property_identity=identity)
        first = property_programme.for_spec(spec)
        self.assertEqual(first, property_programme.for_spec(spec))
        self.assertEqual(first.size_modifier, 'large')
        self.assertTrue(all(0 < value < 1 for _, value in first.proportions))
        self.assertNotIn('car_park', first.decorations)
        self.assertEqual(property_programme.for_spec(SimpleNamespace(inference=self.resolve('house'), seed='x')), None)


if __name__ == '__main__':
    unittest.main()
