"""Stable, bounded surface aging shared by shell, lite and detailed buildings.

No geometry, material variants, per-building textures or collision changes.
The affine height gradient interpolates identically across different wall LODs.
Fine rain streaks and mottling come from one shared material detail map.
"""
from functools import lru_cache
import numpy as np


@lru_cache(maxsize=4096)
def strength(seed):
    import buildings as b
    value=b._hash01(seed,'surface_age_v1')
    # A few recently maintained properties, mostly lived-in, some strongly aged.
    return .06+.26*(value/.18) if value<.18 else .32+.68*((value-.18)/.82)


def apply(positions,colors,tris,materials,ranges):
    import buildings as b
    if not ranges or not len(positions):return colors
    response=np.ones(len(b.MATERIALS))
    for name,weight in ((b.OFFICE,.08),(b.SHOP,.12),(b.FACADE,.35)):
        response[b.MATERIALS.index(name)]=weight
    vertex_material=np.zeros(len(positions),dtype=np.int64)
    vertex_material[tris.ravel()]=np.repeat(materials,3)
    result=colors.copy()
    for index,(start,seed,base,height) in enumerate(ranges):
        end=ranges[index+1][0] if index+1<len(ranges) else len(positions)
        if start==end:continue
        age=strength(seed)
        h=np.clip((positions[start:end,2]-base)/max(1.,height),0.,1.)
        amount=age*(.12+.16*(1-h))*response[vertex_material[start:end]]
        rgb=colors[start:end,:3].astype(float)
        grey=rgb.mean(axis=1,keepdims=True)
        # Sun-muted paint and warm grey dirt; bounded to preserve mapped colours.
        rgb=rgb*(1-.10*age)+grey*(.10*age)
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
