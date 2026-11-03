"""Batched matching retains the original scalar predicate and match order."""
from collections import defaultdict
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
from shapely import STRtree,linestrings
from shapely.geometry import box

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import walk_skin
from walk_skin import BoundarySkin,_edge


def scalar_shared(points,triangles,materials,selected,tolerance=1e-7):
    """Frozen pre-batching match loop, including scalar STRtree traversal."""
    edges=defaultdict(list)
    for face in np.flatnonzero(materials==0):
        xyz=points[triangles[face]]
        for j in range(3):edges[_edge(xyz[j],xyz[(j+1)%3])].append(int(face))
    keys=tuple(edges);tree=STRtree(linestrings(np.asarray(keys)[:,:,:2])) if keys else None
    shared=defaultdict(list)
    for face in selected:
        xyz=points[triangles[face]]
        for j in range(3):
            key=_edge(xyz[j],xyz[(j+1)%3]);matches=[key] if key in edges else []
            if tree is not None:
                a,b=np.asarray(key);lo,hi=np.minimum(a,b),np.maximum(a,b)
                for index in tree.query(box(lo[0]-tolerance,lo[1]-tolerance,hi[0]+tolerance,hi[1]+tolerance)):
                    candidate=keys[int(index)];c,d=np.asarray(candidate);cd=d-c;length2=float(cd@cd)
                    if length2<=1e-24:continue
                    params=(np.asarray((a,b))-c)@cd/length2
                    error=np.linalg.norm(np.asarray((a,b))-(c+params[:,None]*cd),axis=1)
                    overlap=min(1.,params.max())-max(0.,params.min())
                    if error.max()<=tolerance and overlap*np.sqrt(length2)>tolerance:matches.append(candidate)
            for match in matches:
                if match not in shared[int(face)]:shared[int(face)].append(match)
    return dict(shared)


def fixture(top_count=1,extra_edges=0):
    points=[];triangles=[];materials=[]
    def face(a,b,c,material):
        base=len(points);points.extend((a,b,c));triangles.append((base,base+1,base+2));materials.append(material)
    for _ in range(top_count):face((0.,0.,0.),(1.,0.,0.),(0.,2.,0.),1)
    candidates=[((-1.,0.,0.),(2.,0.,0.)),((0.,0.,0.),(1.,0.,0.)),
                ((.2,0.,0.),(.7,0.,0.)),((0.,0.,.001),(1.,0.,.001)),
                ((2.,0.,0.),(3.,0.,0.)),((0.,0.,0.),(0.,0.,0.))]
    candidates.extend(((-1.-i*.001,0.,0.),(2.+i*.001,0.,0.)) for i in range(extra_edges))
    for i,(a,b) in enumerate(candidates):face(a,b,(.5,-1.,-3.-i*.01),0)
    p=np.asarray(points);t=np.asarray(triangles,np.int64);m=np.asarray(materials,np.int64)
    return p,t,np.zeros((len(p),2)),m,np.flatnonzero(m==1)


class BatchedMatchingTests(unittest.TestCase):
    def test_cached_keys_are_exact_for_used_float32_and_float64_vertices(self):
        for dtype in (np.float32,np.float64):
            with self.subTest(dtype=dtype):
                p,t,uv,m,selected=fixture()
                unused=np.array([[999.,1000.,1001.],[999.,1002.,1003.],[999.,1004.,1005.]],dtype=dtype)
                p=np.vstack((unused,p.astype(dtype),unused+10))
                t=np.vstack((t+len(unused),[len(p)-3,len(p)-2,len(p)-1]))
                uv=np.zeros((len(p),2),dtype=dtype);m=np.r_[m,6]
                used=np.unique(t[np.r_[np.flatnonzero(m==0),selected]])
                expected={int(i):walk_skin._point(p[i]) for i in used}
                shared=scalar_shared(p,t,m,selected)
                # Initial adjacency, selected-edge records and rebuilt incident
                # faces must all reuse the cached keys, not recreate tuples.
                with patch.object(walk_skin,'_point',side_effect=AssertionError('coordinate key recreated')):
                    skin=BoundarySkin(p,t,uv,m,selected)
                    old=np.array([[0.,0.,0.],[.5,0.,0.],[1.,0.,0.]])
                    changed=old.copy();changed[:,2]=[.25,.75,.4]
                    skin.collect(0,old,changed)
                    removed,replacement=skin.rebuild()
                self.assertEqual(skin.point_keys,expected)
                self.assertEqual(dict(skin.shared),shared)
                self.assertFalse(any(i in skin.point_keys for i in range(len(unused))))
                self.assertFalse(any(i in skin.point_keys for i in range(len(p)-3,len(p))))
                self.assertTrue(all(type(c) is float for key in skin.point_keys.values() for c in key))
                self.assertGreater(len(removed),0)
                self.assertIsNotNone(replacement)

    def test_exact_key_also_retains_long_and_subedge_matches_in_scalar_order(self):
        p,t,uv,m,selected=fixture()
        actual=BoundarySkin(p,t,uv,m,selected)
        self.assertEqual(dict(actual.shared),scalar_shared(p,t,m,selected))
        found=actual.shared[0]
        self.assertIn(_edge((0,0,0),(1,0,0)),found)
        self.assertIn(_edge((-1,0,0),(2,0,0)),found)
        self.assertIn(_edge((.2,0,0),(.7,0,0)),found)
        self.assertNotIn(_edge((0,0,.001),(1,0,.001)),found)
        self.assertNotIn(_edge((2,0,0),(3,0,0)),found)

    def test_crosses_query_and_pair_batch_boundaries_without_reordering(self):
        p,t,uv,m,selected=fixture(top_count=100,extra_edges=100)
        expected=scalar_shared(p,t,m,selected)
        calls=[];original=np.einsum
        def measured(signature,*values,**kwargs):
            calls.append(values[0].shape[0])
            return original(signature,*values,**kwargs)
        with patch.object(walk_skin.np,'einsum',side_effect=measured):
            actual=BoundarySkin(p,t,uv,m,selected)
        self.assertEqual(dict(actual.shared),expected)
        self.assertGreater(len(calls),2)
        self.assertIn(8192,calls)
        self.assertLessEqual(max(calls),8192)


if __name__=='__main__':unittest.main()
