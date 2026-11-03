"""Native rear replacement keeps approach profiles and continuous shared skins."""
from collections import Counter
from pathlib import Path
import sys
import unittest

import numpy as np
from shapely import union_all
from shapely.geometry import Polygon

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import sidewalks as sw
from walk_geometry import corner_rear
from walk_surfaces import curved_corner
from walk_back import (continuous_back,BackMergeIncompatible,BACK_RUN,SINK,
                       CROSS_SLOPE,CURB_REPEAT_M,V_LIGHT,V_DARK)


def fixture(radius=3.,widths=(1.2,1.2),slope=0.,origin=(0.,0.,0.),angle=0.,ramps=()):
    theta=np.linspace(-np.pi/2,-np.pi,37)
    inward=-np.c_[np.cos(theta),np.sin(theta)]
    arc=np.c_[-radius*inward,np.zeros(len(theta))]
    arc[:,2]=slope*arc[:,0]
    rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    arc[:,:2]=arc[:,:2]@rotation.T;inward=inward@rotation.T
    arc+=np.array([121.,-83.,7.])
    ends=arc[[0,-1]].copy();ends[:,:2]+=inward[[0,-1]]*np.asarray(widths)[:,None]
    rear=corner_rear(arc,inward,*widths,*ends)
    assert rear.stations is not None,'these tests require an ordinary slab boundary'
    outer=rear.outer.copy();outer[:,2]+=(rear.widths-2.5)*sw.CROSS_SLOPE
    piece=(1,arc,inward,outer,list(ramps),2.5,sw.CURB_H,(False,False),1)
    meshes=sw.native_mesh([piece],np.asarray(origin,float),True)
    return arc,inward,outer,rear.stations,meshes


def edge_counts(points,faces):
    # Exact geometric correspondence across separately indexed native/run parts.
    def key(i):return tuple(np.round(points[i],9))
    return Counter(tuple(sorted((key(int(a)),key(int(b)))))
                   for f in faces for a,b in zip(f,np.roll(f,-1)))


class ContinuousBackTests(unittest.TestCase):
    def repaired(self,raw,arc,n,outer,stations,origin,overlap_regions=None):
        saved=tuple(a.copy() for a in raw)
        mapped=curved_corner(raw,origin,arc,n,outer,stations,3.25)
        before=tuple(a.copy() for a in mapped)
        result=continuous_back(mapped,raw,origin,arc,n,outer,stations,sw.CURB_H,
                               overlap_regions=overlap_regions)
        for a,b in zip(raw,saved):np.testing.assert_array_equal(a,b)
        for a,b in zip(mapped,before):np.testing.assert_array_equal(a,b)
        p,t,uv,m=result
        np.testing.assert_array_equal(p[:len(mapped[0])],mapped[0])
        np.testing.assert_array_equal(uv[:len(mapped[2])],mapped[2])
        original_back_first=int(raw[1][np.flatnonzero(raw[3]==1)[-1]+1:].min())
        back=(mapped[3]==0)&np.all((mapped[1]>=original_back_first)&(mapped[1]<len(raw[0])),axis=1)
        old_count=int((~back).sum())
        np.testing.assert_array_equal(t[:old_count],mapped[1][~back])
        np.testing.assert_array_equal(m[:old_count],mapped[3][~back])
        faces=t[old_count:]
        self.assertTrue((m[old_count:]==0).all())
        self.assertTrue((faces>=len(mapped[0])).all())
        self.assertTrue(np.isfinite(p).all() and np.isfinite(uv).all())
        xyz=p[faces];cross=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0])[:,2]
        self.assertTrue((cross>0).all())
        polygons=[Polygon(q[:,:2]) for q in xyz]
        shape=union_all(polygons)
        top=outer[::-1].copy()-np.asarray(origin)
        top[:,2]+=sw.CURB_H+2.5*sw.CROSS_SLOPE
        for point in top:self.assertTrue(np.all(p[len(mapped[0]):]==point,axis=1).any())
        return result,faces,shape,float(cross.sum()/2),top,len(mapped[0])

    def assert_simple_shared(self,result,faces,shape,total_area):
        self.assertAlmostEqual(shape.area,total_area,places=8)
        counts=edge_counts(result[0],faces)
        self.assertTrue(all(count in (1,2) for count in counts.values()))
        self.assertGreater(sum(count==2 for count in counts.values()),0)
        boundary=sum(np.linalg.norm(np.asarray(a)[:2]-np.asarray(b)[:2])
                     for (a,b),count in counts.items() if count==1)
        self.assertAlmostEqual(boundary,shape.length,places=7)

    def assert_approach_weld(self,result,faces,shape,top,arc,n,origin):
        p,t,uv,m=result
        stations=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(arc[:,:2],axis=0),axis=1))]
        top_s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(top[:,:2],axis=0),axis=1))]
        width=np.linalg.norm(top[[0,-1],:2]-(arc[[0,-1],:2]-np.asarray(origin)[:2]),axis=1)
        descent=BACK_RUN*(sw.CURB_H+SINK+width*CROSS_SLOPE)
        bottoms=top[[0,-1]].copy();bottoms[:,:2]+=n[[0,-1]]*descent[:,None]
        bottoms[:,2]-=descent/BACK_RUN
        directions=np.array([arc[0,:2]-arc[1,:2],arc[-1,:2]-arc[-2,:2]])
        # Exact endpoint tangents, independent of sampled circular chords.
        tangents=np.c_[n[[0,-1],1],-n[[0,-1],0]]
        tangents*=np.sign(np.einsum('ij,ij->i',tangents,directions))[:,None]
        approach_polys=[];all_p=list(p);all_t=list(faces)
        for index,(a,b,d) in enumerate(zip(top[[0,-1]],bottoms,tangents)):
            self.assertTrue(np.all(p==b,axis=1).any(),'exact full run bottom endpoint must be retained')
            extension=np.r_[d*3.,0.]
            quad=np.array([a,b,b+extension,a+extension]);base=len(all_p)
            all_p.extend(quad);all_t.extend(np.array([[0,1,2],[0,2,3]])+base)
            approach_polys.append(Polygon(quad[:,:2]))
            cap=tuple(sorted((tuple(np.round(a,9)),tuple(np.round(b,9)))))
            self.assertEqual(edge_counts(np.asarray(all_p),np.asarray(all_t))[cap],2)
        self.assertAlmostEqual(shape.intersection(union_all(approach_polys)).area,0.,places=8)

    def test_ordinary_widths_both_native_streams_exact_weld_and_no_overlaps(self):
        for widths,radius,slope,angle in (((.6,.6),3.,0.,0.),((1.2,1.2),3.,0.,.43),
                                           ((.6,1.2),6.,.07,.24)):
            origin=(100.,-100.,3.)
            arc,n,outer,stations,meshes=fixture(radius,widths,slope,origin,angle,ramps=[(1.1,2.8)])
            for raw in meshes:
                with self.subTest(widths=widths,lean=len(raw[0])):
                    result,faces,shape,area,top,base=self.repaired(raw,arc,n,outer,stations,origin)
                    self.assert_simple_shared(result,faces,shape,area)
                    self.assert_approach_weld(result,faces,shape,top,arc,n,origin)
                    metric=result[2][base:]
                    top_s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(top[:,:2],axis=0),axis=1))]
                    np.testing.assert_allclose(metric[:len(top),0],top_s/CURB_REPEAT_M,atol=1e-12)
                    np.testing.assert_array_equal(metric[:len(top),1],np.full(len(top),V_LIGHT))
                    np.testing.assert_array_equal(metric[len(top):,1],np.full(len(metric)-len(top),V_DARK))
                    # Width changes along the source stations, not the rear's
                    # different arclength. Every buried datum must remain exact.
                    width=np.linalg.norm(top[:,:2]-(arc[:,:2]-np.asarray(origin)[:2]),axis=1)
                    expected=top[::-1,2]-(sw.CURB_H+SINK+width[::-1]*CROSS_SLOPE)
                    np.testing.assert_allclose(result[0][base+len(top):,2],expected,atol=1e-12)

    def test_consumed_flat_bottom_shared_cap_height_is_proved(self):
        arc,n,outer,stations,meshes=fixture(3.,(2.5,2.5))
        for raw in meshes:
            regions=[]
            result,faces,shape,area,top,base=self.repaired(raw,arc,n,outer,stations,(0,0,0),regions)
            self.assert_simple_shared(result,faces,shape,area)
            self.assertEqual(regions,[])
            bottom=result[0][base+len(top):]
            self.assertEqual(len(bottom),1)
            # The shared center meets both approach profiles before their
            # beyond-center endpoints; those endpoints belong to approach union.
            np.testing.assert_allclose(bottom[0,:2],[121.,-83.],atol=1e-8)
            self.assertAlmostEqual(bottom[0,2],7.+sw.CURB_H+2.5*CROSS_SLOPE-.25,places=8)
            self.assertAlmostEqual(result[2][-1,1],V_LIGHT+(V_DARK-V_LIGHT)*(.5/.575),places=8)

    def test_incompatible_consumed_profiles_require_explicit_envelope_contract(self):
        arc,n,outer,stations,meshes=fixture(3.,(2.5,2.5),slope=.05)
        for raw in meshes:
            mapped=curved_corner(raw,(0,0,0),arc,n,outer,stations,0.)
            with self.assertRaises(BackMergeIncompatible) as caught:
                continuous_back(mapped,raw,(0,0,0),arc,n,outer,stations,sw.CURB_H)
            diagnostic=caught.exception.diagnostic
            self.assertAlmostEqual(diagnostic['height_difference_m'],.15,places=8)
            self.assertEqual(diagnostic['source']['arc'],arc.tolist())
            regions=[]
            result,faces,shape,area,top,base=self.repaired(raw,arc,n,outer,stations,(0,0,0),regions)
            self.assertEqual(len(regions),1)
            self.assertLess(regions[0].symmetric_difference(shape).area,1e-9)
            self.assertGreater(area-shape.area,1e-8,'candidate overlap must be resolved by the caller')
            appended=result[0][base:];count=len(top)
            self.assertEqual(len(appended),2*count)
            widths=np.linalg.norm(top[:,:2]-arc[:,:2],axis=1)
            descent=BACK_RUN*(sw.CURB_H+SINK+widths*CROSS_SLOPE)
            expected=top.copy();expected[:,:2]+=n*descent[:,None];expected[:,2]-=descent/BACK_RUN
            np.testing.assert_array_equal(appended[:count],top)
            np.testing.assert_allclose(appended[count:],expected,atol=1e-12)
            # Consecutive cells share one actual indexed bottom edge, rather
            # than independently extruding chord normals into wedge gaps.
            counts=Counter(tuple(sorted((int(a),int(b)))) for face in faces
                           for a,b in zip(face,np.roll(face,-1)))
            for i in range(1,count-1):self.assertEqual(counts[(base+i,base+count+i)],2)

    def test_unpaired_merged_slab_is_unchanged(self):
        mesh=tuple(np.array([]) for _ in range(4))
        self.assertIs(continuous_back(mesh,mesh,None,None,None,None,None,.15),mesh)


if __name__=='__main__':unittest.main()
