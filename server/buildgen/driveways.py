"""Bounded garage-to-street profiles, curved mouths and receiving-area fallbacks.

Nine sections, one normal terrain batch and one lazy batch per failed property's
receiving alternatives. No terrain edits or unbounded path search.
"""
from dataclasses import replace
import math
import os
import numpy as np

MAX_LENGTH=18.
MAX_GRADE=.15
MAX_FILL=.35
SECTIONS=9
MAX_QUERY_SEGMENTS=64


class _QueryBudget(ValueError):
    pass


def hermite(t,a,b,length,grade0=-.02,grade1=-.015):
    t=np.asarray(t)
    return (2*t**3-3*t**2+1)*a+(t**3-2*t**2+t)*length*grade0 \
        +(-2*t**3+3*t**2)*b+(t**3-t**2)*length*grade1


def branch_candidate(spec,xy,clear,drive_outline):
    from shapely.geometry import Polygon
    from .access import basis
    if os.environ.get('BNE_BUILDING_PATHS','auto')=='off' or spec.inference.use.value not in ('residential','mixed'):
        return None
    paths=[s for s in spec.access.solids if s.kind in ('path','path_landing')]
    thresholds=[s for s in spec.access.solids if s.kind=='threshold']
    if paths:
        a,c=np.asarray(paths[0].top)[[0,3]]
    elif thresholds:
        a,c=np.asarray(thresholds[-1].top)[[1,2]]
    else:return None  # don't bridge into a raised deck without a resolved stair
    _,tangent,normal=basis(spec,*spec.door)
    pad=np.array([a[:2],a[:2]+normal*1.2,c[:2]+normal*1.2,c[:2]])
    origin=xy[0,1]
    station=(xy[:,1]-origin)@normal
    wanted=np.array([(a[:2]-origin)@normal,(a[:2]-origin)@normal+1.2])
    if np.any(np.diff(station)<=0) or wanted[0]<0 or wanted[-1]>station[-1]-.2:return None
    door_side=float(((a[:2]+c[:2])/2-origin)@tangent)>0
    side=2 if door_side else 0
    on_drive=np.column_stack([np.interp(wanted,station,xy[:,side,j]) for j in range(2)])
    pad_indices=(0,1) if door_side else (3,2)
    bridge=np.array([pad[pad_indices[0]],on_drive[0],on_drive[1],pad[pad_indices[1]]])
    gap=np.linalg.norm(bridge[0]-bridge[1])
    if not .6<=gap<=8:return None
    shapes=(Polygon(pad),Polygon(bridge))
    if any(not clear(p) or p.intersection(drive_outline).area>1e-6 for p in shapes):return None
    points=np.r_[pad,bridge,pad.mean(axis=0)[None],bridge.mean(axis=0)[None]]
    return pad,bridge,np.array([a[2],c[2]]),station,wanted,side,pad_indices,points


def branch_build(branch,z,ground):
    from .access import Solid
    if branch is None or not np.isfinite(ground).all():return ()
    pad,bridge,start,station,wanted,side,indices,_=branch
    pad,bridge,start,station,wanted=map(np.asarray,(pad,bridge,start,station,wanted))
    pz=np.array([start[0],start[0]-.018,start[1]-.018,start[1]])
    dz=np.interp(wanted,station,z[:,0 if side==0 else 1])
    bz=np.array([pz[indices[0]],dz[0],dz[1],pz[indices[1]]])
    if max(abs(bz[1]-bz[0])/np.linalg.norm(bridge[1]-bridge[0]),
           abs(bz[2]-bz[3])/np.linalg.norm(bridge[2]-bridge[3]))>.05:return ()
    heights=np.r_[pz,bz,pz.mean(),bz.mean()]
    if np.any(heights-ground<.005) or np.any(heights-ground>.15):return ()
    solids=[]
    for kind,xy,h in (('path_landing',pad,pz),('path_link',bridge,bz)):
        top=np.c_[xy,h]
        area=np.sum(xy[:,0]*np.roll(xy[:,1],-1)-xy[:,1]*np.roll(xy[:,0],-1))
        if area<0:top=top[::-1]
        solids.append(Solid(kind,tuple(tuple(map(float,p)) for p in top),float(ground.min()-.1)))
    return tuple(solids)


def resolve(items,lines,walks,raw_walks,ground,x0,y0,drives=None,*,audit=None):
    """Freeze at most four full route proposals per garage, sample once, commit one.

    A failed full connection can use an independently fitted receiving area.
    The accepted route's entire physical strip must fit before any curb drops.
    """
    from shapely import STRtree
    from shapely.geometry import Polygon, LineString, Point
    import sidewalks
    import vehicle_crossings
    from .access import basis, Solid
    from sitegen.portals import StreetPortal, RouteProposal, ranked, simplified_lines, installed_owner, OWNER_TOKEN_PREFIX
    from sitegen.surfaces import contains_known_site
    from sitegen.shared_courts import managed
    offset=np.array([x0,y0])
    actual_walks=walks
    # A proposal sees its own prior cuts removed from a detached planning view.
    # Actual cuts/records remain installed until an accepted replacement commits.
    walks=[dict(walk) for walk in actual_walks]
    for walk in walks:
        remaining=list(walk.get('driveways',()))
        for interval in walk.get('building_driveways',()):
            match=next((i for i,row in enumerate(remaining) if tuple(row)==tuple(interval)),None)
            if match is not None:remaining.pop(match)
        walk['driveways']=remaining
    def source_key(spec):
        return str(getattr(spec.evidence,'source_id','') or ''),float(spec.seed or 0)
    anchors={}
    for spec,_,_ in items:
        key=source_key(spec);origin=np.min(np.asarray(spec.ring,float),axis=0)
        anchors[key]=np.minimum(anchors[key],origin) if key in anchors else origin
    def component_key(spec):
        anchor=anchors[source_key(spec)]
        rings=(spec.footprint.outer,*spec.footprint.holes) if spec.footprint is not None else (spec.ring,)
        return tuple(tuple(map(tuple,np.round(np.asarray(ring)-anchor,8))) for ring in rings)
    eligible=sorted((s for s,_,_ in items if s.inference is not None and s.garage_opening and s.access is not None and not managed(s)),
                    key=lambda s:(source_key(s),component_key(s)))
    if audit is not None:
        for s,_,_ in items:
            reason=('no_v2_inference' if s.inference is None else
                    'no_garage_opening' if not s.garage_opening else
                    'no_access_plan' if s.access is None else 'eligible')
            audit.record('eligibility',reason)
    if drives is not None:drives[:]=[d for d in drives if not d.get('bne_v2_drive')]
    if not eligible:return
    installed={id(spec):installed_owner(spec) for spec in eligible}
    occupied={owner for walk in actual_walks for owner in walk.get('building_driveway_owners',{})}
    if drives is not None:occupied.update(d['bne_building_owner'] for d in drives if d.get('bne_building_owner'))
    def owner_id(spec):
        import hashlib
        if installed.get(id(spec)) is not None:return installed[id(spec)]
        component=hashlib.sha256(repr(component_key(spec)).encode()).hexdigest()[:24]
        owner=':'.join(map(str,source_key(spec)))+':component:'+component
        if owner in occupied:
            # A fresh partial member cannot claim an installed sibling merely
            # because their equal-shaped components normalize to the same ring.
            # Use explicit frame-local geometry only to allocate a NEW token;
            # installed tokens above remain authoritative across replans/rebases.
            rings=(spec.footprint.outer,*spec.footprint.holes) if spec.footprint is not None else (spec.ring,)
            absolute=tuple(tuple(map(tuple,np.round(np.asarray(ring)+offset,8))) for ring in rings)
            suffix=hashlib.sha256(repr(absolute).encode()).hexdigest()[:24]
            base=owner+':frame-local:'+suffix
            owner=base;serial=0
            while owner in occupied:
                serial+=1;owner=base+':'+str(serial)
        occupied.add(owner)
        installed[id(spec)]=owner
        return owner
    def remove_cuts(walk,owner):
        owners=dict(walk.get('building_driveway_owners',{}))
        intervals=owners.pop(owner,())
        for field in ('driveways','building_driveways'):
            remaining=list(walk.get(field,()))
            for interval in intervals:
                match=next((i for i,row in enumerate(remaining) if tuple(row)==tuple(interval)),None)
                if match is not None:remaining.pop(match)
            if remaining:walk[field]=remaining
            else:walk.pop(field,None)
        if owners:walk['building_driveway_owners']=owners
        else:walk.pop('building_driveway_owners',None)
    def retire_owned(spec):
        owner=owner_id(spec)
        for collection in (actual_walks,raw_walks if raw_walks is not actual_walks else None):
            for walk in collection or ():remove_cuts(walk,owner)
        if drives is not None:drives[:]=[d for d in drives if d.get('bne_building_owner')!=owner]
    from .topology import Footprint
    obstacle_rows=[];inventory_unknown=False
    for s,_,_ in items:
        # A raised volume is not proof of vehicle headroom.
        try:obstacle_rows.append((None,(s.footprint or Footprint(s.ring)).shape()))
        except (ValueError,TypeError):inventory_unknown=True
        if s.access is not None:
            obstacle_rows.extend((s,Polygon([p[:2] for p in solid.top])) for solid in s.access.solids)
    obstacle_rows.extend((None,LineString(np.asarray(line[0])[:,:2]-offset).buffer(float(line[1])))
                         for line in lines if len(line[0])>1)
    obstacles=[p for _,p in obstacle_rows]
    tree=STRtree(obstacles)
    def clear(poly,spec):
        return (not inventory_unknown and poly.is_valid and not poly.is_empty and contains_known_site(spec,poly)
                and all((obstacle_rows[int(i)][0] is spec) or poly.intersection(obstacles[int(i)]).area<1e-7
                        for i in tree.query(poly)))
    street=[];walk_pieces=[]
    for wi,wk in enumerate(walks):
        if 'corner' in wk:
            corner=wk['corner'];p=np.concatenate((np.asarray(corner['arc']),np.asarray(corner['outer'])))
            shape=Polygon(p[:,:2]-offset)
            if shape.is_valid:walk_pieces.append((wi,shape))
            continue
        w=wk.get('w',2.5)
        curb,out=sidewalks.run_geometry(wk['pts'],wk['side'],w)
        keep=sidewalks.simplify(curb,tol=1e-6)
        curb,out=curb[keep],out[keep]
        arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(curb[:,:2],axis=0),axis=1))]
        for j in range(len(curb)-1):
            shape=Polygon([curb[j,:2]-offset,curb[j+1,:2]-offset,
                           curb[j+1,:2]+out[j+1]*w-offset,curb[j,:2]+out[j]*w-offset])
            if shape.is_valid:walk_pieces.append((wi,shape))
            if not wk.get('median'):street.append((wi,j,curb,out,arc,w))
    stree=STRtree([LineString(row[2][row[1]:row[1]+2,:2]-offset) for row in street])
    walk_tree=STRtree([p for _,p in walk_pieces])
    road_data=[line for line in simplified_lines(lines) if len(line[0])>1]
    road_shapes=[LineString(np.asarray(line[0])[:,:2]-offset) for line in road_data]
    road_tree=STRtree(road_shapes)
    controlled=lambda line:len(line)>2 and line[2] in ('motorway','motorway_link')
    def rejected(reason):
        if audit is not None:audit.record('candidate_rejections',reason)
    def protected_walk(poly,wi=None):
        return any(walk_pieces[int(i)][0]!=wi and poly.intersection(walk_pieces[int(i)][1]).area>1e-7
                   for i in walk_tree.query(poly))

    def interfaces(spec,origin,tangent,normal,width):
        mouth=max(3.2,width);half=mouth/2+.1
        nearby=stree.query(Point(origin).buffer(MAX_LENGTH+3.))
        if len(nearby)>MAX_QUERY_SEGMENTS:
            rejected('sidewalk_query_budget');raise _QueryBudget('sidewalk_query_budget')
        road_nearby=road_tree.query(Point(origin).buffer(MAX_LENGTH+4.))
        if sum(len(road_data[int(i)][0])-1 for i in road_nearby)>MAX_QUERY_SEGMENTS:
            rejected('road_query_budget');raise _QueryBudget('road_query_budget')
        for si in nearby:
            if audit is not None:audit.record('candidates','sidewalk_segments_examined')
            wi,j,curb,out,arc,w=street[int(si)]
            a,b=curb[j,:2]-offset,curb[j+1,:2]-offset
            v=b-a;length=float(np.linalg.norm(v));direction=v/max(length,1e-9)
            u=float((origin-a)@v/max(length*length,1e-9))
            if not 0<=u<=1:rejected('outside_segment');continue
            facing=out[j]*(1-u)+out[j+1]*u
            if facing@(-normal)<.94:rejected('frontage_alignment');continue
            reach=float((a+u*v-origin)@normal)
            if not 2.<reach<=MAX_LENGTH+3:rejected('frontage_distance');continue
            if w<vehicle_crossings.MIN_WIDTH:rejected('footpath_width');continue
            station=arc[j]+u*length
            # Same evidenced straight frontage, bounded gentle lateral options.
            # These are route alternatives, not new mapped entrances or source IDs.
            shift=min(1.5,max(0.,reach-w)*.2)
            for change in (0.,-shift,shift):
                s=float(station+change)
                if s-half-vehicle_crossings.FLARE<0 or s+half+vehicle_crossings.FLARE>arc[-1]:
                    rejected('mouth_extent');continue
                covered=np.flatnonzero((arc[:-1]<s+half+vehicle_crossings.FLARE)&(arc[1:]>s-half-vehicle_crossings.FLARE))
                delta=np.diff(curb[:,:2],axis=0)[covered]
                directions=delta/np.maximum(np.linalg.norm(delta,axis=1),1e-9)[:,None]
                if not len(delta) or np.min(directions@direction)<math.cos(math.radians(25)):
                    rejected('curved_frontage');continue
                curved=np.min(directions@direction)<.999999
                if any(hi>=s-half-vehicle_crossings.FLARE and lo<=s+half+vehicle_crossings.FLARE
                       for lo,hi in walks[wi].get('ramps',())):
                    rejected('pedestrian_ramp');continue
                if any(row[1]+vehicle_crossings.FLARE>=s-half-vehicle_crossings.FLARE
                       and row[0]-vehicle_crossings.FLARE<=s+half+vehicle_crossings.FLARE
                       for row in walks[wi].get('driveways',())):
                    rejected('reserved_crossing');continue
                q=np.array([np.interp(s,arc,curb[:,k]-offset[k]) for k in (0,1)])
                # A nearby controlled carriageway cannot acquire inferred access.
                if any(controlled(road_data[int(i)]) and road_shapes[int(i)].distance(Point(q))<=float(road_data[int(i)][1])+.5
                       for i in road_tree.query(Point(q).buffer(w+12.))):
                    rejected('controlled_road');continue
                facing=np.array([np.interp(s,arc,out[:,k]) for k in (0,1)])
                end=q+facing*w
                end_tangent=direction if direction@tangent>0 else -direction
                zends=np.interp([s-mouth/2,s+mouth/2],arc,curb[:,2])
                check=arc[(arc>s-mouth/2)&(arc<s+mouth/2)]
                if not curved and len(check) and np.max(np.abs(np.interp(check,arc,curb[:,2])-
                       np.interp(check,[s-mouth/2,s+mouth/2],zends)))>.01:
                    rejected('curb_height_profile');continue
                z=float(zends.mean())+walks[wi].get("curb_h",sidewalks.CURB_H)+w*sidewalks.CROSS_SLOPE
                grade=float((zends[1]-zends[0])/mouth)*(1 if direction@tangent>0 else -1)
                # Two overlaid/adjacent footpaths need joint planning, not a cut
                # through only one source run while the other retains its curb.
                rear=()
                if curved:
                    stations=np.unique(np.r_[np.linspace(s-mouth/2,s+mouth/2,9),check])
                    if len(stations)>17:rejected('curved_mouth_budget');continue
                    rr=np.column_stack([np.interp(stations,arc,curb[:,k]-offset[k])+w*np.interp(stations,arc,out[:,k]) for k in (0,1)])
                    rz=np.interp(stations,arc,curb[:,2])+walks[wi].get('curb_h',sidewalks.CURB_H)+w*sidewalks.CROSS_SLOPE
                    rr=np.c_[rr,rz]
                    if direction@tangent<0:rr=rr[::-1]
                    rear=tuple(map(tuple,rr))
                crossing_shape=Polygon([end-end_tangent*mouth/2,end+end_tangent*mouth/2,
                                        q+end_tangent*mouth/2,q-end_tangent*mouth/2])
                if rear:
                    front=np.column_stack([np.interp(stations,arc,curb[:,k]-offset[k]) for k in (0,1)])
                    if direction@tangent<0:front=front[::-1]
                    crossing_shape=Polygon(np.r_[np.asarray(rear)[:,:2],front[::-1]])
                    if not crossing_shape.is_valid:rejected('folded_crossing');continue
                if protected_walk(crossing_shape,wi):rejected('overlapping_footpaths');continue
                yield StreetPortal('sidewalk',tuple(end),tuple(end_tangent),mouth,float(np.linalg.norm(end-origin)),z,grade,
                                   (int(wi),s-half,s+half),rear)
        for ri in road_nearby:
            line=road_data[int(ri)]
            if controlled(line):rejected('controlled_road');continue
            pts=np.asarray(line[0])[:,:2]-offset
            for a,b in zip(pts,pts[1:]):
                if audit is not None:audit.record('candidates','road_segments_examined')
                v=b-a;ll=float(v@v)
                if ll<1e-8:continue
                u=float(np.clip((origin-a)@v/ll,0,1));q=a+u*v
                toward=origin-q;dist=float(np.linalg.norm(toward))
                if dist<=float(line[1])+.5:continue
                facing=toward/dist
                if facing@(-normal)<.94:continue
                end=q+facing*float(line[1]);reach=float(np.linalg.norm(end-origin))
                if not 1.<=reach<=MAX_LENGTH:continue
                direction=v/math.sqrt(ll)
                if direction@tangent<0:direction=-direction
                shift=min(1.5,reach*.2)
                for change in (0.,-shift,shift):
                    target=end+direction*change
                    if not 0<=float((target-a)@v/ll)<=1:continue
                    yield StreetPortal('road',tuple(target),tuple(direction),mouth,float(np.linalg.norm(target-origin)))

    plans=[];all_points=[]
    for spec in eligible:
        edge,along,width,_=spec.garage_opening
        origin,tangent,normal=basis(spec,edge,along);width+=.3
        budget_reason=None
        try:proposals=ranked(interfaces(spec,origin,tangent,normal,width))
        except _QueryBudget as exc:proposals=();budget_reason=str(exc)
        record=dict(spec=spec,choices=[],failures=[],crossing=any(p.crossing is not None for p in proposals))
        if audit is not None and record['crossing']:audit.record('crossings','selected_before_internal_fit')
        if not proposals:record['failures'].append('driveway_omitted_'+(budget_reason or 'no_direct_frontage'))
        for rank,portal in enumerate(proposals,1):
            if audit is not None:audit.record('candidates','complete_route_proposals')
            end=np.asarray(portal.end);end_tangent=np.asarray(portal.tangent);reach=portal.distance
            reason=None
            if not 1.<=reach<=MAX_LENGTH:reason='short_setback' if reach<1 else 'route_length'
            t=np.linspace(0.,1.,SECTIONS)
            centres=(2*t**3-3*t**2+1)[:,None]*origin+(t**3-2*t**2+t)[:,None]*reach*normal \
                +(-2*t**3+3*t**2)[:,None]*end+(t**3-t**2)[:,None]*reach*(-np.array([-end_tangent[1],end_tangent[0]]))
            if np.dot(centres[-1]-centres[-2],normal)<=0:centres=origin+(end-origin)*t[:,None]
            tangents=(1-t[:,None])*tangent+t[:,None]*end_tangent
            tangents/=np.linalg.norm(tangents,axis=1)[:,None]
            widths=width+(portal.width-width)*(t*t*(3-2*t))
            xy=np.stack([centres-tangents*widths[:,None]/2,centres,centres+tangents*widths[:,None]/2],axis=1)
            if portal.rear:
                rear=np.asarray(portal.rear)
                fractions=np.linspace(-.5,.5,len(rear))
                xy=centres[:,None,:]+tangents[:,None,:]*widths[:,None,None]*fractions[None,:,None]
                xy+=(t*t*(3-2*t))[:,None,None]*(rear[None,:,:2]-xy[-1][None,:,:])
            outline=Polygon(np.r_[xy[:,0],xy[-1,1:-1],xy[::-1,-1],xy[0,-2:0:-1]])
            if reason is None and inventory_unknown:reason='unknown_obstacle_inventory'
            if reason is None and not clear(outline,spec):reason='obstruction'
            if reason is None and protected_walk(outline):reason='unsupported_footpath_crossing'
            branch=branch_candidate(spec,xy,lambda p:clear(p,spec),outline) if reason is None and not portal.rear else None
            proposal=RouteProposal(portal,xy,branch)
            off=len(all_points)
            if reason is None:
                all_points.extend(xy.reshape(-1,2)+offset)
                if branch is not None:all_points.extend(branch[-1]+offset)
            record['choices'].append((rank,proposal,off,outline,reason))
        # A receiving area is evaluated independently, only behind an evidenced
        # garage-facing mouth. Full connections keep priority. Never replace an
        # existing complete route with a disconnected receiving slab.
        if not any(s.kind=='driveway' for s in spec.access.solids):
            for portal in proposals:
                if portal.crossing is None:continue
                end=np.asarray(portal.end); tangent=np.asarray(portal.tangent)
                inward=np.array([-tangent[1],tangent[0]])
                if inward@normal>0:inward=-inward
                t=np.linspace(0.,1.,SECTIONS)
                rear=np.asarray(portal.rear) if portal.rear else np.c_[end+np.array([-.5,0,.5])[:,None]*portal.width*tangent, np.zeros(3)]
                xy=rear[None,:,:2]+(1-t)[:,None,None]*5.5*inward
                outline=Polygon(np.r_[xy[:,0],xy[-1,1:-1],xy[::-1,-1],xy[0,-2:0:-1]])
                if not clear(outline,spec) or protected_walk(outline):continue
                if any(outline.intersection(Polygon(np.asarray(s.top)[:,:2])).area>1e-7
                       for s in spec.access.solids if s.kind not in ('path','paved_margin','driveway')):continue
                record['choices'].append((len(record['choices'])+1,RouteProposal(portal,xy,None,'crossing_only'),None,outline,None))
        plans.append(record)
    if audit is not None:
        audit.record('work','terrain_jobs',sum(reason is None and off is not None for record in plans for _,_,off,_,reason in record['choices']))
        audit.record('work','terrain_points',len(all_points))
        audit.record('work','terrain_calls',int(ground is not None and bool(all_points)))
    terrain=(np.asarray(ground(np.asarray(all_points)),float) if ground is not None and all_points
             else np.full(len(all_points),np.nan))
    accepted={}
    def buckets(poly):
        a,b,c,d=poly.bounds
        return [(i,j) for i in range(math.floor(a/16),math.floor(c/16)+1)
                      for j in range(math.floor(b/16),math.floor(d/16)+1)]
    def conflicts(poly):
        nearby={id(p):p for key in buckets(poly) for p in accepted.get(key,())}
        return any(poly.intersection(p).area>1e-7 for p in nearby.values())
    for record in plans:
        spec=record['spec'];failures=record['failures'];outcomes=[];selected=False
        for rank,proposal,off,outline,reason in record['choices']:
            portal=proposal.portal;xy=np.asarray(proposal.sections);branch=proposal.branch
            t=np.linspace(0.,1.,SECTIONS);reach=portal.distance
            if reason is None and conflicts(outline):reason='neighbour_access_conflict'
            if reason is None and any(not Polygon([xy[i,j],xy[i+1,j],xy[i+1,j+1],xy[i,j+1]]).is_valid
                                      for i in range(SECTIONS-1) for j in range(xy.shape[1]-1)):
                reason='folded_route'
            if reason is None and portal.crossing is not None:
                wi,lo,hi=portal.crossing
                walk=actual_walks[wi]
                own=walk.get('building_driveway_owners',{}).get(owner_id(spec),())
                if any(tuple(row) not in own and row[1]+vehicle_crossings.FLARE>=lo-vehicle_crossings.FLARE
                       and row[0]-vehicle_crossings.FLARE<=hi+vehicle_crossings.FLARE
                       for row in walk.get('driveways',())):reason='neighbour_crossing_conflict'
            cols=xy.shape[1];point_count=SECTIONS*cols
            if reason is None and off is None:
                if 'receiving_terrain' not in record:
                    receiving=[(r,np.asarray(p.sections).reshape(-1,2)+offset) for r,p,o,_,why in record['choices'] if o is None and why is None]
                    points=np.concatenate([p for _,p in receiving])
                    values=np.asarray(ground(points),float).reshape(-1) if ground is not None else np.full(len(points),np.nan)
                    if len(values)!=len(points):values=np.full(len(points),np.nan)
                    record['receiving_terrain']={};at=0
                    for r,p in receiving:record['receiving_terrain'][r]=values[at:at+len(p)];at+=len(p)
                    if audit is not None:
                        audit.record('work','terrain_calls',int(ground is not None))
                        audit.record('work','terrain_points',len(points));audit.record('work','terrain_jobs',len(receiving))
                        audit.record('crossings','receiving_area_evaluated')
                ground_z=record['receiving_terrain'][rank].reshape(SECTIONS,cols)
            else:
                ground_z=terrain[off:off+point_count].reshape(SECTIONS,cols) if reason is None else None
            if reason is None and not np.isfinite(ground_z).all():reason='missing_terrain'
            if reason is None and proposal.mode=='connected' and spec.access.garage_z is None:reason='missing_garage_height'
            if reason is None:
                if proposal.mode=='crossing_only':reach=5.5
                target=ground_z[-1].max()+.01 if portal.height is None else portal.height
                start=spec.access.garage_z if proposal.mode=='connected' else float(ground_z[0].max()+.03)
                height=hermite(t,start,target,reach,grade0=-.02 if proposal.mode=='connected' else 0.,grade1=-.015 if portal.crossing else 0.)
                widths=np.linalg.norm(xy[:,-1]-xy[:,0],axis=1)
                fall=t*t*(3-2*t)*portal.crossfall*widths/2
                z=np.column_stack((height-fall,height+fall))
                lengths=np.linalg.norm(np.diff(xy[:,cols//2],axis=0),axis=1)
                grades=np.diff(z,axis=0)/lengths[:,None]
                full_z=height[:,None]+np.linspace(-1,1,cols)[None,:]*fall[:,None]
                if portal.rear:
                    end_z=np.asarray(portal.rear)[:,2]
                    full_z+=(t*t*(3-2*t))[:,None]*(end_z-full_z[-1])[None,:]
                    z=full_z[:,[0,-1]]
                    grades=np.diff(full_z,axis=0)/np.maximum(np.linalg.norm(np.diff(xy,axis=0),axis=2),1e-9)
                fill=full_z-ground_z
                if (np.any(lengths<1e-6) or np.any(np.abs(grades)>MAX_GRADE)
                        or np.any(fill<.004) or np.any(fill>MAX_FILL)):reason='grading'
            if reason is not None:
                failures.append('driveway_omitted_'+reason)
                outcomes.append(f'driveway_candidate_{rank}_rejected_{reason}')
                rejected('route_'+reason)
                continue
            panels=[]
            for i in range(SECTIONS-1):
                for left,right in ([(0,cols-1)] if not portal.rear else zip(range(cols-1),range(1,cols))):
                    p=(tuple((*xy[i,left],full_z[i,left])),tuple((*xy[i+1,left],full_z[i+1,left])),
                       tuple((*xy[i+1,right],full_z[i+1,right])),tuple((*xy[i,right],full_z[i,right])))
                    panels.append(Solid('driveway',p,float(ground_z[i:i+2].min()-.12)))
            keep=tuple(s for s in spec.access.solids if s.kind not in (('apron','driveway') if proposal.mode=='connected' else ('driveway',)) and
                       not (s.kind in ('path','paved_margin') and Polygon([p[:2] for p in s.top]).intersection(outline).area>1e-7))
            if spec.inference.selection.preset.id=='garage_outbuilding':keep=tuple(s for s in keep if s.kind!='threshold')
            linked=branch_build(branch,z,terrain[off+point_count:off+point_count+10]) if branch is not None else ()
            linked_shapes=[Polygon([p[:2] for p in s.top]) for s in linked]
            if any(conflicts(p) for p in linked_shapes):linked=();linked_shapes=[]
            if linked:keep=tuple(s for s in keep if s.kind not in ('path','path_link','path_landing','paved_margin'))+linked
            notes=tuple(n for n in spec.access.diagnostics if not n.startswith('driveway_'))
            outcomes.append(f'driveway_candidate_{rank}_selected')
            status='driveway_'+proposal.mode
            notes+=tuple(outcomes)+(OWNER_TOKEN_PREFIX+owner_id(spec),status)+(('driveway_pedestrian_link',) if linked else ())
            from .landscaping import trim_to_links
            landscape=tuple(s for s in trim_to_links(spec.access.landscape,linked) if all(
                Polygon([p[:2] for p in s.top]).intersection(p).area<1e-7 for p in (outline,*linked_shapes)))
            retire_owned(spec)
            spec.access=replace(spec.access,solids=keep+tuple(panels),diagnostics=tuple(sorted(notes)),landscape=landscape)
            if audit is not None:
                audit.record('outcomes',status)
                audit.record('candidates',f'selected_rank_{rank}')
                if portal.crossing is not None:audit.record('crossings',proposal.mode)
            spec.facades=None
            for poly in (outline,*linked_shapes):
                for key in buckets(poly):accepted.setdefault(key,[]).append(poly)
            if portal.crossing:
                wi,lo,hi=portal.crossing
                interval=(lo,hi)
                for collection in (actual_walks,raw_walks if raw_walks is not actual_walks else None):
                    if collection is None or wi>=len(collection):continue
                    walk=collection[wi]
                    walk.setdefault('driveways',[]).append(interval)
                    walk.setdefault('building_driveways',[]).append(interval)
                    owners=dict(walk.get('building_driveway_owners',{}))
                    owners[owner_id(spec)]=[interval]
                    walk['building_driveway_owners']=owners
            if drives is not None:
                drives.append(dict(m='road_asphalt_2lane',w=float(widths.max()),tl=11.,p=19,
                                   n=[[*p,0.] for p in xy[:,cols//2]+offset],bne_access_only=True,bne_building_driveway=True,
                                   bne_building_owner=owner_id(spec)))
            selected=True
            break
        if not selected:
            message=('driveway_omitted_all_candidates' if len(record['choices'])>1 else
                     failures[-1] if failures else 'driveway_omitted_no_direct_frontage')
            previous=any(s.kind=='driveway' for s in spec.access.solids)
            if previous:
                message='driveway_replan_retained_previous'
                notes=tuple(n for n in spec.access.diagnostics if not n.startswith('driveway_candidate_') and n!=message)
            else:
                retire_owned(spec)
                notes=tuple(n for n in spec.access.diagnostics if not n.startswith('driveway_'))
            spec.access=replace(spec.access,diagnostics=tuple(sorted(notes+tuple(outcomes)+(message,))))
            if audit is not None:
                audit.record('outcomes',message)
                if record['crossing']:
                    audit.record('crossings','receiving_area_rejected' if 'receiving_terrain' in record else 'internal_route_failed_receiving_area_untested')
