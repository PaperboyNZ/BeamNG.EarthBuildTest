"""Analytical convex roof partitions for Minimum's common rectangular forms.

Keep the full solver for concave, courtyard and intersecting-wing roofs. Clip
scalar polygons against the same planes, without constructing GEOS objects for
every intermediate half-plane. This avoids translation-dependent cache churn.
"""
from functools import lru_cache
import math
import numpy as np


def _clip(poly,nx,ny,h):
    if not poly:return []
    out=[];a=poly[-1];da=nx*a[0]+ny*a[1]+h
    for c in poly:
        dc=nx*c[0]+ny*c[1]+h
        if (da>=0)!=(dc>=0):
            t=da/(da-dc)
            out.append((a[0]+(c[0]-a[0])*t,a[1]+(c[1]-a[1])*t))
        if dc>=0:out.append(c)
        a,da=c,dc
    return out


@lru_cache(maxsize=256)
def envelope(fp,kind,variant):
    from .roofs import Envelope
    if kind not in ('gabled','hipped') or fp.holes or len(fp.outer)!=4 or not fp.is_rectangle():return None
    if variant not in ('standard','shed','saltbox','gambrel','mansard','broad_eave','industrial_barrel'):return None
    import buildings as b
    centre,u,hl,hw=b.oriented_box(np.asarray(fp.outer))
    cx,cy=map(float,centre);ux,uy=map(float,u);vx,vy=-uy,ux
    if variant=='standard':
        planes=[(vx,vy,hw),(-vx,-vy,hw)]
        if kind=='hipped':planes.extend(((ux,uy,hl),(-ux,-uy,hl)))
    elif variant=='shed':planes=[(vx,vy,hw)]
    elif variant=='saltbox':
        ridge=.25*hw
        planes=[(vx/(hw+ridge),vy/(hw+ridge),hw/(hw+ridge)),
                (-vx/(hw-ridge),-vy/(hw-ridge),hw/(hw-ridge))]
    elif variant in ('gambrel','mansard'):
        planes=[(2*vx,2*vy,2*hw),(-2*vx,-2*vy,2*hw),(.5*vx,.5*vy,1.1*hw),(-.5*vx,-.5*vy,1.1*hw)]
        if variant=='mansard':
            planes.extend(((2*hw/hl*ux,2*hw/hl*uy,2*hw),(-2*hw/hl*ux,-2*hw/hl*uy,2*hw),
                           (.5*hw/hl*ux,.5*hw/hl*uy,1.1*hw),(-.5*hw/hl*ux,-.5*hw/hl*uy,1.1*hw)))
    elif variant=='industrial_barrel':
        marks=np.linspace(-1.,1.,7)
        planes=[(-(a+c)*vx,-(a+c)*vy,hw*(1.+a*c)) for a,c in zip(marks,marks[1:])]
    else:planes=[(.45*vx,.45*vy,.45*hw),(1.5*vx,1.5*vy,1.185*hw),
                 (-1.5*vx,-1.5*vy,1.185*hw),(-.45*vx,-.45*vy,.45*hw)]
    ring=tuple((x-cx,y-cy) for x,y in fp.outer)
    def height(p):
        x,y=p
        if variant=='broad_eave':
            t=(vx*x+vy*y)/hw
            a,c,h=planes[0 if t<-.7 else 1 if t<0 else 2 if t<.7 else 3]
            return a*x+c*y+h
        return max(0.,min(a*x+c*y+h for a,c,h in planes))
    pieces=[]
    for i,(a,c,h) in enumerate(planes):
        poly=list(ring)
        if variant=='broad_eave':
            lo,hi=((-1.,-.7),(-.7,0.),(0.,.7),(.7,1.))[i]
            poly=_clip(poly,vx,vy,-lo*hw);poly=_clip(poly,-vx,-vy,hi*hw)
        else:
            for j,(d,e,k) in enumerate(planes):
                if i!=j:poly=_clip(poly,d-a,e-c,k-h)
        for j in range(1,len(poly)-1):
            tri=(poly[0],poly[j],poly[j+1])
            aa,bb,cc=tri
            area=(bb[0]-aa[0])*(cc[1]-aa[1])-(bb[1]-aa[1])*(cc[0]-aa[0])
            if area>2e-10:pieces.append((i,tri))
    if not pieces:return None
    peak=max(height(p) for _,tri in pieces for p in tri)
    if peak<=1e-8:return None
    def point(p):return (float(p[0]+cx),float(p[1]+cy),max(0.,min(1.,height(p)/peak)))
    triangles=tuple(tuple(point(p) for p in tri) for _,tri in pieces)
    boundary=[];wall_u=[];run=0.
    for a,c in zip(ring,ring[1:]+ring[:1]):
        dx,dy=c[0]-a[0],c[1]-a[1];length=math.hypot(dx,dy);cuts=[0.,1.]
        if variant=='broad_eave':
            den=vx*dx+vy*dy
            if abs(den)>1e-10:
                cuts.extend((s*hw-vx*a[0]-vy*a[1])/den for s in (-.7,0.,.7)
                            if 1e-8<(s*hw-vx*a[0]-vy*a[1])/den<1-1e-8)
        else:
            for i,(nx,ny,h) in enumerate(planes):
                for mx,my,k in planes[i+1:]:
                    nx2,ny2=nx-mx,ny-my;den=nx2*dx+ny2*dy
                    if abs(den)>1e-10:
                        t=-(nx2*a[0]+ny2*a[1]+h-k)/den
                        if 1e-8<t<1-1e-8:cuts.append(t)
        cuts=sorted(set(cuts))
        for s,t in zip(cuts,cuts[1:]):
            if t-s<=1e-8:continue
            boundary.append((point((a[0]+dx*s,a[1]+dy*s)),point((a[0]+dx*t,a[1]+dy*t))))
            wall_u.append((run+length*s,run+length*t))
        run+=length
    return Envelope(triangles,tuple(boundary),tuple(wall_u),tuple(i for i,_ in pieces),
                    tuple(tuple(map(float,p)) for p in planes),(cx,cy),float(peak),
                    'clipped_envelope' if variant=='standard' else 'regional_'+variant)
