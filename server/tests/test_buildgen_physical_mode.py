"""Accepted physical recipes outlive every visual ceiling and worker boundary."""
from dataclasses import replace
import pickle
import unittest

import numpy as np
import buildings as b
from buildgen import freeze_items, quality
from buildgen.progressive import DETAIL
from test_buildgen_facades import building


class PhysicalModeTests(unittest.TestCase):
    def fixture(self, detail):
        spec=building(num_floors=2)
        spec.front=0
        spec.inference=replace(spec.inference,modifiers=('bay_windows',))
        return quality.run(detail,freeze_items,[(spec,0.,0.)])

    def test_collision_and_occupied_bounds_do_not_follow_visual_quality(self):
        for accepted in ('minimum','ultra'):
            items=self.fixture(accepted)
            original=quality.run(accepted,b.collision_mesh,items)
            occupied=quality.run(accepted,b.collider_boxes,items,100.,-200.)
            for ceiling in quality.NAMES:
                actual=quality.run(ceiling,b.collision_mesh,items)
                for index in (0,1,2,3,5):
                    np.testing.assert_array_equal(actual[index],original[index])
                self.assertEqual(quality.run(ceiling,b.collider_boxes,items,100.,-200.),occupied)
                restored=quality.run(ceiling,freeze_items,pickle.loads(pickle.dumps(items)))
                self.assertEqual(restored[0][0].physical_mode,items[0][0].physical_mode)
                self.assertEqual(restored[0][0].facades,items[0][0].facades)

    def test_minimum_downgrade_keeps_closed_accepted_bay_silhouette(self):
        items=self.fixture('ultra'); spec=items[0][0]
        self.assertTrue(any(o.assembly=='regional_bay' for e in spec.facades.elevations for o in e.openings))
        mesh=quality.run('minimum',b.build,items)
        # The source front is y=0; the accepted physical bay projects .30m.
        self.assertLessEqual(mesh[0][:,1].min(),-.30+1e-8)

    def test_compact_acceptance_cannot_gain_projecting_bays_in_visual_refinement(self):
        items=self.fixture('minimum')
        self.assertEqual(items[0][0].physical_mode,'compact')
        self.assertIsNone(items[0][0].facades)
        for ceiling in quality.NAMES:
            mesh=quality.run(ceiling,b.build,items)
            self.assertGreaterEqual(mesh[0][:,1].min(),-.03)
