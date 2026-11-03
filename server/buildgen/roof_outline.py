"""Interpret imagery outlines as roof extents, with fitted walls beneath them.

Only the existing ML/imagery route (or an explicit roof-outline input) uses this
assumption. Surveyed/mapped wall inputs and specialist assemblies are preserved.
"""
import numpy as np
from .topology import Footprint


def fit(spec,imagery=False):
    if not imagery or getattr(spec,'roof_outline',None) is not None:return
    if (spec.inference is None or spec.footprint is None or spec.roof=='flat'
            or spec.church or spec.terminal or spec.city or spec.deck):return
    if spec.inference.roof_solver == 'fast' and not spec.footprint.is_rectangle():
        # A flush low-tier silhouette keeps source walls/holes intact without
        # adding offset/buffer work for newly pitched complex imagery outlines.
        spec.diagnostics=tuple(spec.diagnostics or ())+('fast_roof_flush_outline',)
        return
    import buildings as b
    from . import roof_edges,roofs
    t=roof_edges.treatment(spec,outline=True)
    centre,u,hl,hw=b.oriented_box(np.asarray(spec.footprint.outer));v=np.array([-u[1],u[0]])
    end=t.eave if spec.roof=='hipped' and roofs.variant(spec) in ('standard','mansard','flared_hip') else t.rake
    if min(hl-end,hw-t.eave)<.75:
        spec.diagnostics=tuple(spec.diagnostics or ())+('roof_outline_narrow_flush_fallback',)
        return
    if spec.footprint.is_rectangle():
        wall=Footprint(tuple(tuple(centre+u*s*(hl-end)+v*r*(hw-t.eave))
                             for s,r in ((-1,-1),(1,-1),(1,1),(-1,1))))
    else:
        from .roof_domains import offset
        wall=offset(spec.footprint,spec.roof,roofs.variant(spec),t.eave,t.rake,inward=True)
        if wall is None or wall==spec.footprint:
            spec.diagnostics=tuple(spec.diagnostics or ())+('roof_outline_narrow_flush_fallback',)
            return
    spec.roof_outline=spec.footprint
    spec.footprint=wall;spec.ring=np.asarray(wall.outer,np.float64)
    spec.diagnostics=tuple(spec.diagnostics or ())+('imagery_roof_outline_inset_walls',)
    spec.facades=None


def resample_ground(items,ground):
    selected=[(i,s) for i,(s,_,_) in enumerate(items) if getattr(s,'roof_outline',None) is not None]
    if not selected:return items
    points=np.concatenate([s.ring for _,s in selected])
    heights=np.asarray(ground(points),float).reshape(-1)
    if len(heights)!=len(points):raise ValueError('inset wall ground sample count')
    result=list(items);offset=0;invalid=set()
    for i,s in selected:
        values=heights[offset:offset+len(s.ring)];offset+=len(s.ring)
        if not np.isfinite(values).all():invalid.add(i);continue
        s.gring=values.copy();result[i]=(s,float(values.min()),float(values.max()))
    return [item for i,item in enumerate(result) if i not in invalid]
