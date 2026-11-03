"""Continuous ordinary-corner rear slopes; no slab, curb or Builder mutation.

Call after curved_corner with its original native tuple retained separately.
Unsupported merged3D profiles produce an explicit diagnostic for the caller to
handle; they are never clipped away or reported as a repaired back.
"""
import numpy as np
from shapely import constrained_delaunay_triangles, union_all
from shapely.geometry import Polygon

from walk_geometry import corner_rear, MergedCornerRequired

BACK_RUN=2.
SINK=.10
CROSS_SLOPE=.015
CURB_REPEAT_M=9.
V_LIGHT=1.-40./512.
V_DARK=1.-63./512.


class BackMergeIncompatible(ValueError):
    """A merged footprint cannot weld the two actual approach profiles in3D."""
    def __init__(self,diagnostic):
        self.diagnostic=diagnostic
        super().__init__('merged back3D compatibility failed: '+str(diagnostic))


def _native_back(native,rear_count):
    p,t,uv,m=(np.asarray(value) for value in native)
    slab=np.flatnonzero(m==1)
    if not len(slab):raise ValueError('native corner has no slab ordering for rear identification')
    rows=np.arange(int(slab[-1])+1,len(t))
    if not len(rows) or np.any(m[rows]!=0):raise ValueError('native corner rear M0 suffix is missing')
    first=int(t[rows].min())
    if first<rear_count or np.any(t[rows]<first) or np.any(t[rows]>=len(p)):
        raise ValueError('native rear vertex block is invalid')
    return p[first-rear_count:first][::-1],rows,first


def _stations(points):
    return np.r_[0.,np.cumsum(np.linalg.norm(np.diff(points[:,:2],axis=0),axis=1))]


def _nearest_station(point,chain,stations):
    d=np.diff(chain[:,:2],axis=0);squared=np.einsum('ij,ij->i',d,d)
    t=np.clip(np.einsum('ij,ij->i',point-chain[:-1,:2],d)/np.maximum(squared,1e-30),0,1)
    distance=np.linalg.norm(chain[:-1,:2]+t[:,None]*d-point,axis=1)
    return float(np.median((stations[:-1]+t*np.diff(stations))[distance<=distance.min()+1e-8]))


def _profile_height(point,top,bottom):
    delta=bottom[:2]-top[:2];squared=float(delta@delta)
    fraction=float((point-top[:2])@delta/squared) if squared>1e-20 else np.nan
    residual=float(np.linalg.norm(top[:2]+fraction*delta-point))
    return dict(parameter=fraction,residual_m=residual,
                height=float(top[2]+fraction*(bottom[2]-top[2])))


def _geometry(top,normals,widths,h,source):
    descents=BACK_RUN*(float(h)+SINK+widths*CROSS_SLOPE)
    if np.any(descents<=0) or not np.isfinite(descents).all():raise ValueError('positive rear-profile descents required')
    ends=top[[0,-1]].copy()
    ends[:,:2]+=normals[[0,-1]]*descents[[0,-1],None]
    # corner_rear carries top-datum Z; subtract each returned horizontal
    # descent/BACK_RUN once, including the exact endpoint profiles.
    plan=corner_rear(top,normals,float(descents[0]),float(descents[-1]),ends[0],ends[1],
                     station_widths=descents)
    bottom=plan.outer.copy();bottom[:,2]-=plan.widths/BACK_RUN
    exact_bottom=ends.copy();exact_bottom[:,2]-=descents[[0,-1]]/BACK_RUN
    top_s=_stations(top)
    bottom_v=np.full(len(bottom),V_DARK)
    if plan.merged_inner:
        # A consumed offset omits an inverted loop behind the approaches. A
        # new cap intersection must have the same height on BOTH untouched
        # approach rear profiles; nearest-arc/median Z alone cannot prove this.
        for index,point in enumerate(bottom[:,:2]):
            profiles=[_profile_height(point,a,b) for a,b in zip(top[[0,-1]],exact_bottom)]
            gap=abs(profiles[0]['height']-profiles[1]['height'])
            valid=all(np.isfinite((p['parameter'],p['residual_m'],p['height'])).all()
                      and -1e-9<=p['parameter']<=1+1e-9 and p['residual_m']<=1e-8 for p in profiles)
            if not valid or gap>1e-8:
                raise BackMergeIncompatible(dict(reason='approach profile intersection is unavailable or has inconsistent Z',
                    point_xy=point.tolist(),height_difference_m=gap,profiles=profiles,
                    top_endpoints=top[[0,-1]].tolist(),exact_bottom_endpoints=exact_bottom.tolist(),source=source))
            bottom[index,2]=(profiles[0]['height']+profiles[1]['height'])/2
            bottom_v[index]=V_LIGHT+(V_DARK-V_LIGHT)*np.mean([p['parameter'] for p in profiles])
        bottom_s=np.array([_nearest_station(point,top,top_s) for point in bottom[:,:2]])
    else:
        bottom[0],bottom[-1]=exact_bottom[1],exact_bottom[0]
        bottom_s=plan.stations
    vertices=np.vstack((top,bottom))
    texture=np.vstack((np.c_[top_s/CURB_REPEAT_M,np.full(len(top),V_LIGHT)],
                       np.c_[bottom_s/CURB_REPEAT_M,bottom_v]))
    polygon=Polygon(vertices[:,:2])
    if not polygon.is_valid or polygon.area<=1e-10:raise ValueError('continuous rear footprint is folded or empty')
    return vertices,texture,polygon,plan.merged_inner,exact_bottom


def _overlapping_candidates(top,normals,widths,h):
    """Exact station profiles pending the caller's combined upper envelope."""
    descent=BACK_RUN*(float(h)+SINK+widths*CROSS_SLOPE)
    bottom=top.copy();bottom[:,:2]+=normals*descent[:,None]
    bottom[:,2]-=descent/BACK_RUN
    vertices=np.vstack((top,bottom));n=len(top);station=_stations(top)
    texture=np.vstack((np.c_[station/CURB_REPEAT_M,np.full(n,V_LIGHT)],
                       np.c_[station/CURB_REPEAT_M,np.full(n,V_DARK)]))
    faces=[];polygons=[]
    for i in range(n-1):
        for ids in ((i,i+1,n+i+1),(i,n+i+1,n+i)):
            face=np.asarray(ids,np.int64)
            a,b=vertices[face[1:],:2]-vertices[face[0],:2]
            cross=float(a[0]*b[1]-a[1]*b[0])
            if abs(cross)<=1e-12:continue
            if cross<0:face=face[::-1]
            faces.append(face);polygons.append(Polygon(vertices[face,:2]))
    if not faces:raise ValueError('consumed rear candidates have no positive footprint')
    return vertices,texture,np.asarray(faces,np.int64),union_all(polygons)


def continuous_back(mapped_mesh,native_mesh,origin,arc,inward,outer,outer_stations,h,*,overlap_regions=None):
    """Replace only native rear M0 faces, preserving all pre-existing P/UV.

Ordinary endpoints match their adjoining full rear-profile segments. A consumed
bottom footprint may meet the approaches at a shared cap intersection instead;
that intersection's Z is proved against both actual3D profiles. The original
full beyond-center endpoint segments are outside that merged corner component.
An incompatible consumed profile requires an overlap_regions list. Its full
station quads are then candidates ONLY: the caller must apply the combined
corner/approach upper envelope before publishing either visual or lean mesh.
Without that explicit repair contract BackMergeIncompatible is raised.
    """
    if outer_stations is None:return mapped_mesh
    p,t,uv,m=(np.asarray(value) for value in mapped_mesh)
    raw_p,raw_t,raw_uv,raw_m=(np.asarray(value) for value in native_mesh)
    origin=np.asarray(origin,float);arc=np.asarray(arc,float);inward=np.asarray(inward,float)
    outer=np.asarray(outer,float);station=np.asarray(outer_stations,float)[::-1]
    if (origin.shape!=(3,) or arc.ndim!=2 or arc.shape[1]!=3 or len(arc)<2
            or inward.shape!=(len(arc),2) or outer.ndim!=2 or outer.shape[1]!=3
            or len(outer)<2 or station.shape!=(len(outer),)
            or not np.isfinite(h) or h<0
            or not all(np.isfinite(value).all() for value in (origin,arc,inward,outer,station))):
        raise ValueError('finite paired corner metadata required for rear slope')
    if len(p)<len(raw_p) or not np.array_equal(p[:len(raw_p)],raw_p) or not np.array_equal(uv[:len(raw_uv)],raw_uv):
        raise ValueError('continuous_back must precede material UV scaling and retain its native prefix')
    top,back_rows,back_first=_native_back(native_mesh,len(outer))
    if np.max(np.linalg.norm(top[:,:2]-(outer[::-1,:2]-origin[:2]),axis=1))>1e-8:
        raise ValueError('native rear top differs from supplied outer boundary')
    source_s=_stations(arc)
    if np.any(np.diff(source_s)<=0) or np.any(np.diff(station)<=0) or abs(station[0])>1e-8 or abs(station[-1]-source_s[-1])>1e-8:
        raise ValueError('rear stations must cover the source arc monotonically')
    normals=np.column_stack([np.interp(station,source_s,inward[:,j]) for j in range(2)])
    lengths=np.linalg.norm(normals,axis=1)
    if np.any(lengths<=1e-9):raise ValueError('rear source directions vanish')
    normals/=lengths[:,None]
    curb=np.column_stack([np.interp(station,source_s,arc[:,j])-origin[j] for j in range(2)])
    widths=np.linalg.norm(top[:,:2]-curb,axis=1)
    source=dict(origin=origin.tolist(),arc=arc.tolist(),inward=inward.tolist(),
                outer=outer.tolist(),outer_stations=np.asarray(outer_stations).tolist(),h=float(h))
    pending_region=None
    try:
        vertices,texture,polygon,merged,exact_bottom=_geometry(top,normals,widths,h,source)
    except (BackMergeIncompatible,MergedCornerRequired) as exc:
        if overlap_regions is None:
            if isinstance(exc,BackMergeIncompatible):raise
            raise BackMergeIncompatible(dict(reason=str(exc),source=source)) from exc
        vertices,texture,candidate_faces,pending_region=_overlapping_candidates(top,normals,widths,h)
        polygon=None
    lookup={tuple(q):i for i,q in enumerate(vertices[:,:2])}
    if polygon is not None and len(lookup)!=len(vertices):raise ValueError('rear boundary has coincident XY with ambiguous height')
    faces=[];area=0.
    for triangle in constrained_delaunay_triangles(polygon).geoms if polygon is not None else ():
        coordinates=np.asarray(triangle.exterior.coords)[:3,:2]
        try:face=np.array([lookup[tuple(q)] for q in coordinates],np.int64)
        except KeyError as exc:raise ValueError('rear triangulation introduced an unbounded vertex') from exc
        a,b=vertices[face[1:],:2]-vertices[face[0],:2]
        signed=float(a[0]*b[1]-a[1]*b[0])
        if abs(signed)<=1e-12:continue
        if signed<0:face=face[::-1]
        faces.append(face+len(p));area+=abs(signed)/2
    if polygon is None:faces=candidate_faces+len(p)
    elif not faces or abs(area-polygon.area)>max(1e-8,polygon.area*1e-8):
        raise ValueError('continuous rear triangulation does not cover its footprint')
    # curved_corner retained exactly these raw rear indices. Avoid removing
    # later material0 geometry merely because it also uses appended vertices.
    remove=(m==0)&np.all((t>=back_first)&(t<len(raw_p)),axis=1)
    if not np.array_equal(t[remove],raw_t[back_rows]):raise ValueError('mapped rear faces do not match native rear descriptor')
    keep=~remove
    if pending_region is not None:overlap_regions.append(pending_region)
    return np.vstack((p,vertices)),np.vstack((t[keep],np.asarray(faces,np.int64))),np.vstack((uv,texture)),np.r_[m[keep],np.zeros(len(faces),np.int64)]
