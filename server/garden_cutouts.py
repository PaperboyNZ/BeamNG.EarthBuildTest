"""Cut compact tree gardens out of visual and collision sidewalk triangles."""
import numpy as np
from shapely import STRtree, constrained_delaunay_triangles
from shapely.geometry import Polygon
from shapely.ops import unary_union


def cut(mesh, gardens, origin):
    if mesh is None or not gardens:return mesh
    P,T,UV,M=map(np.asarray,mesh)
    holes=[Polygon(np.asarray(g['ring'],float)[:,:2]-np.asarray(origin)[:2]) for g in gardens]
    holes=[p for p in holes if p.is_valid and .1<p.area<4.]
    if not holes:return mesh
    tree=STRtree(holes)
    # Most road triangles never approach a garden. Cull in NumPy before any
    # polygon clipping; no runtime mesh work is done by the game client.
    xy=P[T,:2];lo=xy.min(axis=1);hi=xy.max(axis=1)
    affected=np.zeros(len(T),bool)
    for hole in holes:
        x0,y0,x1,y1=hole.bounds
        affected|=(hi[:,0]>x0)&(lo[:,0]<x1)&(hi[:,1]>y0)&(lo[:,1]<y1)
    keep=np.ones(len(T),bool);positions=[];uvs=[];triangles=[];materials=[]
    for idx in np.flatnonzero(affected):
        source=P[T[idx]];coords=source[:,:2]
        matrix=np.column_stack((coords[1]-coords[0],coords[2]-coords[0]))
        det=np.linalg.det(matrix)
        if abs(det)<1e-10:continue  # vertical outer curb faces
        poly=Polygon(coords);hits=tree.query(poly,predicate='intersects')
        if not len(hits):continue
        remaining=poly.difference(unary_union([holes[int(i)] for i in hits]))
        if abs(remaining.area-poly.area)<1e-10:continue
        keep[idx]=False
        if remaining.is_empty:continue
        pieces=constrained_delaunay_triangles(remaining)
        inv=np.linalg.inv(matrix)
        for tri in pieces.geoms:
            pts=np.asarray(tri.exterior.coords)[:3]
            if tri.area<1e-10:continue
            orientation=np.linalg.det(np.column_stack((pts[1]-pts[0],pts[2]-pts[0])))
            if orientation*det<0:pts=pts[::-1]
            weights=(pts-coords[0])@inv.T
            weights=np.column_stack((1-weights.sum(axis=1),weights))
            start=len(P)+len(positions)
            positions.extend(weights@source);uvs.extend(weights@UV[T[idx]])
            triangles.append((start,start+1,start+2));materials.append(M[idx])
    if not positions:return P,T[keep],UV,M[keep]
    return (np.vstack((P,positions)),np.vstack((T[keep],triangles)),np.vstack((UV,uvs)),np.r_[M[keep],materials].astype(M.dtype))
