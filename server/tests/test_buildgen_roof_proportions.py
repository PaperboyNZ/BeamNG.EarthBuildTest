"""Roof silhouette acceptance across styles, shapes and evidence sources."""
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import house_styles, regional_architecture, regional_roofs, roofs
from buildgen.inference import resolve
from buildgen.topology import Footprint
from buildgen.environments import Environment
from building_fixtures import complex_roofs, transform


def rectangle(width=12., length=18.):
    return Footprint(((0., 0.), (length, 0.), (length, width), (0., width)))


def planned(fp, **attrs):
    return b.plan(np.asarray(fp.outer), dict({'class': 'house', 'num_floors': 1,
                  'seed_id': 'roof-proportions', '_footprint': fp}, **attrs))


class RoofProportionsTests(unittest.TestCase):
    def test_all_regions_and_contemporary_families_keep_roofs_below_a_storey(self):
        styles = [house_styles.HouseStyle('regional', region)
                  for region in regional_architecture.catalogue()]
        styles += [house_styles.HouseStyle('contemporary', '', alternate=family)
                   for family in house_styles.CONTEMPORARY]
        for style in styles:
            with patch('buildgen.house_styles.select', return_value=style), \
                 patch('buildgen.environments.resolve', return_value=Environment(region=style.profile)):
                for width in (6., 12., 20.):
                    for floors in (1, 2, 3):
                        fp = rectangle(width, 24.)
                        for seed in range(8):
                            r = resolve({'class': 'house', 'num_floors': floors,
                                         'seed_id': str(seed)}, fp, width / 2.)
                            with self.subTest(style=style, width=width, floors=floors, seed=seed):
                                broken = r.roof_variant in ('mansard', 'gambrel')
                                self.assertLessEqual(r.roof_rise, (.75 if broken else .60) * r.body_height + 1e-7)
                                self.assertLessEqual(r.roof_rise, (3.6 if broken else 3.) + 1e-7)
                                self.assertAlmostEqual(r.body_height, floors * 3.)

    def test_joined_and_courtyard_roofs_use_actual_slope_runs(self):
        for name, outer, holes in complex_roofs():
            for angle in (0., 33.):
                fp = Footprint(transform(outer, angle), tuple(transform(h, angle) for h in holes))
                for kind in ('gabled', 'hipped'):
                    spec = planned(fp, roof_shape=kind)
                    roof = roofs.envelope(fp, kind)
                    for i in set(roof.triangle_planes):
                        slope = spec.inference.roof_rise * math.hypot(*roof.planes[i][:2]) / roof.peak
                        self.assertLessEqual(math.degrees(math.atan(slope)), 26. + 1e-6, (name, kind))

    def test_every_special_profile_has_bounded_actual_slopes(self):
        from buildgen.roof_proportions import inferred_rise
        for variant in regional_roofs.VARIANTS:
            for width in (4., 12., 20.):
                fp = rectangle(width, 24.)
                kind = 'hipped' if variant in ('mansard', 'flared_hip') else 'gabled'
                rise = inferred_rise(fp, kind, variant, width / 2., 36., 3., False, True)
                roof = roofs.envelope(fp, kind, variant)
                for i in set(roof.triangle_planes):
                    angle = math.degrees(math.atan(rise * math.hypot(*roof.planes[i][:2]) / roof.peak))
                    limit = 60. if variant in ('mansard', 'gambrel') else 14. if variant == 'shed' else 42.
                    self.assertLessEqual(angle, limit + 1e-7, variant)

    def test_mapped_roof_height_is_not_capped(self):
        for kind in ('gabled', 'hipped'):
            for height in (None, 8.):
                spec = planned(rectangle(), roof_shape=kind, roof_height=4., height=height)
                self.assertEqual(spec.inference.roof_rise, 4.)
                self.assertEqual(spec.inference.height.value, 7. if height is None else height)

    def test_mapped_total_keeps_top_and_does_not_invent_a_roof_storey(self):
        for kind in ('gabled', 'hipped'):
            spec = planned(rectangle(20., 24.), roof_shape=kind, height=5.)
            self.assertAlmostEqual(spec.inference.height.value, 5.)
            self.assertLessEqual(spec.inference.roof_rise, .60 * spec.height + 1e-7)
            items = [(spec, 0., 0.)]
            for mesh in (b.build(items), b.build(items, lite=True), b._sky_mesh(items), b.collision_mesh(items)):
                self.assertTrue(np.isfinite(mesh[0]).all())
                self.assertAlmostEqual(float(mesh[0][:, 2].max()), 5., places=5)


if __name__ == '__main__':
    unittest.main()
