"""Bounded orthogonal hip roofs from maximal occupied rectangles.

Each wing contributes a hip envelope; their upper union creates continuous joins
and valleys. This handles orthogonal courts and L/T/H/U outlines, not arbitrary
straight skeletons. Other forms retain the existing diagnosed envelope fallback.
"""
import math
from dataclasses import replace
from functools import lru_cache
import numpy as np

from .topology import Footprint, triangles


def solve(footprint):
    from shapely.errors import GEOSException
    from .topology import InvalidFootprint
    x, y = footprint.outer[0]
    try:
        roof = _local(footprint.translated(-x, -y))
    except (GEOSException, InvalidFootprint):
        return None
    if roof is None:
        return None
    return replace(roof, triangles=tuple(tuple((px+x,py+y,z) for px,py,z in t) for t in roof.triangles),
                   boundary=tuple(tuple((px+x,py+y,z) for px,py,z in edge) for edge in roof.boundary),
                   centre=(roof.centre[0]+x,roof.centre[1]+y))


@lru_cache(maxsize=256)
def _local(footprint):
    import buildings as b
    from shapely.geometry import Polygon, box
    from .roofs import Envelope
    centre, u, _, _ = b.oriented_box(np.asarray(footprint.outer))
    v = np.array([-u[1], u[0]])
    rings = [np.column_stack(((np.asarray(r)-centre) @ u, (np.asarray(r)-centre) @ v))
             for r in (footprint.outer, *footprint.holes)]
    for ring in rings:
        d = np.roll(ring, -1, axis=0)-ring
        if np.any(np.min(np.abs(d), axis=1) > 1e-6):
            return None
    # Round only solver coordinates, never the stored source footprint.
    xs = sorted(set(round(float(x), 7) for r in rings for x,y in r))
    ys = sorted(set(round(float(y), 7) for r in rings for x,y in r))
    if len(xs) > 10 or len(ys) > 10:
        return None
    shape = Polygon(rings[0], rings[1:])
    candidates = []
    for a in range(len(xs)-1):
        for c in range(a+1,len(xs)):
            for d in range(len(ys)-1):
                for e in range(d+1,len(ys)):
                    rect = box(xs[a],ys[d],xs[c],ys[e])
                    if rect.difference(shape).area <= 1e-6:
                        candidates.append((rect.area,(xs[a],ys[d],xs[c],ys[e])))
    rectangles = []
    for _, r in sorted(candidates, reverse=True):
        if not any(q[0] <= r[0] and q[1] <= r[1] and q[2] >= r[2] and q[3] >= r[3] for q in rectangles):
            rectangles.append(r)
    if not 2 <= len(rectangles) <= 8:
        return None
    from shapely.ops import unary_union
    if unary_union([box(*r) for r in rectangles]).symmetric_difference(shape).area > 1e-6:
        return None
    # Plane value is signed horizontal distance to a wing's supporting eave.
    wings = [((u,-x0),(-u,x1),(v,-y0),(-v,y1)) for x0,y0,x1,y1 in rectangles]
    planes = [plane for wing in wings for plane in wing]
    def clip(regions, a, h, oa, oh):
        normal = oa-a
        den = float(normal @ normal)
        if den < 1e-12:
            return regions if h <= oh+1e-9 else ()
        point = centre+normal*((h-oh)/den)
        return tuple(part for region in regions for part in region.half(point,normal))
    pieces = []
    for wi, (bounds, wing) in enumerate(zip(rectangles,wings)):
        x0,y0,x1,y1 = bounds
        fp = Footprint(tuple(tuple(centre+u*x+v*y) for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1))))
        for pi,(a,h) in enumerate(wing):
            regions = (fp,)
            for j,(oa,oh) in enumerate(wing):
                if pi != j:
                    regions = clip(regions,a,h,oa,oh)
            for other_index, other_wing in enumerate(wings):
                if other_index == wi:
                    continue
                # Other roof exceeds this plane where ALL its planes exceed it.
                dominated = regions
                for oa,oh in other_wing:
                    if np.linalg.norm(oa-a) < 1e-9 and abs(oh-h) < 1e-7 and other_index > wi:
                        dominated = () # deterministic owner for coplanar overlap
                        break
                    dominated = clip(dominated,a,h,oa,oh)
                if dominated:
                    cut = unary_union([r.shape() for r in dominated])
                    next_regions = []
                    for region in regions:
                        remaining = region.shape().difference(cut)
                        polygons = [remaining] if remaining.geom_type == "Polygon" else getattr(remaining,"geoms",())
                        for polygon in polygons:
                            if polygon.geom_type == "Polygon" and polygon.area > 1e-9:
                                next_regions.append(Footprint(tuple(polygon.exterior.coords)[:-1],
                                    tuple(tuple(r.coords)[:-1] for r in polygon.interiors)))
                    regions = tuple(next_regions)
            pieces.extend((wi*4+pi,t) for r in regions for t in triangles(r,min_area=1e-9))
    area = math.fsum(abs((t[1][0]-t[0][0])*(t[2][1]-t[0][1])-
                         (t[1][1]-t[0][1])*(t[2][0]-t[0][0]))*.5 for _,t in pieces)
    if not math.isclose(area,footprint.area,rel_tol=1e-7,abs_tol=1e-6):
        return None
    def height(p, i):
        a,h = planes[i]
        return max(0.,float(a @ (np.asarray(p)-centre)+h))
    peak = max((height(p,i) for i,t in pieces for p in t),default=0.)
    if peak < 1e-7:
        return None
    tt = tuple(tuple((float(p[0]),float(p[1]),height(p,i)/peak) for p in t) for i,t in pieces)
    boundary, runs = [], []
    for ring in (footprint.outer,*footprint.holes):
        run = 0.
        for p,q in zip(ring,ring[1:]+ring[:1]):
            length = math.dist(p,q)
            boundary.append(((*p,0.),(*q,0.)))
            runs.append((run,run+length))
            run += length
    return Envelope(tt,tuple(boundary),tuple(runs),tuple(i for i,_ in pieces),
                    tuple((float(a[0]),float(a[1]),float(h)) for a,h in planes),tuple(centre),peak,"orthogonal_wings")
