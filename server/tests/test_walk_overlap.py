"""Bounded upper envelopes retain exact back planes and compatible edge coverage."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
from shapely import STRtree,union_all
from shapely.geometry import Polygon,box

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from walk_overlap import upper_back_envelope
import walk_overlap


def make_mesh(specs):
    """(triangle XY, height callable, texture callable, material) per source face."""
    points,triangles,textures,materials=[],[],[],[]
    for xy,height,texture,material in specs:
        xy=np.asarray(xy,np.float64)
        base=len(points)
        points.extend(np.c_[xy,height(xy[:,0],xy[:,1])])
        textures.extend(texture(xy[:,0],xy[:,1]))
        triangles.append((base,base+1,base+2));materials.append(material)
    return tuple(np.asarray(a,dtype=d) for a,d in ((points,np.float64),(triangles,np.int64),
                                               (textures,np.float64),(materials,np.int64)))


def quad(x0,y0,x1,y1,height,texture,material=0):
    a,b,c,d=(x0,y0),(x1,y0),(x1,y1),(x0,y1)
    return [([a,b,c],height,texture,material),([a,c,d],height,texture,material)]


ZA=lambda x,y:.25*x+.5
ZB=lambda x,y:-.25*x+.25*y+.5
UA=lambda x,y:np.c_[.5*x+2.,.25*y+3.]
UB=lambda x,y:np.c_[2.*x-1.,3.*y+4.]


def crossing():
    return make_mesh(quad(-3.,-1.,3.,1.,ZA,UA)+quad(-1.,-3.,1.,3.,ZB,UB))


def height_at(mesh,point):
    p,t,uv,m=mesh
    heights=[]
    for tri in p[t]:
        a,b,c=tri
        matrix=np.column_stack((b[:2]-a[:2],c[:2]-a[:2]))
        if abs(np.linalg.det(matrix))<1e-14:continue
        s,v=np.linalg.solve(matrix,np.asarray(point)-a[:2])
        if min(s,v,1.-s-v)>=-1e-8:
            heights.append(float(a[2]+s*(b[2]-a[2])+v*(c[2]-a[2])))
    return heights


def projected_faces(mesh,region=None):
    p,t,uv,m=mesh
    shapes=[Polygon(q[:,:2]) for q in p[t[m==0]]]
    return shapes if region is None else [q.intersection(region) for q in shapes]


class UpperBackEnvelopeTests(unittest.TestCase):
    def test_vector_half_planes_match_scalar_vertices_and_zero_ties_exactly(self):
        square=box(0.,0.,2.,2.)
        hole=Polygon([(0.,0.),(2.,0.),(2.,2.),(0.,2.)],
                     holes=[[(.75,.75),(1.25,.75),(1.25,1.25),(.75,1.25)]])
        cases=[(square,(1.,1.),-1.,(0.,0.)),  # five vertices
               (square,(1.,1.),-3.,(0.,0.)),  # three vertices
               (square,(1.,0.),-1.,(0.,0.)),  # four vertices
               (square,(1.,1.),-2.,(0.,0.)),  # exact zero corner ties
               (square,(1.,-1.),0.,(0.,0.)),
               (square,(0.,0.),0.,(0.,0.)),   # all-zero must be None
               (square,(0.,0.),1.,(0.,0.)),
               (square,(0.,0.),-1.,(0.,0.)),
               (hole,(1.,0.),-1.,(0.,0.)),
               (box(111.,222.,113.,224.),(.5,-.25),.125,(111.,222.))]
        overlaps=np.asarray([c[0] for c in cases],object)
        gradients=np.asarray([c[1] for c in cases],float)
        constants=np.asarray([c[2] for c in cases],float)
        origins=np.asarray([c[3] for c in cases],float)
        for sign in (1.,-1.):
            expected=[walk_overlap._positive_domain(p,np.asarray(g)*sign,c*sign,np.asarray(o)) for p,g,c,o in cases]
            actual=walk_overlap._positive_domains(overlaps,gradients*sign,constants*sign,origins)
            for i,(a,b) in enumerate(zip(actual,expected)):
                with self.subTest(sign=sign,index=i):
                    if b is None:self.assertIsNone(a)
                    else:self.assertEqual(a.wkb,b.wkb)

    def test_bounded_vector_pairs_keep_scalar_order_clipping_and_coverage(self):
        polygons=np.asarray([Polygon([(x,0.),(x+2.,0.),(x,2.)])
                             for x in (0.,.125,.25,.5,.75,1.,3.)],dtype=object)
        region=box(-.25,-.25,2.25,2.25)
        tree=STRtree(polygons)
        relevant=sorted(int(i) for i in tree.query(region,predicate='intersects'))
        expected=[]
        for i in relevant:
            for j in sorted(int(k) for k in tree.query(polygons[i],predicate='intersects')):
                if j<=i or j not in relevant:continue
                overlap=polygons[i].intersection(polygons[j]).intersection(region)
                if overlap.area>1e-12:expected.append((i,j,overlap))
        original_intersection=walk_overlap.intersection
        batches=[]
        def bounded(a,b):
            batches.append(len(a))
            return original_intersection(a,b)
        with patch.object(walk_overlap,'SOURCE_QUERY_BATCH',2),patch.object(walk_overlap,'PAIR_BATCH',3), \
             patch.object(walk_overlap,'intersection',side_effect=bounded), \
             patch.object(walk_overlap,'covers',wraps=walk_overlap.covers) as covered:
            actual=list(walk_overlap._overlapping_pairs(polygons,tree,relevant,region))
        self.assertEqual(covered.call_count,1)
        self.assertTrue(batches)
        self.assertLessEqual(max(batches),3)
        self.assertEqual([(i,j) for i,j,_ in actual],[(i,j) for i,j,_ in expected])
        for (_,_,a),(_,_,b) in zip(actual,expected):
            self.assertLess(a.symmetric_difference(b).area,1e-12)

    def test_crossing_sloped_strips_equal_analytic_max_without_duplicate_xy(self):
        source=crossing();original=tuple(a.copy() for a in source)
        region=box(-1.5,-1.5,1.5,1.5)
        result=upper_back_envelope(source,[region])
        for a,b in zip(source,original):np.testing.assert_array_equal(a,b)
        for x,y in ((0.,0.),(.2,.4),(.2,.39999),(.2,.40001),(-.2,-.40001),
                    (-.2,-.39999),(.8,.8),(-.8,.8),(2.,0.),(0.,-2.)):
            values=height_at(result,(x,y))
            expected=[]
            if -3.<=x<=3. and -1.<=y<=1.:expected.append(ZA(x,y))
            if -1.<=x<=1. and -3.<=y<=3.:expected.append(ZB(x,y))
            self.assertTrue(values,(x,y))
            np.testing.assert_allclose(values,max(expected),atol=1e-10)
        polygons=projected_faces(result)
        desired=union_all([box(-3,-1,3,1),box(-1,-3,1,3)])
        actual=union_all(polygons)
        self.assertLess(actual.symmetric_difference(desired).area,1e-10)
        self.assertAlmostEqual(sum(p.area for p in polygons),actual.area,places=10)
        # Every generated face follows one original Z and UV plane exactly.
        p,t,uv,m=result
        for face in t:
            xyz=p[face];texture=uv[face]
            a=np.allclose(xyz[:,2],ZA(xyz[:,0],xyz[:,1]),atol=1e-10)
            b=np.allclose(xyz[:,2],ZB(xyz[:,0],xyz[:,1]),atol=1e-10)
            self.assertTrue(a or b)
            self.assertTrue(a and np.allclose(texture,UA(xyz[:,0],xyz[:,1]),atol=1e-10)
                            or b and np.allclose(texture,UB(xyz[:,0],xyz[:,1]),atol=1e-10))
            q=xyz[1:,:2]-xyz[0,:2]
            self.assertGreater(np.linalg.det(q),0.)

    def assert_intersection_weld(self,result):
        p,t,uv,m=result
        a=np.array([-.5,-1.]);b=np.array([.5,1.]);direction=b-a
        intervals=[]
        for tri in p[t]:
            for u,v in zip(tri,np.roll(tri,-1,axis=0)):
                if abs(u[1]-2*u[0])<1e-8 and abs(v[1]-2*v[0])<1e-8:
                    lo,hi=sorted(((u[:2]-a)@direction/(direction@direction),
                                  (v[:2]-a)@direction/(direction@direction)))
                    lo,hi=max(0.,lo),min(1.,hi)
                    if hi-lo>1e-10:intervals.append((lo,hi))
        stops=sorted(set([0.,1.]+[float(v) for edge in intervals for v in edge]))
        self.assertTrue(intervals)
        for lo,hi in zip(stops,stops[1:]):
            if hi-lo<=1e-9:continue
            mid=(lo+hi)/2
            self.assertEqual(sum(a-1e-9<=mid<=b+1e-9 for a,b in intervals),2,(lo,hi,intervals))
            values=height_at(result,a+mid*direction)
            np.testing.assert_allclose(values,ZA(*(a+mid*direction)),atol=1e-10)

    def test_plane_intersection_has_two_mates_on_every_atomic_edge_interval(self):
        result=upper_back_envelope(crossing(),[box(-1.5,-1.5,1.5,1.5)])
        self.assert_intersection_weld(result)

    def test_intersection_checker_rejects_one_millimeter_opening(self):
        result=upper_back_envelope(crossing(),[box(-1.5,-1.5,1.5,1.5)])
        p,t,uv,m=result
        moved=p.copy();texture=uv.copy();ids=set()
        for face in t:
            tri=p[face]
            if (np.allclose(tri[:,2],ZA(tri[:,0],tri[:,1]),atol=1e-10)
                    and np.mean(tri[:,1]-2*tri[:,0]) < -1e-7):
                ids.update(int(i) for i in face if abs(p[i,1]-2*p[i,0])<1e-8)
        self.assertTrue(ids)
        ids=np.asarray(sorted(ids),np.int64)
        moved[ids,:2]+=np.array([2.,-1.])*.001/np.sqrt(5.)
        moved[ids,2]=ZA(moved[ids,0],moved[ids,1])
        texture[ids]=UA(moved[ids,0],moved[ids,1])
        np.testing.assert_allclose(np.linalg.norm(moved[ids,:2]-p[ids,:2],axis=1),.001,atol=1e-12)
        with self.assertRaises(AssertionError):self.assert_intersection_weld((moved,t,texture,m))

    def test_region_only_occlusion_supports_holes_and_preserves_outside_planes(self):
        triangle=[(-5.,-5.),(5.,-5.),(0.,5.)]
        zero=lambda x,y:np.zeros_like(x)
        one=lambda x,y:np.ones_like(x)
        mesh=make_mesh([(triangle,zero,UA,0),(triangle,one,UB,0),
                        ([(20.,0.),(21.,0.),(20.,1.)],one,UA,6)])
        originals=tuple(a.copy() for a in mesh)
        region=box(-.5,-.5,.5,.5)
        result=upper_back_envelope(mesh,[region])
        p,t,uv,m=result
        np.testing.assert_array_equal(p[:len(mesh[0])],mesh[0])
        np.testing.assert_array_equal(uv[:len(mesh[2])],mesh[2])
        self.assertTrue(np.any(np.all(t==mesh[1][2],axis=1)))
        self.assertEqual(np.count_nonzero(m==6),1)
        for a,b in zip(mesh,originals):np.testing.assert_array_equal(a,b)
        np.testing.assert_allclose(height_at(result,(0.,0.)),1.,atol=1e-12)
        self.assertEqual(set(round(z,10) for z in height_at(result,(0.,-3.))),{0.,1.})
        lower=[Polygon(q[:,:2]) for q in p[t[m==0]] if np.all(q[:,2]==0.)]
        self.assertAlmostEqual(sum(s.area for s in lower),49.,places=10)
        self.assertLess(union_all(lower).intersection(region).area,1e-10)
        # Positive-area duplicates may remain outside the explicitly flagged patch.
        inside=projected_faces((p,t[m==0],uv,m[m==0]),region)
        self.assertAlmostEqual(sum(q.area for q in inside),union_all(inside).area,places=10)

    def test_coplanar_equal_faces_deduplicate_by_original_index_and_keep_owner_uv(self):
        tri=[(0.,0.),(2.,0.),(0.,2.)]
        plane=lambda x,y:.25*x+.5*y+.125
        mesh=make_mesh([(tri,plane,UA,0),(tri,plane,UB,0)])
        result=upper_back_envelope(mesh,[box(-1,-1,3,3)])
        np.testing.assert_array_equal(result[1],mesh[1][:1])
        np.testing.assert_array_equal(result[0],mesh[0])
        np.testing.assert_array_equal(result[2],mesh[2])
        repeat=upper_back_envelope(mesh,[box(-1,-1,3,3)])
        for a,b in zip(result,repeat):self.assertEqual(a.tobytes(),b.tobytes())

    def test_disjoint_edge_contacts_empty_regions_and_unselected_material_are_identity(self):
        zero=lambda x,y:np.zeros_like(x)
        mesh=make_mesh([([(0.,0.),(1.,0.),(0.,1.)],zero,UA,0),
                        ([(1.,0.),(1.,1.),(0.,1.)],zero,UB,0)])
        self.assertIs(upper_back_envelope(mesh,[box(-1,-1,2,2)]),mesh)
        cross=crossing()
        self.assertIs(upper_back_envelope(cross,[]),cross)
        self.assertIs(upper_back_envelope(cross,[box(20,20,21,21)]),cross)
        p,t,uv,m=cross
        other=(p,t,uv,np.full_like(m,6))
        self.assertIs(upper_back_envelope(other,[box(-4,-4,4,4)]),other)

    def test_translation_and_input_reversal_preserve_analytic_heights(self):
        for reverse in (False,True):
            source=crossing();p,t,uv,m=source
            if reverse:t=t[:,::-1].copy()
            delta=np.array([123456.,-234567.,81.])
            mesh=(p+delta,t,uv,m)
            region=box(delta[0]-1.5,delta[1]-1.5,delta[0]+1.5,delta[1]+1.5)
            result=upper_back_envelope(mesh,[region])
            for x,y in ((.2,.3),(.2,.5),(-.2,-.4)):
                values=height_at(result,np.array([x,y])+delta[:2])
                np.testing.assert_allclose(values,max(ZA(x,y),ZB(x,y))+delta[2],atol=1e-8)
            np.testing.assert_array_equal(result[0][:len(p)],p+delta)

    def test_nonfinite_source_is_rejected_even_when_regions_are_empty(self):
        source=crossing()
        for stream,column in ((0,2),(2,1)):
            arrays=[a.copy() for a in source];arrays[stream][0,column]=np.nan
            with self.assertRaises(ValueError):upper_back_envelope(tuple(arrays),[])

    def test_only_subthreshold_occlusion_or_source_degeneracy_preserves_identity(self):
        tri=[(0.,0.),(2.,0.),(0.,2.)]
        zero=lambda x,y:np.zeros_like(x)
        one=lambda x,y:np.ones_like(x)
        source=make_mesh([(tri,zero,UA,0),(tri,one,UB,0)])
        self.assertIs(upper_back_envelope(source,[box(0.,0.,1e-7,1e-7)]),source)
        tiny=[(0.,0.),(1e-7,0.),(0.,1e-7)]
        source=make_mesh([(tiny,zero,UA,0),(tiny,one,UB,0)])
        self.assertIs(upper_back_envelope(source,[box(-1.,-1.,1.,1.)]),source)

    def test_original_stream_dtypes_and_unused_prefix_bytes_are_preserved(self):
        p,t,uv,m=crossing()
        source=(p.astype(np.float32),t.astype(np.uint32),uv.astype(np.float32),m.astype(np.uint8))
        result=upper_back_envelope(source,[box(-1.5,-1.5,1.5,1.5)])
        for old,new in zip(source,result):self.assertEqual(old.dtype,new.dtype)
        self.assertEqual(result[0][:len(p)].tobytes(),source[0].tobytes())
        self.assertEqual(result[2][:len(uv)].tobytes(),source[2].tobytes())


if __name__=='__main__':unittest.main()
