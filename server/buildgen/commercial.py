"""Bounded procedural commercial elevations; no inferred parcels or truck yards.

Widths/counts derive from the available wall. Retail/service work uses the
resolved frontage; bounded office windows also use secondary outer elevations.
All extra entries are closed facade panels, never traversable portals.
"""
from dataclasses import replace
import math

import numpy as np

from . import materials, programme as programmes, commercial_forms

# Existing site-layout ownership stays limited to its original three adapters.
IDS = {'ci_logistics_hall', 'ci_supermarket', 'ci_trade_units'}
FACADE_IDS = IDS | {'ci_strip_shops'} | commercial_forms.IDS
MAX_GROUPS = 16
MAX_OPENINGS = 64
MAX_OBSTACLES = 64
MARGIN = .65
MAX_OFFICE_FLOORS = 12
MAX_ARCHITECTURE_OPENINGS = 256


def kind(spec):
    return spec.inference.selection.preset.id if spec.inference else ''


def office_profile(spec):
    """Material-compatible composition, never a claim about construction era.

    Taller sources keep the established renderer. No profile changes source
    floor count, height, roof, material, outline or occupancy.
    """
    if kind(spec) != 'office' or not 1 <= spec.floors <= MAX_OFFICE_FLOORS \
            or spec.windows is False or spec.plain or (getattr(spec,'terminal',None) or {}).get('accepted'):
        return ''
    material = spec.inference.facade.value
    return 'office_curtain' if material == 'glass' else 'office_ribbon' if material in ('concrete','metal') else 'office_punched'


def derive_programme(spec):
    """Optional shared composition; source validation failures keep old geometry."""
    if not (office_profile(spec) or kind(spec) in FACADE_IDS or (getattr(spec,'terminal',None) or {}).get('accepted')):
        return None
    try:
        return programmes.derive(spec)
    except ValueError:
        return False


def front_length(spec):
    """Full measured frontage, without changing its accepted source-edge door."""
    if spec.front is None:
        return 0.
    shared=derive_programme(spec)
    if shared:
        return shared.run(0,spec.front).length
    return math.dist(spec.ring[spec.front],spec.ring[(spec.front+1)%len(spec.ring)])


def can_public_entry(spec,programme=None):
    """One fit gate for the wide visual entry, threshold and stock-door prop."""
    if kind(spec)!='ci_supermarket' or not spec.door or (spec.min_h or 0.)>.5:
        return False
    shared=derive_programme(spec) if programme is None else programme
    if shared is False:return False
    if shared:
        run=shared.run(0,spec.door[0])
        anchor=run.member(spec.door[0]).start+spec.door[1]
        length=run.length
    else:
        length=math.dist(spec.ring[spec.door[0]],spec.ring[(spec.door[0]+1)%len(spec.ring)])
        anchor=spec.door[1]
    return (anchor-1.8>=MARGIN and anchor+1.8<=length-MARGIN
            and min(spec.floor_h-.35,spec.height-.35)>=2.25)


def _source_position(spec,shared,edge,position):
    """Convert a merged-run distance back to original ground-sample coordinates."""
    if shared:
        run=shared.run(0,edge)
        for member in run.members:
            if position<=member.end+1e-9:
                return member.edge,max(0.,position-member.start)
        return run.members[-1].edge,run.members[-1].end-run.members[-1].start
    return edge,position


def _front(spec,boundary,edge,shared):
    return not boundary and spec.front is not None and (
        shared.run(0,edge).member(spec.front) is not None if shared else edge==spec.front)


def _office_parameters(spec,shared):
    profile=office_profile(spec)
    u=shared.seed('structure',('office-grid',profile))
    if profile=='office_punched':return 3.0+.7*u,1.2+.25*u,.8,min(3.1,spec.floor_h-.5),1
    if profile=='office_ribbon':return 7.+2.*u,6.4+2.*u,.95,min(2.85,spec.floor_h-.55),5
    return 3.8+.6*u,3.56+.6*u,.18,spec.floor_h-.28,3


def office_grid(spec,run,shared):
    """One structural lattice for every floor and collinear member of a run."""
    bay,width,_,_,_= _office_parameters(spec,shared)
    lo,hi=MARGIN,run.length-MARGIN
    if office_profile(spec)=='office_curtain' and run.length>=12.:
        end_zone=min(4.5,run.length*.15)
        if shared.seed('structure','office-opaque-end')<.5:lo+=end_zone
        else:hi-=end_zone
    count=max(1,min(MAX_GROUPS,MAX_OPENINGS//max(1,len(shared.datums))))
    grid=programmes.fit_grid(max(0.,hi-lo),bay,width,margin=0.,gap=.24,max_bays=count,
                            mode='centered',reserved_mode='omit')
    return programmes.BayGrid(run.length,tuple(programmes.Bay(b.index,b.left+lo,b.right+lo) for b in grid.bays),grid.diagnostics)


def glazing_segments(spec,elevation,opening,shared,cache):
    """Keep mullion phase through entrance fragments of one structural bay."""
    if office_profile(spec) and shared and opening.kind in ('window','office'):
        run=shared.run(elevation.boundary,elevation.edge)
        if run.index not in cache:cache[run.index]=office_grid(spec,run,shared)
        bay=next((b for b in cache[run.index].bays if b.index==opening.variant),None)
        if bay is not None:
            result=[]
            for col in range(opening.columns):
                a=bay.left+(bay.right-bay.left)*col/opening.columns
                c=bay.left+(bay.right-bay.left)*(col+1)/opening.columns
                lo,hi=max(a,opening.left),min(c,opening.right)
                if hi-lo>1e-8:result.append((lo,hi,col,col>0 and abs(lo-a)<1e-8))
            return tuple(result)
    return tuple((opening.left+(opening.right-opening.left)*i/opening.columns,
                  opening.left+(opening.right-opening.left)*(i+1)/opening.columns,i,i>0)
                 for i in range(opening.columns))


def architecture_diagnostics(spec):
    if kind(spec) in commercial_forms.IDS:
        return ('ci_composition:'+kind(spec), 'ci_style:footprint_and_neighbourhood_prior', 'ci_occupancy:unchanged')
    profile = office_profile(spec)
    if profile:
        return ('ci_composition:'+profile, 'ci_style:weak_material_compatible_prior', 'ci_era:unknown')
    if kind(spec) == 'office':
        return ('ci_composition:existing_office_fallback', 'ci_era:unknown')
    if kind(spec) == 'ci_strip_shops':
        return ('ci_composition:strip_frontage', 'ci_tenancy:inferred_closed_frontage_only')
    return ()


def detail_family(spec):
    return office_profile(spec) or (kind(spec) if kind(spec) in FACADE_IDS else '')


def _free_spans(left, right, bottom, top, reserved, gap=.38):
    """Remaining complete wall intervals, including the actual entry reservation."""
    spans=[]
    for op in sorted(reserved,key=lambda o:o.left):
        if op.bottom >= top+gap or op.top <= bottom-gap:
            continue
        if op.left-gap > left:
            spans.append((left,min(right,op.left-gap)))
        left=max(left,op.right+gap)
        if left >= right:
            break
    if left < right:
        spans.append((left,right))
    return tuple((a,c) for a,c in spans if c-a >= .8)


def office_openings(spec,boundary,edge,length,reserved,budget,shared):
    """Bounded punched, ribbon or curtain groups fitted to one elevation."""
    from .facades import Opening
    profile=office_profile(spec)
    if not profile or not shared:
        return None
    result=list(reserved)
    role=profile+('_public' if spec.door and _front(spec,boundary,edge,shared) else '_secondary')
    if shared.run(boundary,edge).party_wall:
        return tuple(result),'party_wall'
    # Courtyard shapes/voids remain intact, but this slice does not infer their
    # elevation programme or access. The outer-wall fitter must never sample a
    # courtyard opening against an unrelated outer edge.
    if boundary or length < 2*MARGIN+1.:
        return tuple(result),role
    _,_,sill,head,columns=_office_parameters(spec,shared)
    if head-sill < .65:
        return tuple(result),role
    # A finite run stays a plausible module width on giant source elevations.
    limit=min(MAX_OPENINGS,max(0,budget))
    if limit<=len(result):
        return tuple(result),role
    run=shared.run(boundary,edge)
    grid=office_grid(spec,run,shared)
    for datum in shared.datums:
        z0,z1=datum.bottom+sill,min(datum.bottom+head,datum.top-.2)
        for bay in grid.bays:
            for a,c in _free_spans(bay.left,bay.right,z0,z1,reserved):
                if len(result)>=limit:
                    break
                op=Opening('window' if profile=='office_punched' else 'office',datum.index,
                           a,c,z0,min(z1,spec.height-.2),
                           min(columns,max(1,int((bay.right-bay.left)/1.15))),bay.index)
                if op.top-op.bottom>=.65 and not any(op.overlaps(other,.32) for other in result):
                    result.append(op)
    return tuple(sorted(result,key=lambda o:(o.floor,o.left))),role


def bands(spec,elevation,programme=None):
    """Shallow wall-plane subdivisions, clipped around all accepted apertures.

    These add no awning, projecting cornice, site support or collision volume.
    Near and lite retain identical major composition and source envelope.
    """
    profile=office_profile(spec)
    if elevation.boundary or not elevation.openings:
        return ()
    margin=MARGIN
    left,right=margin,elevation.length-margin
    if right-left<1.:
        return ()
    if profile:
        shared=programme if programme is not None else derive_programme(spec)
        if not shared:return ()
        result=[]
        for datum in shared.datums:
            top=min(spec.height-.04,datum.top-.08)
            thickness=.14 if profile=='office_punched' else .28 if profile=='office_ribbon' else .08
            result.append((left,right,max(0.,top-thickness),top))
        return tuple(result)
    if kind(spec)=='ci_strip_shops' and elevation.role=='strip_public':
        top=min(spec.floor_h-.3,3.65,spec.height-.2)
        return ((left,right,max(3.,top-.5),top),) if top>3.1 else ()
    return ()


def groups(spec, length):
    """Fit complete trade frontages without stretching doors or fractional units."""
    width = 7. + 3. * materials.unit(spec.seed, 'ci-unit-width')
    n = min(MAX_GROUPS, max(0, int((length-2*MARGIN)/width)))
    if not n:
        return ()
    # Preserve plausible module sizes on exceptionally long walls; residual wall
    # stays blank rather than stretching sixteen units across a kilometre.
    span = min(length-2*MARGIN, n*(width+1.5))
    start = MARGIN+(length-2*MARGIN-span) * (.25 + .5*materials.unit(spec.seed, 'ci-run-position'))
    grid=programmes.fit_grid(span,(span/n)*(1-1e-12),span/n,margin=0.,gap=0.,max_bays=n,allow_single=False)
    # Keep the function/threshold coordinates bit-for-bit while using the shared
    # bounded module count. New structure/vocabulary channels never move access.
    return tuple((start+b.index*span/n,start+(b.index+1)*span/n) for b in grid.bays)


def entry_position(spec, length):
    if kind(spec) in commercial_forms.IDS:
        return commercial_forms.entry_position(spec,length)
    k = kind(spec)
    if k not in FACADE_IDS or length < 5.:
        return None
    u = materials.unit(spec.seed, 'ci-entry-side')
    if k == 'ci_trade_units':
        spans = groups(spec, length)
        if spans:
            lo, hi = spans[0 if u < .5 else -1]
            return lo+1.25
    if k == 'ci_logistics_hall':
        return min(length*.25, 3.5) if u < .5 else length-min(length*.25, 3.5)
    return max(2.25,min(length-2.25,length*(.3+.4*u)))


def entry_width(spec, fallback=1.4):
    if can_public_entry(spec):return 3.6
    return fallback


def openings(spec, boundary, edge, length, base, high, reserved, budget=MAX_OPENINGS,programme=None):
    """Return a fitted facade and role, or None to use the established renderer."""
    k = kind(spec)
    shared=programme if programme is not None else derive_programme(spec)
    office=office_openings(spec,boundary,edge,length,reserved,budget,shared)
    if office is not None:
        return office
    if k not in FACADE_IDS:
        return None
    if shared is False:return None
    if shared and shared.run(boundary,edge).party_wall:return tuple(reserved),'party_wall'
    if k in commercial_forms.IDS:
        return commercial_forms.openings(spec,boundary,edge,length,base,high,reserved,budget,shared)
    from .facades import Opening
    import buildings as b
    result = list(reserved)
    if not _front(spec,boundary,edge,shared) or not spec.door or (spec.min_h or 0.) > .5:
        return tuple(result), 'blank'
    head = min(spec.floor_h-.35, spec.height-.35)
    anchor = spec.door[1]+(shared.run(0,edge).member(spec.door[0]).start if shared else 0.)

    def add(kind_, left, right, bottom, top, columns=1):
        op = Opening(kind_, 0, float(left), float(right), float(bottom), float(top), columns)
        if len(result) >= min(MAX_OPENINGS,budget) or left < MARGIN or right > length-MARGIN \
                or right-left < .6 or top-bottom < .65 or top > spec.height-.2:
            return
        if any(op.overlaps(other, .32) for other in result):
            return
        result.append(op)

    def service(lo, hi):
        def at(position):
            source_edge,along=_source_position(spec,shared,edge,position)
            return b.door_ground(spec,source_edge,along,high)
        z = max(at(lo),at(hi))-base+.06
        if head-z >= 2.6:
            add('service',lo,hi,z,min(z+3.5,head))

    if k == 'ci_strip_shops':
        door=next((o for o in reserved if o.kind=='door'),None)
        z=door.bottom if door else 0.
        # Repeat opaque-separated display groups. Only the actual reserved door
        # is an entrance; tenancy, extra public routes and interiors are unknown.
        for lo,hi in groups(spec,length):
            for a,c in _free_spans(lo+.3,hi-.3,z+.15,min(z+2.85,head),reserved):
                add('storefront',a,c,z+.15,min(z+2.85,head),min(4,max(1,int((c-a)/1.4))))
        return tuple(sorted(result,key=lambda o:o.left)), 'strip_public'

    if k == 'ci_supermarket':
        if can_public_entry(spec,programme=shared):
            result = [replace(o,kind='public_entry',left=anchor-1.6,right=anchor+1.6,
                              top=min(o.bottom+2.7,head),columns=2) if o.kind=='door' else o for o in result]
        # Concentrate display glazing around the entrance. Side/rear walls are
        # opaque, and mapped upper floors do not acquire fictitious shopfronts.
        span = min(length-2*MARGIN, 12.+12.*materials.unit(spec.seed,'ci-shop-span'))
        lo, hi = max(MARGIN,anchor-span*.5), min(length-MARGIN,anchor+span*.5)
        bay = 2.8+materials.unit(spec.seed,'ci-shop-bay')
        door = next((o for o in reserved if o.kind == 'door'),None)
        z = door.bottom if door else 0.
        # Fit the remaining intervals around the actual entrance, rather than
        # deleting grid windows and leaving oversized gaps beside the doors.
        for a,c in ((lo,anchor-2.),(anchor+2.,hi)):
            if c-a < 1.4:
                continue
            n=min(6,max(1,math.ceil((c-a)/bay)))
            grid=programmes.fit_grid(c-a,((c-a)/n)*(1-1e-12),max(.1,(c-a)/n-.36),
                                    margin=0.,gap=.36,max_bays=n,allow_single=False)
            for module in grid.bays:
                add('storefront',a+module.left,a+module.right,z+.15,min(z+2.9,head),2)
        return tuple(sorted(result,key=lambda o:o.left)), 'public'
    if k == 'ci_trade_units':
        for lo,hi in groups(spec,length):
            centre = lo+1.25
            source_edge,along=_source_position(spec,shared,edge,centre)
            z = b.door_ground(spec,source_edge,along,high)-base+.06
            add('staff_door',centre-.625,centre+.625,z,min(z+2.25,head))
            service(lo+2.6,min(lo+6.2,hi-.5))
            if head >= 4.8:
                add('office',lo+.5,hi-.5,head-1.15,head,2)
        return tuple(sorted(result,key=lambda o:o.left)), 'trade'
    # Warehouse staff zone follows its entry, leaving the rest for service bays.
    staff = min(12.,max(6.,length*.18))
    left_staff = anchor < length/2
    lo,hi = (MARGIN,staff) if left_staff else (length-staff,length-MARGIN)
    for a,c in ((lo,min(hi,anchor-.95)),(max(lo,anchor+.95),hi)):
        if c-a < 1.2:
            continue
        n=min(3,max(1,int((c-a)/2.8)))
        w=min(1.8,(c-a)/n-.2)
        for i in range(n):
            centre=a+(c-a)*(i+.5)/n
            add('office',centre-w/2,centre+w/2,1.,min(2.6,head))
    lo,hi = (staff+.6,length-MARGIN) if left_staff else (MARGIN,length-staff-.6)
    bay = 5.5+2.*materials.unit(spec.seed,'ci-service-bay')
    grid=programmes.fit_grid(max(0.,hi-lo),bay,3.2,margin=0.,gap=0.,max_bays=MAX_GROUPS,
                            mode='centered',allow_single=False)
    for module in grid.bays:
        service(lo+module.left,lo+module.right)
    return tuple(sorted(result,key=lambda o:o.left)), 'staff_service'


def resolve(items, lines, ground, x0, y0):
    """Validate optional openings in one bounded terrain batch and spatial index.

    We do not project yards/aprons onto unknown parcels. Only small staff-door
    thresholds become surfaces. Road corridors and other buildings stay clear.
    """
    from shapely import STRtree
    from shapely.geometry import Polygon, LineString
    from . import facades, access
    import buildings as b
    targets = [(s,lo,hi) for s,lo,hi in items if (kind(s) in FACADE_IDS and s.door or office_profile(s))
               and derive_programme(s) is not False
               and not (ground is None and s.facades is not None)]
    if not targets:
        return
    for spec,_,_ in targets:
        if spec.access is not None:
            spec.access = replace(spec.access,solids=tuple(s for s in spec.access.solids if s.kind!='ci_threshold'))
    shapes = [s.footprint.shape() for s,_,_ in items
              if s.footprint is not None and (s.min_h or 0.) <= .5]
    shapes.extend(LineString(np.asarray(line[0])[:,:2]-[x0,y0]).buffer(float(line[1])+.25)
                  for line in lines if len(line[0]) >= 2)
    # Existing paths/steps are reservations too: extra staff thresholds cannot
    # overlap the shared primary entrance or a neighbour's accepted access.
    structural_count = len(shapes)
    shapes.extend(Polygon([p[:2] for p in solid.top]) for s,_,_ in items if s.access
                  for solid in s.access.solids)
    tree = STRtree(shapes)
    samples, pending = [], []
    for spec,low,high in targets:
        layout = facades.plan(spec,low,high)
        shared=derive_programme(spec)
        reservations={}
        for elevation in layout.elevations:
            for op in elevation.openings:
                if op.kind not in ('service','staff_door','office','storefront','window'):
                    continue
                # A narrow exterior reservation suppresses hidden/party openings.
                depth = .5 if op.kind == 'staff_door' else .35
                # Repeated storeys share an exterior footprint and ground batch;
                # fitting the same bay again must not multiply GEOS/terrain work.
                reservation=(elevation.boundary,elevation.edge,op.left,op.right,depth,
                             op.kind in ('service','staff_door'))
                if reservation not in reservations:
                    if shared:
                        run=shared.run(elevation.boundary,elevation.edge)
                        tangent=(np.asarray(run.end)-run.start)/run.length
                        origin=np.asarray(run.start)+tangent*op.left
                        normal=np.array([tangent[1],-tangent[0]])
                    else:
                        origin,tangent,normal = access.basis(spec,elevation.edge,op.left)
                    width = op.right-op.left
                    q = [origin+tangent*t+normal*d for d,t in
                         ((.01,0.),(.01,width),(depth,width),(depth,0.))]
                    polygon = Polygon(q)
                    hits = tree.query(polygon)
                    clear = len(hits) <= MAX_OBSTACLES and all(
                        polygon.intersection(shapes[int(i)]).area < 1e-7 for i in hits
                        if int(i)<structural_count or op.kind in ('service','staff_door'))
                    pts = [origin+tangent*t+normal*d for d in (0.,depth) for t in (0.,width/2,width)]
                    off = len(samples)
                    samples.extend(pts)
                    reservations[reservation]=(clear,off)
                clear,off=reservations[reservation]
                pending.append((spec,low,high,elevation.boundary,elevation.edge,op,clear,off,depth))
        spec.facades = layout
    heights = np.full(len(samples),np.nan)
    if ground is not None and samples:
        heights[:] = np.asarray(ground(np.asarray(samples)+[x0,y0])).reshape(-1)
    replacements, notes, thresholds = {}, {}, {}
    for spec,low,high,boundary,edge,op,clear,off,depth in pending:
        key = id(spec)
        z = heights[off:off+6]
        change = op
        reason = None
        base = b.base_z(spec,low,high)+(spec.min_h or 0.)
        if not clear:
            reason = 'ci_opening_omitted_obstruction'
        elif op.kind in ('service','staff_door'):
            if not np.isfinite(z).all():
                reason = 'ci_opening_omitted_missing_terrain'
            elif np.ptp(z[:3]) > .15 or np.max(np.abs(z[3:]-z[:3])) > .15 \
                    or (op.kind=='staff_door' and np.ptp(z) > .09):
                reason = 'ci_opening_omitted_grade'
            else:
                bottom = float(z.max())+.06-base
                top = min(bottom+(op.top-op.bottom),spec.height-.35,spec.floor_h-.35)
                if top-bottom < (2.6 if op.kind=='service' else 2.15):
                    reason = 'ci_opening_omitted_headroom'
                else:
                    change = replace(op,bottom=bottom,top=top)
                    # Reject vertical conflicts after moving to sampled ground.
                    elevation = next(e for e in spec.facades.elevations if e.boundary==0 and e.edge==edge)
                    if any(change.overlaps(other,.25) for other in elevation.openings if other is not op):
                        reason = 'ci_opening_omitted_ground_conflict'
                    elif op.kind == 'staff_door' and spec.access is not None:
                        datum = bottom+base
                        solid = access.patch(spec,edge,(op.left+op.right)/2,op.right-op.left,
                                             0.,depth,(datum,datum-.01,datum-.01,datum),float(z.min())-.1,'ci_threshold')
                        thresholds.setdefault(key,[]).append(solid)
        elif np.isfinite(z[:3]).all() and z[:3].max()+.05 > base+op.bottom:
            reason = 'ci_glazing_omitted_ground'
        if reason:
            notes.setdefault(key,set()).add(reason)
            if reason=='ci_opening_omitted_obstruction':
                notes[key].add(f'ci_obstruction_run:{boundary}:{edge}')
            change = None
        replacements[(key,boundary,edge,op)] = change
    for spec,_,_ in targets:
        key = id(spec)
        elevations = tuple(replace(e,openings=tuple(new for op in e.openings
            if (new := replacements.get((key,e.boundary,e.edge,op),op)) is not None)) for e in spec.facades.elevations)
        spec.facades = replace(spec.facades,elevations=elevations,
                               diagnostics=tuple(sorted(set(spec.facades.diagnostics)|notes.get(key,set()))))
        if thresholds.get(key):
            spec.access = replace(spec.access,solids=spec.access.solids+tuple(thresholds[key]))
