"""Piecewise-linear upper envelopes for explicitly flagged corner back patches.

Only material-zero faces with nonzero XY area participate. Original streams are
retained; occluded domains are removed only inside supplied regions, and newly
triangulated domains inherit their original triangle's exact Z and UV planes.
No terrain sampling, source endpoint snapping, or global state belongs here.
"""
import numpy as np
from shapely import (STRtree, area, bounds, constrained_delaunay_triangles, covers,
                     get_coordinates, intersection, polygons as make_polygons, union_all)
from shapely.geometry import Polygon

AREA_EPS = 1e-12  # Same projected degeneracy scale as sidewalk terrain/strip triangulation.
SOURCE_QUERY_BATCH = 256
PAIR_BATCH = 4096


def _parts(shape):
    if shape.geom_type == 'Polygon':
        if shape.area > 0:
            yield shape
    elif hasattr(shape, 'geoms'):
        for part in shape.geoms:
            yield from _parts(part)


def _gradient(triangle):
    return np.linalg.solve(triangle[1:, :2]-triangle[0, :2], triangle[1:, 2]-triangle[0, 2])


def _positive_domain(overlap, gradient, constant, origin):
    """Clip a bounding box by one affine half-plane, then the exact overlap."""
    x0,y0,x1,y1 = overlap.bounds
    corners = np.array(((x0,y0),(x1,y0),(x1,y1),(x0,y1)), np.float64)
    values = (corners-origin) @ gradient + constant
    if np.all(values <= 0):
        return None
    if np.all(values >= 0):
        return overlap
    clipped = []
    for a,b,da,db in zip(corners,np.roll(corners,-1,axis=0),values,np.roll(values,-1)):
        if da >= 0:
            clipped.append(a)
        if (da >= 0) != (db >= 0):
            clipped.append(a+(b-a)*(da/(da-db)))
    if len(clipped) < 3:
        return None
    result = overlap.intersection(Polygon(clipped))
    return result if result.area > AREA_EPS else None


def _positive_domains(overlaps,gradients,constants,origins):
    """The scalar half-plane algorithm in bounded, order-preserving arrays."""
    result=np.empty(len(overlaps),dtype=object);result[:]=None
    if not len(overlaps):return result
    boxes=bounds(overlaps)
    corners=np.stack((boxes[:,[0,1]],boxes[:,[2,1]],boxes[:,[2,3]],boxes[:,[0,3]]),axis=1)
    values=np.matmul(corners-origins[:,None,:],gradients[:,:,None])[:,:,0]+constants[:,None]
    if not np.isfinite(values).all():raise ValueError('non-finite back half-plane values')
    empty=np.all(values<=0,axis=1)
    full=~empty & np.all(values>=0,axis=1)
    result[full]=overlaps[full]
    mixed=np.flatnonzero(~(empty|full))
    if not len(mixed):return result
    points=corners[mixed];signed=values[mixed]
    following=np.roll(points,-1,axis=1)
    next_signed=np.roll(signed,-1,axis=1)
    inside=signed>=0
    crossing=inside!=np.roll(inside,-1,axis=1)
    fraction=np.divide(signed,signed-next_signed,out=np.zeros_like(signed),where=crossing)
    slots=np.empty((len(mixed),8,2),np.float64)
    slots[:,::2]=points
    slots[:,1::2]=points+(following-points)*fraction[:,:,None]
    valid=np.empty((len(mixed),8),bool)
    valid[:,::2]=inside;valid[:,1::2]=crossing
    counts=valid.sum(axis=1)
    if np.any((counts<3)|(counts>5)):
        raise ValueError('back half-plane box produced an invalid clipping ring')
    rings=np.empty((len(mixed),5,2),np.float64)
    rows=np.broadcast_to(np.arange(len(mixed))[:,None],valid.shape)[valid]
    columns=(np.cumsum(valid,axis=1)-1)[valid]
    rings[rows,columns]=slots[valid]
    # Group only equal ring lengths. Supplying padded/duplicate vertices would
    # differ from the exact original start/intersection ordering on zero ties.
    for count in (3,4,5):
        group=np.flatnonzero(counts==count)
        if not len(group):continue
        clipped=intersection(overlaps[mixed[group]],make_polygons(rings[group,:count]))
        positive=area(clipped)>AREA_EPS
        result[mixed[group[positive]]]=clipped[positive]
    return result


def _interpolate(xy, triangle, texture):
    a,b,c = triangle
    ab,ac = b[:2]-a[:2],c[:2]-a[:2]
    det = ab[0]*ac[1]-ab[1]*ac[0]
    rel = xy-a[:2]
    s = (rel[:,0]*ac[1]-rel[:,1]*ac[0])/det
    t = (ab[0]*rel[:,1]-ab[1]*rel[:,0])/det
    xyz = np.c_[xy,a[2]+s*(b[2]-a[2])+t*(c[2]-a[2])]
    uv = texture[0]+s[:,None]*(texture[1]-texture[0])+t[:,None]*(texture[2]-texture[0])
    # Retain any source endpoint bit-for-bit instead of re-evaluating its plane.
    for point,tex in zip(triangle,texture):
        same = np.all(xy == point[:2],axis=1)
        xyz[same],uv[same] = point,tex
    if not np.isfinite(xyz).all() or not np.isfinite(uv).all():
        raise ValueError('non-finite interpolated back envelope')
    return xyz,uv


def _overlap_batches(polygons,tree,relevant,region):
    """Yield the scalar algorithm's ordered pairs in bounded GEOS arrays."""
    relevant=np.asarray(relevant,np.int64)
    selected=np.zeros(len(polygons),bool);selected[relevant]=True
    contained=np.zeros(len(polygons),bool)
    contained[relevant]=covers(region,polygons[relevant])
    for start in range(0,len(relevant),SOURCE_QUERY_BATCH):
        source=relevant[start:start+SOURCE_QUERY_BATCH]
        pairs=tree.query(polygons[source],predicate='intersects')
        left,right=source[pairs[0]],pairs[1]
        keep=(right>left)&selected[right]
        left,right=left[keep],right[keep]
        # STRtree result order is unspecified. Retain exactly the prior outer-i,
        # sorted-inner-j order, including source indices used for coplanar ties.
        order=np.lexsort((right,left));left,right=left[order],right[order]
        for offset in range(0,len(left),PAIR_BATCH):
            i,j=left[offset:offset+PAIR_BATCH],right[offset:offset+PAIR_BATCH]
            overlaps=intersection(polygons[i],polygons[j])
            clip=~(contained[i]|contained[j])
            if np.any(clip):overlaps[clip]=intersection(overlaps[clip],region)
            positive=area(overlaps)>AREA_EPS
            if np.any(positive):yield i[positive],j[positive],overlaps[positive]


def _overlapping_pairs(polygons,tree,relevant,region):
    """Scalar iterator retained for focused order/reference checks."""
    for left,right,overlaps in _overlap_batches(polygons,tree,relevant,region):
        for i,j,overlap in zip(left,right,overlaps):yield int(i),int(j),overlap


def upper_back_envelope(mesh, regions):
    """Remove only lower, positive-area M0 overlap inside flagged regions.

Coplanar equal faces are owned by the lower original triangle index. Mere edge
contacts do not alter the mesh. Outside the region union, original source planes
remain intact, either as original rows or their triangulated remainder. Return
the original tuple itself when no positive-area occlusion exists.
    """
    p,t,uv,m = (np.asarray(a) for a in mesh)
    if (p.ndim != 2 or p.shape[1] != 3 or p.dtype.kind != 'f'
            or uv.shape != (len(p),2) or uv.dtype.kind != 'f'
            or t.ndim != 2 or t.shape[1] != 3 or t.dtype.kind not in 'iu'
            or m.shape != (len(t),) or m.dtype.kind not in 'iu' or not np.isfinite(p).all()
            or not np.isfinite(uv).all() or not np.isfinite(m).all()
            or len(t) and (t.min() < 0 or t.max() >= len(p))):
        raise ValueError('finite back mesh with valid triangle, UV and material streams required')
    regions = tuple(regions)
    for region in regions:
        if (region.geom_type not in ('Polygon','MultiPolygon') or not region.is_valid
                or not np.isfinite(get_coordinates(region)).all()):
            raise ValueError('finite valid polygon regions required for back envelope')
    if not regions or not len(t):
        return mesh
    region = union_all(regions)
    if region.is_empty:
        return mesh
    original = np.asarray(p[t],np.float64)
    ab,ac = original[:,1,:2]-original[:,0,:2],original[:,2,:2]-original[:,0,:2]
    determinant = ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
    if not np.isfinite(determinant).all():
        raise ValueError('non-finite projected back triangle area')
    eligible = np.flatnonzero((m == 0) & (np.abs(determinant) > AREA_EPS))
    if len(eligible) < 2:
        return mesh
    polygons = np.empty(len(eligible),dtype=object)
    for start in range(0,len(eligible),PAIR_BATCH):
        polygons[start:start+PAIR_BATCH] = make_polygons(original[eligible[start:start+PAIR_BATCH],:,:2])
    tree = STRtree(polygons)
    relevant = sorted(int(i) for i in tree.query(region,predicate='intersects'))
    planes=np.zeros((len(eligible),2),np.float64)
    for i in relevant:planes[i]=_gradient(original[eligible[i]])
    if not np.isfinite(planes[relevant]).all():
        raise ValueError('non-finite back triangle plane')
    occluded = {}
    for left,right,overlaps in _overlap_batches(polygons,tree,relevant,region):
        ti,tj=original[eligible[left],0],original[eligible[right],0]
        gradients=planes[right]-planes[left]
        constants=tj[:,2]+np.matmul(planes[right,None,:],(ti[:,:2]-tj[:,:2])[:,:,None])[:,0,0]-ti[:,2]
        if not np.isfinite(gradients).all() or not np.isfinite(constants).all():
            raise ValueError('non-finite back plane difference')
        coplanar=np.all(gradients==0,axis=1)&(constants==0)
        ordinary=np.flatnonzero(~coplanar)
        higher_j=np.empty(len(left),object);higher_j[:]=None
        higher_i=np.empty(len(left),object);higher_i[:]=None
        higher_j[ordinary]=_positive_domains(overlaps[ordinary],gradients[ordinary],constants[ordinary],ti[ordinary,:2])
        higher_i[ordinary]=_positive_domains(overlaps[ordinary],-gradients[ordinary],-constants[ordinary],ti[ordinary,:2])
        # Keep old pair and per-owner append order even though ring construction
        # and GEOS operations above are grouped by clipping-ring length.
        for i,j,overlap,tie,hj,hi in zip(left,right,overlaps,coplanar,higher_j,higher_i):
            i,j=int(i),int(j)
            if tie:occluded.setdefault(j,[]).append(overlap)
            else:
                if hj is not None:occluded.setdefault(i,[]).append(hj)
                if hi is not None:occluded.setdefault(j,[]).append(hi)
    if not occluded:
        return mesh
    keep = np.ones(len(t),bool)
    added_points,added_uvs,added_faces = [],[],[]
    for index in sorted(occluded):
        face = int(eligible[index])
        removed = union_all(occluded[index])
        if removed.area <= AREA_EPS:
            continue
        visible = polygons[index].difference(removed)
        keep[face] = False
        for part in _parts(visible):
            for triangle in constrained_delaunay_triangles(part).geoms:
                xy = np.asarray(triangle.exterior.coords,np.float64)[:3]
                delta = xy[1:]-xy[0]
                cross = delta[0,0]*delta[1,1]-delta[0,1]*delta[1,0]
                if abs(cross) <= AREA_EPS:
                    continue
                if cross < 0:
                    xy = xy[::-1]
                xyz,tex = _interpolate(xy,original[face],uv[t[face]])
                base = len(p)+len(added_points)
                added_points.extend(xyz);added_uvs.extend(tex)
                added_faces.append((base,base+1,base+2))
    if keep.all():
        return mesh
    if added_faces and added_faces[-1][-1] > np.iinfo(t.dtype).max:
        raise ValueError('back envelope vertex indices exceed source triangle dtype')
    return (np.vstack((p,np.asarray(added_points,dtype=p.dtype).reshape(-1,3))),
            np.vstack((t[keep],np.asarray(added_faces,dtype=t.dtype).reshape(-1,3))),
            np.vstack((uv,np.asarray(added_uvs,dtype=uv.dtype).reshape(-1,2))),
            np.r_[m[keep],np.zeros(len(added_faces),dtype=m.dtype)])
