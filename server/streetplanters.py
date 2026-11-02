"""Small, deterministic planter assemblies in genuinely spare sidewalk width."""
import math
from functools import lru_cache
import numpy as np
from shapely.geometry import Point, Polygon
from shapely import STRtree, make_valid

CONTAINERS=('planter_square','planter_octagon','planter_trough')
GARDENS=('garden_square','garden_octagon','garden_trough')
GROUPS=CONTAINERS+GARDENS
GARDEN_RADIUS=.85
GARDEN_HEIGHT=.55
GARDEN_SOIL=-.04
RADIUS=.65
CLEAR=.15
HEIGHT=.65
SOIL=.48
MAX_PER_TILE=32


def fit(rows, lanes, access, obstacles, bounds=None, *, walks=(), radius_of=None):
    """Fit a real opening around a source tree before moving it off the walk.

    The oriented bed, including clearance, must fit the furnishing strip. Style
    comes from the walk's existing geographic palette, not a per-tree random
    country guess. Large trees keep their identity and size in ground gardens;
    containers are reserved for trees that were already small.
    """
    import sidewalks
    if not lanes or not any(r[0]=='deciduous' and not (len(r)>8 and isinstance(r[8],dict) and r[8].get('group') in GROUPS) for r in rows):
        return rows
    result=[];used=[];count=0
    lane_index=STRtree([lane[0] for lane in lanes])
    furniture_index=None
    styles=[w for w in walks if 'pts' in w and not w.get('median')]
    strips={}
    for row in rows:
        # A second clearance pass must not plant another bed beneath an
        # already paired tree. The root metadata survives that pass.
        paired=len(row)>8 and isinstance(row[8],dict) and row[8].get('group') in GROUPS
        if row[0]!='deciduous' or paired or count>=MAX_PER_TILE or not lanes:
            result.append(row);continue
        point=Point(*row[1:3])
        index=int(lane_index.nearest(point));lane=lanes[index]
        line,curb,out,arc,w,h=lane
        if w<2.49 or line.distance(point)>w:
            result.append(row);continue
        if index not in strips:
            back=curb[:,:2]+out*w
            strips[index]=make_valid(Polygon(np.vstack((curb[:,:2],back[::-1]))))
        style=styles[index] if index<len(styles) else {}
        kinds=variants(style,float(row[6]))
        station=line.project(point);best=None
        rear_offset=float(sidewalks.profile(h=h,w=w)[:,0].max())+max(.18,float(row[6])*.035)+.25+.12
        probe_s=station+np.array([0.,-.25,.25,-.5,.5,-1.,1.,-2.,2.,-3.,3.,-4.,4.])
        bases=np.column_stack([np.interp(probe_s,arc,curb[:,j]) for j in range(3)])
        normals=np.column_stack([np.interp(probe_s,arc,out[:,j]) for j in range(2)])
        normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-9)
        source_offsets=((np.asarray(row[1:3])-bases[:,:2])*normals).sum(axis=1)
        # Do not pull an off-path tree onto concrete just to decorate it.
        if not 0<=source_offsets[0]<=w:
            result.append(row);continue
        # Rank by actual displacement, not by shape or trial enumeration. A
        # trough at the original station beats an ornate bed metres away.
        for kind in kinds:
            garden=kind in GARDENS
            ring,outline,rx,ry,quarter_turn=bed_geometry(kind)
            if rx*2+.13>w-1.5:continue
            # A narrow tree opening is appropriate for modest street trees;
            # do not squeeze a mature mapped crown into a tiny pot or resize it.
            if garden and kind=='garden_trough' and row[6]>10.:continue
            ends=np.interp(np.stack((probe_s-ry,probe_s+ry)),arc,curb[:,2])
            possible=(probe_s>=8.+ry)&(probe_s<=arc[-1]-8.-ry)&(np.abs(ends[1]-ends[0])<=.07)
            if not possible.any():continue
            offsets=np.clip(source_offsets,rx+.12,w-1.5-rx-.01)
            positions=bases.copy();positions[:,:2]+=normals*offsets[:,None]
            positions[:,2]+=h+sidewalks.CROSS_SLOPE*offsets-.035
            distances=np.linalg.norm(positions[:,:2]-row[1:3],axis=1)
            possible&=distances<=np.maximum(.5,rear_offset-source_offsets)
            for j in np.argsort(distances,kind='stable'):
                if not possible[j]:continue
                s=probe_s[j];pos=positions[j];normal=normals[j];distance=float(distances[j])
                rotation=np.column_stack((normal,[-normal[1],normal[0]]))
                # A garden should reduce relocation, not send the tree farther
                # along the street than the ordinary nearest rear-ground option.
                if best is not None and distance>=best[0]-1e-8:break
                # Reject unsupported grades before constructing/querying polygons.
                stations=np.r_[s-ry,arc[(arc>s-ry)&(arc<s+ry)],s+ry]
                heights=np.interp(stations,arc,curb[:,2])
                if np.ptp(heights)>.07:continue
                footprint=Polygon(outline@rotation.T+pos[:2])
                if bounds is not None and not (bounds[0]<=footprint.bounds[0] and bounds[1]<=footprint.bounds[1] and footprint.bounds[2]<bounds[2] and footprint.bounds[3]<bounds[3]):continue
                if not strips[index].covers(footprint):continue
                if len(access.query(footprint,predicate='intersects')) or len(obstacles.query(footprint,predicate='intersects')):continue
                if any(footprint.intersects(other) for other in used):continue
                if furniture_index is None:
                    # No envelopes or index are needed on a street where grade,
                    # width or access rules already rule out every bed.
                    furniture_index=STRtree([Point(*r[1:3]).buffer(rad) for r in rows
                        if r[0] not in ('deciduous','lamplens','lampglow')
                        and (rad:=radius_of(r) if radius_of else .7) is not None])
                if len(furniture_index.query(footprint,predicate='intersects')):continue
                yaw=math.degrees(math.atan2(normal[1],normal[0]))+(90. if quarter_turn else 0.)
                best=(distance,pos,kind,ring,rotation,footprint,yaw)
                break
        if best is None:
            result.append(row);continue
        _,selected,kind,ring,rotation,footprint,yaw=best
        garden=kind in GARDENS;used.append(footprint)
        meta=dict(footprint=(np.asarray(footprint.exterior.coords)[:-1]-selected[:2]).tolist())
        planter=[kind,*map(float,selected),yaw,1.,GARDEN_HEIGHT if garden else HEIGHT,0.,meta]
        if garden:
            xy=ring@rotation.T+selected[:2]
            meta['garden']=dict(ring=np.column_stack((xy,np.full(len(xy),selected[2]))).tolist(),kind=kind)
        # Preserve original species alias, height, yaw and deterministic rank.
        tree=row
        tree[1:4]=[float(selected[0]),float(selected[1]),float(selected[2]+(GARDEN_SOIL if garden else SOIL))]
        tree[8:]=[dict(group=kind)]
        result.extend((planter,tree));count+=1
    return result


@lru_cache(maxsize=6)
def bed_geometry(kind):
    ring=garden_ring(kind) if kind in GARDENS else container_ring(kind)
    quarter_turn=kind=='planter_trough'
    if quarter_turn:ring=ring@np.array([[0.,1.],[-1.,0.]])
    local=Polygon(ring).buffer(.08,join_style='mitre')
    rx=max(abs(local.bounds[0]),abs(local.bounds[2]));ry=max(abs(local.bounds[1]),abs(local.bounds[3]))
    return ring,np.asarray(local.exterior.coords)[:-1],rx,ry,quarter_turn


def variants(style,height):
    """Authored regional palette, keyed on the already-resolved walk style."""
    pavement=style.get('pavement','slab')
    if pavement=='brick':gardens=('garden_square','garden_trough','garden_octagon')
    elif pavement=='stone':gardens=('garden_octagon','garden_square','garden_trough')
    else:gardens=('garden_trough','garden_square','garden_octagon')
    if height>3.5:return gardens
    pots=(('planter_octagon','planter_square','planter_trough') if pavement=='stone'
          else ('planter_square','planter_trough','planter_octagon'))
    # Continuous planted verges belong to the street, so prefer ground gardens.
    return (*gardens,*pots) if style.get('verge') else (*pots,*gardens)


def container_ring(kind):
    # Conservative authored model envelope, including the pot's top lip.
    if kind=='planter_trough':return np.array([[-.55,-.3],[.55,-.3],[.55,.3],[-.55,.3]])
    if kind=='planter_square':return np.array([[-.46,-.46],[.46,-.46],[.46,.46],[-.46,.46]])
    a=np.arange(8)*np.pi/4;return np.column_stack((np.cos(a),np.sin(a)))*.65


def garden_ring(kind):
    # Local X faces away from the road: beds extend mainly along the curb.
    if kind=='garden_square':return np.array([[-.6,-.6],[.6,-.6],[.6,.6],[-.6,.6]])
    if kind=='garden_octagon':
        a=np.arange(8)*np.pi/4;return np.column_stack((np.cos(a),np.sin(a)))*.80
    return np.array([[-.35,-.75],[.35,-.75],[.35,.75],[-.35,.75]])


def attach(walks, rows, raw_walks=None):
    """Only accepted fenced gardens cut pavement; copy into the rebased skin."""
    import sidewalks
    from shapely.geometry import Polygon
    gardens=[r[8]['garden'] for r in rows or () if len(r)>8 and 'garden' in r[8]]
    for group in (walks,raw_walks or ()):
        for wk in group or ():
            wk.pop('tree_gardens',None)
            if 'pts' not in wk:continue
            curb,out=sidewalks.run_geometry(wk['pts'],wk['side'],wk.get('w',2.5))
            back=curb[:,:2]+out*wk.get('w',2.5)
            strip=make_valid(Polygon(np.vstack((curb[:,:2],back[::-1]))))
            found=[g for g in gardens if strip.intersects(Polygon(np.asarray(g['ring'])[:,:2]))]
            if found:wk['tree_gardens']=found
