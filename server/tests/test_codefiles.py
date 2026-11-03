"""Nested generator source/catalogue edits invalidate both cache identities."""
import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import codefiles
import peerwork
import revisit


class SourceIdentityTest(unittest.TestCase):
    def test_generator_mode_and_geometry_library_invalidate_cache(self):
        import shapely
        def identity(mode, version):
            with mock.patch.dict(os.environ, {"BNE_BUILDING_GENERATOR": mode}), \
                    mock.patch.object(shapely, "geos_version_string", version), mock.patch.object(revisit, "_code", []):
                return revisit.code_key()
        self.assertNotEqual(identity("legacy", "3.10"), identity("v2", "3.10"))
        self.assertNotEqual(identity("v2", "3.10"), identity("v2", "3.14"))
        self.assertEqual(identity("legacy", "3.10"), identity("legacy", "3.14"))

    def test_nested_code_and_catalogues_invalidate_development_and_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "entry.py").write_text("# entry\n")
            pkg = root / "buildgen"
            pkg.mkdir()
            (pkg / "plan.py").write_text("VERSION = 1\n")
            cat = pkg / "catalog"
            cat.mkdir()
            (cat / "materials.json").write_text('{"version":1}')
            (pkg / "__pycache__").mkdir()
            (pkg / "__pycache__" / "ignore.py").write_text("irrelevant")
            (root / "tests").mkdir()
            (root / "tests" / "test_plan.py").write_text("irrelevant")
            self.assertEqual(codefiles.source_files(root),
                             ["buildgen/catalog/materials.json", "buildgen/plan.py", "entry.py"])

            def identities():
                with mock.patch.object(revisit, "__file__", str(root / "revisit.py")), \
                        mock.patch.object(revisit, "_code", []):
                    return peerwork.source_id(root), revisit.code_key()

            initial = identities()
            (pkg / "plan.py").write_text("VERSION = 2\n")
            changed_code = identities()
            self.assertTrue(all(a != b for a, b in zip(initial, changed_code)))
            (cat / "materials.json").write_text('{"version":2}')
            changed_catalogue = identities()
            self.assertTrue(all(a != b for a, b in zip(changed_code, changed_catalogue)))
            (pkg / "__pycache__" / "ignore.py").write_text("still irrelevant")
            self.assertEqual(identities(), changed_catalogue)
            climate = root / "koppen_1991_2020_0p1.png"
            climate.write_bytes(b"grid-v1")
            grid1 = identities()
            self.assertTrue(all(a != b for a, b in zip(changed_catalogue, grid1)))
            climate.write_bytes(b"grid-v2")
            self.assertTrue(all(a != b for a, b in zip(grid1, identities())))
            shared = root / 'sitegen'
            (shared / 'profiles').mkdir(parents=True)
            (shared / 'identity.py').write_text('VERSION = 1\n')
            profile = shared / 'profiles' / 'vehicles.json'
            profile.write_text('{"version":1}')
            first_site = identities()
            (shared / 'identity.py').write_text('VERSION = 2\n')
            second_site = identities()
            self.assertTrue(all(a != b for a,b in zip(first_site,second_site)))
            profile.write_text('{"version":2}')
            self.assertTrue(all(a != b for a,b in zip(second_site,identities())))
            self.assertIn('sitegen/profiles/vehicles.json',codefiles.source_files(root))


if __name__ == "__main__":
    unittest.main()
