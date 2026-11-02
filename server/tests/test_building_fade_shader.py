import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import building_fade_shader as fade


class BuildingFadeShaderTests(unittest.TestCase):
    def test_complementary_mask_all_thresholds(self):
        ranks = []
        for y in range(8):
            for x in range(8):
                rank = 0
                for bit in range(3):
                    a, b = (x >> bit) & 1, (y >> bit) & 1
                    rank |= ((a ^ b) * 2 + b) << (4 - bit * 2)
                ranks.append(rank)
        self.assertEqual(sorted(ranks), list(range(64)))
        previous = 0
        for value in range(256):
            incoming = [(rank + .5) / 64 < value / 255 for rank in ranks]
            outgoing = [not pixel for pixel in incoming]
            self.assertTrue(all(a != b for a, b in zip(incoming, outgoing)))
            self.assertGreaterEqual(sum(incoming), previous)
            previous = sum(incoming)
        self.assertEqual(previous, 64)

    def test_install_is_local_idempotent_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            game, mod = Path(temp)/'game', Path(temp)/'mod'
            support = game/'shaders/common/material/shadergen/shadergen.h.hlsl'
            support.parent.mkdir(parents=True)
            support.write_text('uint4 getInstanceBaseColors(uint instanceIdx) {}')
            originals = {}
            for name, function in fade.HOOKS.items():
                path = game/name;path.parent.mkdir(parents=True, exist_ok=True)
                originals[name] = f'void {function}(inout Material material, float2 vPos) {{\ngetInstanceVisibility(material.instanceId);\n}}'
                path.write_text(originals[name])
            self.assertTrue(fade.install(mod, game))
            self.assertFalse(fade.install(mod, game))
            for name in fade.HOOKS:
                self.assertEqual((game/name).read_text(), originals[name])
                self.assertEqual((mod/name).read_text().count(fade.INCLUDE), 1)
            (game/next(iter(fade.HOOKS))).write_text('changed engine contract')
            with self.assertRaises(ValueError): fade.install(mod, game)
            fade.remove(mod)
            self.assertFalse(any((mod/name).exists() for name in fade.GENERATED))


if __name__ == '__main__': unittest.main()
