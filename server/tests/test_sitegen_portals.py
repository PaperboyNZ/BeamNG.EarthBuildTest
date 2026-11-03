"""Detached local proposal records and bounded deterministic top-four selection."""
from dataclasses import FrozenInstanceError
from pathlib import Path
import pickle
import sys
import unittest

import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sitegen.portals import StreetPortal,RouteProposal,ranked,simplified_lines


class PortalTests(unittest.TestCase):
    def test_detached_route_and_portal_records_round_trip_without_mutable_arrays(self):
        end=[1.,-5.];direction=[1.,0.]
        portal=StreetPortal('road',end,direction,3.5,5.)
        points=np.zeros((9,3,2));branch=[np.ones((4,2)),[0,1]]
        route=RouteProposal(portal,points,branch)
        end[0]=100;points[0,0,0]=100;branch[0][0,0]=100
        self.assertEqual(route.sections[0][0][0],0.)
        self.assertEqual(route.branch[0][0][0],1.)
        self.assertEqual(route.portal.end,(1.,-5.))
        self.assertEqual(route,pickle.loads(pickle.dumps(route)))
        with self.assertRaises(FrozenInstanceError):route.portal=portal

    def test_rank_is_permutation_stable_and_retains_only_four(self):
        values=[StreetPortal('road',(float(i),-5.),(1.,0.),3.5,float(i+5)) for i in range(100)]
        first=ranked(iter(values));second=ranked(reversed(values))
        self.assertEqual(first,second)
        self.assertEqual(len(first),4)
        self.assertEqual([p.distance for p in first],[5.,6.,7.,8.])

    def test_coincident_endpoints_do_not_erase_different_source_crossing_references(self):
        a=StreetPortal('sidewalk',(0.,-5.),(1.,0.),3.5,5.,.2,0.,(0,10.,14.))
        b=StreetPortal('sidewalk',(0.,-5.),(1.,0.),3.5,5.,.2,0.,(1,10.,14.))
        self.assertEqual(len(ranked([a,b,a])),2)

    def test_collinear_line_simplification_retains_evidence_and_height_breaks(self):
        points=np.column_stack((np.arange(100.),np.zeros(100)))
        source=(points,3.,'residential',False)
        result=simplified_lines([source])[0]
        self.assertEqual(result[1:],source[1:])
        np.testing.assert_array_equal(result[0],points[[0,-1]])
        with self.assertRaises(ValueError):result[0].setflags(write=True)
        heights=np.column_stack((np.arange(3.),np.zeros(3),[0.,1.,0.]))
        self.assertEqual(len(simplified_lines([(heights,3.)])[0][0]),3)
        self.assertEqual(simplified_lines([([],3.),([[0.,0.]],3.)]),())


if __name__=='__main__':unittest.main()
