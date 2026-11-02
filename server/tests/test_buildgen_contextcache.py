"""Complete evidence reuse across independent providers, never partial input."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from buildgen import context, contextcache
import productcache
from test_buildgen_context import MapData


class ContextCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.md = MapData()
        self.md.cache_dir = self.tmp.name

    def query(self, md=None):
        md = md or self.md
        return context.Provider(md).query(md.buildings, 0)

    def test_fresh_provider_reuses_exact_complete_observations(self):
        expected = self.query()
        with mock.patch.object(context._Bundle, '__init__', autospec=True,
                               side_effect=context._Bundle.__init__) as build:
            # decode allocates with __new__; no source planning occurs.
            actual = self.query()
        self.assertEqual(actual, expected)
        self.assertEqual(build.call_count, 0)

    def test_source_arrays_and_revision_are_dependencies(self):
        expected = self.query()
        changed = MapData(copy.deepcopy(self.md.buildings), self.md.land)
        changed.cache_dir = self.tmp.name
        changed.buildings.attrs['height'][1] = 16.
        self.assertNotEqual(self.query(changed), expected)
        self.md.revision += '-new'
        self.assertNotEqual(self.query().manifest.digest, expected.manifest.digest)

    def test_corrupt_cache_rebuilds_and_does_not_change_output(self):
        expected = self.query()
        paths = list(Path(self.tmp.name).glob('products/*/building-context/*.zip'))
        self.assertEqual(len(paths), 1)
        paths[0].write_bytes(b'broken')
        self.assertEqual(self.query(), expected)
        self.assertGreater(paths[0].stat().st_size, 6)

    def test_failed_write_is_not_failed_world_generation(self):
        with mock.patch.object(productcache.Store, 'put', return_value=productcache.Lookup('unavailable')):
            actual = self.query()
        self.assertEqual(actual, self.query())

    def test_missing_required_source_never_reads_ready_evidence(self):
        self.query()
        self.md.land = None
        with self.assertRaisesRegex(ValueError, 'required land_use'):
            self.query()

    def test_holes_and_full_evidence_survive_codec(self):
        import mapcells
        key = mapcells.cell_of(45., 9.)
        cells = [self.md.cell(k, context.LAYERS, 'demand') for k in context.halo(key)]
        original = context._Bundle(key, cells, 'test')
        encoded = contextcache.encode(original)
        codec = productcache.Codec()
        tree = codec.encode(encoded)
        restored = contextcache.decode(codec.decode(tree))
        self.assertEqual(restored.manifest, original.manifest)
        self.assertEqual(restored.query(self.md.buildings, 0), original.query(self.md.buildings, 0))
        self.assertEqual([s.wkb for _, s, _ in restored.buildings], [s.wkb for _, s, _ in original.buildings])
        encoded['lengths'] = encoded['lengths'] + 1
        with self.assertRaisesRegex(ValueError, 'layout'):
            contextcache.decode(encoded)


if __name__ == '__main__':
    unittest.main()
