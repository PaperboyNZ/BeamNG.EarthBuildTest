"""Road-envelope preparation is reused without weakening curb protection."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from shapely.geometry import box
import parkinggrade
from test_roads import FRAME,features

class ProtectionReuseTests(unittest.TestCase):
    def setUp(self):
        self.feats=features([[(-100,0),(100,0)],[(-100,900),(100,900)]],
                            ['residential']*2,ids=['near','far'])
        self.md=SimpleNamespace(cell=lambda *a,**kw:SimpleNamespace(layers={'roads':self.feats}))
        self.pg=parkinggrade.ParkingGrader(self.md,lambda a,b:a*0)

    def test_reuses_specs_and_rejects_only_remote_envelopes(self):
        with patch.object(parkinggrade.mapcells,'cells_for_points',return_value=['cell']),\
             patch.object(parkinggrade.roads,'road_specs',wraps=parkinggrade.roads.road_specs) as specs,\
             patch.object(parkinggrade,'LineString',wraps=parkinggrade.LineString) as lines:
            a=self.pg._protected(FRAME,box(-20,-10,20,10))
            b=self.pg._protected(FRAME,box(-20,-10,20,10))
            self.assertEqual(a.wkb,b.wkb)
            self.assertTrue(a.covers(box(-10,-1,10,1)))
            self.assertEqual(specs.call_count,1)
            self.assertEqual(lines.call_count,2) # Near road only, once per patch.

    def test_replacement_source_invalidates_prepared_roads(self):
        with patch.object(parkinggrade.mapcells,'cells_for_points',return_value=['cell']):
            a=self.pg._protected(FRAME,box(-20,-10,20,10))
            replacement=features([[(-100,900),(100,900)]],['residential'],ids=['remote'])
            self.pg._remember_roads('cell',replacement)
            b=self.pg._protected(FRAME,box(-20,-10,20,10))
            self.assertFalse(a.is_empty)
            self.assertTrue(b.is_empty)

    def test_remote_geometry_still_counts_towards_safety_budget(self):
        with patch.object(parkinggrade.mapcells,'cells_for_points',return_value=['cell']),\
             patch.object(parkinggrade,'MAX_PROTECTION_POINTS',3):
            with self.assertRaisesRegex(ValueError,'geometry budget'):
                self.pg._protected(FRAME,box(-20,-10,20,10))

if __name__=='__main__':unittest.main()
