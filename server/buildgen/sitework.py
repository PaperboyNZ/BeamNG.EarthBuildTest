"""Bounded frontage paths and planted/gravel margins, not inferred land parcels.

See docs/BUILDING_DETAIL_ENGINEERING.md for references and modeling assumptions.
All terrain is sampled by access.resolve's single batch. Difficult grades remain
unresolved instead of generating retaining walls or changing downloaded terrain.
"""
from dataclasses import dataclass
import math
import os
import numpy as np

WIDTH = 1.2
MARGIN = .24
CROSSFALL = .015
MAX_GRADE = .05
MAX_FILL = .15
MAX_LENGTH = 12.
MAX_MARGIN_PATCHES = 12


@dataclass(frozen=True, slots=True)
class Route:
    stations: tuple
    points: tuple
    width: float = WIDTH
    margins: tuple = ((MARGIN,'gravel_margin'),(MARGIN,'gravel_margin'))


def candidate(spec, goal):
    from .access import basis
    if os.environ.get('BNE_BUILDING_PATHS','auto')=='off' or goal is None or spec.inference.use.value not in ('residential','commercial','civic','mixed','industrial'):
        return None
    origin, tangent, normal = basis(spec,*spec.door)
    goal = np.asarray(goal)
    reach = round(float((goal-origin) @ normal),6)
    # Only straight frontage links; a separate site solver is needed for turns.
    if not 1.2 <= reach <= MAX_LENGTH or abs(float((goal-origin) @ tangent)) > .25:
        return None
    stations = np.linspace(0.,reach,max(3,math.ceil(reach/.6)+1))
    from . import landscaping,commercial
    width=min(landscaping.treatment(spec).width,commercial.entry_width(spec))
    margins=landscaping.margins(spec)
    offsets = (-width/2-margins[0][0],-width/2,0.,width/2,width/2+margins[1][0])
    points = [origin+normal*s+tangent*t for s in stations for t in offsets]
    return Route(tuple(stations),tuple(tuple(map(float,p)) for p in points),width,margins)


def build(spec, route, terrain, solids, clear):
    from .access import Solid, basis, SURFACE_LIFT
    if route is None:
        return (),(),('front_path_unresolved_route',)
    width=route.width
    def fits_site(solid):
        from shapely.geometry import Polygon
        from sitegen.surfaces import contains_known_site
        shape=Polygon([p[:2] for p in solid.top])
        return contains_known_site(spec, shape)
    if not np.isfinite(terrain).all():
        return (),(),('front_path_omitted_missing_terrain',)
    entry = [s for s in solids if s.kind in ('threshold','step')]
    if not entry:
        return (),(),('front_path_omitted_no_landing',)
    last = entry[-1]
    origin, tangent, normal = basis(spec,*spec.door)
    start = float((np.asarray(last.top[1][:2])-origin) @ normal)
    end = route.stations[-1]
    if end-start < .6:
        return (),(),('front_path_omitted_short_frontage',)
    stations = np.array(sorted({start,min(end,start+1.2),*[s for s in route.stations if s>start+1e-7]}))
    source = np.asarray(terrain).reshape(-1,5)
    ground = np.column_stack([np.interp(stations,route.stations,source[:,i]) for i in range(5)])
    # One planar cross-section per station. Grade relative to actual sampled
    # ground, then reject excessive fill rather than pretending to regrade it.
    centres = ground[:,1:4].max(axis=1)+SURFACE_LIFT
    half_fall = CROSSFALL*width/2
    heights = np.column_stack((centres-half_fall,centres+half_fall))
    if last.kind=='threshold':
        connection=np.array([last.top[1][2],last.top[2][2]])
        # Develop the crossfall over a short transition, not a twisted abrupt
        # wedge between the level landing and the first sampling station.
        target=np.column_stack((ground[:,1:4].max(axis=1)+.04-half_fall,
                                ground[:,1:4].max(axis=1)+.04+half_fall))
        blend=np.minimum(1.,(stations-start)/1.2)[:,None]
        heights=connection*(1.-blend)+target*blend
    else:
        # The stair's final riser lands on the independently sampled path.
        rise = last.top[1][2]-float(heights[0].max())
        if not .04 <= rise <= .2:
            return (),(),('front_path_omitted_stair_connection',)
    fill = heights-ground[:,[1,3]]
    grades = np.diff(heights,axis=0)/np.diff(stations)[:,None]
    if np.any(fill < .005) or np.any(fill > MAX_FILL) or np.any(np.abs(grades)>MAX_GRADE+1e-8):
        return (),(),('front_path_omitted_grading',)
    if last.kind=='threshold' and np.any(grades[0] > .005):
        return (),(),('front_path_omitted_adverse_fall',)
    # Sampling density must not become mesh density. Remove a station only if
    # BOTH paved edges and all five ground samples lie on the same interpolant.
    # This preserves grade/clearance checks while keeping flat yards inexpensive.
    values=np.column_stack((heights,ground))
    keep=[]
    for i in range(len(stations)):
        keep.append(i)
        while len(keep)>=3:
            a,m,c=keep[-3:]
            t=(stations[m]-stations[a])/(stations[c]-stations[a])
            if np.max(np.abs(values[m]-(values[a]*(1-t)+values[c]*t)))>1e-6:
                break
            keep.pop(-2)
    stations,heights,ground=stations[keep],heights[keep],ground[keep]
    paths, margins = [],[]
    paved_count=0
    for i,(s0,s1) in enumerate(zip(stations,stations[1:])):
        def point(s,t,z):
            p=origin+normal*s+tangent*t
            return (float(p[0]),float(p[1]),float(z))
        top=(point(s0,-width/2,heights[i,0]),point(s1,-width/2,heights[i+1,0]),
             point(s1,width/2,heights[i+1,1]),point(s0,width/2,heights[i,1]))
        solid=Solid('path',top,float(min(ground[i:i+2,1:4].min(),min(p[2] for p in top))-.1))
        if not fits_site(solid) or not clear(solid) or any(_overlap(solid,s) for s in solids if s.kind=='apron'):
            return (),(),('front_path_omitted_obstruction',)
        paths.append(solid)
        for side,cols,margin_data in zip((-1,1),((0,1),(3,4)),route.margins):
            margin_width,kind=margin_data
            a,c=sorted((side*width/2,side*(width/2+margin_width)))
            j,k=cols
            band_heights=ground[i:i+2,[j,k]]+.012
            if kind=='paved_margin':
                # Extend the path plane across its concrete shoulder; the
                # transition inherits exact path edge levels at both stations.
                h=heights[i:i+2]
                band_heights=h[:,0,None]+((np.array([a,c])+width/2)/width)*(h[:,1]-h[:,0])[:,None]
                fill=band_heights-ground[i:i+2,[j,k]]
                if np.any(fill<.005) or np.any(fill>MAX_FILL) or np.any(np.abs(np.diff(band_heights,axis=0)/(s1-s0))>MAX_GRADE):continue
            elif np.max(np.abs(np.diff(band_heights,axis=0)/(s1-s0)))>.25 or np.max(np.abs(np.diff(band_heights,axis=1)/margin_width))>.25:
                continue
            band=(point(s0,a,band_heights[0,0]),point(s1,a,band_heights[1,0]),
                  point(s1,c,band_heights[1,1]),point(s0,c,band_heights[0,1]))
            margin=Solid(kind,band,float(ground[i:i+2,j:k+1].min()-.1))
            if fits_site(margin) and clear(margin) and not any(_overlap(margin,s) for s in solids):
                if kind=='paved_margin' and paved_count<MAX_MARGIN_PATCHES:
                    paths.append(margin);paved_count+=1
                elif kind!='paved_margin' and len(margins)<MAX_MARGIN_PATCHES:margins.append(margin)
    return tuple(paths),tuple(margins),('front_path_inferred_no_parcel_boundary',)


def _overlap(a,b):
    from shapely.geometry import Polygon
    return Polygon([p[:2] for p in a.top]).intersection(Polygon([p[:2] for p in b.top])).area>1e-7


def coordinate(items):
    """Commit optional groundcover after all accepted physical routes/surfaces.

    One local scene pass, no terrain queries and no inferred parcel extents.
    Existing accepted essential surfaces are preserved. This does not certify
    physical conflicts between essential routes or between vertical levels.
    """
    from dataclasses import replace
    import hashlib
    from . import landscaping
    from shapely import STRtree
    from shapely.geometry import Polygon
    from sitegen.surfaces import MAX_RESERVATIONS, SurfaceReservation, overlaps

    scene_origin=np.min(np.vstack([np.asarray(s.ring,float) for s,_,_ in items]),axis=0) if items else np.zeros(2)

    def shape(solid):
        return Polygon([p[:2] for p in solid.top])

    def owner_key(spec):
        source = getattr(getattr(spec,'evidence',None),'source_id','')
        geometry = spec.footprint.outer if spec.footprint is not None else tuple(map(tuple,spec.ring))
        # Local tie-break only: remove scene translation before hashing. Stable
        # source/seed labels keep competing beds from swapping priority on rebase.
        relative=() if source else tuple(map(tuple,np.round(np.asarray(geometry)-scene_origin,8)))
        return hashlib.sha256(repr((str(source),str(spec.seed),relative)).encode()).hexdigest()

    owners = sorted(((owner_key(s),s) for s,_,_ in items if s.access is not None),key=lambda row:row[0])
    reservations=[];overflow=False;unsupported=False
    def reserve(owner,kind,outer,holes=()):
        nonlocal overflow,unsupported
        if len(reservations)>=MAX_RESERVATIONS:
            overflow=True
        else:
            try:reservation=SurfaceReservation(owner,kind,outer,holes)
            except (ValueError,TypeError):
                unsupported=True
                return
            reservations.append(reservation)
    for spec,_,_ in items:
        owner=owner_key(spec)
        if spec.footprint is not None:
            reserve(owner,'building',spec.footprint.outer,spec.footprint.holes)
        else:reserve(owner,'building',tuple(map(tuple,spec.ring)))
        if spec.access is not None:
            for solid in spec.access.solids:
                reserve(owner,solid.kind,tuple(p[:2] for p in solid.top))
        garage=getattr(spec,'garage_access',None)
        if garage is not None and garage.status=='connected':
            for solid in garage.surfaces:reserve(owner,'garage_apron',tuple(p[:2] for p in solid.top))
    # The cap suppresses optional work, never truncates essential route geometry.
    protected=[r.shape() for r in reservations] if not (overflow or unsupported) else []
    tree=STRtree(protected)
    admitted=[]
    updates=[]
    for owner,spec in owners:
        plan=spec.access;notes=set(plan.diagnostics);gardens=[]
        if overflow:notes.add('site_coordination_reservation_budget')
        if unsupported:notes.add('site_coordination_obstacle_unresolved')
        for band in plan.landscape:
            def clear(p):
                return (not (overflow or unsupported) and len(protected)+len(admitted)<MAX_RESERVATIONS
                        and not any(overlaps(p,protected[int(i)]) for i in tree.query(p))
                        and not any(overlaps(p,q) for q in admitted))
            accepted=landscaping.accepted_groundcover(spec,band,clear) if len(gardens)<landscaping.MAX_GROUNDCOVER_PATCHES else None
            if accepted is not None:
                gardens.append(accepted);admitted.append(shape(accepted))
            else:notes.add('landscape_omitted_shared_reservation')
        updates.append((spec,replace(plan,landscape=tuple(gardens),diagnostics=tuple(sorted(notes)))))
    # No owner observes a half-coordinated scene while decisions are being made.
    for spec,plan in updates:spec.access=plan
    return tuple(sorted(reservations,key=lambda r:(r.owner,r.kind,r.outer,r.holes)))


def draw_details(mesh,spec):
    """Fine joints/edge restraints are visual; broad walking surfaces collide."""
    import buildings as b
    from .details import beam
    mats=b._Looks(spec.seed)
    edge=mats[b.custom_look(b.CONCRETE,(.59,.59,.55))]
    paths=[s for s in spec.access.solids if s.kind=='path']
    def restraint(a,c,cap_start,cap_end):
        d=c[:2]-a[:2]; d=d/np.linalg.norm(d)
        n=np.array([-d[1],d[0],0.])
        profile=((- .025,-.065),(.025,-.065),(.025,-.008),(.017,.002),(-.017,.002),(-.025,-.008))
        left=[a+n*w+[0,0,z] for w,z in profile]
        right=[c+n*w+[0,0,z] for w,z in profile]
        uv=((0.,0.),(1.,0.),(1.,.1),(0.,.1))
        for j in range(6):
            k=(j+1)%6
            mesh.quad(left[j],right[j],right[k],left[k],*uv,edge)
        for ring,cap in ((left[::-1],cap_start),(right,cap_end)):
            if cap:
                for j in range(1,5):
                    mesh.tri(ring[0],ring[j],ring[j+1],(0.,0.),(1.,0.),(1.,1.),edge)
    for i,solid in enumerate(paths):
        p=np.asarray(solid.top)
        # Edge restraints meet successive panels exactly; no decorative kerb
        # across the walking route or threshold.
        for a,c in ((0,1),(2,3)):
            restraint(p[a],p[c],i==0 if a==0 else i==len(paths)-1,
                      i==len(paths)-1 if a==0 else i==0)
    # Repeated paving joints are in the shared surface texture, not seam meshes.
    steps=[s for s in spec.access.solids if s.kind=='step']
    if len(steps)>=3:
        rail=mats[b.custom_look(b.METALWALL,(.32,.34,.35))]
        # Handrails follow the landing and stair pitch; posts bear on treads.
        # These are visual access details, not a certified fall-protection system.
        for side in (0,3):
            endside=1 if side==0 else 2
            first=np.asarray(steps[0].top[side]); landing=np.asarray(steps[0].top[endside])
            last=np.asarray(steps[-1].top[endside])
            inward=(np.asarray(steps[0].top[3-side])-first)
            inward=inward/max(float(np.linalg.norm(inward)),1e-9)*.045
            first+=inward; landing+=inward; last+=inward
            beam(mesh,first+[0,0,.9],landing+[0,0,.9],.025,rail)
            beam(mesh,landing+[0,0,.9],last+[0,0,.9],.025,rail)
            for p in (first,landing,last):
                beam(mesh,p,p+[0,0,.9],.022,rail)
