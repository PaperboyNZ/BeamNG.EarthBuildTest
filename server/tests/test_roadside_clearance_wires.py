"""Bare furniture spans and typed power-line spans share relocation semantics."""
from pathlib import Path
import sys
import unittest

import numpy as np
from shapely.geometry import box

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import furniture
import roadside_clearance as clearance


def pole(x,y=2.,z=0.):return ['pole',float(x),float(y),float(z),0.,1.,9.,0.]


def sidewalk():
    return dict(pts=np.array([[-20.,1.25,0.],[80.,1.25,0.]]),side=1,w=2.5,curb_h=.15)


def span(a,b):
    t=np.linspace(0.,1.,5)[:,None]
    points=(1.-t)*np.asarray(a)+t*np.asarray(b)
    points[:,2]-=[0.,1.25,2.,1.5,0.]
    return points


class RoadsideWireContractTests(unittest.TestCase):
    def relocated(self,rows,wires):
        original=[np.array(r[1:4],float) for r in rows]
        kept=clearance.clear(rows,wires=wires,areas=[box(-30.,1.,90.,2.5)],walks=[sidewalk()])
        poles=[r for r in kept if r[0]=='pole']
        self.assertEqual(len(poles),len(original))
        return [np.asarray(r[1:4])-old for r,old in zip(poles,original)]

    def assert_radius(self,wire,expected):
        points=wire[0] if isinstance(wire,tuple) else wire
        mesh=furniture.wire_mesh([wire],(0.,0.,0.))
        self.assertIsNotNone(mesh)
        self.assertAlmostEqual(float(np.linalg.norm(mesh[0][0]-points[0])),expected,places=12)

    def test_typed_span_one_moved_pole_keeps_width_and_multistation_sag(self):
        rows=[pole(0.),pole(20.,.47)]
        points=span([0.,2.,9.],[20.,.47,10.])
        before=points.copy();points.setflags(write=False)
        radius=np.float64(.071)
        wires=[(points,radius)]
        deltas=self.relocated(rows,wires)
        self.assertGreater(np.linalg.norm(deltas[0]),.1)
        np.testing.assert_array_equal(deltas[1],np.zeros(3))
        self.assertIsInstance(wires[0],tuple)
        self.assertIs(wires[0][1],radius)
        t=np.linspace(0.,1.,len(points))[:,None]
        expected=before+(1.-t)*deltas[0]+t*deltas[1]
        np.testing.assert_array_equal(wires[0][0],expected)
        np.testing.assert_array_equal(points,before)
        old_sag=before[:,2]-((1.-t[:,0])*before[0,2]+t[:,0]*before[-1,2])
        new=wires[0][0]
        new_sag=new[:,2]-((1.-t[:,0])*new[0,2]+t[:,0]*new[-1,2])
        np.testing.assert_allclose(new_sag,old_sag,atol=1e-12)
        self.assert_radius(wires[0],radius)

    def test_mixed_spans_both_poles_move_in_order_and_keep_distinct_mesh_widths(self):
        rows=[pole(0.),pole(20.)]
        a=span([0.,2.,9.],[20.,2.,9.]);b=a+[0.,0.,2.];c=a+[0.,0.,4.]
        before=[p.copy() for p in (a,b,c)]
        for p in (a,b,c):p.setflags(write=False)
        wires=[(a,.019),b,(c,.063)]
        deltas=self.relocated(rows,wires)
        self.assertTrue(all(np.linalg.norm(d)>.1 for d in deltas))
        t=np.linspace(0.,1.,len(a))[:,None]
        for i,(wire,old) in enumerate(zip(wires,before)):
            moved=wire[0] if isinstance(wire,tuple) else wire
            np.testing.assert_array_equal(moved,old+(1.-t)*deltas[0]+t*deltas[1])
            self.assertEqual(isinstance(wire,tuple),i!=1)
        for original,saved in zip((a,b,c),before):np.testing.assert_array_equal(original,saved)
        for wire,width in zip(wires,(.019,furniture.WIRE_R,.063)):self.assert_radius(wire,width)
        self.assertIsNotNone(furniture.wire_mesh(wires,(0.,0.,0.)))

    def test_removed_pole_rejects_whole_typed_and_bare_spans(self):
        points=span([0.,0.,9.],[20.,20.,9.]);points.setflags(write=False)
        unrelated=span([20.,20.,9.],[40.,20.,9.]);unrelated.setflags(write=False)
        typed=(points,.041)
        wires=[typed,points,unrelated]
        rows=[pole(0.,0.),pole(20.,20.)]
        kept=clearance.clear(rows,wires=wires,areas=[box(-1.,-1.,1.,1.)])
        self.assertEqual(len(kept),1)
        self.assertEqual(len(wires),1)
        self.assertIs(wires[0],unrelated)

    def test_no_matching_pole_preserves_exact_arrays_and_typed_wrapper(self):
        points=span([-0.,0.,9.],[20.,0.,9.]);points.setflags(write=False)
        bare=points.copy();bare.setflags(write=False)
        typed=(points,np.float64(.083));wires=[typed,bare]
        saved=[points.tobytes(),bare.tobytes()]
        clearance.clear([pole(80.,80.)],wires=wires,areas=[])
        self.assertIs(wires[0],typed);self.assertIs(wires[1],bare)
        self.assertEqual(points.tobytes(),saved[0]);self.assertEqual(bare.tobytes(),saved[1])

    def test_matching_unchanged_endpoints_preserve_negative_zero_and_input_identity(self):
        points=np.array([[-0.,-0.,-0.],[5.,1.,-2.],[10.,0.,0.]])
        points.setflags(write=False);typed=(points,.027);wires=[typed,points]
        saved=points.tobytes()
        clearance.clear([pole(0.,0.),pole(10.,0.)],wires=wires,areas=[])
        self.assertIs(wires[0],typed);self.assertIs(wires[1],points)
        self.assertEqual(points.tobytes(),saved)


if __name__=='__main__':unittest.main()
