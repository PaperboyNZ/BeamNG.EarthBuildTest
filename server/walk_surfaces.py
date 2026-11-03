"""Metric paving on ordinary paired corners, independent of Builder imports.

The native curb and rear skins remain untouched. Only pavement triangles are
replaced, using native boundary XYZ (including ramp/lean height samples).
"""
import math

import numpy as np


def _slab_block(mesh, rear_count):
    p,t,uv,m=mesh
    rows=np.flatnonzero(m==1)
    if not len(rows):raise ValueError('paired corner has no native slab triangles')
    if len(rows)!=rows[-1]-rows[0]+1:
        raise ValueError('paired corner requires native triangle ordering')
    start=int(t[:rows[0]].max())+1 if rows[0] else 0
    end=int(t[rows[-1]+1:].min()) if rows[-1]+1<len(t) else len(p)
    front_count=end-start-rear_count
    if front_count<2 or rear_count<2 or start<0 or end>len(p):
        raise ValueError('paired corner native slab block is invalid')
    if np.any(t[rows]<start) or np.any(t[rows]>=end):
        raise ValueError('paired corner slab indices escape its native block')
    return start,end,front_count


def _front_stations(front, source, stations, inward, curb_width, tolerance):
    delta=np.diff(source,axis=0);squared=np.einsum('ij,ij->i',delta,delta)
    if np.any(squared<=1e-18):raise ValueError('corner offset source has a zero-length segment')
    # Ramp refinement normalizes interpolated unit normals. Its offset can lie
    # slightly off the straight source-offset chord; bound that exact deviation.
    dot=np.einsum('ij,ij->i',inward[:-1],inward[1:])
    residual_bound=curb_width*(1-np.sqrt(np.clip((1+dot)/2,0,1)))+tolerance
    recovered=[]
    for point in front[:,:2]:
        distances=np.linalg.norm(source-point,axis=1)
        exact=int(np.argmin(distances))
        if distances[exact]<=tolerance:
            recovered.append(stations[exact]);continue
        fraction=np.clip(np.einsum('ij,ij->i',point-source[:-1],delta)/squared,0,1)
        residual=np.linalg.norm(source[:-1]+fraction[:,None]*delta-point,axis=1)
        segment=int(np.argmin(residual))
        if residual[segment]>residual_bound[segment]:
            raise ValueError('native corner front exceeds source-offset residual bound')
        recovered.append(stations[segment]+fraction[segment]*(stations[segment+1]-stations[segment]))
    recovered=np.asarray(recovered)
    if np.linalg.norm(front[0,:2]-source[0])>tolerance or np.linalg.norm(front[-1,:2]-source[-1])>tolerance:
        raise ValueError('native corner front lost an exact source endpoint')
    recovered[0],recovered[-1]=stations[0],stations[-1]
    return recovered


def _compact_front(front,stations):
    # Native refine sorts then deduplicates exact floats: .5 and 1.1-.6 can
    # survive as two ULP-adjacent stations with coincident XYZ. Collapse only
    # consecutive coincident geometry AND coincident station values. The raw
    # native P/UV streams remain untouched; physical folds are still rejected.
    keep=[0]
    for index in range(1,len(front)):
        previous=keep[-1]
        difference=stations[index]-stations[previous]
        if abs(difference)<=1e-9 and np.linalg.norm(front[index]-front[previous])<=1e-9:
            if index==len(front)-1:keep[-1]=index  # preserve the exact final endpoint
            continue
        if difference<=1e-10:raise ValueError('native corner front stations fold or repeat')
        keep.append(index)
    return front[keep],stations[keep]


def _union_stations(front,rear,tolerance):
    values=np.sort(np.r_[front,rear])
    union=[float(values[0])]
    for value in values[1:]:
        if value-union[-1]>tolerance:union.append(float(value))
    return np.asarray(union)


def _chain_at(stations,points,union,tolerance):
    result=np.column_stack([np.interp(union,stations,points[:,j]) for j in range(3)])
    # Retain every original boundary vertex bit-for-bit, including endpoint Z.
    for station,point in zip(stations,points):
        index=int(np.argmin(np.abs(union-station)))
        if abs(union[index]-station)>tolerance:raise ValueError('native boundary station lost during merge')
        result[index]=point
    return result


def _cross(a,b):
    return a[...,0]*b[...,1]-a[...,1]*b[...,0]


def curved_corner(mesh,origin,arc,inward,outer,outer_stations,phase,curb_width=.15):
    """Rebuild native M1 as station pairs and return unscaled metric UVs.

``outer`` and its stations run opposite to ``arc``. Call on one native corner
before complete_corner_slab or any triangle reordering. A None station mapping
belongs to the caller's merged/planar branch and is deliberately left alone.
Unused old slab vertices are retained so every non-slab vertex/index/UV is exact.
    """
    if outer_stations is None:return mesh
    p,t,uv,m=(np.asarray(a) for a in mesh)
    origin=np.asarray(origin,float);arc=np.asarray(arc,float);inward=np.asarray(inward,float)
    outer=np.asarray(outer,float);rear_s=np.asarray(outer_stations,float)[::-1].copy()
    if (p.ndim!=2 or p.shape[1]!=3 or uv.shape!=(len(p),2) or t.ndim!=2 or t.shape[1]!=3 or m.shape!=(len(t),)
            or origin.shape!=(3,) or arc.ndim!=2 or arc.shape[1]!=3 or len(arc)<2
            or inward.shape!=(len(arc),2) or outer.ndim!=2 or outer.shape[1]!=3 or len(outer)<2
            or rear_s.shape!=(len(outer),) or not math.isfinite(phase) or not math.isfinite(curb_width) or curb_width<=0):
        raise ValueError('paired corner requires finite native mesh and matching arc/rear metadata')
    if not all(np.isfinite(a).all() for a in (p,uv,origin,arc,inward,outer,rear_s)):
        raise ValueError('paired corner metadata is not finite')
    if len(t) and (t.min()<0 or t.max()>=len(p)):raise ValueError('native corner triangle index outside vertex stream')
    if np.any(np.abs(np.linalg.norm(inward,axis=1)-1)>1e-7):raise ValueError('corner inward directions must be unit vectors')
    source_s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(arc[:,:2],axis=0),axis=1))]
    if np.any(np.diff(source_s)<=1e-10):raise ValueError('corner source stations fold or repeat')
    tolerance=2e-8
    station_tolerance=max(1e-9,source_s[-1]*1e-12)
    if np.any(np.diff(rear_s)<=station_tolerance) or abs(rear_s[0])>station_tolerance or abs(rear_s[-1]-source_s[-1])>station_tolerance:
        raise ValueError('corner rear stations must cover the source arc in reverse order')
    rear_s[0],rear_s[-1]=0.,source_s[-1]
    start,end,front_count=_slab_block((p,t,uv,m),len(outer))
    front=p[start:start+front_count]
    rear=p[start+front_count:end][::-1]
    if np.max(np.linalg.norm(rear[:,:2]-(outer[::-1,:2]-origin[:2]),axis=1))>tolerance:
        raise ValueError('native corner rear does not match supplied outer boundary')
    source_front=arc[:,:2]+inward*curb_width-origin[:2]
    front_s=_front_stations(front,source_front,source_s,inward,curb_width,tolerance)
    front,front_s=_compact_front(front,front_s)
    union=_union_stations(front_s,rear_s,station_tolerance)
    f=_chain_at(front_s,front,union,station_tolerance)
    r=_chain_at(rear_s,rear,union,station_tolerance)
    from shapely.geometry import Polygon
    outline=Polygon(np.vstack((f[:,:2],r[::-1,:2])))
    if not outline.is_valid or outline.area<=1e-10:raise ValueError('paired corner outline folds or has no area')
    curb=np.column_stack([np.interp(union,source_s,arc[:,j])-origin[j] for j in range(2)])
    widths=np.linalg.norm(r[:,:2]-curb,axis=1)
    if np.any(widths<=curb_width+1e-9):raise ValueError('paired corner rear consumes the pavement width')
    middle=(f[:,:2]+r[:,:2])/2
    u=float(phase)+np.r_[0.,np.cumsum(np.linalg.norm(np.diff(middle,axis=0),axis=1))]
    if np.any(np.diff(u)<=1e-10):raise ValueError('paired corner midline folds or has no length')
    vertices=np.stack((f,r),axis=1).reshape(-1,3)
    metric=np.column_stack((np.repeat(u,2),np.column_stack((np.full(len(union),curb_width),widths)).ravel()))
    # The same ordered strip may be clockwise or reflected. Choose a valid
    # diagonal per cell, then orient every emitted triangle upward in XY.
    signed=_cross(f[1:,:2]-f[:-1,:2],r[1:,:2]-f[:-1,:2])+_cross(r[1:,:2]-f[:-1,:2],r[:-1,:2]-f[:-1,:2])
    orientation=np.sign(signed[0])
    if not orientation or np.any(signed*orientation<=1e-12):raise ValueError('paired corner station cells fold')
    faces=[];area=0.
    for i in range(len(union)-1):
        a,b,c,d=2*i,2*i+2,2*i+3,2*i+1
        for candidate in (((a,b,c),(a,c,d)),((a,b,d),(b,c,d))):
            tri=np.asarray(candidate,np.int64)
            xy=vertices[tri,:2]
            cross=_cross(xy[:,1]-xy[:,0],xy[:,2]-xy[:,0])
            if np.all(cross*orientation>1e-12):break
        else:raise ValueError('paired corner cell has no nonfolded diagonal')
        if orientation<0:tri=tri[:,::-1]
        faces.extend(tri+len(p));area+=float(np.abs(cross).sum()/2)
    if abs(area-outline.area)>max(1e-8,outline.area*1e-9):raise ValueError('paired corner station cells do not cover the native boundary')
    keep=m!=1
    return np.vstack((p,vertices)),np.vstack((t[keep],np.asarray(faces,np.int64))),np.vstack((uv,metric)),np.r_[m[keep],np.ones(len(faces),np.int64)]
