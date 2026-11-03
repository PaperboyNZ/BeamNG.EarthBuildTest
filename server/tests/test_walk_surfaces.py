"""Paired corner paving follows its metric midline without changing native skins."""
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

import numpy as np
from shapely import union_all
from shapely.geometry import Polygon

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import buildings
import sidewalks as sw
from walk_geometry import corner_rear
from walk_surfaces import curved_corner
from buildgen import access


def corner(widths=(2.,2.),angle=0.,transpose=False,ramps=False,origin=(0.,0.,0.),samples=37):
    theta=np.linspace(-np.pi/2,-np.pi,samples)
    inward=-np.c_[np.cos(theta),np.sin(theta)]
    arc=np.c_[-6.*inward,np.linspace(10.,10.4,len(theta))]
    rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    arc[:,:2]=arc[:,:2]@rotation.T;inward=inward@rotation.T
    if transpose:arc[:,:2]=arc[:,[1,0]];inward=inward[:,::-1]
    arc+=np.array([121.,-83.,7.])
    start,end=arc[0].copy(),arc[-1].copy()
    start[:2]+=inward[0]*widths[0];end[:2]+=inward[-1]*widths[1]
    rear=corner_rear(arc,inward,*widths,start,end)
    outer=rear.outer.copy();outer[:,2]+=(rear.widths-2.5)*sw.CROSS_SLOPE
    length=float(np.linalg.norm(np.diff(arc[:,:2],axis=0),axis=1).sum())
    lowered=list(ramps) if isinstance(ramps,(tuple,list)) else ([(.35*length,.6*length)] if ramps else [])
    piece=(1,arc,inward,outer,lowered,2.5,sw.CURB_H,(False,False),1)
    native=sw.native_mesh([piece],np.asarray(origin,float),True)
    return arc,inward,outer,rear.stations,native


def native_chains(mesh,rear_count):
    p,t,uv,m=mesh;rows=np.flatnonzero(m==1)
    start=int(t[:rows[0]].max())+1 if rows[0] else 0
    end=int(t[rows[-1]+1:].min()) if rows[-1]+1<len(t) else len(p)
    split=end-rear_count
    return start,end,p[start:split],p[split:end][::-1]


def max_chain_residual(points,chain):
    a=chain[:-1];d=np.diff(chain,axis=0);squared=np.einsum('ij,ij->i',d,d)
    result=0.
    for point in points:
        u=np.clip(np.einsum('ij,ij->i',point-a,d)/np.maximum(squared,1e-30),0,1)
        result=max(result,float(np.linalg.norm(a+u[:,None]*d-point,axis=1).min()))
    return result


class CurvedCornerTests(unittest.TestCase):
    def check_corner(self,raw,arc,inward,outer,stations,origin,phase=7.25):
        saved=tuple(a.copy() for a in raw)
        _,_,native_front,native_rear=native_chains(raw,len(outer))
        result=curved_corner(raw,origin,arc,inward,outer,stations,phase)
        p,t,uv,m=result
        for before,after in zip(saved,raw):np.testing.assert_array_equal(before,after)
        np.testing.assert_array_equal(p[:len(raw[0])],raw[0])
        np.testing.assert_array_equal(uv[:len(raw[2])],raw[2])
        np.testing.assert_array_equal(t[m!=1],raw[1][raw[3]!=1])
        np.testing.assert_array_equal(m[m!=1],raw[3][raw[3]!=1])
        self.assertTrue(np.isfinite(p).all() and np.isfinite(uv).all())
        pairs=p[len(raw[0]):].reshape(-1,2,3)
        metric=uv[len(raw[0]):].reshape(-1,2,2)
        front,rear=pairs[:,0],pairs[:,1]
        # Native vertices remain exact except a redundant ULP-coincident pair
        # may share one row within1e-9m; inserted points remain on native3D edges.
        for old,new in ((native_front,front),(native_rear,rear)):
            for index,point in enumerate(old):
                if not np.all(new==point,axis=1).any():
                    neighbors=np.delete(old,index,axis=0)
                    self.assertLessEqual(float(np.linalg.norm(neighbors-point,axis=1).min()),1e-9)
                    self.assertLessEqual(float(np.linalg.norm(new-point,axis=1).min()),1e-9)
            self.assertLess(max_chain_residual(new,old),1e-8)
            np.testing.assert_array_equal(new[[0,-1]],old[[0,-1]])
        faces=t[m==1];xyz=p[faces]
        cross=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0])[:,2]
        self.assertTrue((cross>0).all(),'pavement winding must face upward')
        intended=Polygon(np.vstack((native_front[:,:2],native_rear[::-1,:2])))
        actual=union_all([Polygon(q[:,:2]) for q in xyz])
        self.assertLess(actual.symmetric_difference(intended).area,1e-8)
        self.assertAlmostEqual(float(cross.sum()/2),intended.area,places=8)
        # Each face stays in one adjacent station pair: no long triangle fan
        # can stretch one texture interval across many stations.
        local=faces-len(raw[0]);row=local//2
        self.assertTrue((row.max(axis=1)-row.min(axis=1)==1).all())
        self.assertEqual(len(faces),2*(len(pairs)-1))
        np.testing.assert_array_equal(metric[:,0,0],metric[:,1,0])
        midpoint=pairs[:,:,:2].mean(axis=1)
        distance=np.linalg.norm(np.diff(midpoint,axis=0),axis=1)
        np.testing.assert_allclose(np.diff(metric[:,0,0]),distance,atol=1e-10)
        self.assertEqual(metric[0,0,0],phase)
        np.testing.assert_array_equal(metric[:,0,1],np.full(len(pairs),sw.CURB_W))
        # At all original rear metadata stations, V measures actual distance
        # from that curb point, not a normalized0..1 strip coordinate.
        for index,point in enumerate(native_rear):
            hit=np.flatnonzero(np.all(rear==point,axis=1))
            self.assertEqual(len(hit),1)
            width=np.linalg.norm(point[:2]+np.asarray(origin)[:2]-arc[index,:2])
            self.assertAlmostEqual(metric[hit[0],1,1],width,places=8)
        return result

    def test_constant_variable_rotated_and_reflected_circle_full_and_lean(self):
        for widths in ((2.,2.),(1.1,3.4)):
            for angle,transpose in ((0.,False),(.61,False),(.23,True)):
                with self.subTest(widths=widths,angle=angle,transpose=transpose):
                    arc,n,outer,stations,meshes=corner(widths,angle,transpose)
                    for mesh in meshes:self.check_corner(mesh,arc,n,outer,stations,(0.,0.,0.))

    def test_ramp_refinement_and_lean_preserve_native_boundary_elevations(self):
        origin=(100.,-100.,3.)
        arc,n,outer,stations,meshes=corner((1.4,3.1),.37,True,True,origin)
        for mesh in meshes:self.check_corner(mesh,arc,n,outer,stations,origin)
        # Lean and visual fronts may have different samples; both must include
        # their own native ramp low points and complete piecewise 3D chains.
        front=native_chains(meshes[0],len(outer))[2]
        self.assertGreater(len(front),len(arc))

    def test_origins_do_not_change_metric_phase_or_world_boundary(self):
        outputs=[]
        for origin in ((0.,0.,0.),(100000.,-200000.,80.)):
            arc,n,outer,stations,meshes=corner((1.5,2.8),origin=origin)
            mesh=meshes[0];new=self.check_corner(mesh,arc,n,outer,stations,origin)
            outputs.append((new[0][len(mesh[0]):]+origin,new[2][len(mesh[0]):]))
        np.testing.assert_allclose(outputs[0][0],outputs[1][0],atol=2e-8)
        np.testing.assert_allclose(outputs[0][1],outputs[1][1],atol=2e-8)

    def test_native_exact_refine_dedup_may_leave_ulp_coincident_front_rows(self):
        arc,n,outer,stations,meshes=corner((2.5,2.5),ramps=[(1.1,2.8)],samples=7)
        front=native_chains(meshes[0],len(outer))[2]
        self.assertTrue(np.any(np.linalg.norm(np.diff(front,axis=0),axis=1)<=1e-9))
        for mesh in meshes:self.check_corner(mesh,arc,n,outer,stations,(0.,0.,0.))

    def test_partial_native_slab_triangles_do_not_drop_boundary_vertices(self):
        arc,n,outer,stations,meshes=corner()
        p,t,uv,m=meshes[0];rows=np.flatnonzero(m==1)
        keep=m!=1;keep[rows[0]]=True
        self.check_corner((p,t[keep],uv,m[keep]),arc,n,outer,stations,(0.,0.,0.))

    def test_bad_station_or_front_projection_is_rejected_and_merged_is_untouched(self):
        arc,n,outer,stations,meshes=corner()
        mesh=meshes[0]
        self.assertIs(curved_corner(mesh,(0,0,0),arc,n,outer,None,0.),mesh)
        bad=stations.copy();bad[2],bad[3]=bad[3],bad[2]
        with self.assertRaisesRegex(ValueError,'rear stations'):
            curved_corner(mesh,(0,0,0),arc,n,outer,bad,0.)
        start,end,front,_=native_chains(mesh,len(outer))
        p=mesh[0].copy();p[start+len(front)//2,:2]+=[20.,20.]
        with self.assertRaisesRegex(ValueError,'residual bound'):
            curved_corner((p,*mesh[1:]),(0,0,0),arc,n,outer,stations,0.)
        # A real backwards source-station step must not be mistaken for the
        # sub-nanometre duplicate case above.
        backwards=mesh[0].copy();i=start+len(front)//2
        backwards[[i,i+1]]=backwards[[i+1,i]]
        with self.assertRaisesRegex(ValueError,'stations fold or repeat'):
            curved_corner((backwards,*mesh[1:]),(0,0,0),arc,n,outer,stations,0.)
        folded=mesh[0].copy()
        # Force the rear to touch the middle of the front boundary, consuming
        # the slab width. The former large perturbation could remain a valid
        # widened strip and was not a valid negative-control fixture.
        folded[end-1-len(front)//2]=front[len(front)//2]
        supplied=outer.copy();supplied[:,:2]=folded[end-len(outer):end,:2]
        with self.assertRaises(ValueError):curved_corner((folded,*mesh[1:]),(0,0,0),arc,n,supplied,stations,0.)


class AccessMetricPavingTests(unittest.TestCase):
    def test_physical_across_and_along_scale_is_independent_of_width_and_rotation(self):
        for kind,repeat in (('path',1.2),('path_link',1.2),('driveway',2.4),('apron',2.4)):
            for width in (.8,1.4,2.5,3.,3.01,4.8,7.2):
                for angle in (0.,.63):
                    with self.subTest(kind=kind,width=width,angle=angle):
                        tangent=np.array([np.cos(angle),np.sin(angle)])
                        normal=np.array([-tangent[1],tangent[0]])
                        a=np.array([121.,-81.]);length=5.7
                        xy=np.array([a,a+tangent*length,a+tangent*length+normal*width,a+normal*width])
                        top=tuple(map(tuple,np.c_[xy,np.full(4,.2)]))
                        solid=access.Solid(kind,top,-.1)
                        spec=SimpleNamespace(seed='metric-width',inference=None,access=access.AccessPlan(.2,None,(solid,)))
                        visual=buildings.Mesh();collision=buildings.Mesh()
                        access.draw(visual,spec);access.draw(collision,spec,True)
                        p,uv,t,*_=visual.arrays();cp,_,ct,*_=collision.arrays()
                        np.testing.assert_array_equal(p[:4],top)
                        np.testing.assert_allclose(uv[:4],((0,0),(0,length/repeat),(width/repeat,length/repeat),(width/repeat,0)),atol=1e-12)
                        np.testing.assert_array_equal(p,cp);np.testing.assert_array_equal(t,ct)


if __name__=='__main__':unittest.main()
