"""Saved generation modes and explicit startup overrides."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import building_settings


class BuildingSettingsTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.user = Path(self.folder.name)
        (self.user / "settings").mkdir()
        self.file = self.user / "settings/beamngEarth.json"

    def save(self, value):
        self.file.write_text(json.dumps({"buildingGenerator": value}), encoding="utf-8")

    def test_no_setting_preserves_simple_default(self):
        self.assertEqual(building_settings.resolve(self.user, environ={}), "legacy")
        self.assertEqual(building_settings.resolve(None, environ={}), "legacy")

    def test_both_modes_and_switching_back_are_read_on_each_start(self):
        for mode in ("v2", "legacy", "v2"):
            self.save(mode)
            self.assertEqual(building_settings.resolve(self.user, environ={}), mode)

    def test_lowercase_settings_filename(self):
        self.file = self.user / "settings/beamngearth.json"
        self.save("v2")
        self.assertEqual(building_settings.resolve(self.user, environ={}), "v2")

    def test_bom_from_windows_tools(self):
        self.file.write_text('{"buildingGenerator":"v2"}', encoding="utf-8-sig")
        self.assertEqual(building_settings.resolve(self.user, environ={}), "v2")

    def test_old_malformed_or_invalid_settings_fall_back(self):
        for content in ('{', 'null', '[]', '{}', '42', '{"buildingGenerator": "unknown"}',
                        '{"buildingGenerator": []}', '{"buildingGenerator": true}'):
            with self.subTest(content=content):
                self.file.write_text(content)
                self.assertEqual(building_settings.resolve(self.user, environ={}), "legacy")

    def test_explicit_overrides_win_in_both_directions(self):
        for saved, override in (("legacy", "v2"), ("v2", "legacy")):
            self.save(saved)
            env = {"BNE_BUILDING_GENERATOR": override}
            self.assertEqual(building_settings.resolve(self.user, environ=env), override)
            self.assertEqual(building_settings.resolve(self.user, saved, env), saved)
            self.assertEqual(building_settings.saved_generator(self.user), saved)

    def test_invalid_explicit_mode_fails_clearly(self):
        for value in ("", "advanced", "unknown"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                building_settings.resolve(self.user, environ={"BNE_BUILDING_GENERATOR": value})
        self.assertEqual(building_settings.resolve(self.user, "v2", {"BNE_BUILDING_GENERATOR": "bad"}), "v2")


if __name__ == "__main__":
    unittest.main()
