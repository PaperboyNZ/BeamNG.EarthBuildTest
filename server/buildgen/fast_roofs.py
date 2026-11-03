"""Bounded scalar roof patches for inexpensive regional silhouettes.

Triangulate an occupied footprint once, then clip convex pieces numerically.
There are no intermediate GEOS polygons, unions, offsets or wing searches.
Courtyards and notches are retained, including boundary wall fills. The profile
uses the same planes as the detailed regional recipes on rectangular buildings;
on irregular buildings it is a clipped silhouette rather than a wing solution.
"""
from functools import lru_cache
from collections import OrderedDict
import math
import threading
import numpy as np

VARIANTS = frozenset(('standard', 'shed', 'saltbox', 'gambrel', 'mansard',
                      'broad_eave', 'industrial_barrel', 'flared_hip', 'cross_gable'))
MAX_VERTICES = 256
MAX_TRIANGLES = 8192
_DRAW_CACHE=OrderedDict()
_DRAW_LOCK=threading.RLock()
_DRAW_VERTICES=0


def draw(mesh,spec,top,mats,overhang=False):
    """Reuse exact numeric roof streams between visual and physical passes."""
    global _DRAW_VERTICES
    import buildings as b
    from . import roofs,regional_architecture as regional
    wall=mats[spec.facade]
    if isinstance(mats,b._Looks):
        _,wall=regional.wall_materials(spec,regional.for_spec(spec),mats,wall)
    r=spec.inference
    key=(spec.footprint,spec.roof_outline,spec.roof,roofs.variant(spec),r.roof_rise,
         spec.height,r.roof_material.value,r.facade.value,mats[spec.roof_mat],wall,overhang)
    with _DRAW_LOCK:
        data=_DRAW_CACHE.get(key)
        if data is not None:_DRAW_CACHE.move_to_end(key)
    if data is None:
        part=b.Mesh()
        roofs._draw(part,spec,0.,mats,overhang)
        data=part.arrays()
        count=len(data[0])
        if count<=32768:
            with _DRAW_LOCK:
                if key not in _DRAW_CACHE:
                    while _DRAW_CACHE and (len(_DRAW_CACHE)>=1024 or _DRAW_VERTICES+count>32768):
                        _,old=_DRAW_CACHE.popitem(last=False);_DRAW_VERTICES-=len(old[0])
                    _DRAW_CACHE[key]=data;_DRAW_VERTICES+=count
    p,uv,t,m,c=data
    if mesh._exported:mesh._detach()
    mesh.P.extend(p+(0.,0.,top));mesh.UV.extend(uv);mesh.C.extend(c)
    mesh.T.extend(t+mesh.n);mesh.M.extend(m);mesh.n+=len(p)


def _bounded_cache(solve):
    # Source and street-refitted outlines can both be used during planning.
    # A 256-entry LRU thrashes on ordinary dense tiles. Bound actual retained
    # geometry as well as entries, so dense tiles fit without unbounded memory.
    values=OrderedDict();lock=threading.RLock();vertices=faces=0
    def cached(fp,kind,variant='standard',domain=None):
        nonlocal vertices,faces
        key=(fp,kind,variant,domain)
        with lock:
            if key in values:
                values.move_to_end(key)
                return values[key][0]
        result=solve(fp,kind,variant,domain)
        cost=fp.vertex_count+(domain.vertex_count if domain is not None else 0)
        count=len(result.triangles)
        with lock:
            if key in values:return values[key][0]
            if cost<=8192 and count<=16384:
                while values and (len(values)>=1024 or vertices+cost>8192 or faces+count>16384):
                    _,(_,v,f)=values.popitem(last=False);vertices-=v;faces-=f
                values[key]=(result,cost,count);vertices+=cost;faces+=count
        return result
    def clear():
        nonlocal vertices,faces
        with lock:values.clear();vertices=faces=0
    def info():
        with lock:return dict(entries=len(values),vertices=vertices,triangles=faces)
    cached.cache_clear=clear
    cached.cache_info=info
    return cached


def _clip(poly, nx, ny, h):
    if not poly:return []
    out=[];a=poly[-1];da=nx*a[0]+ny*a[1]+h
    for b in poly:
        db=nx*b[0]+ny*b[1]+h
        if (da>=0)!=(db>=0):
            t=da/(da-db)
            out.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
        if db>=0:out.append(b)
        a,da=b,db
    return out


def _difference(p, q):return tuple(a-b for a,b in zip(p,q))


@lru_cache(maxsize=1024)
def _layout(hl, hw, kind, variant):
    """Translation/rotation-independent planes and convex ownership regions."""
    hip=((0.,1.,hw),(0.,-1.,hw),(1.,0.,hl),(-1.,0.,hl))
    if variant=='standard':planes=hip if kind=='hipped' else hip[:2]
    elif variant=='shed':planes=((0.,1.,hw),)
    elif variant=='saltbox':
        ridge=.25*hw
        planes=((0.,1/(hw+ridge),hw/(hw+ridge)),(0.,-1/(hw-ridge),hw/(hw-ridge)))
    elif variant in ('gambrel','mansard'):
        planes=((0.,2.,2*hw),(0.,-2.,2*hw),(0.,.5,1.1*hw),(0.,-.5,1.1*hw))
        if variant=='mansard':
            planes+=((2*hw/hl,0.,2*hw),(-2*hw/hl,0.,2*hw),
                     (.5*hw/hl,0.,1.1*hw),(-.5*hw/hl,0.,1.1*hw))
    elif variant=='industrial_barrel':
        marks=tuple(-1.+i/3. for i in range(7))
        planes=tuple((0.,-(a+b),hw*(1.+a*b)) for a,b in zip(marks,marks[1:]))
    elif variant=='broad_eave':
        planes=((0.,.45,.45*hw),(0.,1.5,1.185*hw),
                (0.,-1.5,1.185*hw),(0.,-.45,.45*hw))
    elif variant=='cross_gable':
        span=.48*hl;shift=.25*hl;rise=.82
        planes=((0.,1/hw,1.),(0.,-1/hw,1.),(1/hl,0.,10.),(-1/hl,0.,10.),
                (rise/span,0.,rise-rise*shift/span),(-rise/span,0.,rise+rise*shift/span),
                (0.,1/hw,10.),(0.,-1/hw,10.))
    else: # flared hip: shallow lower band, steeper upper band
        coefficients=((.5,0.),(.85/.7,-.85/.7*.3+.15))
        planes=tuple((a*m,b*m,h*m+c*hw) for m,c in coefficients for a,b,h in hip)
    cells=[]
    if variant=='broad_eave':
        for i,(lo,hi) in enumerate(((-1.,-.7),(-.7,0.),(0.,.7),(.7,1.))):
            cells.append((i,((0.,1.,-lo*hw),(0.,-1.,hi*hw))))
    elif variant=='flared_hip':
        for i,p in enumerate(hip):
            own=tuple(_difference(q,p) for j,q in enumerate(hip) if i!=j)
            a,b,h=p
            cells.append((i,own+((-a,-b,.3*hw-h),)))
            cells.append((i+4,own+((a,b,h-.3*hw),)))
    elif variant=='cross_gable':
        for i in (0,1):
            for j in (4,5):
                own=(_difference(planes[1-i],planes[i]),_difference(planes[9-j],planes[j]))
                cells.append((i,own+(_difference(planes[i],planes[j]),)))
                cells.append((j,own+(_difference(planes[j],planes[i]),)))
    else:
        for i,p in enumerate(planes):
            cells.append((i,tuple(_difference(q,p) for j,q in enumerate(planes) if i!=j)))
    # Discard empty ownership cells once, before clipping source triangles.
    active=[]
    for i,constraints in cells:
        poly=[(-hl,-hw),(hl,-hw),(hl,hw),(-hl,hw)]
        for constraint in constraints:poly=_clip(poly,*constraint)
        if len(poly)>=3 and abs(_area2(poly))>1e-10:active.append((i,constraints))
    return planes,tuple(active)


def _area2(poly):
    a=poly[0]
    return math.fsum((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
                     for b,c in zip(poly[1:],poly[2:]))


@_bounded_cache
def envelope(fp, kind, variant='standard', domain=None):
    from .roofs import Envelope
    from .topology import triangles
    if kind not in ('gabled','hipped') or fp.vertex_count>MAX_VERTICES:
        raise ValueError('fast roof exceeds supported form budget')
    if variant not in VARIANTS:raise ValueError('unknown fast roof profile')
    occupied=domain or fp
    if occupied.vertex_count>MAX_VERTICES:raise ValueError('fast roof exceeds domain budget')
    import buildings as b
    centre,u,hl,hw=b.oriented_box(np.asarray(fp.outer))
    cx,cy=map(float,centre);ux,uy=map(float,u);vx,vy=-uy,ux
    if min(hl,hw)<=1e-8:raise ValueError('fast roof has no usable width')
    planes,cells=_layout(float(hl),float(hw),kind,variant)
    def local(p):
        x,y=p[0]-cx,p[1]-cy
        return ux*x+uy*y,vx*x+vy*y
    rings=tuple(tuple(local(p) for p in ring) for ring in (occupied.outer,*occupied.holes))
    ring=rings[0]
    convex=not occupied.holes and all(
        (q[0]-p[0])*(r[1]-q[1])-(q[1]-p[1])*(r[0]-q[0])>=-1e-10
        for p,q,r in zip(ring,ring[1:]+ring[:1],ring[2:]+ring[:2]))
    domains=(ring,) if convex else tuple(tuple(local(p) for p in tri) for tri in triangles(occupied))
    pieces=[]
    for i,constraints in cells:
        for source in domains:
            poly=source
            for constraint in constraints:
                poly=_clip(poly,*constraint)
                if len(poly)<3:break
            for j in range(1,len(poly)-1):
                tri=(poly[0],poly[j],poly[j+1])
                if _area2(tri)>2e-10:pieces.append((i,tri))
    if not pieces or len(pieces)>MAX_TRIANGLES:raise ValueError('fast roof patch budget exhausted')
    def raw(p,i):
        a,b,h=planes[i]
        return a*p[0]+b*p[1]+h
    peak=envelope(fp,kind,variant).peak if domain is not None else max(raw(p,i) for i,tri in pieces for p in tri)
    if peak<=1e-8:raise ValueError('fast roof has no positive rise')
    def index(p):
        values=[raw(p,i) for i in range(len(planes))]
        if variant in ('flared_hip','cross_gable'):
            left=min(range(4),key=values.__getitem__);right=min(range(4,8),key=values.__getitem__)
            return left if values[left]>=values[right] else right
        if variant=='broad_eave':return 0 if p[1]<-.7*hw else 1 if p[1]<0 else 2 if p[1]<.7*hw else 3
        return min(range(len(planes)),key=values.__getitem__)
    def point(p,i):
        x,y=p
        return (cx+ux*x+vx*y,cy+uy*x+vy*y,max(0.,min(1.,raw(p,i)/peak)))
    tt=tuple(tuple(point(p,i) for p in tri) for i,tri in pieces)
    area=math.fsum(_area2(tri)*.5 for _,tri in pieces)
    if not math.isclose(area,occupied.area,rel_tol=1e-7,abs_tol=1e-7):
        raise ValueError('fast roof partition does not preserve occupied area')
    # Split only at actual pitch changes; ignore inactive plane intersections.
    cuts_at=tuple(set(c for _,constraints in cells for c in constraints))
    boundary=[];runs=[]
    for ring in rings:
        run=0.
        for a,b in zip(ring,ring[1:]+ring[:1]):
            dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);cuts=[0.,1.]
            for nx,ny,h in cuts_at:
                den=nx*dx+ny*dy
                if abs(den)>1e-10:
                    t=-(nx*a[0]+ny*a[1]+h)/den
                    if 1e-8<t<1-1e-8:cuts.append(t)
            cuts=sorted(cuts);unique=[cuts[0]]
            for t in cuts[1:]:
                if t-unique[-1]>1e-8:unique.append(t)
            spans=[]
            for s,t in zip(unique,unique[1:]):
                i=index((a[0]+dx*(s+t)*.5,a[1]+dy*(s+t)*.5))
                if spans and spans[-1][2]==i:spans[-1]=(spans[-1][0],t,i)
                else:spans.append((s,t,i))
            for s,t,i in spans:
                boundary.append((point((a[0]+dx*s,a[1]+dy*s),i),point((a[0]+dx*t,a[1]+dy*t),i)))
                runs.append((run+length*s,run+length*t))
            run+=length
    world=tuple((a*ux+b*vx,a*uy+b*vy,h) for a,b,h in planes)
    return Envelope(tt,tuple(boundary),tuple(runs),tuple(i for i,_ in pieces),world,(cx,cy),float(peak),
                    'clipped_envelope' if variant=='standard' else 'regional_'+variant)
