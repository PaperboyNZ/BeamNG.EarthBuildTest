"""Analytical rectangular roof silhouettes, confined to the original footprint."""
import math
from functools import lru_cache
import numpy as np
from . import roofs
from .topology import triangles

VARIANTS = frozenset(('gambrel', 'mansard', 'saltbox', 'shed', 'broad_eave', 'flared_hip', 'cross_gable', 'industrial_barrel'))


def supported_form(footprint):
    # This is a roof-local suitability check, not a reinterpretation of mapped
    # wall geometry. Regional planes are clipped to the actual source polygon.
    # Allow ordinary surveyed quads and redundant boundary vertices; retain the
    # joined-wing solver on genuinely concave or courtyard outlines.
    if footprint.holes or footprint.vertex_count>24:return False
    shape=footprint.shape()
    return shape.area/shape.minimum_rotated_rectangle.area>=.96

@lru_cache(maxsize=256)
def envelope(footprint, kind, variant):
    if variant not in VARIANTS or kind not in ('gabled', 'hipped') or not supported_form(footprint):
        return roofs._envelope(footprint, kind)
    if variant=='flared_hip':return flared(footprint)
    if variant=='cross_gable':return crossed(footprint)
    import buildings as b
    centre, u, hl, hw = b.oriented_box(np.asarray(footprint.outer))
    u = np.asarray(u, dtype=float)
    v = np.array([-u[1], u[0]])
    # Plane coefficients describe raw height in metres relative to centre.
    # The emitted heights are normalised by the actual maximum below.
    if variant == 'shed':
        planes = [(v, hw)]
    elif variant == 'industrial_barrel':
        # Six planar sheets approximate a shallow parabolic barrel. Even
        # segmentation avoids a zero-gradient cap and keeps UV frames finite.
        marks = np.linspace(-1., 1., 7)
        planes = []
        for left, right in zip(marks, marks[1:]):
            slope = -(left + right)
            planes.append((v * slope, hw * (1. + left * right)))
    elif variant == 'saltbox':
        # Ridge 25% of the half-width towards +v, with unequal pitches.
        ridge = .25 * hw
        planes = [(v / (hw + ridge), hw / (hw + ridge)),
                  (-v / (hw - ridge), hw / (hw - ridge))]
    elif variant in ('gambrel', 'mansard'):
        planes = [(v * 2., 2 * hw), (-v * 2., 2 * hw),
                  (v * .5, 1.1 * hw), (-v * .5, 1.1 * hw)]
        if variant == 'mansard':
            # Apply the same broken slope to both ends as well as both sides.
            planes += [(u * (2 * hw / hl), 2 * hw), (-u * (2 * hw / hl), 2 * hw),
                       (u * (.5 * hw / hl), 1.1 * hw), (-u * (.5 * hw / hl), 1.1 * hw)]
    else:
        # Four strips: a shallow outer section transitioning to a steeper
        # inner section. This profile is not a globally concave envelope.
        planes = [(v * .45, .45 * hw), (v * 1.5, 1.185 * hw),
                  (-v * 1.5, 1.185 * hw), (-v * .45, .45 * hw)]
    def height(p):
        xy = np.asarray(p) - centre
        if variant == 'broad_eave':
            t = float(v @ xy) / hw
            i = 0 if t < -.7 else 1 if t < 0 else 2 if t < .7 else 3
            a,h=planes[i]
            return float(a @ xy + h)
        return min(float(a @ xy + h) for a,h in planes)
    pieces=[]
    for i,(a,h) in enumerate(planes):
        regions=(footprint,)
        if variant == 'broad_eave':
            bounds=((-1.,-.7),(-.7,0.),(0.,.7),(.7,1.))[i]
            for t,normal in ((bounds[0],v),(bounds[1],-v)):
                regions=tuple(part for region in regions for part in region.half(centre+v*(t*hw),normal))
        else:
            for j,(other,oh) in enumerate(planes):
                if i==j: continue
                normal=other-a
                if float(normal @ normal)<1e-20: continue
                point=centre+normal*((h-oh)/float(normal @ normal))
                regions=tuple(part for region in regions for part in region.half(point,normal))
        pieces.extend((i,tri) for region in regions if region.area>1e-10 for tri in triangles(region,min_area=1e-10))
    peak=max(height(p) for _,tri in pieces for p in tri)
    if peak<=1e-8: raise ValueError('roof envelope has no positive rise')
    tt=tuple(tuple((float(p[0]),float(p[1]),max(0.,min(1.,height(p)/peak))) for p in tri) for _,tri in pieces)
    boundary=[];wall_u=[];run=0.
    for pa,pb in zip(footprint.outer,footprint.outer[1:]+footprint.outer[:1]):
        a=np.asarray(pa); delta=np.asarray(pb)-a; length=float(np.linalg.norm(delta));cuts=[0.,1.]
        if variant=='broad_eave':
            den=float(v@delta)
            if abs(den)>1e-10:
                for s in (-.7,0.,.7):
                    t=(s*hw-float(v@(a-centre)))/den
                    if 1e-8<t<1-1e-8:cuts.append(t)
        else:
            for j,(n,h) in enumerate(planes):
                for other,oh in planes[j+1:]:
                    dn=n-other;den=float(dn@delta)
                    if abs(den)>1e-10:
                        t=-float(dn@(a-centre)+h-oh)/den
                        if 1e-8<t<1-1e-8:cuts.append(t)
        cuts=sorted(cuts)
        cuts=[x for j,x in enumerate(cuts) if j==0 or x-cuts[j-1]>1e-8]
        for s0,s1 in zip(cuts,cuts[1:]):
            p,q=a+delta*s0,a+delta*s1
            boundary.append(((float(p[0]),float(p[1]),max(0.,min(1.,height(p)/peak))),
                             (float(q[0]),float(q[1]),max(0.,min(1.,height(q)/peak)))))
            wall_u.append((run+length*s0,run+length*s1))
        run+=length
    area=math.fsum(abs((t[1][0]-t[0][0])*(t[2][1]-t[0][1])-(t[1][1]-t[0][1])*(t[2][0]-t[0][0]))*.5 for t in tt)
    if not math.isclose(area,footprint.area,rel_tol=1e-7,abs_tol=1e-7):raise ValueError('roof partition does not preserve occupied area')
    return roofs.Envelope(tt,tuple(boundary),tuple(wall_u),tuple(i for i,_ in pieces),
                          tuple((float(a[0]),float(a[1]),float(h)) for a,h in planes),
                          tuple(map(float,centre)),float(peak),'regional_'+variant)


@lru_cache(maxsize=256)
def crossed(footprint):
    """Intersecting room-wing ridges fitted inside the actual source outline.

    An inferred roof composition, not evidence of an interior layout. An upper
    union of two gables gives continuous valleys and two unequal ridge heights,
    with no overlapping panels, invented courtyard or change to the source top.
    """
    import buildings as b
    from . import roof_edges
    centre,u,hl,hw=b.oriented_box(np.asarray(footprint.outer));u=np.asarray(u);v=np.array([-u[1],u[0]])
    # Two inactive end planes retain the existing four-plane wing contract.
    # Their height is strictly above either gable throughout this bounded domain.
    main=[(v/hw,1.),(-v/hw,1.),(u/hl,10.),(-u/hl,10.)]
    span=.48*hl;shift=.25*hl;rise=.82
    side=[(u*rise/span,rise-rise*shift/span),(-u*rise/span,rise+rise*shift/span),
          (v/hw,10.),(-v/hw,10.)]
    source=roofs.Envelope((),(),(),(),tuple((float(a[0]),float(a[1]),float(h)) for a,h in main+side),
                          tuple(map(float,centre)),1.,'regional_cross_gable')
    solved=roof_edges.extended(footprint,'gabled','cross_gable',0.,0.,domain=footprint,source=source)
    from dataclasses import replace
    def point(p):
        x,y,z=p
        if not -1e-7<=z<=1.+1e-7:raise ValueError('crossed roof exceeded source height range')
        return x,y,max(0.,min(1.,z))
    return replace(solved,triangles=tuple(tuple(point(p) for p in t) for t in solved.triangles),
                   boundary=tuple(tuple(point(p) for p in edge) for edge in solved.boundary))


@lru_cache(maxsize=256)
def flared(footprint):
    """Two fitted pitches on every hip, retaining actual outlines and total top.

    The shallow lower slope and steeper upper roof are a bounded residential
    interpretation of swept eaves, not a temple/palace roof or a curve survey.
    """
    from dataclasses import replace
    from .topology import Footprint
    base=roofs._envelope(footprint,'hipped')
    n=len(base.planes);centre=np.asarray(base.centre);knee=.3*base.peak
    coefficients=((.5,0.),(.85/.7,-.85/.7*.3+.15))
    planes=tuple((a*m,b*m,h*m+c*base.peak) for m,c in coefficients for a,b,h in base.planes)
    pieces=[]
    for tri,index in zip(base.triangles,base.triangle_planes):
        fp=Footprint(tuple(p[:2] for p in tri))
        a,b,h=base.planes[index];normal=np.array([a,b]);den=float(normal@normal)
        point=centre+normal*((knee-h)/den)
        for band,(m,c) in enumerate(coefficients):
            regions=fp.half(point,normal if band else -normal)
            for region in regions:
                for face in triangles(region,min_area=1e-10):
                    xyz=tuple((x,y,((a*(x-centre[0])+b*(y-centre[1])+h)/base.peak)*m+c) for x,y in face)
                    pieces.append((index+band*n,xyz))
    boundary=[];runs=[]
    for (p,q),(u0,u1) in zip(base.boundary,base.wall_u):
        cuts=[0.,1.]
        if abs(q[2]-p[2])>1e-10:
            t=(.3-p[2])/(q[2]-p[2])
            if 1e-8<t<1.-1e-8:cuts.insert(1,t)
        def interpolate(t):
            x,y,z=np.asarray(p)+(np.asarray(q)-p)*t
            return float(x),float(y),max(m*z+c for m,c in coefficients)
        for s,t in zip(cuts,cuts[1:]):
            boundary.append((interpolate(s),interpolate(t)))
            runs.append((u0+(u1-u0)*s,u0+(u1-u0)*t))
    return replace(base,triangles=tuple(t for _,t in pieces),triangle_planes=tuple(i for i,_ in pieces),
                   boundary=tuple(boundary),wall_u=tuple(runs),planes=planes,strategy='regional_flared_hip')
