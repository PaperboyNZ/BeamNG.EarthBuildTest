"""Offline distant-facade baking, explicitly invoked by the render laboratory.

Only closed, shallow, outward-facing facade surfaces are flattened. The roof,
footprint holes, underside and projecting/sideways faces keep their original
triangles. No baking runs in the streaming or per-frame path.
"""
from dataclasses import dataclass
import hashlib
import math
import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

CHANNELS = ('color', 'normal', 'roughness', 'metallic', 'ao', 'emissive')
VERSION = 1


@dataclass
class Card:
    points: np.ndarray
    pixels: dict
    source_triangles: np.ndarray
    signature: str


def _raster(p, uv, colors, tris, materials, sample, width, height, bounds):
    """Sample actual source materials with nearest-surface depth ownership."""
    left,bottom,right,top = bounds
    screen = np.column_stack(((p[:,0]-left)/(right-left)*width,
                              (top-p[:,1])/(top-bottom)*height))
    depth = np.full((height,width), -np.inf)
    result = {k:np.zeros((height,width,3),np.uint8) for k in CHANNELS}
    for tri,mat in zip(tris,materials):
        abc = screen[tri]
        x0,y0 = np.maximum(0,np.floor(abc.min(0)).astype(int))
        x1,y1 = np.minimum((width,height),np.ceil(abc.max(0)).astype(int))
        if x1<=x0 or y1<=y0:continue
        a,b,c = abc
        den = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-12:continue
        x,y = np.meshgrid(np.arange(x0,x1)+.5,np.arange(y0,y1)+.5)
        w0=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
        w1=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den
        weights=np.stack((w0,w1,1-w0-w1),-1)
        z=weights@p[tri,2]
        current=depth[y0:y1,x0:x1]
        mask=(weights.min(-1)>=-1e-7)&(z>=current-1e-9)
        if not mask.any():continue
        coords=weights[mask]@uv[tri]
        tint=weights[mask]@colors[tri,:3]/255.
        # UV Jacobian informs source mip selection instead of aliasing full
        # resolution textures into a few distant pixels.
        jac=np.linalg.solve(np.column_stack((abc,np.ones(3))),uv[tri])[:2]
        values=sample(mat,coords,tint,jac)
        # Reorient tangent-space normals into the card's tangent frame. Source
        # UVs may be rotated/mirrored even when the physical face is coplanar.
        delta_uv=uv[tri[1:]]-uv[tri[0]]
        delta_uv[:,1]*=-1.  # the CDAE encoder flips v
        if abs(np.linalg.det(delta_uv))>1e-14:
            frame=np.linalg.solve(delta_uv,p[tri[1:],:2]-p[tri[0],:2])
            tangent=frame[0]/max(np.linalg.norm(frame[0]),1e-20)
            bitangent=np.array((-tangent[1],tangent[0]))
            if bitangent@frame[1]<0:bitangent=-bitangent
            normal=values['normal'].astype(float)/127.5-1.
            planar=normal[:,:1]*tangent+normal[:,1:2]*bitangent
            normal=np.column_stack((planar[:,0],-planar[:,1],normal[:,2]))
            normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-20)
            values['normal']=np.clip(np.rint((normal+1)*127.5),0,255).astype(np.uint8)
        for channel in CHANNELS:result[channel][y0:y1,x0:x1][mask]=values[channel]
        current[mask]=z[mask]
    if not np.isfinite(depth).all():
        raise ValueError('facade raster has uncovered pixels')
    return result


def cards(mesh, spec, gmin, gmax, sample, pixels_per_metre=8., max_side=512):
    """Return accepted cards; rejected faces stay in their original mesh."""
    import buildings as b
    if (spec.footprint is None or spec.inference is None or spec.deck or
            spec.church is not None or spec.cls in b.BRIDGE_CLASSES or spec.cls=='ship'):
        return [], ['specialized_envelope_retained']
    if not math.isfinite(pixels_per_metre) or not 1<=pixels_per_metre<=64 or not 8<=max_side<=2048:
        raise ValueError('invalid facade texture budget')
    p,uv,t,mi,mats,col=mesh[:6]
    mh=spec.min_h or 0.
    base=b.base_z(spec,gmin,gmax)+mh
    bottom=gmin-b.SKIRT_LITE_M if mh<=.5 else base
    top=base+spec.height
    normals=np.cross(p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]])
    lengths=np.linalg.norm(normals,axis=1)
    normals=normals/np.maximum(lengths[:,None],1e-30)
    accepted=[];notes=[];claimed=np.zeros(len(t),bool)
    for boundary,ring in enumerate((spec.footprint.outer,*spec.footprint.holes)):
        for edge,(a,c) in enumerate(zip(ring,ring[1:]+ring[:1])):
            a,c=np.asarray(a),np.asarray(c);length=float(np.linalg.norm(c-a))
            if length<.05:continue
            d=(c-a)/length;out=np.array((d[1],-d[0]))
            width,height=max(8,math.ceil(length*pixels_per_metre)),max(8,math.ceil((top-bottom)*pixels_per_metre))
            if max(width,height)>max_side:
                notes.append(f'{boundary}:{edge}:resolution_budget_retained');continue
            local=np.column_stack(((p[:,:2]-a)@d,p[:,2],(p[:,:2]-a)@out))
            tri=local[t]
            selected=(~claimed)&(normals[:,:2]@out>.99999)&(lengths>1e-12)
            selected &= (tri[:,:,0].min(1)>=-1e-7)&(tri[:,:,0].max(1)<=length+1e-7)
            selected &= (tri[:,:,1].min(1)>=bottom-1e-7)&(tri[:,:,1].max(1)<=top+1e-7)
            selected &= (tri[:,:,2].min(1)>=-1e-7)&(tri[:,:,2].max(1)<=.04+1e-7)
            ids=np.flatnonzero(selected)
            if len(ids)<=2:continue
            surface=unary_union([Polygon(q[:,:2]) for q in tri[ids]])
            # Prove continuous coverage geometrically; a pixel mask alone could
            # accidentally close a narrow doorway or an arcade.
            target=box(0.,bottom,length,top)
            if not surface.buffer(1e-8).covers(target):
                notes.append(f'{boundary}:{edge}:open_surface_retained');continue
            try:
                pixels=_raster(local,uv,col,t[ids],[mats[i] for i in mi[ids]],sample,width,height,(0.,bottom,length,top))
            except (KeyError,ValueError,FileNotFoundError) as exc:
                notes.append(f'{boundary}:{edge}:material_retained:{exc}');continue
            key=hashlib.sha256(str((VERSION,width,height)).encode())
            for channel in CHANNELS:key.update(pixels[channel].tobytes())
            points=np.array([(*a,bottom),(*c,bottom),(*c,top),(*a,top)])
            accepted.append(Card(points,pixels,ids,key.hexdigest()))
            claimed[ids]=True
    return accepted,notes


def assemble(mesh, cards_, placements):
    """Retain original attributes/order on all non-facade triangles."""
    p,uv,t,mi,mats,col=mesh[:6]
    keep=np.ones(len(t),bool)
    for card in cards_:keep[card.source_triangles]=False
    remaining=t[keep]
    used,remap=np.unique(remaining,return_inverse=True)
    pp=[p[used]];uu=[uv[used]];tt=[remap.reshape(-1,3)];mm=[mi[keep]];cc=[col[used]]
    names=list(mats);n=len(used)
    for card in cards_:
        material,coords=placements[card.signature]
        if material not in names:names.append(material)
        pp.append(card.points);uu.append(np.asarray(coords));tt.append(np.array(((0,1,2),(0,2,3)))+n)
        mm.append(np.full(2,names.index(material),np.int64));cc.append(np.full((4,4),255,np.uint8));n+=4
    return np.concatenate(pp),np.concatenate(uu),np.concatenate(tt),np.concatenate(mm),tuple(names),np.concatenate(cc)
