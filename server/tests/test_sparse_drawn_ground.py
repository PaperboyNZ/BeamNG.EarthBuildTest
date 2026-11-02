"""Sparse probes retain the terrain's two triangles, without sampling empty space."""
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import roadmesh


class Frame:
    def enu_to_geodetic(self,x,y,z):return x,y,z
    def geodetic_to_enu(self,x,y,z):return x,y,z


class SparseGroundTests(unittest.TestCase):
    def test_triangle_diagonal_and_vertex_quantization(self):
        # Four lattice heights: 0,10,20,100. Bilinear interpolation would give
        # different answers; BeamNG cuts the square on its SW/NE diagonal.
        def heights(x,y):return 10*x+20*y+70*x*y+.1
        xy=np.array([[.2,.7],[.7,.2],[0,0],[1,1]])
        np.testing.assert_allclose(roadmesh.drawn_ground(Frame(),heights,xy,.25),[30,25,0,100])

    def test_separated_points_sample_unique_corners_once(self):
        calls=[]
        def heights(x,y):calls.append(np.c_[x,y]);return x*.5-y*.25
        xy=np.array([[-100.2,-80.8],[100.1,80.9],[-100.2,-80.8]])
        np.testing.assert_allclose(roadmesh.drawn_ground(Frame(),heights,xy),xy[:,0]*.5-xy[:,1]*.25)
        self.assertEqual(len(calls),1)
        self.assertEqual(len(calls[0]),8)
        self.assertTrue(np.equal(calls[0],np.floor(calls[0])).all())

    def test_empty_does_not_sample(self):
        def heights(x,y):self.fail('empty request sampled terrain')
        self.assertEqual(roadmesh.drawn_ground(Frame(),heights,[]).size,0)


if __name__=='__main__':unittest.main()
