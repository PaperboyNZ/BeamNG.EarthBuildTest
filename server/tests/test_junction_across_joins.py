"""Across-connector producers retain the exact branch-cut curb/rear joins."""
from collections import Counter
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from shapely import union_all
from shapely.geometry import Polygon

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import junctions as j
import sidewalks as sw


def scene(ui,uj,length=1.,half_widths=(3.2,3.,3.),walks=(.8,1.1)):
    """Compact real-piece cases: near-straight connector, or consumed return."""
    pi=np.array([0.,0.]);pj=np.array([length,0.])
    ui=np.asarray(ui,float);uj=np.asarray(uj,float)
    ui/=np.linalg.norm(ui);uj/=np.linalg.norm(uj)
    roads=[]
    for name,p,u,width,walk,z in (('i',pi,ui,half_widths[0],walks[0],0.),
                                ('j',pj,uj,half_widths[1],walks[1],.25)):
        spec=SimpleNamespace(width=2*width,walk=walk,cls='residential')
        line=np.c_[np.vstack((p,p+u*60.)),[z,z+.2]]
        roads.append((name,spec,line,0.))
    roads.append(('c',SimpleNamespace(width=2*half_widths[2],walk=max(walks),cls='residential'),
                  np.c_[np.vstack((pi,pj)),[0.,.25]],0.))
    bi=(0.,0,0,1,ui,1,pi);bj=(0.,1,0,1,uj,1,pj)
    return roads,bi,bj,2,(pi+pj)/2


def geometric_edges(mesh):
    p,t,uv,m=mesh
    def key(index):return tuple(np.round(p[index],8))
    return Counter(tuple(sorted((key(int(a)),key(int(b))))) for face in t
                   for a,b in zip(face,np.roll(face,-1)))


class AcrossJoinTests(unittest.TestCase):
    def assert_joined(self,fixture):
        roads,bi,bj,connector,centre=fixture
        before=[road[2].copy() for road in roads]
        debug=[];got=j._across(*fixture,None,debug)
        self.assertIsNotNone(got,debug)
        c,ti,tj=got;ui,uj=bi[4],bj[4];pi,pj=bi[6],bj[6]
        wi,wj=roads[0][1].width/2,roads[1][1].width/2
        ni,nj=j._left(ui),j._left(uj)
        ci,cj=pi+ui*ti+ni*wi,pj+uj*tj-nj*wj
        np.testing.assert_array_equal(c['arc'][0,:2],ci)
        np.testing.assert_array_equal(c['arc'][-1,:2],cj)
        np.testing.assert_allclose(c['outer'][-1,:2],pi+ui*ti+ni*(wi+roads[0][1].walk),atol=1e-12)
        np.testing.assert_allclose(c['outer'][0,:2],pj+uj*tj-nj*(wj+roads[1][1].walk),atol=1e-12)
        np.testing.assert_array_equal(c['inward'][0],ni)
        np.testing.assert_array_equal(c['inward'][-1],-nj)
        self.assertGreater(float((c['arc'][1,:2]-ci)@-ui),1e-9)
        self.assertGreater(float((cj-c['arc'][-2,:2])@uj),1e-9)
        self.assertEqual(float(c['outer_widths'][-1]),roads[0][1].walk)
        self.assertEqual(float(c['outer_widths'][0]),roads[1][1].walk)
        shape=Polygon(np.vstack((c['arc'][:,:2],c['outer'][:,:2])))
        self.assertTrue(shape.is_valid);self.assertGreater(shape.area,0.)
        for old,road in zip(before,roads):np.testing.assert_array_equal(old,road[2])
        return c,ti,tj

    def assert_continuous_mesh(self,corner):
        builder=sw.Builder((0.,0.,0.),collision=True)
        builder.add_corner(corner['arc'],corner['inward'],sw.corner_outer(corner),
                           outer_stations=corner['outer_stations'])
        top=sw.corner_outer(corner)[::-1].copy();top[:,2]+=sw.CURB_H+2.5*sw.CROSS_SLOPE
        for mesh in (builder.arrays(),builder.col.arrays()):
            p,t,uv,m=mesh
            self.assertTrue(np.isfinite(p).all() and np.isfinite(uv).all())
            xyz=p[t[m==1]]
            cross=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0])[:,2]
            self.assertTrue((cross>0).all(),'accepted corner paving must have positive XY winding')
            shapes=[Polygon(q[:,:2]) for q in xyz]
            self.assertAlmostEqual(sum(q.area for q in shapes),union_all(shapes).area,places=8)
            edges=geometric_edges(mesh)
            for a,b in zip(top[:-1],top[1:]):
                edge=tuple(sorted((tuple(np.round(a,8)),tuple(np.round(b,8)))))
                self.assertEqual(edges[edge],2,'each actual rear top edge must meet slab and continuous back')

    def test_two_near_straight_singletons_use_both_branch_widths_and_directions(self):
        fixture=scene((-1.,.02),(1.,.04),length=9.,half_widths=(3.2,3.4,3.))
        roads,bi,bj,_,_=fixture
        uc=np.array([1.,0.])
        self.assertEqual(len(j._piece(bi[6],bi[4],3.2,uc,3.,3.)[0]),1)
        self.assertEqual(len(j._piece(bj[6],-uc,3.,bj[4],3.4,3.)[0]),1)
        c,ti,tj=self.assert_joined(fixture)
        self.assertEqual((ti,tj),(0.,0.));self.assertEqual(len(c['arc']),2)
        self.assert_continuous_mesh(c)

    def test_first_consumed_piece_changes_only_first_arc_sample_and_fill_join(self):
        fixture=scene((-1.,.02),(0.,-1.))
        roads,bi,bj,_,_=fixture
        p2=j._piece(bj[6],np.array([-1.,0.]),3.,bj[4],3.,3.)
        self.assertGreater(p2[1],1.)
        c,ti,tj=self.assert_joined(fixture)
        np.testing.assert_array_equal(c['arc'][1:,:2],p2[0][1:])
        self.assertAlmostEqual(ti,p2[1]-1.);self.assertEqual(tj,p2[2])
        np.testing.assert_array_equal(c['fills'][0][1,:2],c['arc'][0,:2])
        self.assert_continuous_mesh(c)

    def test_last_consumed_piece_changes_only_last_arc_sample_and_fill_join(self):
        fixture=scene((0.,-1.),(1.,.02),half_widths=(3.,3.2,3.))
        roads,bi,bj,_,_=fixture
        p1=j._piece(bi[6],bi[4],3.,np.array([1.,0.]),3.,3.)
        self.assertGreater(p1[2],1.)
        c,ti,tj=self.assert_joined(fixture)
        np.testing.assert_array_equal(c['arc'][:-1,:2],p1[0][:-1])
        self.assertEqual(ti,p1[1]);self.assertAlmostEqual(tj,p1[2]-1.)
        np.testing.assert_array_equal(c['fills'][0][-1,:2],c['arc'][-1,:2])
        self.assert_continuous_mesh(c)

    def test_terminal_wins_over_multiple_nearby_interior_samples_without_mutation(self):
        fixture=scene((-1.,0.),(1.,0.),length=9.,half_widths=(3.,3.,3.))
        # Explicit unit stencil isolates the dedup policy: three retained
        # interior suffix samples all lie within5cm of the final exact join.
        a=np.array([[0.,-3.],[4.,-3.],[8.,-3.],[8.965,-3.03],[8.965,-2.97],[9.,-3.02]])
        b=np.array([[9.,-3.]])
        saved=(a.copy(),b.copy())
        with patch.object(j,'_piece',side_effect=[(a,0.,0.,None),(b,0.,0.,None)]):
            c,_,_=self.assert_joined(fixture)
        np.testing.assert_array_equal(c['arc'][:,:2],[[0.,-3.],[4.,-3.],[8.,-3.],[9.,-3.]])
        np.testing.assert_array_equal(a,saved[0]);np.testing.assert_array_equal(b,saved[1])
        self.assert_continuous_mesh(c)

    def test_reversed_or_coincident_join_returns_fallback_before_rear_solver(self):
        fixture=scene((-1.,0.),(1.,0.),length=9.,half_widths=(3.,3.,3.))
        a=np.array([[0.,-3.],[-1.,-3.]])
        b=np.array([[9.,-3.]])
        debug=[]
        with patch.object(j,'_piece',side_effect=[(a,0.,0.,None),(b,0.,0.,None)]),\
             patch.object(j,'corner_rear',side_effect=AssertionError('reversed producer reached rear solver')):
            self.assertIsNone(j._across(*fixture,None,debug))
        self.assertEqual(debug[-1][0],'across: reversed branch join')
        debug=[]
        tiny=scene((-1.,0.),(1.,0.),length=.04,half_widths=(3.,3.,3.))
        with patch.object(j,'corner_rear',side_effect=AssertionError('coincident producer reached rear solver')):
            self.assertIsNone(j._across(*tiny,None,debug))
        self.assertEqual(debug[-1][0],'across: coincident branch joins')


if __name__=='__main__':unittest.main()
