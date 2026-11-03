import pickle
import unittest
from dataclasses import replace

from buildgen.presentation_contracts import ComponentIdentity, PresentationRequest


class PresentationContractsTests(unittest.TestCase):
    def setUp(self):
        self.identity = ComponentIdentity('semantic-1', 'physical-1', 'facade',
                                          'tile/group-1', 'recipe-1', 'fast', 'atlas-1')

    def test_each_persistent_dependency_changes_key(self):
        changes = dict(semantic_revision='semantic-2', physical_revision='physical-2',
                       system='roof', group='tile/group-2', recipe_version='recipe-2',
                       variant='detailed', material_revision='atlas-2')
        for field, value in changes.items():
            with self.subTest(field=field):
                self.assertNotEqual(self.identity.key(), replace(self.identity, **{field: value}).key())

    def test_epoch_is_not_geometry_identity_and_survives_worker_boundary(self):
        a, b = PresentationRequest(self.identity, 1), PresentationRequest(self.identity, 2)
        self.assertEqual(a.component.key(), b.component.key())
        self.assertEqual(pickle.loads(pickle.dumps(a)), a)

    def test_invalid_inputs_fail_closed(self):
        for changes in ({'system': '../roof'}, {'variant': 'lite'}, {'group': ''},
                        {'semantic_revision': 'x' * 513}, {'physical_revision': ''}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.identity, **changes)
        for epoch in (-1, True, 1.5):
            with self.subTest(epoch=epoch), self.assertRaises(ValueError):
                PresentationRequest(self.identity, epoch)


if __name__ == '__main__':
    unittest.main()
