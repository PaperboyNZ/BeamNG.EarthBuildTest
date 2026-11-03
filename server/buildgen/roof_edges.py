"""Bounded style-aware roof construction, in metres (visual recipes, not codes).

Extend the original supporting planes, retaining ridges and slope breaks. A
separate box enlargement would move gambrel knees and detach fascia/gutters.
Polygon-local offsets retain mapped walls, courtyards and narrow recesses.
"""
from dataclasses import dataclass, replace
from functools import lru_cache
import math
import numpy as np
from .topology import Footprint, triangles


def _polygons(shape):
    """Ignore only numerical surface slivers, never repair source polygons."""
    from .topology import InvalidFootprint
    if shape.is_empty or shape.area<=1e-10:return ()
    if shape.geom_type=='Polygon':
        try:return (Footprint(shape.exterior.coords,tuple(r.coords for r in shape.interiors)),)
        except InvalidFootprint:
            if shape.area<=1e-8:return ()
            raise
    return tuple(p for g in getattr(shape,'geoms',()) for p in _polygons(g))


@dataclass(frozen=True, slots=True)
class Treatment:
    eave: float
    rake: float
    depth: float


def treatment(spec,outline=False):
    from . import regional_architecture as regional, roofs
    p=regional.base_profile(spec) or {}
    grammar=p.get('massing_grammar','')
    result=_treatment(getattr(spec,'roof_outline',None) or spec.footprint,grammar,roofs.variant(spec),spec.inference.use.value,
                      spec.floors,spec.inference.roof_material.value,spec.seed,
                      not outline and getattr(spec,'roof_outline',None) is None and 'footprint_clipped_clear_of_street' in (spec.diagnostics or ()))
    if 'roof_outline_narrow_flush_fallback' in (spec.diagnostics or ()):
        return replace(result,eave=0.,rake=0.)
    from .architectural_modifiers import has
    from .stepped_gables import for_spec as stepped_gable
    if has(spec,'stepped_gable') and stepped_gable(spec):
        # The roof terminates behind the masonry end, rather than drawing a
        # triangular bargeboard in front of the stepped silhouette.
        result=replace(result,rake=0.)
    if has(spec,'deep_eaves') and 'footprint_clipped_clear_of_street' not in (spec.diagnostics or ()):
        from .roof_domains import widths
        fp=getattr(spec,'roof_outline',None) or spec.footprint
        eave,rake=widths(fp,min(.72,result.eave*1.15),min(.45,result.rake*1.12))
        result=replace(result,eave=eave,rake=rake)
    return result


@lru_cache(maxsize=512)
def _treatment(footprint,grammar,variant,use,floors,family,seed,clipped):
    import buildings as b
    from . import materials
    # Shared construction families cover all regional and contemporary styles.
    eave,rake={
        'timber_veranda':(.48,.24), 'alpine_timber':(.60,.40),
        'east_asian_timber':(.65,.38), 'earthen_recess':(.18,.12),
        'compact_courtyard':(.20,.12), 'urban_shophouse':(.28,.16),
        'panel_modern':(.22,.16), 'plain_modern':(.30,.20),
        'arctic_modular':(.25,.18), 'screened_tropical':(.60,.30),
        'brick_pattern':(.32,.20), 'render_shutters':(.35,.22),
        'masonry_terrace':(.20,.12), 'arcaded_front':(.32,.20),
        'stone_loggia':(.38,.24),
    }.get(grammar,(.35,.22))
    if variant=='broad_eave':eave=max(eave,.60)
    if variant=='mansard':eave,rake=.24,.24
    if use in ('industrial','commercial'):eave,rake=min(eave,.30),min(rake,.20)
    if floors>4:eave,rake=min(eave,.25),min(rake,.18)
    _,_,hl,hw=b.oriented_box(np.asarray(footprint.outer))
    factor=.9+.2*materials.unit(seed,'roof-edge-proportions-v1')
    eave=min(eave*factor,min(hl,hw)*.16)
    rake=min(rake*factor,min(hl,hw)*.12)
    if clipped:
        from .road_conflicts import CLEARANCE
        # This margin was reserved by street clipping, not free building space.
        eave,rake=min(eave,CLEARANCE),min(rake,CLEARANCE)
    depth={'metal':.16,'shingle':.18,'slate':.20,'tile':.23,'concrete':.24,'thatch':.34}.get(family,.18)
    depth=min(depth,max(.10,min(hl,hw)*.12))
    if not footprint.is_rectangle():
        from .roof_domains import widths
        eave,rake=widths(footprint,eave,rake)
    return Treatment(round(eave,4),round(rake,4),depth)


def for_spec(spec):
    from . import roofs
    solver = getattr(spec.inference, 'roof_solver', 'detailed')
    if solver == 'fast':
        outline = getattr(spec, 'roof_outline', None)
        return roofs.envelope(outline, spec.roof, roofs.variant(spec), solver=solver) if outline is not None else roofs.for_spec(spec)
    if getattr(spec,'roof_outline',None) is not None:
        return roofs.envelope(spec.roof_outline,spec.roof,roofs.variant(spec),solver=solver)
    t=treatment(spec)
    if not t.eave:return roofs.for_spec(spec)
    return extended(spec.footprint,spec.roof,roofs.variant(spec),t.eave,t.rake,source=roofs.for_spec(spec))


def height(roof,xy):
    x,y=xy[0]-roof.centre[0],xy[1]-roof.centre[1]
    values=[a*x+b*y+h for a,b,h in roof.planes]
    if roof.strategy in ('orthogonal_wings','regional_flared_hip','regional_cross_gable'):
        return max(min(values[i:i+4]) for i in range(0,len(values),4))/roof.peak
    if roof.strategy.endswith('broad_eave'):
        # Outer shallow planes lie below the steep inner planes beyond knees.
        return max(min(values[0],values[3]),min(values[1],values[2]))/roof.peak
    return min(values)/roof.peak


@lru_cache(maxsize=256)
def extended(fp,kind,variant,eave,rake,domain=None,source=None):
    import buildings as b
    from . import roofs
    original=source if source is not None else roofs.envelope(fp,kind,variant)
    # A non-rectangular fallback has standard supporting planes regardless of
    # a requested regional silhouette. Do not index four-strip recipes on it.
    active_variant=variant if original.strategy=='regional_'+variant else 'standard'
    centre,u,hl,hw=b.oriented_box(np.asarray(fp.outer));v=np.array([-u[1],u[0]])
    end=eave if kind=='hipped' and variant in ('standard','mansard','flared_hip') else rake
    if domain is None:
        if fp.is_rectangle():
            domain=Footprint(tuple(tuple(centre+u*s*(hl+end)+v*t*(hw+eave))
                                  for s,t in ((-1,-1),(1,-1),(1,1),(-1,1))))
        else:
            from .roof_domains import offset
            domain=offset(fp,kind,active_variant,eave,rake)
            if domain is None:return original
    planes=[(np.array((a,c)),h) for a,c,h in original.planes]
    # Mapped height includes the upper edge of a shed. Lower its high wall fill
    # to the same plane instead of letting the overhang exceed the source top.
    if active_variant=='shed':
        factor=2*hw/(2*hw+eave)
        planes=[(a*factor,h*factor) for a,h in planes]
    pieces=[]
    for i,(a,h) in enumerate(planes):
        regions=(domain,)
        if original.strategy in ('orthogonal_wings','regional_flared_hip','regional_cross_gable'):
            # The upper union of per-wing lower envelopes, including its
            # supporting planes outside the original eave. Tie ownership is
            # stable so coplanar patches never double-render.
            wing=i//4
            for j,(other,oh) in enumerate(planes):
                if j//4!=wing or i==j:continue
                normal=other-a;den=float(normal@normal)
                if den<1e-20:continue
                point=centre+normal*((h-oh)/den)
                regions=tuple(p for r in regions for p in r.half(point,normal))
            from shapely.ops import unary_union
            for w in range(len(planes)//4):
                if w==wing:continue
                dominated=regions
                for other,oh in planes[w*4:w*4+4]:
                    normal=a-other;den=float(normal@normal)
                    if den<1e-20:
                        if oh<h-1e-9 or abs(oh-h)<1e-9 and w>wing:
                            dominated=();break
                        continue
                    point=centre+normal*((oh-h)/den)
                    dominated=tuple(p for r in dominated for p in r.half(point,-normal))
                if dominated:
                    cut=unary_union([r.shape() for r in dominated])
                    regions=tuple(p for r in regions for p in _polygons(r.shape().difference(cut)))
        elif active_variant=='broad_eave':
            bounds=((None,-.7),(-.7,0.),(0.,.7),(.7,None))[i]
            for t,n in ((bounds[0],v),(bounds[1],-v)):
                if t is not None:regions=tuple(p for r in regions for p in r.half(centre+v*t*hw,n))
        else:
            for j,(other,oh) in enumerate(planes):
                normal=other-a;den=float(normal@normal)
                if i==j or den<1e-20:continue
                point=centre+normal*((h-oh)/den)
                regions=tuple(p for r in regions for p in r.half(point,normal))
        pieces.extend((i,t) for r in regions if r.area>1e-10 for t in triangles(r,min_area=1e-10))
    roof=replace(original,planes=tuple((float(a[0]),float(a[1]),float(h)) for a,h in planes))
    def point(p):return (float(p[0]),float(p[1]),height(roof,p))
    boundary=[];wall_u=[];run=0.
    for ring in (domain.outer,*domain.holes):
        run=0.
        for pa,pb in zip(ring,ring[1:]+ring[:1]):
            a=np.asarray(pa);d=np.asarray(pb)-a;length=float(np.linalg.norm(d));cuts=[0.,1.]
            for i,(n,h) in enumerate(planes):
                for other,oh in planes[i+1:]:
                    delta=n-other;den=float(delta@d)
                    if abs(den)>1e-10:
                        t=-float(delta@(a-centre)+h-oh)/den
                        if 1e-8<t<1-1e-8:cuts.append(t)
            cuts=sorted(cuts);cuts=[x for i,x in enumerate(cuts) if i==0 or x-cuts[i-1]>1e-8]
            for s,t in zip(cuts,cuts[1:]):
                boundary.append((point(a+d*s),point(a+d*t)));wall_u.append((run+length*s,run+length*t))
            run+=length
    area=math.fsum(abs((t[1][0]-t[0][0])*(t[2][1]-t[0][1])-
                       (t[1][1]-t[0][1])*(t[2][0]-t[0][0]))*.5 for _,t in pieces)
    if not math.isclose(area,domain.area,rel_tol=1e-7,abs_tol=1e-6):
        raise ValueError('extended roof partition does not preserve occupied area')
    return replace(roof,triangles=tuple(tuple(point(p) for p in tri) for _,tri in pieces),
                   triangle_planes=tuple(i for i,_ in pieces),boundary=tuple(boundary),wall_u=tuple(wall_u))


def draw(mesh,spec,top,mats):
    """Fascia/barge boards and raking soffits meet the exact roof surface."""
    import buildings as b
    from . import facades
    roof=for_spec(spec);t=treatment(spec)
    layout=spec.facades or facades.plan(spec,0.,0.)
    mat=mats[layout.trim]
    centre,u,hl,hw=b.oriented_box(np.asarray(spec.footprint.outer));v=np.array([-u[1],u[0]])
    polygonal=not spec.footprint.is_rectangle()
    for p,q in roof.boundary:
        upper=[(x,y,top+h*spec.inference.roof_rise) for x,y,h in (p,q)]
        original_upper=upper
        if not t.eave:
            from .regional_architecture import band_point
            # Flush folded edging sits just outside cladding, including hole
            # boundaries; coplanar fascia would flicker against gable infill.
            for ring in (spec.footprint.outer,*spec.footprint.holes):
                matched=False
                for edge,(a,c) in enumerate(zip(ring,ring[1:]+ring[:1])):
                    d=np.subtract(c,a);length=float(np.linalg.norm(d));d/=length
                    s0,s1=float((np.array(p[:2])-a)@d),float((np.array(q[:2])-a)@d)
                    if (-1e-7<=s0<=length+1e-7 and -1e-7<=s1<=length+1e-7
                            and np.linalg.norm(np.array(p[:2])-a-d*s0)<1e-7
                            and np.linalg.norm(np.array(q[:2])-a-d*s1)<1e-7):
                        upper=[band_point(ring,edge,s0,upper[0][2],.012,0.),
                               band_point(ring,edge,s1,upper[1][2],.012,0.)]
                        matched=True;break
                if matched:break
        lower=[(x,y,z-t.depth) for x,y,z in upper]
        length=math.dist(p[:2],q[:2]);uv=((0.,0.),(length/3.,0.),(length/3.,t.depth/3.),(0.,t.depth/3.))
        mesh.quad(lower[0],lower[1],upper[1],upper[0],*uv,mat)
        if not t.eave:
            mesh.quad(original_upper[0],upper[0],upper[1],original_upper[1],*uv,mat)
            inner=[(x,y,z-t.depth) for x,y,z in original_upper]
            mesh.quad(inner[0],inner[1],lower[1],lower[0],*uv,mat)
            continue
        if polygonal:continue
        inner=[]
        for x,y,_ in lower:
            d=np.array([x,y])-centre
            xy=centre+u*np.clip(d@u,-hl,hl)+v*np.clip(d@v,-hw,hw)
            inner.append((*map(float,xy),top+height(roof,xy)*spec.inference.roof_rise-t.depth))
        mesh.quad(inner[0],inner[1],lower[1],lower[0],*uv,mat)
    if polygonal and t.eave:
        from shapely.geometry import Polygon
        wall=spec.footprint.shape()
        # Clip the underside against each roof patch, retaining its own plane
        # and every concave/courtyard boundary. Normals face down in both LODs.
        for tri,plane in zip(roof.triangles,roof.triangle_planes):
            apron=Polygon([p[:2] for p in tri]).difference(wall)
            ax,ay,h=roof.planes[plane]
            for part in _polygons(apron):
                for face in triangles(part,min_area=1e-10):
                    points=[(x,y,top+((ax*(x-roof.centre[0])+ay*(y-roof.centre[1])+h)/roof.peak)*spec.inference.roof_rise-t.depth)
                            for x,y in face[::-1]]
                    tex=[((x-centre[0])/3.,(y-centre[1])/3.) for x,y,z in points]
                    mesh.tri(*points,*tex,mat)
