"""Bounded roof/underfloor solids shared by visual, collision and skyline tiers."""
from functools import lru_cache
import math
import numpy as np
from . import architectural_modifiers as modifiers, roofs, roof_edges


def box(centre, u, hx, hy, low, high):
    c, u = np.array(centre), np.array(u); v = np.array((-u[1], u[0]))
    ring = [c + u*x + v*y for x,y in ((-hx,-hy),(hx,-hy),(hx,hy),(-hx,hy))]
    return tuple(tuple((*p,z) for p,z in face) for face in
                 [tuple((p,high) for p in ring), tuple((p,low) for p in reversed(ring))] +
                 [((a,low),(b,low),(b,high),(a,high)) for a,b in zip(ring,ring[1:]+ring[:1])])


def plan(spec):
    if getattr(spec.inference, 'roof_solver', 'detailed') == 'fast' and spec.roof != 'flat':return ()
    if not spec.inference or spec.plain or spec.church or spec.terminal or spec.city or spec.deck:
        return ()
    return _plan(spec.footprint, spec.roof_outline, spec.roof, roofs.variant(spec),
                 spec.inference.roof_rise, spec.inference.modifiers, spec.min_h or 0.)


@lru_cache(maxsize=256)
def _plan(fp, outline, kind, variant, rise, selected, min_h):
    import buildings as b
    from shapely.geometry import Polygon
    c,u,hl,hw=b.oriented_box(np.array(fp.outer));u=np.array(u);v=np.array((-u[1],u[0]))
    shape=fp.shape(); result=[]
    def add_box(kind, material, centre, direction, hx, hy, low, high):
        faces=box(centre,direction,hx,hy,low,high)
        if high>low and shape.covers(Polygon([p[:2] for p in faces[0]])):
            result.append((kind,material,faces))
    if kind!='flat':
        roof=roofs.envelope(outline or fp,kind,variant,solver='detailed')
        from .stepped_gables import fits
        if 'stepped_gable' in selected and fits(fp,kind,variant,rise):
            for a,d in zip(fp.outer,fp.outer[1:]+fp.outer[:1]):
                a,d=np.array(a),np.array(d);direction=(d-a)/np.linalg.norm(d-a)
                inward=np.array((-direction[1],direction[0]));length=float(np.linalg.norm(d-a))
                if roof_edges.height(roof,(a+d)/2)<.5:continue
                from .topology import Footprint,triangles
                # A narrow central pier and brick-sized stair bays, rather than
                # a few very broad platforms spread across the whole end wall.
                steps=max(3,min(5,round(rise/.55)));count=2*steps+1
                crown=min(1.20,max(.80,length*.15))
                bay=(length-crown)/(2*steps)
                divisions=[i*bay for i in range(steps+1)]
                divisions += [length/2+crown/2+i*bay for i in range(steps+1)]
                heights=[]
                for i in range(count):
                    s0,s1=divisions[i:i+2]
                    # Include the ridge: endpoint-only sampling left the roof
                    # poking above the centre crown in the previous version.
                    peak=max(roof_edges.height(roof,a+direction*s)*rise for s in (s0,(s0+s1)/2,s1))
                    heights.append(min(rise-.10,peak+.08))
                # One continuous masonry prism, not overlapping thin boxes.
                # Broad courses and a central crown replace serrated railings.
                outline2=[(0.,0.),(length,0.),(length,heights[-1])]
                for i in range(count-1,-1,-1):
                    outline2.append((divisions[i],heights[i]))
                    if i: outline2.append((divisions[i],heights[i-1]))
                profile=Footprint(tuple(outline2))
                def point(p,depth):
                    xy=a+direction*p[0]+inward*depth
                    return (float(xy[0]),float(xy[1]),p[1])
                faces=[]
                for tri in triangles(profile):
                    faces.append(tuple(point(p,-.035) for p in tri))
                    faces.append(tuple(point(p,.44) for p in reversed(tri)))
                for p,q in zip(profile.outer,profile.outer[1:]+profile.outer[:1]):
                    faces.append((point(p,-.035),point(p,.44),point(q,.44),point(q,-.035)))
                result.append(('stepped_gable','wall',tuple(faces)))
                # Light coping stones give every tread a readable horizontal
                # edge. Keep the crown at the existing resolved roof peak.
                for i,z in enumerate(heights):
                    left,right=divisions[i:i+2]
                    centre=a+direction*((left+right)/2)+inward*.20
                    result.append(('gable_coping','coping',box(centre,direction,(right-left)/2+.025,.275,z,z+.10)))
        if 'large_chimneys' in selected and rise>=1.5 and min(hl,hw)>2.5:
            centre=c+u*min(hl*.45,3.)+v*hw*.45
            points=[centre+u*x+v*y for x,y in ((-.6,-.42),(.6,-.42),(.6,.42),(-.6,.42))]
            low=min(roof_edges.height(roof,p)*rise for p in points)-.08
            high=rise-.30
            if high-low>.6:
                add_box('large_chimney','brick',centre,u,.60,.42,low,high)
                add_box('chimney_cap','stone',centre,u,.67,.49,high,high+.12)
                for sign in (-1,1):
                    add_box('chimney_pot','brick',centre+u*sign*.30,u,.13,.13,high+.12,rise)
    elif min(hl,hw)>2.:
        if 'roof_terrace' in selected or 'water_tanks' in selected:
            # A recessed roof deck with a continuous parapet inside the source
            # footprint. Top remains the mapped building top.
            inset=shape.buffer(-.22,join_style='mitre')
            if inset.geom_type=='Polygon' and inset.area>4.:
                for a,d in zip(fp.outer,fp.outer[1:]+fp.outer[:1]):
                    a,d=np.array(a),np.array(d);direction=(d-a)/np.linalg.norm(d-a)
                    normal=np.array((-direction[1],direction[0]))
                    add_box('parapet','wall',(a+d)/2+normal*.12,direction,
                            np.linalg.norm(d-a)/2,.12,-.9,0.)
        if 'water_tanks' in selected:
            # One tank on a recessed pad, with its modest top extension included
            # in visual tiers, collision geometry and occupancy bounds.
            centre=c+u*min(hl*.35,2.)+v*min(hw*.28,1.5)
            radius=.82
            circle=[centre+radius*np.array((math.cos(t),math.sin(t))) for t in np.linspace(0,2*math.pi,13)[:-1]]
            if shape.buffer(-.4).covers(Polygon(circle)):
                faces=[]
                for a,d in zip(circle,circle[1:]+circle[:1]):
                    faces.append(((*a,-.88),(*d,-.88),(*d,.55),(*a,.55)))
                    faces.append(((*centre,.55),(*a,.55),(*d,.55)))
                result.append(('water_tank','tank',tuple(faces)))
                add_box('tank_lid','tank',centre,u,.18,.18,.55,.65)
    return tuple(result)


def recessed_deck(spec):
    return spec.roof=='flat' and bool(plan(spec))


def draw(mesh,spec,top,looks):
    for kind, material, faces in plan(spec):
        if kind=='stepped_gable':
            from .materials import wall_scale
            su,sv=wall_scale(spec.inference.facade.value)
            centre=np.mean([p[:2] for face in faces for p in face],axis=0)
            edges=list(zip(spec.footprint.outer,spec.footprint.outer[1:]+spec.footprint.outer[:1]))
            lengths=[float(np.linalg.norm(np.asarray(d)-a)) for a,d in edges]
            index=min(range(len(edges)),key=lambda i:abs(float(
                np.array((edges[i][1][1]-edges[i][0][1],edges[i][0][0]-edges[i][1][0])) @
                (centre-edges[i][0])))/lengths[i])
            origin=np.asarray(edges[index][0]);direction=(np.asarray(edges[index][1])-origin)/lengths[index]
            run=sum(lengths[:index])
        for face in faces:
            points=[(x,y,top+z) for x,y,z in face]
            uv=[(float(i%2),float(i//2)) for i in range(len(face))]
            if kind=='stepped_gable':
                # Metric planar UVs: never stretch one brick texture over each
                # triangulated piece of the gable.
                uv=[((run+float((np.asarray(p[:2])-origin)@direction))/su,(spec.height+p[2])/sv) for p in face]
            if len(face)==3:mesh.tri(*points,*uv,looks[material])
            else:mesh.quad(*points,*uv,looks[material])


def vertex_count(spec):
    return sum(len(face) for _,_,faces in plan(spec) for face in faces)


def gable_boxes(spec,gmin,gmax,x0,y0):
    """Include the projecting masonry/coping in physical occupancy checks."""
    import buildings as b
    from shapely.geometry import MultiPoint
    groups=[]
    for kind,_,faces in plan(spec):
        if kind=='stepped_gable':groups.append([])
        if kind in ('stepped_gable','gable_coping'):
            groups[-1].extend(p for face in faces for p in face)
    top=b.base_z(spec,gmin,gmax)+(spec.min_h or 0.)+spec.height
    for group in groups:
        points=np.asarray(group)
        hull=MultiPoint(points[:,:2]).convex_hull
        yield [float(points[:,0].min()+x0),float(points[:,1].min()+y0),float(points[:,2].min()+top),
               float(points[:,0].max()+x0),float(points[:,1].max()+y0),float(points[:,2].max()+top),
               [[[float(x+x0),float(y+y0)] for x,y in list(hull.exterior.coords)[:-1]]]]


def top_extension(spec):
    return max(0.,max((p[2] for _,_,faces in plan(spec) for face in faces for p in face),default=0.)
               -(spec.inference.roof_rise if spec.inference else 0.))


def looks(spec,mats):
    import buildings as b
    return dict(wall=mats[spec.facade],brick=mats['bne_brick_red'],
                stone=mats[b.custom_look(b.PANEL,(.54,.53,.50))],
                coping=mats[b.custom_look(b.PANEL,(.78,.76,.69))],
                tank=mats[b.custom_look(b.PANEL,(.19,.20,.20))])
