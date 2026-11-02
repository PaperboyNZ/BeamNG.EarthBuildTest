"""Final, indexed exclusion of roadside furniture from traversable surfaces."""
import numpy as np
from shapely import STRtree
from shapely.geometry import LineString, Point, Polygon

# Conservative full footprints (metres), including the prop's overhang and a
# small clearance. These are not point-in-path tests: a bin's edge matters too.
RADII = {'bin': .45, 'hydrant': .3, 'bench': 1.4, 'streetlight': .3,
         'pole': .3, 'polelamp': .3, 'lamplens': .3, 'lampglow': .3,
         'stop': .65, 'giveway': .65, 'signal': .7, 'deciduous': 1.2}


def keepouts(walks=(), items=(), drives=(), lines=(), chunks=(), origin=(0., 0.)):
    import sidewalks as sw
    import vehicle_crossings as vc
    from shapely.affinity import translate
    result = []
    def polygon(points):
        p = Polygon(np.asarray(points)[:,:2])
        if not p.is_valid: p = p.convex_hull
        if p.is_valid and p.area > 1e-8: result.append(p)
    for walk in walks or ():
        if walk.get('median'): continue
        if 'corner' in walk:
            c = walk['corner']
            polygon(np.vstack((c['arc'],c['outer'])))
            continue
        w = float(walk.get('w',2.5))
        curb, out = sw.run_geometry(walk['pts'],walk['side'],w)
        kept = sw.simplify(np.c_[curb,out],tol=1e-6)
        curb,out = curb[kept],out[kept]
        arc = np.r_[0.,np.cumsum(np.linalg.norm(np.diff(curb[:,:2],axis=0),axis=1))]
        rear = curb[:,:2]+out*w
        inner = curb[:,:2]+out*max(0.,w-1.5)
        for j in range(len(curb)-1):
            polygon([inner[j],inner[j+1],rear[j+1],rear[j]])
        for row in (*walk.get('ramps',()),*walk.get('driveways',())):
            lo, hi = max(0.,row[0]-max(vc.FLARE,sw.RAMP_FLARE)-.2), min(arc[-1],row[1]+max(vc.FLARE,sw.RAMP_FLARE)+.2)
            if hi <= lo: continue
            stations = np.r_[lo,arc[(arc>lo)&(arc<hi)],hi]
            xy = np.column_stack([np.interp(stations,arc,curb[:,i]) for i in (0,1)])
            directions = np.column_stack([np.interp(stations,arc,out[:,i]) for i in (0,1)])
            front, back = xy-directions*.7, xy+directions*(w+.4)
            for j in range(len(stations)-1):
                polygon([front[j],front[j+1],back[j+1],back[j]])
    for spec, _, _ in items or ():
        access = getattr(spec,'access',None)
        solids = list(access.solids) if access else []
        garage = getattr(spec,'garage_access',None)
        if garage: solids.extend(garage.surfaces)
        for solid in solids:
            if solid.kind in ('site_curb',): continue
            shape = Polygon(np.asarray(solid.top)[:,:2])
            if shape.is_valid and not shape.is_empty:
                result.append(translate(shape,xoff=origin[0],yoff=origin[1]))
    for drive in drives or ():
        p = np.asarray(drive.get('n',()),float)
        if len(p)>=2: result.append(LineString(p[:,:2]).buffer(float(drive.get('w',3.))/2+.2))
    for line in lines or ():
        if len(line)>2 and line[2] in ('footway','path','pedestrian','steps','cycleway','service','driveway'):
            result.append(LineString(np.asarray(line[0])[:,:2]).buffer(float(line[1])+.2))
    for chunk in chunks or ():
        if 'crossing' not in chunk.get('m',''): continue
        p = np.asarray(chunk.get('n',()),float)
        if len(p)>=2: result.append(LineString(p[:,:2]).buffer(float(chunk.get('w',3.))/2+.2))
    return result


def clear(rows, *, wires=None, areas=None, walks=(), items=(), lines=(),
          origin=(0.,0.), ground=None, bounds=None, diagnostics=None, **context):
    """Fit nearby supported positions, preserving whole lamp assemblies.

    At most eight already-validated alternatives accompany an assembly. The
    client can select another when neighbouring access masks arrive later.
    Unknown terrain never licenses moving a prop behind the sidewalk.
    """
    import sidewalks as sw
    import furniture
    from shapely.affinity import translate
    areas = keepouts(walks=walks,items=items,lines=lines,origin=origin,**context) if areas is None else areas
    if not rows: return rows
    tree = STRtree(areas)
    obstacles=[]
    for spec,_,_ in items or ():
        ring=getattr(spec,'ring',None)
        if ring is not None:
            shape=Polygon(np.asarray(ring)[:,:2])
            if shape.is_valid: obstacles.append(translate(shape,*origin).buffer(.2))
    # Relocation cannot put a post into a carriageway, even without a sidewalk.
    for line in lines or ():
        if len(line)>1 and len(line[0])>=2:
            obstacles.append(LineString(np.asarray(line[0])[:,:2]).buffer(float(line[1])+.15))
    obstacle_tree=STRtree(obstacles)
    lanes=[]
    for walk in walks or ():
        if 'pts' not in walk or walk.get('median'): continue
        w=float(walk.get('w',2.5))
        curb,out=sw.run_geometry(walk['pts'],walk['side'],w)
        arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(curb[:,:2],axis=0),axis=1))]
        if arc[-1]>.01: lanes.append((LineString(curb[:,:2]),curb,out,arc,w,float(walk.get('curb_h',.15))))
    lane_tree=STRtree([lane[0] for lane in lanes])
    def radius(row):
        value=RADII.get(row[0])
        if value is None and str(row[0]).startswith('site_'):
            from buildgen.landscaping import native_radius,NATIVE_ASSETS
            if row[0] in NATIVE_ASSETS:value=native_radius(row[0],row[6])
        if value is None:return None
        value*=max(1.,float(row[5]))
        if row[0]=='deciduous':value=max(value,float(row[6])*.25)
        return value+.15
    # Accessories use their support's footprint and selection, never their
    # elevated/offset lens position. Regenerate lenses after moving supports.
    accessories={'lamplens','lampglow'}
    supports=[r for r in rows if r[0] not in accessories]
    roots={id(r):r for r in supports}
    poles={(round(r[1],2),round(r[2],2)):r for r in supports if r[0]=='pole'}
    for r in supports:
        if r[0]=='polelamp': roots[id(r)]=poles.get((round(r[1],2),round(r[2],2)),r)
    occupied=[];moves={};choices={};old_poles=[]
    # Reserve already-clear supports before moving others, so a relocation
    # cannot steal a later bin/sign's valid original position.
    reserved=[];reserved_owners=[]
    for r in supports:
        rad=radius(r)
        if roots[id(r)] is not r or rad is None:continue
        footprint=Point(*r[1:3]).buffer(rad)
        if not len(tree.query(footprint,predicate='intersects')):
            reserved.append(footprint);reserved_owners.append(id(r))
    reserved_tree=STRtree(reserved)
    stats=dict(kept=0,moved=0,unplaced=0)
    movable={'streetlight','pole','polelamp','hydrant','bin','bench'}
    for r in supports:
        if roots[id(r)] is not r:continue
        rad=radius(r)
        if rad is None:moves[id(r)]=np.zeros(3);continue
        old=np.array(r[1:4],float)
        def safe(pos,relocated=False):
            footprint=Point(*pos[:2]).buffer(rad)
            if len(tree.query(footprint,predicate='intersects')):return False
            if any(footprint.intersects(p) for p in occupied):return False
            if relocated:
                if bounds is not None and not (bounds[0]<=pos[0]<bounds[2] and bounds[1]<=pos[1]<bounds[3]):return False
                if len(obstacle_tree.query(footprint,predicate='intersects')):return False
                if any(reserved_owners[i]!=id(r) for i in reserved_tree.query(footprint,predicate='intersects')):return False
                if abs(pos[2]-old[2])>1.0:return False
            return True
        candidates=[]
        if safe(old):candidates.append(old)
        if r[0] in movable and lanes:
            lane=lanes[int(lane_tree.nearest(Point(*old[:2])))]
            line,curb,out,arc,w,h=lane
            if line.distance(Point(*old[:2]))<=w+3:
                at=line.project(Point(*old[:2]))
                proposals=[]
                for shift in (0.,-2.,2.,-4.,4.,-8.,8.,-12.,12.):
                    station=at+shift
                    if station<rad+1 or station>arc[-1]-rad-1:continue
                    base=np.array([np.interp(station,arc,curb[:,j]) for j in range(3)])
                    normal=np.array([np.interp(station,arc,out[:,j]) for j in range(2)])
                    normal/=max(np.linalg.norm(normal),1e-9)
                    offsets=[]
                    if w-1.5>=2*rad+.04:offsets.append(rad+.02)
                    if ground is not None:offsets.append(w+rad+.2)
                    for offset in offsets:
                        pos=base.copy();pos[:2]+=normal*offset
                        if offset<=w:pos[2]+=h+sw.CROSS_SLOPE*offset
                        proposals.append((pos,offset>w))
                rear=[pos for pos,needs_ground in proposals if needs_ground]
                heights=iter(np.asarray(ground(np.asarray(rear)[:,:2])).reshape(-1)) if rear else iter(())
                for pos,needs_ground in proposals:
                    if needs_ground:
                        z=next(heights,float('nan'))
                        if not np.isfinite(z):continue
                        pos[2]=float(z)
                    if safe(pos,True) and not any(np.linalg.norm(pos-v)<.1 for v in candidates):candidates.append(pos)
                    if len(candidates)>=8:break
        if candidates:
            selected=candidates[0];delta=selected-old
            moves[id(r)]=delta;choices[id(r)]=[list(map(float,c-selected)) for c in candidates]
            occupied.append(Point(*selected[:2]).buffer(rad))
            stats['moved' if np.linalg.norm(delta)>.01 else 'kept']+=1
        else:moves[id(r)]=None;stats['unplaced']+=1
        if r[0]=='pole':old_poles.append((old,moves[id(r)]))
    # A compiled wire span cannot follow a client's per-prop translation. Its
    # poles are relocated with the span here; late masks suppress that assembly
    # and its wire owner instead of leaving dangling wires at the old position.
    wired=bool(wires)
    kept=[];pending=[]
    for r in supports:
        root=roots[id(r)];delta=moves.get(id(root))
        if delta is None:continue
        r[1:4]=list(map(float,np.array(r[1:4])+delta))
        del r[8:]
        kept.append(r)
        pending.append((r,root))
    for r,root in pending:
        if root[0] in movable:
            r.append(dict(root=list(map(float,root[1:4])),group=root[0],height=float(root[6]),scale=float(root[5]),
                          wired=wired and root[0]=='pole',
                          choices=choices.get(id(root),[[0.,0.,0.]])[:1 if wired and root[0]=='pole' else 8]))
    for r in list(kept):
        if r[0] not in furniture.LAMP_HEADS:continue
        for lens in furniture.lamp_lenses([r]):
            if len(r)>8:lens.append(r[8])
            kept.append(lens)
    if wires is not None and old_poles:
        adjusted=[]
        for wire in wires:
            ends=[];valid=True
            for endpoint in (wire[0],wire[-1]):
                hits=[(np.linalg.norm(np.asarray(endpoint)[:2]-p[:2]),delta) for p,delta in old_poles]
                distance,delta=min(hits,key=lambda v:v[0])
                if distance<3 and delta is None:valid=False;break
                ends.append(delta if distance<3 else np.zeros(3))
            if valid:
                t=np.linspace(0,1,len(wire))[:,None]
                adjusted.append(np.asarray(wire)+(1-t)*ends[0]+t*ends[1])
        wires[:]=adjusted
    if diagnostics is not None:diagnostics.update(stats)
    return kept
