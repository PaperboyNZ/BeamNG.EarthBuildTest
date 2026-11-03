import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from buildgen import fast_facade


class FastFacadeTests(unittest.TestCase):
    def test_accepted_anchors_only_reserve_their_own_exterior_edge(self):
        spec = SimpleNamespace(door=(1, 3.), garage_opening=(1, 8., 3., 2.5),
                               access=SimpleNamespace(door_z=11., garage_z=10.5))
        with patch('buildgen.facades.plan', side_effect=AssertionError('expensive planner')):
            result = fast_facade.reservations(spec, 0, 1, 10., 12.)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0], fast_facade.Reservation(2.15, 3.85, 11., 13.4))
            self.assertEqual(result[1], fast_facade.Reservation(6.3, 9.7, 10.5, 13.2))
            self.assertEqual(fast_facade.reservations(spec, 1, 1, 10., 12.), ())
            self.assertEqual(fast_facade.reservations(spec, 0, 2, 10., 12.), ())

    def test_window_mask_clearance_and_roof_limit(self):
        left = np.array([0., 2., 4., 7., 2., 2.])
        right = left + 1.
        bottom = np.array([0., 0., 0., 0., 3., 9.])
        reserved = (fast_facade.Reservation(2.5, 3.5, 0., 2.4),
                    fast_facade.Reservation(6.5, 9., 0., 2.8))
        got = fast_facade.window_mask(left, right, bottom, 1., 9.5, reserved)
        np.testing.assert_array_equal(got, [True, False, True, False, True, False])

    def test_missing_access_uses_ground_and_base(self):
        spec = SimpleNamespace(door=(0, 2.), garage_opening=(0, 6., 2., 2.), access=None)
        door, garage = fast_facade.reservations(spec, 0, 0, 5., 6.)
        self.assertEqual(door.bottom, 6.)
        self.assertEqual(garage.bottom, 5.)


if __name__ == '__main__':
    unittest.main()
