"""Bounded garage traversal geometry and road-interface adapter.

Dimensions are gameplay envelopes, not a regional building-code profile. Only
accepted access is emitted; unsupported terrain/topology keeps a diagnostic.
"""
from dataclasses import dataclass
from functools import lru_cache
import math

import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from .access import Solid

TURN_RADIUS = 5.0
VEHICLE_LENGTH = 5.2
VEHICLE_WIDTH = 2.1
CLEARANCE = .2
RAMP_EASE = 3.0
MAX_CANDIDATES = 4
MAX_ROAD_SEGMENTS = 64
MAX_FILL = .6
MAX_GRADE = .15
ROAD_LIP = .002


@dataclass(frozen=True, slots=True)
class GarageAccess:
    status: str
    portal: tuple = ()              # centre x/y, tangent x/y, full clear width
    route: tuple = ()               # ground-floor path into the first ramp
    surfaces: tuple[Solid, ...] = ()
    diagnostics: tuple = ()
    terrain_points: int = 0


def ramp_profile(length, rise):
    """Quadratic grade transitions with exactly level endpoints; bounded knots."""
    if length <= 2 * RAMP_EASE:
        return None
    grade = rise / (length - RAMP_EASE)
    x = np.unique(np.r_[np.linspace(0., RAMP_EASE, 9),
                        np.linspace(length-RAMP_EASE, length, 9)])
    z = np.where(x < RAMP_EASE, grade*x*x/(2*RAMP_EASE), grade*(x-RAMP_EASE/2))
    tail = length-x
    z = np.where(x > length-RAMP_EASE, rise-grade*tail*tail/(2*RAMP_EASE), z)
    return x, z, grade


def vehicle_sweep(points):
    """Conservative full-body hulls along sampled poses, including overhangs."""
    return _vehicle_sweep(tuple(tuple(map(float,p)) for p in points))


@lru_cache(maxsize=128)
def _vehicle_sweep(points):
    # GEOS geometries are immutable. Share identical near/lite/collision queries
    # in a bounded process cache, rather than unioning every pose three times.
    points = np.asarray(points, float)
    directions = np.diff(points, axis=0)
    if not len(directions) or np.any(np.linalg.norm(directions, axis=1) < 1e-8):
        return Polygon()
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    tangents = np.vstack((directions[0], directions[:-1]+directions[1:], directions[-1]))
    tangents /= np.maximum(np.linalg.norm(tangents, axis=1), 1e-9)[:, None]
    boxes = []
    for p, t in zip(points, tangents):
        n = np.array([-t[1], t[0]])
        a, c = t*(VEHICLE_LENGTH/2+CLEARANCE), n*(VEHICLE_WIDTH/2+CLEARANCE)
        boxes.append(Polygon([p-a-c, p+a-c, p+a+c, p-a+c]))
    return unary_union([unary_union((a, c)).convex_hull for a, c in zip(boxes, boxes[1:])])


def rounded_route(points):
    """Fillet orthogonal ground paths at the design turning radius; never shrink it."""
    clean = []
    for p in np.asarray(points, float):
        if clean and np.linalg.norm(p-clean[-1]) < 1e-6:
            continue
        while len(clean) >= 2:
            a, c = clean[-1]-clean[-2], p-clean[-1]
            if abs(np.cross(np.r_[a, 0.], np.r_[c, 0.])[2]) > 1e-6:
                break
            if a@c <= 0:
                return None
            clean.pop()
        clean.append(p)
    if len(clean) < 2:
        return None
    p = np.asarray(clean)
    directions = np.diff(p, axis=0)
    lengths = np.linalg.norm(directions, axis=1)
    directions /= lengths[:, None]
    if any(abs(a@c) > 1e-5 for a,c in zip(directions, directions[1:])):
        return None
    cuts = np.full(len(p), TURN_RADIUS); cuts[0] = cuts[-1] = 0.
    if np.any(lengths < cuts[:-1]+cuts[1:]-1e-6):
        return None
    result = [p[0]]
    for i in range(1, len(p)):
        start = p[i-1] + directions[i-1]*cuts[i-1]
        end = p[i] - directions[i-1]*cuts[i]
        count = max(1, int(math.ceil(np.linalg.norm(end-start)/.5)))
        result.extend(start+(end-start)*t for t in np.linspace(0,1,count+1)[1:])
        if i < len(p)-1:
            centre = end + directions[i]*TURN_RADIUS
            radial = end-centre
            sign = np.cross(np.r_[directions[i-1],0.],np.r_[directions[i],0.])[2]
            for angle in np.linspace(0,sign*math.pi/2,25)[1:]:
                rot = np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]])
                result.append(centre+rot@radial)
    return np.asarray(result)


def circulation(plan):
    """Ramp wells and full-vehicle U-turn sweeps shared with structure placement."""
    import buildings as b
    ring, floors, storey, (_, a, u, n, s0, s1) = plan
    w, e, gap = b.DECK_LANE_M, b.DECK_EDGE_M, b.DECK_RAMP_GAP_M
    depth = e+2*w+gap
    at = lambda s,d: a+u*s+n*d
    well = Polygon([at(s0,0),at(s1,0),at(s1,depth),at(s0,depth)])
    turn_sweeps = []
    for end, sign in ((s0,-1),(s1,1)):
        # A straight run-out prevents the rear overhang clipping the rail while
        # the vehicle starts its turn. Both U-turn ends land at the same level.
        centre = at(end+sign*1.5,e+w/2+TURN_RADIUS)
        theta = np.linspace(0,math.pi,65)
        path = centre+sign*TURN_RADIUS*np.sin(theta)[:,None]*u-TURN_RADIUS*np.cos(theta)[:,None]*n
        path=np.vstack((at(end,e+w/2),path,at(end,e+w/2+2*TURN_RADIUS)))
        turn_sweeps.append(vehicle_sweep(path))
    return well, tuple(turn_sweeps)


def reserved(spec, plan):
    well, turns = circulation(plan)
    areas = [well, *turns]
    access = getattr(spec, 'garage_access', None)
    if access and access.status == 'connected':
        areas.append(vehicle_sweep(access.route))
        x,y,dx,dy,width = access.portal
        t=np.array([dx,dy]); n=np.array([-dy,dx]); p=np.array([x,y])
        areas.append(Polygon([p-t*width/2-n, p+t*width/2-n,
                              p+t*width/2+n*3, p-t*width/2+n*3]))
    return unary_union(areas)


def _route(portal, inward, plan, shape, approach):
    import buildings as b
    _,_,_,(_,a,u,n,s0,s1)=plan
    depth=b.DECK_EDGE_M+2*b.DECK_LANE_M+b.DECK_RAMP_GAP_M
    c0=b.DECK_EDGE_M+b.DECK_LANE_M/2
    at=lambda s,d:a+u*s+n*d
    s,d=(portal-a)@u,(portal-a)@n
    # Complete the turn before the ramp rail begins, including front overhang.
    left, right = s0-TURN_RADIUS-1.5, s1+TURN_RADIUS+1.5
    nx,ny=inward@u,inward@n
    if abs(ny)>.999:
        points=[portal,at(s,depth+8),at(left,depth+8),at(left,c0),at(s0+3,c0)]
    elif nx>.999:
        points=[portal,at(left,d),at(left,c0),at(s0+3,c0)]
    elif nx<-.999:
        points=[portal,at(right,d),at(right,depth+8),at(left,depth+8),at(left,c0),at(s0+3,c0)]
    else:
        return None
    route=rounded_route(points)
    if route is None:return None
    sweep=vehicle_sweep(route)
    if not shape.union(approach).buffer(1e-6).covers(sweep):return None
    # The first ramp lane is the destination; every other part of the well is
    # excluded at ground level, including the space under sloping ramps.
    well,_=circulation(plan)
    lane=Polygon([at(s0,c0-b.DECK_LANE_M/2+.1),at(s1,c0-b.DECK_LANE_M/2+.1),
                  at(s1,c0+b.DECK_LANE_M/2-.1),at(s0,c0+b.DECK_LANE_M/2-.1)])
    if sweep.intersection(well.difference(lane)).area>1e-6:return None
    return route


def _walk_contact(portal, tangent, normal, road_end, width, walks, offset):
    """A straight whole-mouth crossing, preserving existing pedestrian ramps."""
    import sidewalks as sw
    import vehicle_crossings as vc
    corridor=LineString([portal,road_end]).buffer(width/2,cap_style=2)
    found=[]
    for wi,wk in enumerate(walks):
        if 'corner' in wk:
            corner=wk['corner']
            shape=Polygon(np.vstack((corner['arc'],corner['outer']))[:,:2]-offset)
            if not shape.is_valid or corridor.intersection(shape).area>1e-6:return None
            continue
        curb,out=sw.run_geometry(wk['pts'],wk['side'],wk.get('w',2.5))
        curb=curb.copy();curb[:,:2]-=offset
        w=wk.get('w',2.5)
        for j in range(len(curb)-1):
            strip=Polygon([curb[j,:2],curb[j+1,:2],curb[j+1,:2]+out[j+1]*w,curb[j,:2]+out[j]*w])
            if corridor.intersection(strip).area<=1e-6:continue
            if 'corner' in wk or wk.get('median') or w<vc.MIN_WIDTH:return None
            delta=curb[j+1,:2]-curb[j,:2];length=np.linalg.norm(delta);direction=delta/length
            if abs(direction@tangent)<.999 or out[j]@normal<.999:return None
            station=(portal-curb[j,:2])@direction
            arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(curb[:,:2],axis=0),axis=1))]
            s=arc[j]+station;half=width/2+.1
            if s-half-vc.FLARE<0 or s+half+vc.FLARE>arc[-1]:return None
            if any(hi>=s-half-vc.FLARE and lo<=s+half+vc.FLARE for lo,hi in wk.get('ramps',())):return None
            covered=np.flatnonzero((arc[:-1]<s+half+vc.FLARE)&(arc[1:]>s-half-vc.FLARE))
            segments=np.diff(curb[:,:2],axis=0)[covered]
            if np.any(segments@direction/np.maximum(np.linalg.norm(segments,axis=1),1e-9)<.999):return None
            if any(row[1]>=s-half-vc.FLARE and row[0]<=s+half+vc.FLARE for row in wk.get('driveways',())):return None
            centre=np.array([np.interp(s,arc,curb[:,k]) for k in range(3)])
            end=centre[:2]+normal*w
            if (portal-end)@normal<1.:return None
            edges=end+np.array([-1,1])[:,None]*tangent*width/2
            stations=(edges-centre[:2])@direction+s
            heights=np.interp(stations,arc,curb[:,2])+wk.get("curb_h",sw.CURB_H)+w*sw.CROSS_SLOPE
            checks=arc[(arc>stations.min())&(arc<stations.max())]
            if len(checks):
                order=np.argsort(stations)
                if np.max(abs(np.interp(checks,arc,curb[:,2])+wk.get("curb_h",sw.CURB_H)+w*sw.CROSS_SLOPE-
                              np.interp(checks,stations[order],heights[order])))>.001:return None
            found.append((wi, end, heights, (s-half,s+half,ROAD_LIP)))
    if not found:return False
    if len({v[0] for v in found})!=1:return None
    return found[0]


def resolve(items, lines, x0, y0, ground=None, walks=(), raw_walks=None, bounds=None):
    """Resolve one entrance/exit and solid apron per supported garage, before freeze."""
    import buildings as b
    from .topology import Footprint
    offset=np.array([x0,y0]); records=[];accepted=[]
    # Replanning a tile owns these cuts as well as its aprons. Remove only this
    # adapter's prior reservations, preserving residential crossings and ramps.
    for collection in (walks,raw_walks if raw_walks is not walks else None):
        for walk in collection or ():
            previous=walk.pop('garage_driveways',())
            remaining=list(walk.get('driveways',()))
            for interval in previous:
                match=next((i for i,row in enumerate(remaining) if tuple(row)==tuple(interval)),None)
                if match is not None:remaining.pop(match)
            if previous:
                if remaining:walk['driveways']=remaining
                else:walk.pop('driveways',None)
    # Read-only scene obstacles: full footprints, holes retained.
    # Until this adapter has a level-aware obstacle index, raised source volumes
    # are also exclusions: min_height > .5 does not prove vehicle headroom.
    obstacles=[(s,(s.footprint or Footprint(s.ring)).shape()) for s,_,_ in items]
    for s,_,_ in items:
        if s.access is not None:
            obstacles.extend((s,Polygon([p[:2] for p in solid.top]))
                             for solid in (*s.access.solids,*s.access.landscape))
    for spec,low,high in sorted(items,key=lambda item:(str(item[0].evidence.source_id if item[0].evidence else ''),float(item[0].seed or 0))):
        if not spec.deck:continue
        spec.garage_access=None
        plan=b.deck_plan(spec,low,high)
        if plan is None:
            spec.garage_access=GarageAccess('rejected',diagnostics=('garage_internal_layout_unfit',));continue
        if ground is None:
            spec.garage_access=GarageAccess('rejected',diagnostics=('garage_missing_terrain',));continue
        ring,_,_,(_,a,u,n,s0,s1)=plan
        shape=(spec.footprint or Footprint(ring)).shape()
        others=[p for s,p in obstacles if s is not spec and p.distance(shape)<b.GARAGE_DRIVE_MAX_M+10]
        if len(others)>64:
            spec.garage_access=GarageAccess('rejected',diagnostics=('garage_obstacle_budget',));continue
        segments=[]
        for line in lines:
            if len(line)>2 and line[2] in ('motorway','motorway_link'):continue
            for p,q in zip(np.asarray(line[0])[:-1,:2]-offset,np.asarray(line[0])[1:,:2]-offset):
                if LineString([p,q]).distance(shape)<=b.GARAGE_DRIVE_MAX_M+float(line[1]):
                    segments.append((p,q,float(line[1])))
        if len(segments)>MAX_ROAD_SEGMENTS:
            spec.garage_access=GarageAccess('rejected',diagnostics=('garage_road_query_budget',));continue
        candidates=[]; width=b.GARAGE_DRIVE_W
        for edge,(p,q) in enumerate(zip(ring,np.roll(ring,-1,axis=0))):
            length=np.linalg.norm(q-p)
            if length<width+1.:continue
            tangent=(q-p)/length;normal=np.array([-tangent[1],tangent[0]])
            positions={length/2}
            for goal in (a+u*(s0/2)+n*(b.DECK_EDGE_M+b.DECK_LANE_M/2),a+u*(s1+s0/2)+n*(b.DECK_EDGE_M+b.DECK_LANE_M/2)):
                positions.add(float(np.clip((goal-p)@tangent,width/2+.5,length-width/2-.5)))
            for along in sorted(positions):
                portal=p+tangent*along
                for ra,rb,half in segments:
                    v=rb-ra;ll=v@v
                    if ll<1e-6:continue
                    direction=v/math.sqrt(ll)
                    if abs(direction@tangent)<.999:continue
                    t=(portal-ra)@v/ll
                    if not 0<=t<=1:continue
                    centre=ra+t*v;end=centre+normal*half
                    distance=(portal-end)@normal
                    if not .5<distance<b.GARAGE_DRIVE_MAX_M:continue
                    candidates.append((distance,edge,along,portal,tangent,normal,end))
        diagnostics=[];points_used=0
        for _,edge,along,portal,tangent,normal,road_end in sorted(candidates,key=lambda c:c[:3])[:MAX_CANDIDATES]:
            mouth=Polygon([portal-tangent*width/2,portal+tangent*width/2,
                           road_end+tangent*width/2,road_end-tangent*width/2])
            if bounds is not None:
                lo=np.asarray(bounds[:2])-offset;hi=np.asarray(bounds[2:])-offset
                a0,b0,a1,b1=mouth.bounds
                if a0<lo[0] or b0<lo[1] or a1>hi[0] or b1>hi[1]:
                    diagnostics.append('garage_cross_tile_access_deferred');continue
            if any(mouth.intersection(p).area>1e-6 for p in (*others,*accepted)):
                diagnostics.append('garage_approach_obstructed');continue
            route=_route(portal,normal,plan,shape,mouth)
            if route is None:
                diagnostics.append('garage_internal_route_unfit');continue
            if any(vehicle_sweep(route).intersects(p) for p in others):
                diagnostics.append('garage_internal_route_obstructed');continue
            contact=_walk_contact(portal,tangent,normal,road_end,width,walks,offset)
            if contact is None:
                diagnostics.append('garage_unsupported_footpath');continue
            end=road_end if contact is False else contact[1]
            length=float((portal-end)@normal)
            if length<1.:
                diagnostics.append('garage_short_transition');continue
            # 33 three-point stations plus 17 road-mouth probes, <=464 samples
            # over four alternatives. Reject non-planar full-width road contact.
            t=np.linspace(0,1,33);centres=end+(portal-end)*t[:,None]
            xy=centres[:,None,:]+np.array([-width/2,0.,width/2])[None,:,None]*tangent
            mouth_across=np.linspace(-width/2,width/2,17)
            probes=end+mouth_across[:,None]*tangent
            samples=xy.reshape(-1,2) if contact is not False else np.vstack((xy.reshape(-1,2),probes))
            sampled=np.asarray(ground(samples+offset),float)
            points_used+=sampled.size
            if not np.isfinite(sampled).all():
                diagnostics.append('garage_missing_terrain');continue
            terrain=sampled[:99].reshape(33,3)
            z0=terrain[0,[0,2]]+ROAD_LIP if contact is False else contact[2]
            if contact is False and np.max(abs(np.interp(mouth_across,[-width/2,width/2],z0)-sampled[99:]))>.005:
                diagnostics.append('garage_road_contact_nonplanar');continue
            z1=high+.03
            grade0=0. if contact is False else .015
            z=(2*t**3-3*t**2+1)[:,None]*z0+(t**3-2*t**2+t)[:,None]*length*grade0+(-2*t**3+3*t**2)[:,None]*z1
            surface=np.column_stack((z[:,0],z.mean(axis=1),z[:,1]))
            fill=surface-terrain
            grades=np.diff(z,axis=0)/(length/32)
            if np.max(abs(grades))>MAX_GRADE or np.max(abs(z[:,1]-z[:,0])/width)>.02 or np.min(fill)<-1e-6 or np.max(fill)>MAX_FILL:
                diagnostics.append('garage_approach_grading');continue
            solids=[]
            for j in range(32):
                top=tuple(tuple(map(float,(*p,h))) for p,h in ((xy[j,0],z[j,0]),(xy[j+1,0],z[j+1,0]),
                      (xy[j+1,2],z[j+1,1]),(xy[j,2],z[j,1])))
                solids.append(Solid('garage_apron',top[::-1],float(terrain[j:j+2].min()-.1)))
            spec.garage_access=GarageAccess('connected',tuple(map(float,(*portal,*tangent,width))),
                tuple(tuple(map(float,p)) for p in route),tuple(solids),tuple(diagnostics),points_used)
            if contact is not False:
                wi,_,_,interval=contact
                walks[wi].setdefault('driveways',[]).append(interval)
                walks[wi].setdefault('garage_driveways',[]).append(interval)
                if raw_walks is not None and raw_walks is not walks and wi<len(raw_walks):
                    raw_walks[wi].setdefault('driveways',[]).append(interval)
                    raw_walks[wi].setdefault('garage_driveways',[]).append(interval)
            accepted.append(mouth)
            # Parking.clear_of consumes the last point as the road mouth.
            path=np.vstack((route[min(4,len(route)-1)],portal,road_end))+offset
            records.append(dict(m=b.DRIVEWAY['m'],w=width,tl=11.,p=19,bne_access_only=True,
                                n=[[*map(float,p),0.] for p in path]))
            break
        else:
            spec.garage_access=GarageAccess('rejected',diagnostics=tuple(diagnostics) or ('garage_no_usable_road',),terrain_points=points_used)
    return records


def draw_apron(mesh,spec,mat):
    access=getattr(spec,'garage_access',None)
    if access is None or access.status!='connected':return
    # One top owner and no internal vertical seams; shared portal/crossing edges.
    for solid in access.surfaces:
        mesh.quad(*solid.top,*[(p[0]/3,p[1]/3) for p in solid.top],mat)
