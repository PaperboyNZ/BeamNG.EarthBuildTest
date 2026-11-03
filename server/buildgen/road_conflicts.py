"""Trim grounded building bodies clear of actual streets and sidewalk edges.

The same operation serves source-based near/far/sky planning and the final road
geometry pass. Elevated parts, tunnel portals and explicit bridge structures are
not inferred to be erroneous buildings. Source evidence and resolved identity stay
attached to clipped geometry; no structure is moved or stretched.
"""
from copy import copy
from dataclasses import replace
import logging
import math

import numpy as np
from shapely.affinity import translate
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

from .topology import Footprint, InvalidFootprint

log=logging.getLogger(__name__)
CLEARANCE=.35
ROAD_HEADROOM=5.5
WALK_HEADROOM=2.4
MIN_AREA=8.
MIN_WIDTH=1.5
MAX_ROADS=10000
MAX_PIECES=20000
MAX_VERTICES=131072
STREETS=frozenset(('motorway','trunk','primary','secondary','tertiary','residential','unclassified','living_street'))
EXEMPT=frozenset(('bridge_structure','toll_booth','ship','pier'))


def _parts(shape):
    if shape.geom_type=='Polygon':return [shape]
    return [p for p in getattr(shape,'geoms',()) if p.geom_type=='Polygon']


def _useful(shape):
    if shape.area<MIN_AREA:return False
    # Thin scraps along a street must not become implausibly narrow buildings.
    return not shape.buffer(-MIN_WIDTH/2,join_style='mitre').is_empty


def _records(chunks,roads,walks,origin):
    """Local XY surface records paired with fixed heights or draped terrain."""
    import roadmesh
    out=[];vertices=0;source_vertices=0
    def source_budget(points):
        nonlocal source_vertices
        source_vertices+=len(points)
        if source_vertices>MAX_VERTICES:raise ValueError('road source vertex budget')
    def add(shape,z=None,headroom=ROAD_HEADROOM):
        nonlocal vertices
        if shape.is_empty or not shape.is_valid:return
        for part in _parts(shape):
            vertices+=len(part.exterior.coords)+sum(len(h.coords) for h in part.interiors)
            if len(out)>=MAX_PIECES or vertices>MAX_VERTICES:raise ValueError('road geometry budget')
            out.append((translate(part,xoff=-origin[0],yoff=-origin[1]),z,headroom))
    chunks=tuple(chunks or ());roads=tuple(roads or ());walks=tuple(walks or ())
    if max(len(chunks),len(roads),len(walks))>MAX_ROADS:raise ValueError('road input budget')
    for _,spec,nodes,_ in roads:
        if spec.cls not in STREETS:continue
        points=np.asarray(nodes,float)
        source_budget(points)
        if points.ndim!=2 or points.shape[1]<2 or len(points)<2 or not np.isfinite(points).all():continue
        width=float(spec.width)
        if not math.isfinite(width) or width<=0:continue
        add(LineString(points[:,:2]).buffer(width/2,cap_style='flat',join_style='mitre',mitre_limit=2))
    physical=[]
    for chunk in chunks:
        material=str(chunk.get('m',''))
        if chunk.get('tube_only') or roadmesh.layer_of(dict(chunk,m=material))!='base':continue
        # Rails, runway decorations, sidewalk markings and furniture are not streets.
        if not (material.startswith('road_') or material in ('dirt_road','gravel_road','dirt','asphalt')):continue
        if chunk.get('poly') is not None:
            p=np.asarray(chunk['poly'],float)
            source_budget(p)
            if p.ndim==2 and p.shape[1]>=2 and len(p)>=3 and np.isfinite(p).all():add(Polygon(p[:,:2]))
        p=np.asarray(chunk.get('n',()),float)
        source_budget(p)
        if p.ndim==2 and p.shape[1]>=3 and len(p)>=2 and np.isfinite(p).all() and float(chunk.get('w',0))>0:
            physical.append(chunk)
    for (left,right,_,_,_,fixed),chunk in roadmesh.ribbon_pairs(physical):
        for i in range(len(left)-1):
            q=np.array([left[i],left[i+1],right[i+1],right[i]])
            heights=None if fixed is None else (float(min(fixed[i:i+2])),float(max(fixed[i:i+2])))
            add(Polygon(q),heights)
    import sidewalks
    for walk in walks:
        if 'corner' in walk:
            corner=walk['corner']
            p=np.concatenate((np.asarray(corner['arc']),np.asarray(corner['outer'])))
            source_budget(p)
            if p.ndim==2 and p.shape[1]>=3 and np.isfinite(p).all():
                add(Polygon(p[:,:2]),(float(p[:,2].min()),float(p[:,2].max())),WALK_HEADROOM)
            continue
        p=np.asarray(walk.get('pts',()),float);width=float(walk.get('w',2.5))
        source_budget(p)
        if p.ndim!=2 or p.shape[1]<3 or len(p)<2 or not np.isfinite(p).all() or not 0<width<20:continue
        curb,outward=sidewalks.run_geometry(p,walk.get('side',1),width)
        profile=sidewalks.profile(w=width)
        back=curb[:,:2]+outward*float(profile[:,0].max())
        for i in range(len(curb)-1):
            shape=Polygon([curb[i,:2],curb[i+1,:2],back[i+1],back[i]])
            heights=curb[i:i+2,2,None]+profile[None,:,1]
            add(shape,(float(heights.min()),float(heights.max())),WALK_HEADROOM)
    return out


def _refit(spec,fp,ground,origin,gmin,gmax):
    """Preserve appearance/inference while invalidating every shape-bound plan."""
    import buildings as b
    from . import churches, roofs
    changed=copy(spec)
    changed.footprint=fp;changed.ring=np.asarray(fp.outer,float)
    changed.roof_outline=None
    changed.diagnostics=tuple(spec.diagnostics or ())+('footprint_clipped_clear_of_street',)
    if getattr(spec,'roof_outline',None) is not None:
        from .roof_outline import fit
        fit(changed,imagery=True)
        fp=changed.footprint
    samples=np.concatenate([changed.ring,*[np.asarray(h) for h in fp.holes]])
    heights=np.asarray(ground(samples+origin),float).reshape(-1)
    if len(heights)!=len(samples) or not np.isfinite(heights).all():raise ValueError('unknown clipped building ground')
    changed.gring=heights[:len(changed.ring)]
    for field in ('facades','door','front','garage_opening','garage_access','access','stoop','sign'):setattr(changed,field,None)
    if changed.site is not None:changed.site=None
    # The compiler can draw supported roofs on the new envelope. Unsupported
    # pitched envelopes use the existing flat fallback rather than an old box.
    if changed.roof!='flat' and not roofs.supported(fp):
        changed.roof='flat';changed.pitch=0.
        if changed.inference is not None:
            changed.inference=replace(changed.inference,roof=replace(changed.inference.roof,value='flat'),roof_rise=0.)
        changed.diagnostics+=('road_clip_roof_flat_fallback',)
    if changed.church is not None:
        attrs={o.field:o.value for o in changed.evidence.observations if o.status=='observed'} if changed.evidence else {}
        attrs.update(_footprint=fp,_evidence=changed.evidence,height=spec.church.total_height,seed_id=str(changed.seed),
                     _church_family=spec.church.family)
        attrs['_church_spire']=spec.church.spire.kind if spec.church.spire is not None else 'none'
        changed.church=churches.adapt(changed,attrs,fp)
    if getattr(spec,'city',None) is not None:
        from .city import refit
        changed.city=refit(changed,spec.city)
    return changed,float(heights.min()),float(heights.max())


def filter_items(items,chunks=(),*,origin=(0.,0.),ground=None,roads=(),walks=(),diagnostics=None):
    """Return ground buildings trimmed .35m behind street/sidewalk edges.

    ``items`` have tile-local footprints; roads, chunks, walk points and the
    terrain sampler use the common global road frame. Unusable residuals are
    omitted. A split retains the largest usable component, preserving its holes.
    Elevated parts survive when their actual body clears 5.5 m above a street
    or 2.4 m above a sidewalk-only overlap. Unknown street heights are not grounds
    for inventing a collision. Budget or
    unsupported-input failures are diagnosed and retain the original items.
    """
    items=list(items);origin=np.asarray(origin[:2],float)
    notes=diagnostics if diagnostics is not None else []
    if not items:return items
    try:records=_records(chunks,roads,walks,origin)
    except (ValueError,TypeError,IndexError) as ex:
        notes.append(dict(reason='road_clip_inventory_unresolved',detail=str(ex)))
        log.warning('Building street clipping inventory unavailable: %s',ex)
        return items
    if not records:return items
    shapes=[p.buffer(CLEARANCE,join_style='mitre') for p,_,_ in records]
    deck_shapes=[p.buffer(CLEARANCE+.5,join_style='mitre') for p,_,_ in records]
    tree=STRtree(shapes);out=[];prepared=[];points=[]
    # One bounded terrain batch for all candidate surface intersections. Road
    # ribbon cells must not turn into thousands of one-point DEM queries.
    for item in items:
        spec,gmin,gmax=item
        if spec.portal or spec.cls in EXEMPT:
            prepared.append((item,None,(),shapes));continue
        fp=getattr(spec,'roof_outline',None) or spec.footprint
        if fp is None:
            try:fp=Footprint(tuple(map(tuple,b_drawn_ring(spec))))
            except InvalidFootprint:prepared.append((item,None,(),shapes));continue
        shape=fp.shape();candidates=[]
        masks=deck_shapes if spec.deck else shapes
        query=shape.buffer(.5) if spec.deck else shape
        for i in tree.query(query):
            i=int(i);intersection=shape.intersection(masks[i])
            if intersection.area<1e-5:continue
            z=records[i][1];probe=None
            if z is None:
                if len(points)>=MAX_PIECES:
                    notes.append(dict(reason='road_clip_query_budget'))
                    log.warning('Building street clipping query budget exceeded')
                    return items
                centre=intersection.representative_point();probe=len(points)
                points.append((centre.x+origin[0],centre.y+origin[1]))
            candidates.append((i,z,probe))
        prepared.append((item,shape,candidates,masks))
    values=np.full(len(points),np.nan)
    if points and ground is not None:
        try:
            sampled=np.asarray(ground(np.asarray(points)),float).reshape(-1)
            if len(sampled)==len(points):values=sampled
        except (ValueError,TypeError,IndexError):pass
    for item,shape,candidates,masks in prepared:
        if shape is None:
            out.append(item);continue
        spec,gmin,gmax=item;blocked=[]
        minimum=float(spec.min_h or 0.)
        base=float(gmax)+minimum
        bottom=float(gmin)-.5 if minimum<=.5 else base
        top=base+float(spec.height or 0.)
        for i,z,probe in candidates:
            if z is None:
                if not np.isfinite(values[probe]):continue
                z=(float(values[probe]),float(values[probe]))
            # A small mapped min_height is not enough to fit traffic below.
            # Preserve genuinely elevated parts using their body bottom, never
            # invent another lift. Walk-only canopies need pedestrian headroom.
            if bottom>=z[1]+records[i][2]-1e-6 or z[0]>top+.1:continue
            blocked.append(masks[i])
        if not blocked:
            out.append(item);continue
        remainder=shape.difference(unary_union(blocked))
        pieces=sorted((p for p in _parts(remainder) if p.is_valid and _useful(p)),key=lambda p:(-p.area,p.bounds))
        source=str(getattr(getattr(spec,'evidence',None),'source_id','') or spec.seed)
        if not pieces:
            notes.append(dict(source=source,reason='road_clip_no_usable_footprint',original_m2=round(shape.area,3)))
            log.debug('Building %s omitted: street consumes usable footprint',source)
            continue
        chosen=pieces[0]
        try:
            fitted=Footprint(tuple(chosen.exterior.coords)[:-1],tuple(tuple(h.coords)[:-1] for h in chosen.interiors))
            if ground is None:raise ValueError('missing clipped building ground')
            new=_refit(spec,fitted,ground,origin,gmin,gmax)
        except (ValueError,TypeError,IndexError) as ex:
            notes.append(dict(source=source,reason='road_clip_fit_unresolved',detail=str(ex)))
            continue
        out.append(new)
        notes.append(dict(source=source,reason='footprint_clipped_clear_of_street',original_m2=round(shape.area,3),
                          retained_m2=round(chosen.area,3),discarded_components=max(0,len(pieces)-1)))
    return out


def b_drawn_ring(spec):
    import buildings as b
    return b.drawn_ring(spec)


def source_items(items,lines,ground):
    """Shared source-width guard before near, far and skyline publication."""
    from types import SimpleNamespace
    rows=[]
    for n,line in enumerate(lines):
        points,width,cls,_urban=line
        rows.append((str(n),SimpleNamespace(cls=cls,width=2*width),np.c_[points,np.zeros(len(points))],None))
    return filter_items(items,ground=ground,roads=rows)
