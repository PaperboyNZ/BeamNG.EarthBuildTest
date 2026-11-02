"""Stable, bounded surface aging shared by shell, lite and detailed buildings.

No geometry, material variants, per-building textures or collision changes.
The affine height gradient interpolates identically across planar wall LODs.
Organic mottling and roof stains share one packed material detail map. Climate
and face exposure bias deposits without inventing condition from geography.
Opaque PBR vertex alpha carries affine roof proximity to the per-pixel blend.
"""
from runtimeprofiler import step as profile_step
from functools import lru_cache
import numpy as np


@lru_cache(maxsize=4096)
def strength(seed):
    import buildings as b
    value=b._hash01(seed,'surface_age_v1')
    # Keep a small maintained minority; most houses should read as lived-in.
    return .18+.30*(value/.12) if value<.12 else .48+.52*((value-.12)/.88)


def exposure(context=None,lat=None,lon=None):
    """Coarse moisture proxy from the existing climate grid, plus pole direction.

    This is an artistic deposition bias, not observed damage or simulated rain.
    Unknown locations stay neutral; no guessed coast, pollution or maintenance.
    """
    location=getattr(context,'location',None)
    if location is not None:lat,lon=location
    climate=getattr(context,'climate',0)
    if not climate and lat is not None and lon is not None:
        import climate as climate_grid
        climate=climate_grid.koppen_at(lat,lon)
    moisture=1.
    if 1<=climate<=3:moisture=1.22
    elif 4<=climate<=7:moisture=.65
    elif 8<=climate<=10:moisture=.85  # summer-dry temperate
    elif 14<=climate<=16:moisture=1.12  # temperate, no dry season
    elif 17<=climate<=28:moisture=.95
    elif 29<=climate<=30:moisture=.65
    # ENU Y points north. Pole-facing surfaces dry less readily outside tropics.
    pole=0. if lat is None else float(np.clip(lat/30.,-1.,1.))
    return moisture,pole



@profile_step('Building surface aging')
def apply(positions,colors,tris,materials,ranges):
    import buildings as b
    if not ranges or not len(positions):return colors
    response=np.ones(len(b.MATERIALS))
    for name,weight in ((b.OFFICE,.08),(b.SHOP,.12),(b.FACADE,.35)):
        response[b.MATERIALS.index(name)]=weight
    vertex_material=np.zeros(len(positions),dtype=np.int64)
    vertex_material[tris.ravel()]=np.repeat(materials,3)
    normals=np.cross(positions[tris[:,1]]-positions[tris[:,0]],
                     positions[tris[:,2]]-positions[tris[:,0]])
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
    vertex_normal=np.zeros_like(positions,dtype=float)
    vertex_normal[tris.ravel()]=np.repeat(normals,3,axis=0)
    result=colors.copy()
    for index,row in enumerate(ranges):
        start,seed,base,height=row[:4]
        moisture,pole=(row[4] if len(row)>4 and row[4] is not None else (1.,0.))
        end=ranges[index+1][0] if index+1<len(ranges) else len(positions)
        if start==end:continue
        age=strength(seed)
        h=np.clip((positions[start:end,2]-base)/max(1.,height),0.,1.)
        normal=vertex_normal[start:end]
        # Reuse this pass's height and normals; no second triangle traversal,
        # extra vertex stream, or per-frame CPU work for the roof-stain blend.
        # Alpha is unused by stock opaque PBR; only our opted-in hook reads it.
        result[start:end,3]=np.where(np.abs(normal[:,2])<=.3,np.rint(h*255),0).astype(np.uint8)
        up=np.clip(normal[:,2],0.,1.)
        shade=np.clip(normal[:,1]*pole,0.,1.)
        # Lower walls collect splashback; shallow upward faces retain deposits.
        # Shade adds damp staining, while steep roofs shed more water/debris.
        wall=.145+.165*(1-h)+.05*shade
        roof=.18+.075*up**4+.045*shade
        deposits=np.where(up>.3,roof,wall)
        deposits*=np.where(normal[:,2]<-.3,.55,1.)  # sheltered undersides
        amount=np.clip(age*moisture*deposits*response[vertex_material[start:end]],0.,.43)
        rgb=colors[start:end,:3].astype(float)
        grey=rgb.mean(axis=1,keepdims=True)
        # Sun-muted paint and warm grey dirt; bounded to preserve mapped colours.
        rgb=rgb*(1-.08*age)+grey*(.08*age)
        rgb*=1-amount[:,None]*np.array([.90,.96,1.])
        result[start:end,:3]=np.clip(np.rint(rgb),0,255).astype(np.uint8)
    return result


def uv(positions,tris):
    """Six-metre detail repeat, projected on the dominant surface plane.

    UV1 is independent of facade atlas UV0, so dirt does not repeat per window.
    Identical positions/face orientation get the same UV at every detail level.
    """
    if not len(positions):return np.empty((0,2))
    normal=np.cross(positions[tris[:,1]]-positions[tris[:,0]],positions[tris[:,2]]-positions[tris[:,0]])
    axis=np.zeros(len(positions),dtype=np.int8)
    axis[tris.ravel()]=np.repeat(np.argmax(np.abs(normal),axis=1),3)
    u=np.where(axis==0,positions[:,1],positions[:,0])
    v=np.where(axis==2,positions[:,1],positions[:,2])
    return np.column_stack((u,v))/6.


