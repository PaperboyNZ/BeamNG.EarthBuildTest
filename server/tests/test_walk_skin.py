"""Corrected pavement welds to its existing sloped rear and vertical cap skins."""
from collections import Counter
from pathlib import Path
import sys
import unittest

import numpy as np
from shapely.geometry import LineString, Point

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sidewalks
from walk_skin import BoundarySkin


def closed_walk(material=1):
    """A 4x2m slab with a sloped rear, vertical caps and fixed buried bottom."""
    a,b,c,d=np.array([[0.,0.,.2],[4.,0.,.2],[4.,2.,.2],[0.,2.,.2]])
    e,f,g,h=np.array([[0.,0.,-.3],[4.,0.,-.3],[4.,2.5,-.3],[0.,2.5,-.3]])
    points,faces,uvs,mats=[],[],[],[]
    for i,quad in enumerate(((a,b,c,d),(d,c,g,h),(b,a,e,f),(a,d,h,e),(c,b,f,g),(h,g,f,e))):
        base=len(points);points.extend(quad)
        faces.extend(((base,base+1,base+2),(base,base+2,base+3)))
        uvs.extend([(p[0]/2.,p[1]/4.+p[2]/7.) for p in quad])
        mats.extend((material,material) if i==0 else (0,0))
    return tuple(np.asarray(a,dtype=dtype) for a,dtype in
                 ((points,np.float64),(faces,np.int64),(uvs,np.float64),(mats,np.int64)))


def edge_counts(mesh, material=None):
    p,t,uv,m=mesh
    counter=Counter()
    for face in t if material is None else t[m==material]:
        q=[tuple(np.round(v,7)) for v in p[face]]
        for a,b in zip(q,q[1:]+q[:1]):
            counter[tuple(sorted((a,b)))]+=1
    return counter


def geometric_edge_counts(mesh,tolerance=1e-8):
    """Atomize 3D collinear edges at every existing mesh endpoint.

Unchanged native faces can retain one straight edge while the adjacent terrain
grid splits its mate. Check exact geometric coverage of those intervals, rather
than requiring unchanged faces to be retessellated. Millimeter gaps and duplicate
overlaps remain visible; tolerance is at most 1e-8m (rounding below 1e-9m).
    """
    p,t,uv,m=mesh
    points=np.unique(np.round(p[np.unique(t)],9),axis=0)
    counts=Counter()
    for triangle in t:
        for i in range(3):
            a,b=p[triangle[i]],p[triangle[(i+1)%3]]
            ab=b-a;length2=float(ab@ab);length=np.sqrt(length2)
            if length<=tolerance:continue
            parameters=(points-a)@ab/length2
            error=np.linalg.norm(a+parameters[:,None]*ab-points,axis=1)
            on=(parameters>=0.)&(parameters<=1.)&(error<=tolerance)
            stops=sorted(np.r_[0.,parameters[on],1.])
            unique=[]
            for value in stops:
                if not unique or (value-unique[-1])*length>tolerance:unique.append(value)
            for lo,hi in zip(unique,unique[1:]):
                q=[tuple(np.round(a+value*ab,9)) for value in (lo,hi)]
                counts[tuple(sorted(q))]+=1
    return counts


class BoundarySkinTests(unittest.TestCase):
    def test_vertical_caps_use_3d_edge_parameters_and_preserve_uvs(self):
        mesh=closed_walk();p,t,uv,m=mesh
        skin=BoundarySkin(p,t,uv,m,np.flatnonzero(m==1))
        original=np.array([[4.,1.,.2],[0.,1.,.2],[4.,0.,.2],[4.,2.,.2]])
        corrected=original.copy();corrected[:,2]+=[.4,.4,.1,.2]
        # The two original top faces have different cap edges.
        for source in np.flatnonzero(m==1):skin.collect(source,original,corrected)
        removed,patch=skin.rebuild()
        self.assertTrue(len(removed))
        sp,st,su,sm=patch
        self.assertTrue(np.isfinite(sp).all())
        self.assertTrue(np.isfinite(su).all())
        self.assertTrue((sm==0).all())
        for xy in ((4.,1.),(0.,1.)):
            ids=np.flatnonzero(np.linalg.norm(sp[:,:2]-xy,axis=1)<1e-9)
            ids=ids[np.abs(sp[ids,2]-.6)<1e-9]
            self.assertGreater(len(ids),0)
            np.testing.assert_allclose(su[ids],np.tile([xy[0]/2.,xy[1]/4.+.2/7.],(len(ids),1)))
        # Bottom endpoints do not move; vertical-cap winding remains outward.
        for face in st:
            tri=sp[face]
            if np.max(np.abs(tri[:,0]-4.))<1e-9:
                self.assertGreater(np.cross(tri[1]-tri[0],tri[2]-tri[0])[0],0.)
        self.assertTrue(np.any(np.all(np.isclose(sp,[4.,2.5,-.3]),axis=1)))

    def test_changed_endpoint_reaches_every_duplicate_incident_skin_face(self):
        p,t,uv,m=closed_walk()
        skin=BoundarySkin(p,t,uv,m,np.flatnonzero(m==1))
        old=np.array([[0.,2.,.2]])
        skin.collect(1,old,np.array([[0.,2.,.8]]))
        changed,patch=skin.rebuild()
        expected={int(i) for i in np.flatnonzero(m==0)
                  if np.any(np.all(p[t[i]]==old[0],axis=1))}
        self.assertTrue(expected.issubset(set(changed)))
        for point in patch[0]:
            if np.linalg.norm(point[:2]-old[0,:2])<1e-9:
                self.assertNotAlmostEqual(point[2],.2)


class TerrainSkinTests(unittest.TestCase):
    def assert_closed(self,mesh):
        counts=geometric_edge_counts(mesh)
        bad=[(edge,count) for edge,count in counts.items() if count!=2]
        self.assertFalse(bad,bad[:6])

    def assert_raised_back_segments(self,mesh):
        top=edge_counts(mesh,material=1);skin=edge_counts(mesh,material=0)
        raised=0
        for edge,count in top.items():
            if count==1 and all(abs(p[1]-2.)<1e-8 for p in edge) and max(p[2] for p in edge)>.2+1e-8:
                self.assertEqual(skin[edge],1,edge)  # strict segment correspondence on actual raised seam
                raised+=1
        self.assertGreater(raised,0)

    def assert_immutable(self,before,mesh):
        for a,b in zip(before,mesh):np.testing.assert_array_equal(a,b)

    def assert_back_is_slope(self,mesh):
        p,t,uv,m=mesh
        back=t[(m==0)&np.all(p[t,1]>=2.-1e-8,axis=1)]
        self.assertGreater(len(back),0)
        # A continuous deformed existing slope replaces the old one. No new
        # vertical band is stacked along the top boundary at y=2.
        self.assertFalse(np.any(np.all(np.abs(p[back,1]-2.)<1e-8,axis=1)))
        ids=np.unique(back)
        expected_uv=np.c_[p[ids,0]/2.,p[ids,1]/4.+(.2-(p[ids,1]-2.))/7.]
        np.testing.assert_allclose(uv[ids],expected_uv,atol=1e-8)

    def test_linear_rise_welds_rear_and_caps_without_moving_bottom(self):
        mesh=closed_walk();before=tuple(a.copy() for a in mesh)
        calls=[]
        def ground(x,y):calls.append((x.copy(),y.copy()));return .1+.3*y
        fixed=sidewalks.clear_terrain(mesh,(0.,0.,0.),ground)
        self.assertEqual(len(calls),1,'skin repair must reuse the existing terrain grid')
        self.assert_immutable(before,mesh)
        self.assert_closed(fixed)
        self.assert_raised_back_segments(fixed)
        self.assert_back_is_slope(fixed)
        p,t,uv,m=fixed
        top=np.unique(t[m==1]);self.assertTrue((p[top,2]>=.1+.3*p[top,1]+.01-1e-8).all())
        rear=top[np.abs(p[top,1]-2.)<1e-8]
        np.testing.assert_allclose(p[rear,2],.71,atol=1e-8)
        # Original buried-bottom triangles remain byte-identical, including UVs.
        for face in mesh[1][10:]:
            self.assertTrue(np.any(np.all(t==face,axis=1)))
        np.testing.assert_array_equal(p[:len(mesh[0])],mesh[0])
        np.testing.assert_array_equal(uv[:len(mesh[2])],mesh[2])

    def test_grid_ridge_midsegment_closes_when_original_endpoints_do_not_move(self):
        mesh=closed_walk()
        ground=lambda x,y:np.maximum(0.,.6-.6*np.abs(x-2.))
        fixed=sidewalks.clear_terrain(mesh,(0.,0.,0.),ground)
        self.assert_closed(fixed);self.assert_back_is_slope(fixed)
        self.assert_raised_back_segments(fixed)
        p,t,uv,m=fixed
        top=np.unique(t[m==1]);skin=np.unique(t[m==0])
        for x,z in ((0.,.2),(2.,.61),(4.,.2)):
            wanted=np.array([x,2.,z])
            self.assertTrue(np.any(np.linalg.norm(p[top]-wanted,axis=1)<1e-8))
            self.assertTrue(np.any(np.linalg.norm(p[skin]-wanted,axis=1)<1e-8))
        crossings=p[skin][(np.abs(p[skin,1]-2.)<1e-8)&(np.abs(p[skin,2]-.2)<1e-8)]
        for x in (1.+.19/.6,3.-.19/.6):
            self.assertTrue(np.any(np.abs(crossings[:,0]-x)<1e-8),'delta=0 edge crossing omitted')

    def test_flat_control_keeps_every_array_byte_and_identity(self):
        mesh=closed_walk();before=tuple(a.tobytes() for a in mesh)
        result=sidewalks.clear_terrain(mesh,(0.,0.,0.),lambda x,y:np.zeros_like(x))
        self.assertIs(result,mesh)
        self.assertEqual(tuple(a.tobytes() for a in result),before)

    def test_geometric_checker_rejects_millimeter_raised_gap_and_fourfold_overlap(self):
        fixed=sidewalks.clear_terrain(closed_walk(),(0.,0.,0.),
            lambda x,y:np.maximum(0.,.6-.6*np.abs(x-2.)))
        p,t,uv,m=fixed
        opened=p.copy()
        skin=np.unique(t[m==0])
        raised=skin[(np.abs(p[skin,1]-2.)<1e-8)&(p[skin,2]>.3)]
        self.assertGreater(len(raised),0)
        opened[raised,1]+=.001
        with self.assertRaises(AssertionError):self.assert_closed((opened,t,uv,m))
        doubled=(p,np.vstack((t,t)),uv,np.r_[m,m])
        self.assertTrue(any(v==4 for v in geometric_edge_counts(doubled).values()))
        with self.assertRaises(AssertionError):self.assert_closed(doubled)

    def test_refined_top_subedges_weld_to_original_long_skin_edge(self):
        p,t,uv,m=closed_walk()
        top=[];faces=[]
        stations=(0.,1.25,2.75,4.)
        for x in stations:top.extend(((x,0.,.2),(x,2.,.2)))
        for j in range(len(stations)-1):
            a=len(p)+2*j
            faces.extend(((a,a+2,a+3),(a,a+3,a+1)))
        top=np.asarray(top)
        mesh=(np.vstack((p,top)),np.vstack((t[m==0],faces)),
              np.vstack((uv,np.c_[top[:,0]/2.,top[:,1]/4.+top[:,2]/7.])),
              np.r_[m[m==0],np.ones(len(faces),np.int64)])
        ground=lambda x,y:np.maximum(0.,.6-.6*np.abs(x-2.))
        fixed=sidewalks.clear_terrain(mesh,(0.,0.,0.),ground)
        self.assert_closed(fixed);self.assert_back_is_slope(fixed)
        sp,st,su,sm=fixed
        ids=np.unique(st[sm==0])
        # Original long-edge endpoints lie outside the raised subedge range.
        for x in (0.,4.):
            self.assertTrue(np.any(np.linalg.norm(sp[ids]-[x,2.,.2],axis=1)<1e-8))
            self.assertFalse(np.any((np.linalg.norm(sp[ids,:2]-[x,2.],axis=1)<1e-8)&(sp[ids,2]>.2+1e-8)))

    def test_ramp_refined_walk_surface_rear_welds_to_native_skin(self):
        # curved_corner inserts union stations for the ramp front while the
        # original native back still spans the coarser supplied rear stations.
        theta=np.linspace(-np.pi/2,-np.pi,7)
        arc=np.c_[8.+6.*np.cos(theta),8.+6.*np.sin(theta),np.zeros(len(theta))]
        inward=-np.c_[np.cos(theta),np.sin(theta)]
        rear=arc.copy();rear[:,:2]+=inward*2.5
        stations=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(arc[:,:2],axis=0),axis=1))]
        builder=sidewalks.Builder((0.,0.,0.),collision=True,ground=lambda x,y:np.full(x.shape,.35,dtype=float))
        builder.add_corner(arc,inward,rear[::-1],ramps=[(1.1,2.8)],outer_stations=stations[::-1])
        mesh=builder.arrays();p,t,uv,m=mesh
        boundary=edge_counts(mesh,material=1);skin=edge_counts(mesh,material=0)
        line=LineString(rear[:,:2]);checked=0
        rear_ids=[i for i in np.unique(t[m==1]) if line.distance(Point(p[i,:2]))<2e-7]
        self.assertTrue(rear_ids)
        self.assertTrue(np.any(np.isclose(p[rear_ids,2],.36,atol=1e-8)),
                        'fixture must actually raise the rear to terrain plus 1cm')
        for edge,count in boundary.items():
            if count==1 and all(line.distance(Point(v[:2]))<2e-7 for v in edge):
                self.assertGreaterEqual(skin[edge],1,edge)
                checked+=1
        self.assertGreater(checked,len(rear)-1,'ramp union stations did not refine the rear fixture')
        collision=builder.col.arrays()
        np.testing.assert_array_equal(collision[0],p)
        np.testing.assert_array_equal(collision[1],t[m!=5])

    def test_translated_and_reversed_faces_keep_welds_and_materials(self):
        for reverse in (False,True):
            for origin in ((0.,0.,0.),(678123.,-251772.,82.)):
                with self.subTest(reverse=reverse,origin=origin):
                    p,t,uv,m=closed_walk(material=sidewalks.STONE)
                    if reverse:t=t[:,::-1].copy()
                    mesh=(p,t,uv,m)
                    ground=lambda x,y:.1+.3*(y-origin[1])+origin[2]
                    fixed=sidewalks.clear_terrain(mesh,origin,ground)
                    self.assert_closed(fixed)
                    self.assertEqual(set(fixed[3]),{0,sidewalks.STONE})
                    self.assertTrue(np.isfinite(fixed[2]).all())
                    self.assert_immutable((p.copy(),t.copy(),uv.copy(),m.copy()),mesh)

    def test_builder_corner_and_run_share_exact_corrected_visual_collision(self):
        builder=sidewalks.Builder((0.,0.,0.),collision=True,
            ground=lambda x,y:np.maximum(0.,.6-.6*np.abs(x-2.)))
        curb=np.array([[0.,0.,0.],[4.,0.,0.]])
        builder.add_run(curb,np.tile([0.,1.],(2,1)),2.5)
        # A separate small corner exercises the same repair with native rear
        # faces and joins/caps present elsewhere in this combined product.
        theta=np.linspace(-np.pi/2,-np.pi,17)
        arc=np.c_[8.+3.*np.cos(theta),8.+3.*np.sin(theta),np.zeros(len(theta))]
        inward=-np.c_[np.cos(theta),np.sin(theta)]
        rear=arc.copy();rear[:,:2]+=inward
        builder.add_corner(arc,inward,rear[::-1])
        visual=builder.arrays();collision=builder.col.arrays()
        np.testing.assert_array_equal(collision[0],visual[0])
        np.testing.assert_array_equal(collision[1],visual[1][visual[3]!=5])
        self.assertTrue((collision[3]==0).all())


if __name__=='__main__':unittest.main()
