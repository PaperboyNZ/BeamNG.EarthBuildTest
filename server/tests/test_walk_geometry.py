"""Corner rear offsets, exact approach joins and consumed-radius walk unions."""
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

import numpy as np
from shapely import make_valid, union_all
from shapely.geometry import LineString, Polygon, box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import junctions
import roads
from walk_geometry import corner_rear, MergedCornerRequired, ENDPOINT_JOIN_TOLERANCE_M


def circular(radius=6., widths=(2., 2.), angle=np.pi/2, shift=(0., 0., 0.)):
    t = np.linspace(-np.pi/2, -np.pi/2-angle, 37)
    inward = -np.c_[np.cos(t), np.sin(t)]
    arc = np.c_[-radius*inward, np.linspace(10., 13., len(t))] + shift
    start, end = arc[0].copy(), arc[-1].copy()
    start[:2] += inward[0]*widths[0]
    end[:2] += inward[-1]*widths[1]
    return arc, inward, start, end


def pavement(arc, rear):
    return Polygon(np.vstack((arc[:, :2], rear.outer[:, :2])))


class CornerRearTests(unittest.TestCase):
    def assert_simple(self, arc, rear):
        shape = pavement(arc, rear)
        self.assertTrue(shape.is_valid)
        self.assertGreater(shape.area, 1e-8)
        self.assertLess(LineString(arc[:, :2]).difference(shape.boundary.buffer(1e-8)).length, 1e-8)
        self.assertEqual(len(rear.outer), len(rear.widths))
        self.assertTrue(np.isfinite(rear.outer).all())
        if rear.stations is not None:
            back = rear.outer[::-1, :2]
            cells = [Polygon([a,b,c,d]) for a,b,c,d in zip(arc[:-1,:2],arc[1:,:2],back[1:],back[:-1])]
            self.assertTrue(all(p.is_valid and p.area > 0 for p in cells))
            combined = union_all(cells)
            self.assertAlmostEqual(sum(p.area for p in cells), combined.area, places=8)
            self.assertLess(combined.symmetric_difference(shape).area, 1e-8)

    def test_constant_width_follows_same_circle_and_exact_join_datums(self):
        arc, n, start, end = circular()
        original = arc.copy()
        rear = corner_rear(arc, n, 2., 2., start, end)
        self.assert_simple(arc, rear)
        self.assertFalse(rear.merged_inner)
        np.testing.assert_allclose(np.linalg.norm(rear.outer[:, :2], axis=1), 4., atol=1e-12)
        np.testing.assert_array_equal(rear.outer[[0, -1]], [end, start])
        np.testing.assert_array_equal(rear.outer[:, 2], arc[::-1, 2])
        np.testing.assert_array_equal(rear.widths, np.full(len(arc), 2.))
        np.testing.assert_allclose(rear.stations, np.r_[0., np.cumsum(np.linalg.norm(np.diff(arc[:, :2], axis=0), axis=1))][::-1])
        np.testing.assert_array_equal(arc, original)
        # Unlike the old miter, each rear station faces the corresponding curb.
        np.testing.assert_allclose(rear.outer[::-1, :2]-arc[:, :2], n*2., atol=1e-12)

    def test_variable_width_skew_and_raw_z_station_interpolation(self):
        arc, n, start, end = circular(8., (1., 3.5), angle=1.97)
        arc[:, 2] = np.linspace(0., 1., len(arc))**2*7
        start[2], end[2] = arc[0, 2], arc[-1, 2]
        rear = corner_rear(arc, n, 1., 3.5, start, end)
        self.assert_simple(arc, rear)
        widths = 1.+2.5*rear.stations/rear.stations[0]
        np.testing.assert_allclose(rear.widths, widths)
        np.testing.assert_allclose(rear.outer[::-1, :2]-arc[:, :2], n*widths[::-1, None], atol=1e-12)
        np.testing.assert_array_equal(rear.outer[:, 2], arc[::-1, 2])

    def test_reversal_and_large_translation_preserve_geometry(self):
        arc, n, start, end = circular(9., (1.2, 3.1), angle=2.1)
        rear = corner_rear(arc, n, 1.2, 3.1, start, end)
        reverse = corner_rear(arc[::-1], n[::-1], 3.1, 1.2, end, start)
        np.testing.assert_allclose(reverse.outer, rear.outer[::-1], atol=1e-12)
        np.testing.assert_allclose(reverse.widths, rear.widths[::-1], atol=1e-12)
        delta = np.array([678123.3, -251772.5, 82.])
        shifted = corner_rear(arc+delta, n, 1.2, 3.1, start+delta, end+delta)
        np.testing.assert_allclose(shifted.outer-delta, rear.outer, atol=1e-9)
        self.assert_simple(arc+delta, shifted)

    def test_chamfer_has_exact_two_rear_endpoints(self):
        arc = np.array([[3., 0., 8.], [0., 3., 9.]])
        n = np.array([[0., 1.], [1., 0.]])
        start, end = [3., 1., 8.], [1.5, 3., 9.]
        rear = corner_rear(arc, n, 1., 1.5, start, end)
        self.assert_simple(arc, rear)
        np.testing.assert_array_equal(rear.outer, [end, start])

    def test_consumed_radius_merges_without_losing_any_approach_pavement(self):
        for width in (3., 4., 7.):
            for shift in ((0., 0., 0.), (531234.2, -283178.1, 42.)):
                with self.subTest(width=width, shift=shift):
                    arc, n, start, end = circular(3., (width, width), shift=shift)
                    rear = corner_rear(arc, n, width, width, start, end)
                    self.assert_simple(arc, rear)
                    self.assertTrue(rear.merged_inner)
                    self.assertIsNone(rear.stations)
                    self.assertEqual(len(rear.outer), 1)
                    np.testing.assert_allclose(rear.outer[0, :2], shift[:2], atol=1e-8)
                    raw = arc.copy();raw[:, :2] += n*width
                    raw[0],raw[-1] = start,end
                    intended = make_valid(Polygon(np.vstack((arc[:, :2], raw[::-1, :2]))))
                    reach=20.
                    a,b=arc[0,:2],arc[-1,:2]
                    first=Polygon([a,start[:2],start[:2]+[reach,0],a+[reach,0]])
                    last=Polygon([b,end[:2],end[:2]+[0,reach],b+[0,reach]])
                    combined=union_all([pavement(arc,rear),first,last])
                    self.assertLess(intended.difference(combined.buffer(1e-8)).area, 1e-8)
                    # No corner fill crosses the unchanged curb into the road.
                    center=np.asarray(shift[:2])
                    sector=Polygon(np.vstack((arc[:,:2],center)))
                    road=box(*(center-3.),*center).difference(sector)
                    self.assertLess(pavement(arc,rear).intersection(road).area,1e-8)

    def test_invalid_or_unmergeable_input_reports_instead_of_publishing(self):
        arc,n,start,end=circular()
        with self.assertRaises(ValueError):corner_rear(arc,n,0.,2.,start,end)
        with self.assertRaisesRegex(ValueError, 'rear endpoint'):
            corner_rear(arc,n,2.,2.,[100.,100.,0.],[-100.,100.,0.])

    def test_recorded_auckland_transported_join_preserves_exact_original_endpoints(self):
        # Committed real evidence frozen with 22ac: separate point/vector frame
        # transforms leave a legitimate ~2.3mm tangential residual at one join.
        path=Path(__file__).resolve().parent/'fixtures/sidewalk_auckland_corner.json'
        source=json.loads(path.read_text(encoding='utf-8'))['corner']
        arc=np.asarray(source['arc'],np.float64);n=np.asarray(source['inward'],np.float64)
        outer=np.asarray(source['outer'],np.float64);widths=source['outer_widths']
        expected=arc[-1,:2]+n[-1]*widths[0]
        residual=np.linalg.norm(outer[0,:2]-expected)
        self.assertGreater(residual,.002)
        self.assertLess(residual,ENDPOINT_JOIN_TOLERANCE_M)
        rear=corner_rear(arc,n,widths[-1],widths[0],outer[-1],outer[0])
        self.assert_simple(arc,rear)
        np.testing.assert_array_equal(rear.outer[[0,-1]],outer[[0,-1]])
        np.testing.assert_array_equal(arc,np.asarray(source['arc']))
        np.testing.assert_array_equal(n,np.asarray(source['inward']))

    def test_endpoint_residual_over_one_centimeter_is_rejected(self):
        arc,n,start,end=circular(8.,(2.5,2.5))
        tangent=np.array([-n[-1,1],n[-1,0]])
        end[:2]+=tangent*(ENDPOINT_JOIN_TOLERANCE_M+.00001)
        with self.assertRaisesRegex(ValueError,'rear endpoint'):
            corner_rear(arc,n,2.5,2.5,start,end)


class JunctionCornerRearTests(unittest.TestCase):
    @staticmethod
    def spec(width=6., walk=2.5):
        return roads.Spec(width, 'paved', True, 'residential', True, walk, 2, None, None, None)

    def assert_corner(self, corner):
        rear=np.asarray(corner['outer']);arc=corner['arc']
        self.assertTrue(Polygon(np.vstack((arc[:,:2],rear[:,:2]))).is_valid)
        self.assertGreater(Polygon(np.vstack((arc[:,:2],rear[:,:2]))).area,0.)
        self.assertEqual(len(rear),len(corner['outer_widths']))
        if not corner['merged_inner']:
            self.assertEqual(len(rear),len(arc))
            self.assertEqual(len(rear),len(corner['outer_stations']))

    def test_normal_constructor_curved_rear_guard_and_exact_approach_joins(self):
        spec=self.spec()
        rs=[('east',spec,np.array([[0.,0.,1.],[100.,0.,3.]]),0.),
            ('north',spec,np.array([[0.,0.,1.],[0.,100.,4.]]),0.)]
        seen=[]
        from walk_geometry import corner_rear as helper
        def observe(*args):
            result=helper(*args);seen.append((args,result));return result
        with patch.object(junctions,'corner_rear',side_effect=observe):
            corners,cuts,*_=junctions.find(rs,roads.has_sidewalks,None)
        self.assertEqual(len(corners),1)
        self.assert_corner(corners[0])
        np.testing.assert_array_equal(corners[0]['outer'][[0,-1]], [seen[-1][0][-1],seen[-1][0][-2]])
        self.assertTrue(cuts)

    def test_approach_bulbs_keep_original_curb_and_use_valid_curved_rear(self):
        spec=self.spec(width=10.,walk=1.2)
        rs=[('east',spec,np.array([[0.,0.,0.],[100.,0.,0.]]),0.),
            ('north',spec,np.array([[0.,0.,0.],[0.,100.,0.]]),0.)]
        corners=junctions.find(rs,roads.has_sidewalks,None,parking_m=2.,has_parking=lambda _:True)[0]
        self.assertEqual(len(corners),1)
        self.assert_corner(corners[0])
        self.assertGreater(len(corners[0]['arc']),6)
        self.assertFalse(corners[0]['merged_inner'])
        np.testing.assert_allclose(corners[0]['outer'][::-1,:2]-corners[0]['arc'][:,:2],corners[0]['inward']*1.2)

    def test_across_constructor_has_matching_station_metadata(self):
        spec=self.spec(width=8.,walk=1.5)
        a,b=np.array([0.,0.]),np.array([7.,-7.])
        rs=[('north',spec,np.array([[*a,0.],[0.,100.,2.]]),0.),
            ('east',spec,np.array([[*b,0.],[100.,-7.,3.]]),0.),
            ('connector',spec,np.array([[*a,0.],[*b,0.]]),0.)]
        bi=(0.,0,0,1,np.array([0.,1.]),1,a)
        bj=(0.,1,0,1,np.array([1.,0.]),1,b)
        # This exact orientation follows the southwest outside of the connector.
        got=junctions._across(rs,bj,bi,2,(a+b)/2,None)
        self.assertIsNotNone(got)
        self.assert_corner(got[0])

    def test_unsupported_compound_does_not_remove_unrelated_good_junction(self):
        spec=self.spec()
        rs=[]
        for offset in (0.,200.):
            p=np.array([offset,offset,0.])
            for name,delta in (('east',[100.,0.,0.]),('north',[0.,100.,0.])):
                rs.append((name+str(offset),spec,np.vstack((p,p+delta)),0.))
        from walk_geometry import corner_rear as helper
        def unsupported_first(arc,*args):
            if arc[:,0].mean()<100.:
                raise MergedCornerRequired('unsupported compound fixture')
            return helper(arc,*args)
        debug=[]
        with patch.object(junctions,'corner_rear',side_effect=unsupported_first):
            corners=junctions.find(rs,roads.has_sidewalks,None,debug=debug)[0]
        self.assertEqual(len(corners),1)
        self.assertGreater(corners[0]['arc'][:,0].mean(),200.)
        self.assertTrue(any(row[0]=='rear offset merge' for row in debug))

    def test_unsupported_across_returns_to_ordinary_junction_fallback(self):
        spec=self.spec(width=8.,walk=1.5)
        a,b=np.array([0.,0.]),np.array([7.,-7.])
        rs=[('north',spec,np.array([[*a,0.],[0.,100.,2.]]),0.),
            ('east',spec,np.array([[*b,0.],[100.,-7.,3.]]),0.),
            ('connector',spec,np.array([[*a,0.],[*b,0.]]),0.)]
        bi=(0.,0,0,1,np.array([0.,1.]),1,a)
        bj=(0.,1,0,1,np.array([1.,0.]),1,b)
        debug=[]
        with patch.object(junctions,'corner_rear',side_effect=MergedCornerRequired('unsupported fixture')):
            self.assertIsNone(junctions._across(rs,bj,bi,2,(a+b)/2,None,debug=debug))
        self.assertTrue(any(row[0]=='across: rear offset merge' for row in debug))

    def test_zero_width_asphalt_constructor_retains_legacy_fill_and_edge_cuts(self):
        spec=roads.Spec(8.,'paved',False,'secondary',True,2.5,2,None,None,None)
        rs=[('east',spec,np.array([[0.,0.,0.],[100.,0.,0.]]),0.),
            ('north',spec,np.array([[0.,0.,0.],[0.,100.,0.]]),0.)]
        with patch.object(junctions,'corner_rear',side_effect=AssertionError('asphalt has no sidewalk rear')):
            corners,cuts,crossings,ramps,*_=junctions.find(rs,lambda _:True,0.,pavement=True)
        self.assertEqual(len(corners),1)
        corner=corners[0]
        np.testing.assert_array_equal(corner['outer'],[[4.,16.,0.],[4.,4.,0.],[16.,4.,0.]])
        np.testing.assert_array_equal(corner['outer_widths'],[0.,0.,0.])
        self.assertIsNone(corner['outer_stations'])
        self.assertGreater(Polygon(corner['fill'][:,:2]).area,0.)
        self.assertGreater(len(corner['arc']),3)
        self.assertEqual(corner['road_sides'],(('east',1),('north',-1)))
        self.assertEqual(len(corner['edge_cuts']),2)
        self.assertFalse(crossings);self.assertFalse(ramps)

    def test_real_curbless_roadcorners_fixture_still_constructs_all_four_fills(self):
        import roadcorners
        from test_roads import FRAME, features
        lines=[[(-100.,0.),(0.,0.),(100.,0.)],[(0.,-100.),(0.,0.),(0.,100.)]]
        f=features(lines,['secondary','secondary'])
        _frame,_rows,corners=roadcorners.source([f],frame=FRAME)
        self.assertEqual(len(corners),4)
        for corner in corners:
            self.assertGreater(len(corner['arc']),3)
            self.assertTrue(corner.get('edge_cuts'))
            self.assertGreater(Polygon(corner['fill'][:,:2]).area,0.)


if __name__=='__main__':unittest.main()
