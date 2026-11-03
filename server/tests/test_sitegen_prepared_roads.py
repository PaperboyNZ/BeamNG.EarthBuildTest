"""Job-local road preparation preserves ordered candidates and live curb state."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
from shapely.geometry import LineString, Point

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sitegen import commercial_access, portals
from sitegen.prepared_roads import PreparedRoads
from test_sitegen_commercial_access import fixture


class PreparedRoadTests(unittest.TestCase):
    def test_nearby_matches_ordered_linear_query_with_boundaries_and_widths(self):
        rng = np.random.default_rng(5701)
        lines = [(rng.uniform(-200, 200, (9, 3)), float(w), kind, False)
                 for w, kind in ((2, 'residential'), (80, 'motorway'), (0, 'path'),
                                 (-1, 'residential'), (3, 'trunk'))]
        lines += [(np.array([[28., -5.], [28., 5.]]), 4., 'residential', False)]
        # Include each ULP around the exact broad-phase reach on both axes.
        # The final GEOS distance predicate remains the acceptance oracle.
        for edge in (np.nextafter(28.,-np.inf),28.,np.nextafter(28.,np.inf)):
            lines.extend(((np.array([[edge,-5.],[edge,5.]]),4.,'residential',False),
                          (np.array([[-5.,edge],[5.,edge]]),4.,'residential',False)))
        for offset in (np.zeros(2), np.array([123456., -654321.])):
            shifted = [(p+np.r_[offset,0.] if p.shape[1]==3 else p+offset, *row[1:])
                       for row in lines for p in (row[0],)]
            roads = PreparedRoads(shifted, offset)
            for portal in (np.zeros(2),np.array([1e-15,-1e-15]), *rng.uniform(-200,200,(30,2))):
                expected=[]
                for line in portals.simplified_lines(shifted):
                    points=np.asarray(line[0],float)[:,:2]-offset
                    half=float(line[1])
                    if not np.isfinite(half) or half<=0:continue
                    for a,b in zip(points[:-1],points[1:]):
                        if LineString([a,b]).distance(Point(portal))<=24+half:
                            expected.append((tuple(a),tuple(b),half,line[2]))
                actual=[(tuple(a),tuple(b),half,line[2]) for _,(a,b,half,line) in roads.nearby(portal,24)]
                self.assertEqual(actual,expected)

    def test_source_snapshot_and_simplification_only_once_per_job(self):
        source=np.array([[-50.,-12.],[0.,-12.],[50.,-12.]])
        roads=PreparedRoads([(source,4.,'residential',False)],(0.,0.))
        source[:]=999.
        with patch.object(portals,'simplified_lines',wraps=portals.simplified_lines) as simplify:
            a=roads.nearby(np.zeros(2),24);b=roads.nearby(np.zeros(2),24)
        self.assertEqual(simplify.call_count,1)
        self.assertEqual(len(a),1)
        np.testing.assert_array_equal(a[0][1][0],[-50.,-12.])
        self.assertIs(a[0][1],b[0][1])
        self.assertIs(roads.corridor(a[0][0]),roads.corridor(a[0][0]))
        with self.assertRaises(ValueError):roads.lines[0][0][0,0]=1.

    def test_live_sidewalk_reservations_are_not_cached(self):
        expected,walks,_,_,receiver,lines,source=fixture(walk=True)
        roads=PreparedRoads(lines,(0.,0.))
        kwargs=dict(owner='site:one',receiving=(receiver,),_roads=roads)
        ground=lambda xy:np.zeros(len(xy))
        self.assertEqual(commercial_access.propose_access(source,lines,walks,ground,0.,0.,**kwargs),expected)
        _,lo,hi,_=expected.crossing
        walks[0]['ramps']=[(lo,hi)]
        self.assertIsNone(commercial_access.propose_access(source,lines,walks,ground,0.,0.,**kwargs))

    def test_blocked_roads_still_charge_nearby_segment_budget(self):
        _,_,_,_,receiver,lines,source=fixture()
        roads=[*lines,*[(p,half,'footway',False) for p,half,*_ in lines]*64]
        self.assertIsNone(commercial_access.propose_access(source,roads,[],lambda xy:np.zeros(len(xy)),
            0.,0.,owner='budget',receiving=(receiver,),_roads=PreparedRoads(roads,(0.,0.))))

    def test_frame_mismatch_is_rejected(self):
        _,walks,_,_,receiver,lines,source=fixture()
        with self.assertRaisesRegex(ValueError,'different planning frame'):
            commercial_access.propose_access(source,lines,walks,lambda xy:np.zeros(len(xy)),0.,0.,
                owner='frame',receiving=(receiver,),_roads=PreparedRoads(lines,(10.,0.)))


if __name__=='__main__':unittest.main()
