"""Mod-local weathering hooks must stay scoped, repeatable and fail closed."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import weathering_shader as shader
import install


class WeatheringShaderTests(unittest.TestCase):
    def source(self):
        return ('MaterialLayer processLayers(VtxOut vtx, bool isFrontFacing) {\n'
                'vtx.color.xyz; float4(ld.detailScale, ld.detailScale);\n'+shader.ANCHOR+'\n}')

    def test_install_does_not_modify_engine_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            game=Path(folder)/'game';mod=Path(folder)/'mod'
            source=game/shader.HOOK;source.parent.mkdir(parents=True)
            source.write_text(self.source())
            mod.mkdir();(mod/'content.txt').write_text('shared mod content')
            before=install.tree_hash(mod)
            self.assertTrue(shader.install(mod,game))
            self.assertFalse(shader.install(mod,game))
            self.assertEqual(install.tree_hash(mod),before)
            self.assertEqual(source.read_text(),self.source())
            generated=(mod/shader.HOOK).read_text()
            self.assertEqual(generated.count(shader.INCLUDE),1)
            self.assertEqual(generated.replace(shader.INCLUDE,shader.ANCHOR),self.source())
            source.write_text('new unsupported shader API')
            with self.assertRaises(ValueError):shader.install(mod,game)
            self.assertEqual((mod/shader.HOOK).read_text(),generated)
            shader.remove(mod)
            self.assertFalse(any((mod/name).exists() for name in shader.GENERATED))

    def test_hook_does_not_change_opacity_or_animate_stains(self):
        hook=(ROOT/'mod/beamng_earth/shaders/beamngEarth/weatheringBlend.hlsl').read_text()
        self.assertIn('ld.detailScale.x == -1.03125',hook)
        self.assertIn('vtx.color.a',hook)
        self.assertNotIn('inLayer.opacity',hook)
        self.assertNotIn('accumTime',hook)
        self.assertEqual(hook.count('sampleMaterialTex('),1)
        self.assertNotIn('sin(',hook)
        self.assertNotIn('cos(',hook)

    def test_launcher_installs_and_refreshes_hook_even_when_mod_content_matches(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);game=root/'game';src=root/'source';user=root/'user'
            source=game/shader.HOOK;source.parent.mkdir(parents=True)
            source.write_text(self.source());src.mkdir();(src/'asset.txt').write_text('mod asset')
            with patch.object(install,'MOD_SRC',str(src)),patch.object(install,'_steam_roots',return_value=[]), \
                 patch.object(install,'install_building_fade',return_value=False), \
                 patch.dict(install.os.environ,{'BNGE_GAME_DIR':str(game)}):
                self.assertEqual(install.install_mod(str(user),True,False,quiet=True),'installed')
                dest=user/'mods/unpacked/beamng_earth'
                self.assertTrue((dest/shader.HOOK).is_file())
                self.assertEqual(install.install_mod(str(user),True,False,quiet=True),'current')
                source.write_text(self.source()+'\n// compatible engine update\n')
                self.assertEqual(install.install_mod(str(user),True,False,quiet=True),'updated')
                self.assertIn('compatible engine update',(dest/shader.HOOK).read_text())


if __name__=='__main__':unittest.main()
