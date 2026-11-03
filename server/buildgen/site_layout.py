"""Property-fitted site surfaces with fixed work limits and conservative fallbacks.

No layout templates, earthworks, route search, network calls or simulated traffic.
Only supplied, measured boundary ports connect to roads/footpaths.
"""
from dataclasses import dataclass, replace
import math
import numpy as np
from shapely.geometry import Polygon
from . import materials

MAX_POINTS=512
MAX_PATCHES=24
MAX_STALLS=12
SPACING=3.


@dataclass(frozen=True, slots=True)
class Layout:
    site_id: str
    revision: str
    parking: int = 0
    docks: int = 0
    terrain_points: int = 0
    connections: tuple = ()
    diagnostics: tuple = ()
    markings: tuple = ()
    baseline_facades: object = None


def quad(origin,tangent,normal,lo,hi,near,far):
    return np.array([origin+tangent*lo+normal*near,origin+tangent*hi+normal*near,
                     origin+tangent*hi+normal*far,origin+tangent*lo+normal*far])


def ordered(q):
    q=np.asarray(q,float)
    if np.sum(q[:,0]*np.roll(q[:,1],-1)-q[:,1]*np.roll(q[:,0],-1))<0:
        q=q[::-1]
    return q


def grid(q):
    # Bilinear grid on a convex quad, with a hard caller-side point budget.
    nx=max(1,math.ceil(max(np.linalg.norm(q[1]-q[0]),np.linalg.norm(q[2]-q[3]))/SPACING))
    ny=max(1,math.ceil(max(np.linalg.norm(q[3]-q[0]),np.linalg.norm(q[2]-q[1]))/SPACING))
    if (nx+1)*(ny+1)>MAX_POINTS:
        return None
    return np.array([(1-v)*((1-u)*q[0]+u*q[1])+v*((1-u)*q[3]+u*q[2])
                     for v in np.linspace(0,1,ny+1) for u in np.linspace(0,1,nx+1)])


def resolve(items,ground,x0,y0):
    from . import commercial, access, facades
    import buildings as b
    if ground is None:
        return
    for spec,low,high in items:
        from sitegen.shared_courts import managed
        if managed(spec):continue
        site=spec.site
        if site is None or commercial.kind(spec) not in commercial.IDS or spec.access is None or spec.facades is None:
            continue
        previous=spec.access.site_layout
        if previous is not None and previous.baseline_facades is not None and any(e.role=='loading_docks' for e in spec.facades.elevations):
            spec.facades=previous.baseline_facades
        baseline_facades=spec.facades
        # Regenerate only this site's surfaces. Primary access remains owned by
        # the existing pipeline; site surfaces are rebuilt atomically below.
        keep=tuple(s for s in spec.access.solids if not s.kind.startswith('site_'))
        spec.access=replace(spec.access,solids=keep,site_layout=None,
                            landscape=tuple(s for s in spec.access.landscape if not s.kind.startswith('site_')))
        if spec.footprint.vertex_count>128:
            spec.access=replace(spec.access,site_layout=Layout(site.id,site.revision,diagnostics=('site_footprint_budget',)))
            continue
        base=b.base_z(spec,low,high)+(spec.min_h or 0.)
        boundary=site.boundary.shape()
        clearance_boundary=boundary.buffer(1e-7)
        if not boundary.covers(spec.footprint.shape()):
            spec.access=replace(spec.access,site_layout=Layout(site.id,site.revision,diagnostics=('site_building_outside_boundary',)))
            continue
        obstacles=[spec.footprint.shape(),*(fp.shape() for fp in site.exclusions)]
        obstacles.extend(Polygon([p[:2] for p in s.top]) for s in keep
                         if s.kind not in ('path','path_link','path_landing','paved_margin'))
        old_paths=[Polygon([p[:2] for p in s.top]) for s in keep if s.kind in ('path','path_link','path_landing','paved_margin')]
        if spec.door:
            origin,tangent,normal=access.basis(spec,*spec.door)
            w=max(1.8,commercial.entry_width(spec))
            old_paths.append(Polygon(quad(origin,tangent,normal,-w/2,w/2,.45,4.)))
        # The catalogue supplies the complete permanent obstacle inventory, so
        # tile load order never changes accepted site choices.
        reservations=[]
        jobs=[]; samples=[]; notes=[]

        def clear(q, extra=(), ignore_paths=False):
            p=Polygon(q)
            return p.is_valid and p.area>.01 and clearance_boundary.covers(p) and all(
                p.intersection(other).area<1e-7 for other in (*obstacles,*reservations,*extra,
                                                            *(() if ignore_paths else old_paths)))

        def add(role,patches,port,opening=(),stall_count=0,marks=(),start=None):
            if sum(len(j['patches']) for j in jobs)+len(patches)>MAX_PATCHES:
                notes.append('site_patch_budget');return False
            grids=[grid(q) for _,q in patches]
            if any(g is None for g in grids) or len(samples)+sum(map(len,grids))>MAX_POINTS:
                notes.append('site_terrain_budget');return False
            off=len(samples)
            for g in grids:samples.extend(g)
            jobs.append(dict(role=role,patches=patches,port=port,opening=opening,stalls=stall_count,
                             marks=marks,start=start,off=off,count=sum(map(len,grids))))
            reservations.extend(Polygon(q) for _,q in patches)
            return True

        def connector(start,tangent,width,port, pedestrian=False):
            a,c=np.asarray(port.a),np.asarray(port.b)
            if (c[:2]-a[:2])@tangent<0:a,c=c,a
            target=(a[:2]+c[:2])/2
            delta=target-start
            if not 1.<=np.linalg.norm(delta)<=50.:
                return None
            normal=np.array([tangent[1],-tangent[0]])
            if not pedestrian and abs(float(delta@tangent))>.25*abs(float(delta@normal)):
                return None  # no unvalidated sharp truck/car turn at a port
            # Straight finite-width connection with compatible end cross-sections.
            if abs(float((c[:2]-a[:2])@tangent))/max(np.linalg.norm(c[:2]-a[:2]),1e-9)<.97:
                return None
            q=ordered([start-tangent*width/2,start+tangent*width/2,c[:2],a[:2]])
            shape=Polygon(q)
            if not shape.is_valid or shape.area<.1 or shape.convex_hull.area-shape.area>1e-7:return None
            return q

        # Pedestrian access is reserved before vehicle operations. It starts at
        # the actual resolved landing/stair toe, and terminates at a measured
        # footpath interface, without altering that footpath or its kerb.
        entries=[s for s in keep if s.kind in ('threshold','step')]
        if spec.door and entries:
            last=entries[-1]
            origin,tangent,normal=access.basis(spec,*spec.door)
            start=np.mean(np.asarray(last.top)[[1,2]],axis=0)
            for port in (p for p in site.ports if p.kind=='pedestrian'):
                width=min(1.8,math.dist(port.a[:2],port.b[:2]),math.dist(last.top[1][:2],last.top[2][:2]))
                if width<1.2:continue
                q=connector(start[:2],tangent,width,port,pedestrian=True)
                if q is not None and clear(q,ignore_paths=True):
                    if add('pedestrian',[('site_path',q)],port,start=start):break

        # Docks use a measured floor offset. A service port alone never creates
        # a raised loading floor. Fit up to six doors within one clear court.
        if site.dock_rise is not None and commercial.kind(spec)!='ci_trade_units':
            candidates=[]
            court_depth=32. if commercial.kind(spec)=='ci_logistics_hall' else 28.
            # Facade openings are expressed along accepted continuous runs.
            # Their first source edge supplies the direction; redundant source
            # vertices must not split a court or disconnect its loading doors.
            for elevation in spec.facades.elevations:
                if elevation.boundary:continue
                edge=elevation.edge
                a=spec.ring[edge];c=spec.ring[(edge+1)%len(spec.ring)]
                length=elevation.length
                if length<12:continue
                t=(c-a)/np.linalg.norm(c-a);n=np.array([t[1],-t[0]])
                for port in (p for p in site.ports if p.kind=='service'):
                    target=(np.asarray(port.a[:2])+port.b[:2])/2
                    distance=float((target-(a+t*length/2))@n)
                    if distance<court_depth+3. or math.dist(port.a[:2],port.b[:2])<6:continue
                    along=float((target-a)@t)
                    candidates.append((distance,edge,along,length,a,t,n,port))
            for _,edge,along,length,a,t,n,port in sorted(candidates,key=lambda r:(r[0],r[1],r[2]))[:4]:
                centre=max(6.,min(length-6.,along))
                span=min(36.,2*min(centre-.65,length-.65-centre))
                count=min(6,int(span/(6.+1.5*materials.unit(spec.seed,'site-dock-bay'))))
                if count<1:continue
                lo,hi=centre-span/2,centre+span/2
                court=quad(a,t,n,lo,hi,1.,court_depth)
                conn=connector(a+t*centre+n*court_depth,t,6.,port)
                if conn is None or not clear(court) or not clear(conn,(Polygon(court),)):continue
                ops=[]; patches=[('site_service',court),('site_service',conn)]
                for k in range(count):
                    s=lo+(hi-lo)*(k+.5)/count
                    op=facades.Opening('service',0,s-1.6,s+1.6,site.dock_rise,min(site.dock_rise+3.4,spec.height-.35))
                    existing=next(e for e in spec.facades.elevations if e.boundary==0 and e.edge==edge)
                    if op.top-op.bottom<2.8 or any(op.overlaps(o,.3) for o in existing.openings if o.kind!='service'):
                        continue
                    platform=quad(a,t,n,s-1.8,s+1.8,0.,1.)
                    if clear(platform):
                        ops.append((edge,op));patches.append(('site_dock',platform))
                if ops and add('service',patches,port,opening=tuple(ops)):break

        # Where there is no raised court, a light service vehicle can approach
        # an existing ground-level shutter directly. Keep staff thresholds and
        # the primary pedestrian route clear; never invent a turning route.
        if not any(j['role']=='service' for j in jobs):
            choices=[]
            for e in spec.facades.elevations:
                if e.boundary:continue
                for op in e.openings:
                    if op.kind!='service':continue
                    origin,t,n=access.basis(spec,e.edge,(op.left+op.right)/2)
                    for port in (p for p in site.ports if p.kind=='service'):
                        if math.dist(port.a[:2],port.b[:2])<3.:continue
                        target=(np.asarray(port.a[:2])+port.b[:2])/2
                        distance=float((target-origin)@n)
                        if distance<5.:continue
                        choices.append((distance,e.edge,op.left,origin,t,op,port))
            for _,_,_,origin,t,op,port in sorted(choices,key=lambda c:c[:3])[:8]:
                q=connector(origin,t,min(4.2,op.right-op.left),port)
                if q is not None and clear(q):
                    start=np.r_[origin,base+op.bottom-.01]
                    if add('service',[('site_service',q)],port,start=start):break

        # Parking rows are computed from facade length and residual section.
        # Whole stalls are retained; tapering/obstructions terminate the row.
        pedestrian_job=next((j for j in jobs if j['role']=='pedestrian'),None)
        if spec.front is not None and pedestrian_job is not None:
            shared=commercial.derive_programme(spec)
            run=shared.run(0,spec.front) if shared else None
            edge=run.edge if run is not None else spec.front
            a=spec.ring[edge];c=spec.ring[(edge+1)%len(spec.ring)]
            length=run.length if run is not None else float(np.linalg.norm(c-a))
            t=(c-a)/np.linalg.norm(c-a);n=np.array([t[1],-t[0]])
            for port in (p for p in site.ports if p.kind=='parking'):
                if math.dist(port.a[:2],port.b[:2])<5.5:continue
                target=(np.asarray(port.a[:2])+port.b[:2])/2
                u=float((target-a)@t)
                # Two orientations along the frontage, chosen by actual access
                # position. No fixed stall count or scaled car park model.
                options=[]
                for direction in (-1,1):
                    near=5.+2.*materials.unit(spec.seed,'site-parking-offset')
                    start=max(.65,min(length-.65,u))
                    bays=[]
                    bay=2.5+.3*materials.unit(spec.seed,'site-parking-bay')
                    for k in range(MAX_STALLS):
                        p=start+direction*k*bay;q=start+direction*(k+1)*bay
                        lo,hi=sorted((p,q))
                        if lo<.65 or hi>length-.65:break
                        stall=quad(a,t,n,lo,hi,near,near+5.2)
                        aisle=quad(a,t,n,lo,hi,near+5.2,near+11.2)
                        if not clear(stall) or not clear(aisle):break
                        bays.append((lo,hi))
                    if len(bays)<2:continue
                    lo=min(v[0] for v in bays);hi=max(v[1] for v in bays)
                    row=quad(a,t,n,lo,hi,near,near+5.2)
                    aisle=quad(a,t,n,lo,hi,near+5.2,near+11.2)
                    connection_width=min(6.,hi-lo)
                    mid=max(lo+connection_width/2,min(hi-connection_width/2,u))
                    conn=connector(a+t*mid+n*(near+11.2),t,connection_width,port)
                    if conn is None or not clear(conn,(Polygon(row),Polygon(aisle))):continue
                    pq=pedestrian_job['patches'][0][1]
                    local=np.c_[(pq-a)@t,(pq-a)@n]
                    # A simple T join is accepted only when it can be expressed
                    # without clipping/overlapping the existing pedestrian slab.
                    xs=sorted(set(np.round(local[:,0],6)))
                    if len(xs)!=2 or local[:,1].min()>near-1.8 or local[:,1].max()<near:continue
                    if xs[1]<=lo:
                        bridge=quad(a,t,n,xs[1],lo,near-1.8,near)
                    elif xs[0]>=hi:
                        bridge=quad(a,t,n,hi,xs[0],near-1.8,near)
                    else:continue
                    walk=quad(a,t,n,lo,hi,near-1.8,near)
                    if not clear(walk,ignore_paths=True) or not clear(bridge,ignore_paths=True):continue
                    marks=tuple((tuple(a+t*s+n*near),tuple(a+t*s+n*(near+5.2)))
                                for s in sorted({round(v,6) for bay in bays for v in bay}))
                    options.append((len(bays),[('site_parking',row),('site_aisle',aisle),('site_access',conn),
                                               ('site_walk',walk),('site_walk',bridge)],marks))
                if options:
                    count,patches,marks=max(options,key=lambda v:v[0])
                    if add('parking',patches,port,stall_count=count,marks=marks):break
        from . import landscaping
        planted=[Polygon([p[:2] for p in s.top]) for s in spec.access.landscape]
        for cover,q,parent in landscaping.site_candidates(spec,jobs):
            if clear(q,extra=planted) and add('landscape',[('site_'+cover,q)],parent['port']):
                jobs[-1]['parent']=id(parent)
        if not jobs:
            spec.access=replace(spec.access,site_layout=Layout(site.id,site.revision,
                diagnostics=tuple(sorted(set(notes+['site_no_feasible_layout'])))))
            continue
        terrain=np.asarray(ground(np.asarray(samples)+[x0,y0]),float).reshape(-1)
        solids=[];gardens=[];accepted=set();marks=[];connections=[];parking=docks=0;changes={};pedestrian_plane=None
        for job in jobs:
            p=np.asarray(samples[job['off']:job['off']+job['count']]);z=terrain[job['off']:job['off']+job['count']]
            if not np.isfinite(z).all():notes.append('site_missing_terrain');continue
            if job['role']=='landscape':
                if job['parent'] not in accepted:continue
                q=job['patches'][0][1]
                origin=p.mean(axis=0)
                coef=np.linalg.lstsq(np.c_[p-origin,np.ones(len(p))],z,rcond=None)[0]
                residual=np.c_[p-origin,np.ones(len(p))]@coef+.015-z
                if np.linalg.norm(coef[:2])>.2 or residual.min()<.004 or residual.max()>.07:continue
                top=np.c_[q,np.c_[q-origin,np.ones(4)]@coef+.015]
                if not Polygon(q).exterior.is_ccw:top=top[::-1]
                gardens.append(access.Solid(job['patches'][0][0],tuple(tuple(map(float,v)) for v in top),float(z.min()-.05)))
                continue
            port=job['port'];pa,pb=np.asarray(port.a),np.asarray(port.b)
            centre=(pa+pb)/2;t=pb[:2]-pa[:2];width=float(np.linalg.norm(t));t/=width
            normal=np.array([t[1],-t[0]])
            # Fixed-size least-squares plane, constrained to both port heights.
            local=p-centre[:2]
            slope=np.linalg.lstsq(np.c_[local,np.ones(len(local))],z,rcond=None)[0][:2]
            slope=slope-(slope@t)*t+((pb[2]-pa[2])/width)*t
            if job['start'] is not None:
                start=job['start'];delta=start[:2]-centre[:2]
                if abs(float(delta@normal))<1.:notes.append('site_bad_path_alignment');continue
                slope=slope-(slope@normal)*normal+((start[2]-centre[2]-(delta@t)*(slope@t))/(delta@normal))*normal
            elif job['role']=='parking':
                if pedestrian_plane is None:
                    notes.append('site_parking_requires_pedestrian_route');continue
                ps,pc=pedestrian_plane
                if max(abs(float((q[:2]-pc[:2])@ps+pc[2]-q[2])) for q in (pa,pb))>1e-5:
                    notes.append('site_parking_connection_level_conflict');continue
                slope,centre=ps.copy(),pc.copy()
            def height(xy):return (np.asarray(xy)-centre[:2])@slope+centre[2]
            # Dock sampling is checked against the pavement datum, not its raised
            # platform: a real dock face is intentionally above the vehicle court.
            fill=height(p)-z
            limit=.05 if job['role']=='pedestrian' else .04 if job['role']=='parking' else .08
            if np.linalg.norm(slope)>limit or np.any(fill<.004) or np.any(fill>.15):
                notes.append('site_omitted_grading');continue
            if job['role']=='pedestrian' and abs(float(slope@t))>.02:
                notes.append('site_path_crossfall');continue
            if job['role']=='pedestrian':pedestrian_plane=(slope.copy(),centre.copy())
            if job['opening']:
                ground_level=float(height(job['patches'][0][1]).mean())
                if not .8<=base+site.dock_rise-ground_level<=1.5:
                    notes.append('site_dock_level_conflict');continue
            added=[]
            for kind,q in job['patches']:
                h=np.full(4,base+site.dock_rise) if kind=='site_dock' else height(q)
                top=np.c_[q,h];top=top if Polygon(q).exterior.is_ccw else top[::-1]
                added.append(access.Solid(kind,tuple(tuple(map(float,v)) for v in top),float(z.min()-.12)))
                if kind=='site_dock':
                    tangent=q[1]-q[0];w=float(np.linalg.norm(tangent));tangent/=w
                    normal=q[3]-q[0];normal/=np.linalg.norm(normal)
                    datum=base+site.dock_rise
                    for along in (.3,w-.3):
                        xy=quad(q[3],tangent,normal,along-.1,along+.1,0.,.15)
                        top=np.c_[xy,np.full(4,datum-.12)]
                        if not Polygon(xy).exterior.is_ccw:top=top[::-1]
                        added.append(access.Solid('site_bumper',tuple(tuple(map(float,v)) for v in top),datum-.55))
                    marks.append(((*(q[3]+normal*.015),datum+.006),(*(q[2]+normal*.015),datum+.006)))
            solids.extend(added);parking+=job['stalls'];docks+=len(job['opening']);connections.append(job['role']);accepted.add(id(job))
            for edge,op in job['opening']:changes.setdefault(edge,[]).append(op)
            for a,c in job['marks']:
                marks.append(((*a,float(height(a))+.006),(*c,float(height(c))+.006)))
        for edge,ops in changes.items():
            es=[]
            for e in spec.facades.elevations:
                if e.boundary==0 and e.edge==edge:
                    remaining=tuple(o for o in e.openings if o.kind!='service')
                    e=replace(e,openings=tuple(sorted((*remaining,*ops),key=lambda o:o.left)),role='loading_docks')
                es.append(e)
            spec.facades=replace(spec.facades,elevations=tuple(es))
        layout=Layout(site.id,site.revision,parking,docks,len(samples),tuple(connections),tuple(sorted(set(notes))),tuple(marks),baseline_facades)
        # Replace the inferred short path only when a measured-footpath route
        # succeeds; otherwise retain the previous primary access unchanged.
        if 'pedestrian' in connections:
            keep=tuple(s for s in keep if s.kind not in ('path','path_link','path_landing','paved_margin'))
        paved=[Polygon([p[:2] for p in s.top]) for s in solids]
        landscape=tuple(s for s in spec.access.landscape if all(
            Polygon([p[:2] for p in s.top]).intersection(p).area<1e-7 for p in paved))
        spec.access=replace(spec.access,solids=keep+tuple(solids),landscape=landscape+tuple(gardens),site_layout=layout)


def draw_markings(mesh,spec):
    import buildings as b
    layout=spec.access.site_layout if spec.access else None
    if layout is None:return
    mat=b._Looks(spec.seed)[b.custom_look(b.PANEL,(.9,.9,.83))]
    for a,c in layout.markings:
        a,c=np.asarray(a),np.asarray(c);d=c[:2]-a[:2]
        n=np.array([-d[1],d[0]])/max(np.linalg.norm(d),1e-9)*.045
        q=[(* (a[:2]-n),a[2]),(*(c[:2]-n),c[2]),(*(c[:2]+n),c[2]),(*(a[:2]+n),a[2])]
        mesh.quad(*q,(0,0),(1,0),(1,1),(0,1),mat)
