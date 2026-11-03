"""Ordered geometry equivalence for the facade interval sweep."""
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from buildgen import facades, freeze_items
import buildings as b


def reference_cells(length, bottom, top, openings):
    """Original direct aperture subtraction, retained as an independent oracle."""
    cuts = sorted({bottom, top, *(max(bottom, min(top, z)) for op in openings for z in (op.bottom, op.top))})
    for lo, hi in zip(cuts, cuts[1:]):
        if hi - lo < 1e-8:
            continue
        active = sorted((op.left, op.right) for op in openings if op.bottom < hi - 1e-8 and op.top > lo + 1e-8)
        start = 0.
        for left, right in active:
            if left > start + 1e-8:
                yield start, left, lo, hi
            start = max(start, right)
        if start < length - 1e-8:
            yield start, length, lo, hi


class WallSweepTests(unittest.TestCase):
    def test_randomized_ordered_rectangles_match_reference(self):
        rng = random.Random(127)
        for case in range(300):
            origin = rng.choice((0., -30., 1e6))
            bottom, top = origin, origin + rng.uniform(.1, 500.)
            ops = []
            for i in range(rng.randrange(180)):
                lo = origin + rng.uniform(-5., top-bottom+5.)
                hi = lo + rng.choice((0., 1e-9, 1e-8, 2e-8, rng.uniform(.1, 6.)))
                left = rng.uniform(-2., 40.)
                ops.append(facades.Opening('window', i, left, left+rng.uniform(.1, 7.), lo, hi))
            rng.shuffle(ops)
            with self.subTest(case=case):
                self.assertEqual(list(facades.wall_cells(40., bottom, top, ops)),
                                 list(reference_cells(40., bottom, top, ops)))

    def test_empty_tiny_and_reversed_ranges_match_reference(self):
        for length in (0., 1e-9, 1e-8, 20.):
            for bottom, top in ((0., 3.), (3., 0.), (0., 0.), (0., 1e-8), (0., 1e-9)):
                self.assertEqual(list(facades.wall_cells(length, bottom, top, ())),
                                 list(reference_cells(length, bottom, top, ())))

    def test_duplicate_overlapping_and_boundary_openings(self):
        ops = [facades.Opening('window', i, 1., 3., i, i+2.) for i in range(60)]
        ops += ops + [facades.Opening('door', 0, 2., 5., -1., 4.)]
        for bottom, top in ((0., 50.), (10., 10.), (50., 0.), (-10., 100.)):
            self.assertEqual(list(facades.wall_cells(10., bottom, top, ops)),
                             list(reference_cells(10., bottom, top, ops)))

    def test_complete_meshes_remain_identical(self):
        from test_buildgen_facades import building
        from test_buildgen_city import make as city
        from test_buildgen_churches import make as church
        from test_buildgen_regional_blocks import building as block
        specs = [building(), block(), block(floors=48), city()[0],
                 city(material='glass', floors=80)[0], church()[0]]
        for spec in specs:
            items = freeze_items([(spec, 0., 0.)])
            for lite in (False, True):
                actual = b.build(items, lite=lite)
                with patch.object(facades, 'wall_cells', reference_cells):
                    expected = b.build(items, lite=lite)
                self.assertEqual(actual[4], expected[4])
                for field in (0, 1, 2, 3, 5):
                    np.testing.assert_array_equal(actual[field], expected[field])


if __name__ == '__main__':
    unittest.main()
