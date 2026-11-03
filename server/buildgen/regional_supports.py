"""Raised-house supports and porch roofs over already accepted access landings."""
import numpy as np
from .architectural_modifiers import has
from .regional_roof_details import box


def plan(spec,gmin=0.,gmax=0.):
    import buildings as b
    result=[]
    if has(spec,'stilts') and (spec.min_h or 0.)>.5 and spec.footprint.is_rectangle():
        base=b.base_z(spec,gmin,gmax)+(spec.min_h or 0.)
        c,u,hl,hw=b.oriented_box(np.asarray(spec.footprint.outer));v=np.array((-u[1],u[0]))
        for x in (-hl+.25,0.,hl-.25):
            for y in (-hw+.25,hw-.25):
                centre=c+u*x+v*y
                result.append(('stilt',box(centre,u,.12,.12,gmin-.2,base)))
    if (has(spec,'front_porch') or has(spec,'veranda')) and spec.access and spec.door and spec.height>=2.8:
        from shapely.geometry import Polygon
        landings=[s for s in spec.access.solids if s.kind in ('landing','step','porch_landing')
                  and abs(max(p[2] for p in s.top)-spec.access.door_z)<.06]
        if landings:
            landing=max(landings,key=lambda s:Polygon([p[:2] for p in s.top]).area)
            points=np.asarray(landing.top)
            c,u,hl,hw=b.oriented_box(points[:,:2]);v=np.array((-u[1],u[0]))
            if hl>.45 and hw>.22:
                z=float(points[:,2].max());roof=z+2.5
                result.append(('porch_roof',box(c,u,hl,hw,roof,roof+.14)))
                a=np.asarray(spec.ring[spec.door[0]]);d=np.asarray(spec.ring[(spec.door[0]+1)%len(spec.ring)])-a
                d/=np.linalg.norm(d);out=np.array((d[1],-d[0]))
                corners=[c+u*x+v*y for x in (-hl+.08,hl-.08) for y in (-hw+.08,hw-.08)]
                for point in sorted(corners,key=lambda p:float((p-a)@out),reverse=True)[:2]:
                    result.append(('porch_post',box(point,u,.055,.055,z,roof)))
    return tuple(result)


def draw(mesh,spec,gmin,gmax,material):
    for _,faces in plan(spec,gmin,gmax):
        for face in faces:mesh.quad(*face,(0,0),(1,0),(1,1),(0,1),material)


def vertex_count(spec):
    return sum(len(face) for _,faces in plan(spec) for face in faces)


def boxes(spec,gmin,gmax,x0,y0):
    for _,faces in plan(spec,gmin,gmax):
        p=np.array([point for face in faces for point in face])
        ring=faces[0]
        yield [float(p[:,0].min()+x0),float(p[:,1].min()+y0),float(p[:,2].min()),
               float(p[:,0].max()+x0),float(p[:,1].max()+y0),float(p[:,2].max()),
               [[[float(x+x0),float(y+y0)] for x,y,_ in ring]]]
