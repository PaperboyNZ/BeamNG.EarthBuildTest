"""Bounded admitted-bed broad phase agrees with the original linear scan."""
import copy
from dataclasses import replace
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from shapely.geometry import box

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from buildgen import landscaping, sitework
from buildgen.access import AccessPlan, Solid
from buildgen.topology import Footprint
from sitegen.surfaces import overlaps


class LinearBeds:
    """Original admission-order scan, without any spatial candidate pruning."""
    def __init__(self):self.polygons=[]
    def __len__(self):return len(self.polygons)
    def append(self,p):self.polygons.append(p)
    def query(self,p):return self.polygons


def bed(x,y,w=2.,d=3.):
    return Solid('garden_bed',((x,y,0.),(x+w,y,0.),(x+w,y+d,0.),(x,y+d,0.)),-.1)


def coordination_scene(n,crowded=False,offset=(0.,0.)):
    items=[]
    for i in range(n):
        dx,dy=(1.3,3.7) if crowded else (20.,20.)
        x=(i%20)*dx+offset[0];y=(i//20)*dy+offset[1]
        footprint=Footprint(((x,y),(x+12,y),(x+12,y+10),(x,y+10)))
        bands=tuple(bed(x+j*3,y-5) for j in range(3))
        spec=SimpleNamespace(seed=str(i),ring=np.asarray(footprint.outer),footprint=footprint,
                             site=None,access=AccessPlan(0.,None,(),landscape=bands))
        items.append((spec,0.,0.))
    return items


class BedIndexTests(unittest.TestCase):
    def test_threshold_build_is_lazy_and_later_admissions_are_indexed(self):
        index=sitework._AdmittedBeds()
        polygons=[box(i*32,0,i*32+1,1) for i in range(65)]
        for p in polygons[:63]:index.append(p)
        self.assertEqual(list(index.query(polygons[0])),polygons[:63])
        self.assertIsNone(index._bins)
        index.append(polygons[63])
        self.assertIsNone(index._bins)
        self.assertEqual(list(index.query(polygons[0])),polygons[:1])
        self.assertIsNotNone(index._bins)
        index.append(polygons[64])
        self.assertEqual(list(index.query(polygons[64])),polygons[64:])
        self.assertEqual(len(index),65)

    def test_negative_boundary_touching_bbox_filter_and_stable_order(self):
        index=sitework._AdmittedBeds()
        near=[box(-32,-16,-16,0),box(-16,-16,0,0),box(-15,1,-14,2),
              box(-16,-16,0,0),box(0,0,16,16)]
        for p in near+[box(i*32,100,i*32+1,101) for i in range(64)]:index.append(p)
        query=box(-16,-8,-15,-4)
        self.assertEqual(list(index.query(query)),[near[i] for i in (0,1,3)])
        self.assertFalse(overlaps(query,near[0]))
        self.assertTrue(overlaps(query,near[1]))
        self.assertEqual(list(index.query(box(0,0,1,1))),[near[i] for i in (1,3,4)])
        # A shared cell alone is insufficient: return only intersecting bboxes.
        self.assertEqual(list(index.query(box(-15,3,-14,4))),[])

    def test_cell_expansion_limit_includes_boundary_cells(self):
        index=sitework._AdmittedBeds()
        self.assertIsNotNone(index._extent((0.,0.,15*16.,15*16.)))
        self.assertIsNone(index._extent((0.,0.,16*16.,15*16.)))
        huge=box(-1e9,-1e9,1e9,1e9)
        polygons=[huge]+[box(i*32,100,i*32+1,101) for i in range(64)]
        for p in polygons:index.append(p)
        self.assertEqual(list(index.query(huge)),polygons)
        self.assertIsNone(index._bins)
        self.assertEqual(list(index.query(box(-1,-1,1,1))),[huge])
        self.assertEqual(index._large,[0])
        later=box(-2e9,-2e9,2e9,2e9)
        index.append(later)
        self.assertEqual(index._large,[0,65])
        self.assertEqual(list(index.query(box(-1,-1,1,1))),[huge,later])
        self.assertEqual(list(index.query(huge)),polygons+[later])
        self.assertLessEqual(sum(map(len,index._bins.values())),64*256)


class CoordinationEquivalenceTests(unittest.TestCase):
    def assert_linear_equal(self,items):
        before=copy.deepcopy(items);after=copy.deepcopy(items)
        with patch.object(sitework,'_AdmittedBeds',LinearBeds):
            expected=sitework.coordinate(before)
        actual=sitework.coordinate(after)
        self.assertEqual(repr((actual,[s.access for s,_,_ in after])),
                         repr((expected,[s.access for s,_,_ in before])))
        return after

    def test_sparse_crowded_and_threshold_transitions(self):
        for n,crowded in ((21,False),(22,False),(25,False),(100,False),(25,True),(100,True)):
            with self.subTest(buildings=n,crowded=crowded):
                self.assert_linear_equal(coordination_scene(n,crowded))

    def test_arbitrary_translation_and_reversed_input(self):
        expected=None
        for offset in ((0.,0.),(-1000.25,2000.5),(37.125,-49.625),(1e6,-1e6)):
            items=coordination_scene(30,offset=offset)
            # Competing bands span negative cells and exact grid boundaries.
            for i in range(0,len(items),2):
                s,c=items[i][0],items[i+1][0]
                c.access=replace(c.access,landscape=s.access.landscape)
            actual=self.assert_linear_equal(items)
            accepted=tuple(s.access.landscape!=() for s,_,_ in actual)
            if expected is None:expected=accepted
            self.assertEqual(accepted,expected)
            reverse=self.assert_linear_equal(items[::-1])
            self.assertEqual(tuple(s.access for s,_,_ in actual),
                             tuple(s.access for s,_,_ in reverse[::-1]))

    def test_large_admitted_polygon_and_large_query_preserve_complete_plans(self):
        items=coordination_scene(30)
        # Buildings sit at y >= 0. These two large optional beds intersect.
        s,c=items[-2][0],items[-1][0]
        s.access=replace(s.access,landscape=(bed(-10000,-10000,20000,1000),))
        c.access=replace(c.access,landscape=(bed(-10000,-9500,20000,1000),))
        self.assert_linear_equal(items)

    def test_touching_beds_on_negative_grid_boundaries_preserve_complete_plans(self):
        items=coordination_scene(30)
        for i,(s,_,_) in enumerate(items):
            s.access=replace(s.access,landscape=tuple(bed(-256+i*6+j*2,-64,2,16) for j in range(3)))
        s=items[-1][0]
        s.access=replace(s.access,landscape=s.access.landscape[:2]+(bed(-256+29*6+3,-64,2,16),))
        actual=self.assert_linear_equal(items)
        self.assertEqual(sum(len(s.access.landscape) for s,_,_ in actual),89)

    def test_reservation_budget_and_unsupported_hazards_match(self):
        items=coordination_scene(30)
        with patch('sitegen.surfaces.MAX_RESERVATIONS',90):
            self.assert_linear_equal(items)
        items[-1][0].footprint=None
        items[-1][0].ring=np.array(((0,0),(2,2),(0,2),(2,0)),float)
        self.assert_linear_equal(items)

    def test_access_plans_publish_only_after_all_decisions(self):
        items=coordination_scene(25)
        original=[s.access for s,_,_ in items]
        accept=landscaping.accepted_groundcover
        def checked(*args):
            for (s,_,_),plan in zip(items,original):self.assertIs(s.access,plan)
            return accept(*args)
        with patch.object(landscaping,'accepted_groundcover',side_effect=checked):
            sitework.coordinate(items)
        for (s,_,_),plan in zip(items,original):self.assertIsNot(s.access,plan)


if __name__=='__main__':unittest.main()
