"""The distributable installer must work without files from a source checkout."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BuildingPackageTests(unittest.TestCase):
    def test_packaged_installer_imports_and_contains_compact_building_assets(self):
        spec = importlib.util.spec_from_file_location('earth_package', ROOT/'tools/package.py')
        package = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(package)
        files = set(package.collect())
        self.assertTrue({'server/buildgen/minimum.py', 'server/buildgen/minimum_roofs.py'} <= files)
        for name in ('glass', 'modern', 'sash', 'tall', 'wide'):
            for suffix in ('.dds', '_opacity.data.png'):
                self.assertIn('mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/'
                              + 'bne_minimum_' + name + suffix, files)
        with tempfile.TemporaryDirectory() as folder:
            # Only copy files selected by the production package collector.
            for name in files:
                if '/' not in name and name.endswith('.py'):
                    shutil.copy2(ROOT/name, Path(folder)/name)
            code = 'import sys; sys.path.insert(0, sys.argv[1]); import install'
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code, folder],
                                    cwd=folder, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
