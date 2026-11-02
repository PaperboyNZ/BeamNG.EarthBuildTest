"""Small, deterministic planter assemblies in genuinely spare sidewalk width."""
import math
import numpy as np
from shapely.geometry import Point

CONTAINERS=('planter_square','planter_octagon','planter_trough')
GARDENS=('garden_square','garden_octagon','garden_trough')
GROUPS=CONTAINERS+GARDENS
GARDEN_RADIUS=.85
GARDEN_HEIGHT=.55
GARDEN_SOIL=-.04
GARDEN_MIN_WALK=3.8
RADIUS=.65
CLEAR=.15
HEIGHT=.65
SOIL=.48
MIN_WALK=3.4
MAX_PER_TILE=32


def fit(rows, lanes, access, obstacles, bounds=None):
    """Keep 1.5 m walking width and test the complete planter plus clearance.

    No pavement exemption is issued without a paired, supported planter. Narrow
    paths keep ordinary tree candidates for the adjacent-ground placement pass.
    """
    import furniture
    import sidewalks
    result=[];used=[];count=0
    for row in rows:
        if row[0]!='deciduous' or count>=MAX_PER_TILE or not lanes:
            result.append(row);continue
        point=Point(*row[1:3])
        lane=min(lanes,key=lambda lane:lane[0].distance(point))
        line,curb,out,arc,w,h=lane
        if w<MIN_WALK or line.distance(point)>w:
            result.append(row);continue
        garden=w>=GARDEN_MIN_WALK
        radius=GARDEN_RADIUS if garden else RADIUS
        station=line.project(point);selected=None
        for shift in (0.,-1.,1.,-2.,2.,-4.,4.):
            s=station+shift
            if not 8.+radius<=s<=arc[-1]-8.-radius:continue
            base=np.array([np.interp(s,arc,curb[:,j]) for j in range(3)])
            normal=np.array([np.interp(s,arc,out[:,j]) for j in range(2)])
            normal/=max(np.linalg.norm(normal),1e-9)
            offset=radius+CLEAR+.22
            pos=base.copy();pos[:2]+=normal*offset
            pos[2]+=h+sidewalks.CROSS_SLOPE*offset-.035
            footprint=Point(*pos[:2]).buffer(radius+CLEAR)
            if bounds is not None and not (bounds[0]<=pos[0]<bounds[2] and bounds[1]<=pos[1]<bounds[3]):continue
            if len(access.query(footprint,predicate='intersects')) or len(obstacles.query(footprint,predicate='intersects')):continue
            if any(footprint.intersects(other) for other in used):continue
            # Keep lamps, hydrants and other candidates' original support space.
            if any(other is not row and other[0] not in ('deciduous','lamplens','lampglow')
                   and math.hypot(other[1]-pos[0],other[2]-pos[1])<2.2 for other in rows):continue
            # Short, level-sided containers tolerate sidewalk crossfall; reject
            # steep longitudinal runs rather than leave a floating container.
            j=min(len(arc)-2,max(0,int(np.searchsorted(arc,s)-1)))
            if abs(curb[j+1,2]-curb[j,2])/max(arc[j+1]-arc[j],1e-9)>.04:continue
            selected=pos;used.append(footprint);break
        if selected is None:
            result.append(row);continue
        variant=min(2,int(furniture._h01(row[4],row[7],'planter')*3))
        yaw=math.degrees(math.atan2(normal[1],normal[0]))
        kind=(GARDENS if garden else CONTAINERS)[variant]
        planter=[kind,*map(float,selected),yaw,1.,GARDEN_HEIGHT if garden else HEIGHT,0.]
        if garden:
            ring=garden_ring(kind)
            angle=math.radians(yaw);rotation=np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]])
            xy=ring@rotation.T+selected[:2]
            planter.append({'garden':dict(ring=np.column_stack((xy,np.full(len(xy),selected[2]))).tolist(),kind=kind)})
        tree=['planted_tree',float(selected[0]),float(selected[1]),float(selected[2]+(GARDEN_SOIL if garden else SOIL)),
              row[4],1.,min(6.5,max(5.,row[6]*.75)) if garden else min(3.5,max(2.6,row[6]*.35)),0.]
        result.extend((planter,tree));count+=1
    return result


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
            strip=Polygon(np.vstack((curb[:,:2],back[::-1])))
            found=[g for g in gardens if strip.intersects(Polygon(np.asarray(g['ring'])[:,:2]))]
            if found:wk['tree_gardens']=found
