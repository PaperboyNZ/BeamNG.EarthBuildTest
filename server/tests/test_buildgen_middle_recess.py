"""Middle representations retain architectural recess depth and closed surfaces."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings as b
from buildgen import facades,freeze_items,residential,regional_architecture as regional
from buildgen.regional_openings import draw_arch
from test_buildgen_facades import building
from test_buildgen_residential_structures import building as dwelling


def hits(mesh, origin, direction):
    """Actual triangle intersections, sorted in metres along a unit ray."""
    pts=mesh[0][mesh[2]]
    a,e1,e2=pts[:,0],pts[:,1]-pts[:,0],pts[:,2]-pts[:,0]
    h=np.cross(np.broadcast_to(direction,e2.shape),e2)
    det=np.einsum('ij,ij->i',e1,h)
    good=np.abs(det)>1e-10
    f=np.zeros_like(det);f[good]=1/det[good]
    s=np.asarray(origin)-a
    u=f*np.einsum('ij,ij->i',s,h)
    q=np.cross(s,e1)
    v=f*(q@direction)
    t=f*np.einsum('ij,ij->i',e2,q)
    good &= (u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)&(t>=0)
    return sorted((float(t[i]),int(mesh[3][i])) for i in np.flatnonzero(good))


class MiddleRecessTests(unittest.TestCase):
    def single(self,depth=.6,lite=True,arch='rectangular'):
        spec=building(width=12.,depth=10.,roof_shape='flat')
        spec.front=0
        plan=freeze_items([(spec,0.,0.)])[0][0]
        opening=facades.Opening('window',0,3.,5.,1.,2.4,depth=depth)
        elevation=facades.Elevation(0,0,12.,(opening,))
        plan=replace(plan,facades=replace(plan.facades,elevations=(elevation,)))
        m=b.Mesh()
        with patch.object(regional,'for_spec',return_value=None),patch.object(regional,'aperture_shape',return_value=arch):
            facades.draw(m,plan,0.,0.,-.5,lite=lite)
        p,uv,t,mat,col=m.arrays()
        return plan,opening,(p,uv,t,mat,b.MATERIALS,col)

    def test_deep_middle_pane_is_recessed_and_visible_through_wall_cut(self):
        _,_,mesh=self.single()
        intersections=hits(mesh,(4.,-5.,1.7),np.array((0.,1.,0.)))
        self.assertTrue(intersections)
        self.assertAlmostEqual(intersections[0][0],5.6,places=8)
        self.assertEqual(mesh[4][intersections[0][1]],b.LOOKS['bne_bld_fac_white'][0])

    def test_four_returns_close_the_retained_hole_without_close_trim_or_sills(self):
        _,o,mesh=self.single()
        triangles=mesh[0][mesh[2]]
        returns=[]
        for tri in triangles:
            if np.ptp(tri[:,1])<.5:continue
            if not (np.all(tri[:,0]>=o.left-1e-8) and np.all(tri[:,0]<=o.right+1e-8)
                    and np.all(tri[:,2]>=o.bottom-1e-8) and np.all(tri[:,2]<=o.top+1e-8)):continue
            returns.append(tri)
        self.assertEqual(len(returns),8)
        area=sum(np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))/2 for t in returns)
        self.assertAlmostEqual(area,2*(o.right-o.left+o.top-o.bottom)*o.depth,places=8)
        _,_,near=self.single(lite=False)
        self.assertLess(len(mesh[0]),len(near[0]))

    def test_shallow_openings_still_use_cheap_overlay(self):
        for depth in (.09,.16,.24,.299):
            with self.subTest(depth=depth):
                _,_,mesh=self.single(depth=depth)
                t,material=hits(mesh,(4.,-5.,1.7),np.array((0.,1.,0.)))[0]
                self.assertAlmostEqual(t,4.98,places=8)
                self.assertEqual(mesh[4][material],b.LOOKS['bne_bld_fac_white'][0])

    def test_deep_middle_glazing_keeps_close_uv_and_variant(self):
        _,_,close=self.single(lite=False)
        _,_,middle=self.single(lite=True)
        def panes(mesh):
            material=mesh[4].index(b.LOOKS['bne_bld_fac_white'][0])
            rear=np.all(np.abs(mesh[0][mesh[2]][:,:,1]-.6)<1e-8,axis=1)
            ids=np.unique(mesh[2][(mesh[3]==material)&rear])
            return mesh[0][ids],mesh[1][ids],mesh[5][ids]
        for expected,actual in zip(panes(close),panes(middle)):
            np.testing.assert_array_equal(expected,actual)

    def test_arch_middle_retains_reveals_with_a_cheaper_curve(self):
        class Mesh:
            def __init__(self):self.faces=[]
            def quad(self,*args):self.faces.append(args[:4])
            def tri(self,*args):self.faces.append(args[:3])
        opening=facades.Opening('window',0,3.,5.,1.,3.,depth=.6)
        at=lambda s,z,d=0.:(s,d,z)
        for shape in ('arched','segmental'):
            middle=Mesh();close=Mesh();flat=Mesh()
            draw_arch(middle,opening,at,1,2,.6,.065,shape,lite=True,retain_depth=True)
            draw_arch(close,opening,at,1,2,.6,.065,shape,lite=False)
            draw_arch(flat,opening,at,1,2,.6,.065,shape,lite=True)
            self.assertTrue(any(min(p[1] for p in f)==-.6 for f in middle.faces))
            self.assertTrue(all(p[1]>=0 for f in flat.faces for p in f))
            self.assertLess(len(middle.faces),len(close.faces))
            # Centre below the spring is glazing, not a front wall/backing.
            _,_,mesh=self.single(depth=.6,arch=shape)
            self.assertAlmostEqual(hits(mesh,(4.,-5.,1.3),np.array((0.,1.,0.)))[0][0],5.6,places=8)

    def test_real_privacy_families_keep_depth_at_middle_and_collision_is_unchanged(self):
        checked=0
        for region,options in residential.catalogue()['regions'].items():
            for family,_ in options:
                if not residential.catalogue()['families'][family].get('privacy'):
                    continue
                with self.subTest(family=family):
                    _,items,near,middle,col=dwelling(region,family,roof_shape='flat')
                    spec=items[0][0]
                    for e in spec.facades.elevations:
                        ring=(spec.footprint.outer,*spec.footprint.holes)[e.boundary]
                        start=np.asarray(ring[e.edge]);end=np.asarray(ring[(e.edge+1)%len(ring)])
                        tangent=(end-start)/e.length
                        outward=np.array((tangent[1],-tangent[0]))
                        for op in e.openings:
                            if op.kind!='window' or op.assembly or (op.depth or 0)<.3:continue
                            point=start+tangent*(op.left+op.right)/2
                            origin=np.r_[point+outward*2,(op.bottom+op.top)/2]
                            ray=np.r_[-outward,0.]
                            closeHit=hits(near,origin,ray)[0]
                            middleHit=hits(middle,origin,ray)[0]
                            self.assertAlmostEqual(middleHit[0],closeHit[0],places=7)
                            self.assertGreater(middleHit[0],2.3)
                            checked+=1
                    frozen=freeze_items(items)
                    for index in (0,1,2,3,5):np.testing.assert_array_equal(b.collision_mesh(frozen)[index],col[index])
                    self.assertLess(len(middle[0]),len(near[0]))
        self.assertGreater(checked,20)

    def test_plan_and_collision_do_not_depend_on_representation_order(self):
        _,items,near,middle,col=dwelling('sahel','sahel_compound',roof_shape='flat')
        spec=items[0][0]
        before=spec.facades
        sky=b._sky_mesh(items)
        for lite,expected in ((True,middle),(False,near),(True,middle)):
            actual=b.build(items,lite=lite)
            for index in (0,1,2,3,5):np.testing.assert_array_equal(actual[index],expected[index])
        self.assertIs(spec.facades,before)
        self.assertTrue(np.isfinite(sky[0]).all())
        self.assertLess(len(sky[0]),len(middle[0]))
        for index in (0,1,2,3,5):np.testing.assert_array_equal(b.collision_mesh(items)[index],col[index])


if __name__=='__main__':unittest.main()
