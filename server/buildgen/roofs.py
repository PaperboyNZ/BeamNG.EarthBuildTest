"""Joined orthogonal hip roofs, with clipped envelopes for other footprints.

Two or four supporting planes are partitioned against the exact occupied area.
Orthogonal hips first use bounded wing decomposition. The remaining forms use
the clipped envelope, not a cross-gable or straight-skeleton solver.
Courtyards and notches remain open in every LOD.
"""
from runtimeprofiler import step as profile_step
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import lru_cache
import math
import threading

import numpy as np

from .topology import Footprint, triangles


MAX_ROOF_VERTICES = 256


def supported(footprint):
    return footprint.vertex_count <= MAX_ROOF_VERTICES


@dataclass(frozen=True, slots=True)
class Envelope:
    triangles: tuple
    boundary: tuple
    wall_u: tuple
    triangle_planes: tuple
    planes: tuple
    centre: tuple
    peak: float
    strategy: str = "clipped_envelope"


@dataclass(slots=True)
class _ServiceCache:
    owner: int
    closed: bool = False
    values: dict = field(default_factory=dict)
    vertices: int = 0


_SERVICE_CACHE = ContextVar('building_roof_service_cache', default=None)


@contextmanager
def service_cache():
    """Retain bounded roof solutions for one building service, never a process."""
    state = _ServiceCache(threading.get_ident())
    token = _SERVICE_CACHE.set(state)
    try:
        yield
    finally:
        state.closed = True
        state.values.clear()
        state.vertices = 0
        _SERVICE_CACHE.reset(token)


def envelope(footprint, kind, variant='standard'):
    state = _SERVICE_CACHE.get()
    if (state is None or state.closed or state.owner != threading.get_ident()
            or not isinstance(footprint, Footprint)):
        return _resolve_envelope(footprint, kind, variant)
    from .progressive import DETAIL
    key = (DETAIL.get(), footprint, kind, variant)
    if key in state.values:
        return state.values[key]
    result = _resolve_envelope(footprint, kind, variant)
    if (isinstance(result, Envelope) and len(state.values) < 2048
            and state.vertices + footprint.vertex_count <= 8192):
        state.values[key] = result
        state.vertices += footprint.vertex_count
    return result


def _resolve_envelope(footprint, kind, variant='standard'):
    from .progressive import ACTIVE, DETAIL
    if DETAIL.get()=='minimum':
        from .minimum_roofs import envelope as compact
        result=compact(footprint,kind,variant)
        if result is not None:return result
    job=ACTIVE.get()
    if job is None:return _envelope(footprint,kind,variant)
    key=(footprint,kind,variant)
    if key in job.roof_cache:return job.roof_cache[key]
    result=_envelope(footprint,kind,variant)
    # Bound both entries and source complexity; released with the worker job.
    if len(job.roof_cache)<2048 and job.roof_cache_vertices+footprint.vertex_count<=8192:
        job.roof_cache[key]=result
        job.roof_cache_vertices+=footprint.vertex_count
    return result


@lru_cache(maxsize=256)
def _envelope(footprint, kind, variant='standard'):
    import buildings as b
    if variant!='standard':
        from .regional_roofs import envelope as regional_envelope,supported_form
        if supported_form(footprint):return regional_envelope(footprint,kind,variant)
    if kind not in ("gabled", "hipped") or not supported(footprint):
        raise ValueError("unsupported roof envelope")
    if kind == "hipped" and not footprint.is_rectangle():
        from .wing_roofs import solve
        roof = solve(footprint)
        if roof is not None:
            return roof
    centre, u, hl, hw = b.oriented_box(np.asarray(footprint.outer))
    v = np.array([-u[1], u[0]])
    planes = [(v, hw), (-v, hw)]
    if kind == "hipped":
        planes += [(u, hl), (-u, hl)]

    def height(p):
        return max(0., min(float(a @ (np.asarray(p) - centre) + h) for a, h in planes))

    pieces = []
    for i, (a, h) in enumerate(planes):
        regions = (footprint,)
        for j, (other, oh) in enumerate(planes):
            if i == j:
                continue
            normal = other - a
            point = centre + normal * ((h - oh) / float(normal @ normal))
            regions = tuple(part for region in regions for part in region.half(point, normal))
        pieces.extend((i, tri) for region in regions if region.area > 1e-10
                      for tri in triangles(region, min_area=1e-10))
    peak = max(height(p) for _, tri in pieces for p in tri)
    if peak <= 1e-8:
        raise ValueError("roof envelope has no positive rise")
    # Normalisation retains the resolved top, including when a courtyard removes
    # the bounding rectangle's central ridge point.
    tt = tuple(tuple((float(p[0]), float(p[1]), height(p) / peak) for p in tri) for _, tri in pieces)
    boundary, wall_u = [], []
    for ring in (footprint.outer, *footprint.holes):
        run = 0.
        for pa, pb in zip(ring, ring[1:] + ring[:1]):
            a, d = np.asarray(pa), np.asarray(pb) - pa
            length = float(np.linalg.norm(d))
            cuts = [0., 1.]
            for i, (normal, h) in enumerate(planes):
                for other, oh in planes[i+1:]:
                    delta = normal - other
                    den = float(delta @ d)
                    if abs(den) > 1e-10:
                        t = -float(delta @ (a - centre) + h - oh) / den
                        if 1e-8 < t < 1 - 1e-8:
                            cuts.append(t)
            for s0, s1 in zip(sorted(set(cuts)), sorted(set(cuts))[1:]):
                p, q = a + d * s0, a + d * s1
                boundary.append(((float(p[0]), float(p[1]), height(p) / peak),
                                 (float(q[0]), float(q[1]), height(q) / peak)))
                wall_u.append((run + length * s0, run + length * s1))
            run += length
    area = math.fsum(abs((t[1][0]-t[0][0]) * (t[2][1]-t[0][1]) -
                         (t[1][1]-t[0][1]) * (t[2][0]-t[0][0])) * .5 for t in tt)
    if not math.isclose(area, footprint.area, rel_tol=1e-7, abs_tol=1e-7):
        raise ValueError("roof partition does not preserve occupied area")
    return Envelope(tt, tuple(boundary), tuple(wall_u), tuple(i for i, _ in pieces),
                    tuple((float(a[0]), float(a[1]), float(h)) for a, h in planes),
                    tuple(map(float, centre)), float(peak))


def expanded_rectangle(footprint, distance):
    import buildings as b
    centre, u, hl, hw = b.oriented_box(np.asarray(footprint.outer))
    v = np.array([-u[1], u[0]])
    return Footprint(tuple(tuple(centre + u*s*(hl+distance) + v*t*(hw+distance))
                           for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1))))


def variant(spec):
    return getattr(spec.inference,'roof_variant','standard') if spec.inference is not None and not spec.church else 'standard'



@profile_step('Building roof solution')
def for_spec(spec, footprint=None):
    if footprint is None and getattr(spec,'roof_outline',None) is not None:
        from .roof_edges import extended
        return extended(spec.roof_outline,spec.roof,variant(spec),0.,0.,spec.footprint)
    return envelope(footprint or spec.footprint,spec.roof,variant(spec))


def draw(mesh, spec, top, mats, overhang=False):
    import buildings as b
    roof_base = top
    rise = spec.inference.roof_rise
    from . import roof_edges
    roof = roof_edges.for_spec(spec) if overhang else for_spec(spec)
    surface = roof
    from .materials import roof_scale
    su, sv = roof_scale(spec.inference.roof_material.value)
    cx,cy = roof.centre
    frames=[]
    for ax,ay,offset in roof.planes:
        gradient=math.hypot(ax,ay)
        frames.append((ay/gradient,-ax/gradient,ax/gradient,ay/gradient,
                       offset/gradient,math.hypot(1.,rise*gradient/roof.peak)))
    for tri, plane in zip(roof.triangles, roof.triangle_planes):
        points = [(x, y, roof_base + h * rise) for x, y, h in tri]
        ux,uy,vx,vy,offset,slope=frames[plane]
        # Use the analytical supporting plane, never a normal reconstructed from
        # a thin triangle. V rises from the eave towards the ridge, as the stock
        # roof textures expect. Every triangle on this plane shares one frame.
        uv = [(((x-cx)*ux+(y-cy)*uy)/su,
               ((x-cx)*vx+(y-cy)*vy+offset)*slope/sv) for x,y,_ in tri]
        mesh.tri(*points, *uv, mats[spec.roof_mat])
    roof = for_spec(spec)
    rise = spec.inference.roof_rise
    from .materials import wall_scale
    su, sv = wall_scale(spec.inference.facade.value)
    wall=mats[spec.facade]
    if isinstance(mats,b._Looks):
        from . import regional_architecture as regional
        _,wall=regional.wall_materials(spec,regional.for_spec(spec),mats,wall)
        su,sv=wall_scale('stone' if b.MATERIALS[wall[0]] in (b.STONE,b.BRICK_WALL) else 'render')
    for (p, q), (u0, u1) in zip(roof.boundary, roof.wall_u):
        if overhang and variant(spec)=='shed' and spec.footprint.is_rectangle():
            p=(*p[:2],max(0.,roof_edges.height(surface,p[:2])))
            q=(*q[:2],max(0.,roof_edges.height(surface,q[:2])))
        a, c = (*p[:2], top), (*q[:2], top)
        ap, cp = (*p[:2], top + p[2] * rise), (*q[:2], top + q[2] * rise)
        uv = ((u0 / su, spec.height / sv), (u1 / su, spec.height / sv),
              (u1 / su, (spec.height + q[2] * rise) / sv), (u0 / su, (spec.height + p[2] * rise) / sv))
        if p[2] <= 1e-8 and q[2] <= 1e-8:
            continue
        if p[2] <= 1e-8:
            mesh.tri(a, c, cp, *uv[:3], wall)
        elif q[2] <= 1e-8:
            mesh.tri(a, c, ap, uv[0], uv[1], uv[3], wall)
        else:
            mesh.quad(a, c, cp, ap, *uv, wall)
    from .attics import draw_structure
    draw_structure(mesh, spec, top, wall, mats[spec.roof_mat])
    from . import regional_roof_details as details
    detail_looks = details.looks(spec, mats) if isinstance(mats, b._Looks) else {k:wall for k in ('wall','brick','stone','coping','tank')}
    details.draw(mesh,spec,top,detail_looks)


def eaves(mesh, spec, top, mats):
    from .roof_edges import draw
    draw(mesh,spec,top,mats)
