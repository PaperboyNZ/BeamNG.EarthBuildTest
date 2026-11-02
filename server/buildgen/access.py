"""Grounded thresholds, short entrance stairs and garage aprons.

Surface samples are batched in the caller's frame. The immutable result is shared
by props, facades, visual LODs and collision; it never moves the building envelope.
"""
from runtimeprofiler import step as profile_step
from dataclasses import dataclass
import math

import numpy as np


LANDING = .8
TREAD = .28
MAX_STEPS = 7
MAX_RISE = .2
ENTRY_WIDTH = 1.4
APRON_DEPTH = 2.5
SURFACE_LIFT = .06


@dataclass(frozen=True, slots=True)
class Solid:
    kind: str
    top: tuple
    bottom: float


@dataclass(frozen=True, slots=True)
class AccessPlan:
    door_z: float
    garage_z: float | None
    solids: tuple[Solid, ...]
    diagnostics: tuple[str, ...] = ()
    landscape: tuple[Solid, ...] = ()
    site_layout: object = None


def ground_in_frame(frame, elev, x0=0., y0=0.):
    def sample(xy):
        xy = np.asarray(xy)
        la, lo, _ = frame.enu_to_geodetic(xy[:, 0]+x0, xy[:, 1]+y0, np.zeros(len(xy)))
        return np.asarray(frame.geodetic_to_enu(la, lo, elev(la, lo))[2], np.float64)
    return sample


def basis(spec, edge, along):
    a, c = np.asarray(spec.ring[edge]), np.asarray(spec.ring[(edge+1) % len(spec.ring)])
    d = (c-a) / np.linalg.norm(c-a)
    return a + d*along, d, np.array([d[1], -d[0]])


def strip(spec, edge, along, width, distances):
    p, d, out = basis(spec, edge, along)
    return np.asarray([p + out*s + d*t for s in distances for t in (-width/2., 0., width/2.)])


def patch(spec, edge, along, width, start, end, heights, bottom, kind):
    p, d, out = basis(spec, edge, along)
    # CCW viewed from above; left inside, left outside, right outside, right inside.
    xy = [p + out*s + d*t for s, t in ((start, -width/2), (end, -width/2),
                                     (end, width/2), (start, width/2))]
    return Solid(kind, tuple((float(q[0]), float(q[1]), float(z)) for q, z in zip(xy, heights)), float(bottom))


def entrance_width(spec):
    from .commercial import entry_width
    from .architectural_modifiers import has
    width=entry_width(spec,ENTRY_WIDTH)
    if spec.door and (has(spec,'front_porch') or has(spec,'veranda')):
        edge,along=spec.door
        length=float(np.linalg.norm(spec.ring[(edge+1)%len(spec.ring)]-spec.ring[edge]))
        width=max(width,min(4.8 if has(spec,'veranda') else 3.,2*(along-.2),2*(length-along-.2)))
    return width



@profile_step('Building access planning')
def resolve(records, items, ground=None, x0=0., y0=0., lines=()):
    """records: (spec, gmin, gmax, road setback, mutable door prop row)."""
    import buildings as b
    from shapely.geometry import Polygon, LineString
    from shapely import STRtree
    candidates, samples = [], []
    from . import sitework
    for record in records:
        spec, low, high, setback, row = record[:5]
        goal = record[5] if len(record)>5 else None
        if spec.access is not None and ground is None:
            row[3] = round(spec.access.door_z, 2)
            continue
        edge, along = spec.door
        distances = (0., .45, *(LANDING + k*TREAD for k in range(MAX_STEPS)))
        pts = strip(spec, edge, along, entrance_width(spec), distances)
        garage = spec.garage_opening
        depth = min(APRON_DEPTH, max(0., setback - .4))
        if garage:
            pts = np.concatenate((pts, strip(spec, garage[0], garage[1], garage[2]+.3, (0., depth))))
        core_count = len(pts)
        route = sitework.candidate(spec,goal)
        if route is not None:
            pts = np.concatenate((pts,np.asarray(route.points)))
        candidates.append((spec, low, high, setback, row, distances, depth, len(samples), len(pts),core_count,route))
        samples.extend(pts)
    if not candidates:
        return
    heights = np.full(len(samples), np.nan)
    if ground is not None:
        heights[:] = np.asarray(ground(np.asarray(samples) + [x0, y0]), np.float64).reshape(-1)
    occupied = [s.footprint.shape() for s, _, _ in items if s.footprint is not None and (s.min_h or 0.) <= .5]
    occupied.extend(LineString(np.asarray(line[0])[:, :2] - [x0, y0]).buffer(float(line[1]) + .25)
                    for line in lines if len(line[0]) >= 2)
    tree = STRtree(occupied)

    def clear(solid):
        area = Polygon([p[:2] for p in solid.top])
        return all(area.intersection(occupied[int(i)]).area < 1e-7 for i in tree.query(area))

    for spec, low, high, setback, row, distances, depth, off, count, core_count, route in candidates:
        z = heights[off:off+count].copy()
        from sitegen.portals import OWNER_TOKEN_PREFIX
        # A fresh terrain fit must not reassign an already installed component's
        # local driveway ownership merely because a sibling is no longer resident.
        diagnostics = [note for note in spec.access.diagnostics if note.startswith(OWNER_TOKEN_PREFIX)] if spec.access is not None else []
        # Without a terrain provider, use the observed frontage's local gradient,
        # not the highest corner at the other end of the building.
        for i, p in enumerate(samples[off:off+count]):
            if not np.isfinite(z[i]):
                edge, along = spec.door
                origin, d, _ = basis(spec, edge, along)
                z[i] = b.door_ground(spec, edge, along + float((p-origin) @ d), high)
        if ground is None or not np.isfinite(heights[off:off+count]).all():
            diagnostics.append("access_ground_interpolated_from_frontage")
        door_ground = z[:len(distances)*3].reshape(-1, 3)
        base = b.base_z(spec, low, high) + (spec.min_h or 0.)
        local = float(door_ground[0].max())
        solids, door_z = [], local + SURFACE_LIFT
        # Keep a modest raised floor when a short, usable stair fits. Larger
        # differences receive a lower entrance in the foundation wall.
        if .2 <= base - local <= 1.4:
            for n in range(1, MAX_STEPS+1):
                reach = LANDING + (n-1)*TREAD
                foot = float(door_ground[n+1].max()) + SURFACE_LIFT
                rise = (base-foot) / n
                if reach > setback-.4 or not .08 <= rise <= MAX_RISE:
                    continue
                stairs = []
                for k in range(n):
                    start = 0. if k == 0 else LANDING+(k-1)*TREAD
                    end = LANDING+k*TREAD
                    top = base-k*rise
                    terrain = door_ground[0] if k == 0 else door_ground[k+1]
                    # Never put a tread under rising terrain.
                    if float(max(terrain.max(), door_ground[k+2].max())) > top-SURFACE_LIFT+.01:
                        break
                    stairs.append(patch(spec, *spec.door, entrance_width(spec), start, end, (top,)*4,
                                        min(low, float(door_ground.min()))-.2, "step"))
                if len(stairs) == n and all(clear(s) for s in stairs):
                    solids, door_z = stairs, base
                    break
        if not solids:
            # A guessed raised dwelling needs usable stairs. If the validated
            # landing cannot fit, ground it rather than putting a door under it.
            from .architectural_modifiers import has
            if has(spec,'stilts') and spec.inference.height.status != 'observed' and (spec.min_h or 0.) == 1.05:
                spec.min_h=0.
                base=b.base_z(spec,low,high)
                diagnostics.append('inferred_stilts_omitted_no_stair_clearance')
            landing_z = float(door_ground[:2].max()) + SURFACE_LIFT
            # Small outward fall at the threshold, without changing the door
            # datum or lowering the slab into the sampled terrain.
            outer_z = landing_z-.45*.02
            landing = patch(spec, *spec.door, entrance_width(spec), 0., .45,
                            (landing_z,outer_z,outer_z,landing_z),
                            min(low, float(door_ground[:2].min()))-.2, "threshold")
            if (has(spec,'front_porch') or has(spec,'veranda')) and setback>=1.9:
                reach=LANDING+2*TREAD
                zfront=landing_z-reach*.02
                if float(door_ground[:5].max())<zfront-.01:
                    porch=patch(spec,*spec.door,entrance_width(spec),0.,reach,
                                (landing_z,zfront,zfront,landing_z),
                                min(low,float(door_ground[:5].min()))-.2,'porch_landing')
                    if clear(porch):landing=porch
            if setback >= .85 and clear(landing):
                solids.append(landing)
                door_z = landing_z
            else:
                diagnostics.append("entrance_projection_omitted_clearance")
            if base-door_z > .2:
                diagnostics.append("entrance_lowered_to_local_ground")
        garage_z = None
        if spec.garage_opening:
            garage = spec.garage_opening
            gz = z[core_count-6:core_count].reshape(2, 3)
            garage_z = float(gz[0].max()) + SURFACE_LIFT
            end = gz[1] + SURFACE_LIFT
            if np.max(np.abs(end-garage_z))<.02:
                end=np.maximum(gz[1]+.015,garage_z-.02*depth)
            if np.max(end)>garage_z+.01:
                diagnostics.append("garage_apron_adverse_fall_drainage_unresolved")
            apron = patch(spec, garage[0], garage[1], garage[2]+.3, 0., depth,
                          (garage_z, end[0], end[2], garage_z), min(low, float(gz.min()))-.2, "apron")
            if depth >= .5 and clear(apron):
                solids.append(apron)
            else:
                diagnostics.append("garage_apron_omitted_clearance")
        paths, landscape, notes = sitework.build(spec,route,heights[off+core_count:off+count],solids,clear)
        solids.extend(paths)
        diagnostics.extend(notes)
        spec.access = AccessPlan(float(door_z), garage_z, tuple(solids), tuple(diagnostics),landscape)
        spec.facades = None
        row[3] = round(door_z, 2)


@profile_step('Building access geometry')
def draw(mesh, spec, collision=False, detail=False):
    import buildings as b
    if spec.access is None:
        return
    from . import landscaping
    concrete=landscaping.treatment(spec).concrete if spec.inference else (.7,.7,.67)
    mat = (b.MATERIALS.index(b.PANEL), (128, 128, 128, 255)) if collision else \
        b._Looks(spec.seed)[b.custom_look(b.CONCRETE, concrete)]
    # Adjacent panels share exact top edges. Their buried internal faces cannot
    # be seen or driven on; omit them without an expensive mesh union.
    edges = {}
    for solid in spec.access.solids:
        for a,c in zip(solid.top,solid.top[1:]+solid.top[:1]):
            key=tuple(sorted((a,c)))
            edges[key]=edges.get(key,0)+1
    paving_run = {}
    for solid in spec.access.solids:
        top = solid.top
        surface_mat=mat
        if not collision and solid.kind in ('site_service','site_parking','site_aisle','site_access','site_driveway'):
            surface_mat=b._Looks(spec.seed)[b.custom_look(b.CONCRETE,(.27,.28,.28))]
        elif not collision and solid.kind=='site_bumper':
            surface_mat=b._Looks(spec.seed)[b.custom_look(b.PANEL,(.1,.11,.12))]
        uv = tuple((p[0]/2., p[1]/2.) for p in top)
        if not collision and solid.kind in ('apron','driveway','path','path_link','path_landing'):
            surface_mat=b._Looks(spec.seed)[b.custom_look(b.PAVING,concrete)]
            length=(math.dist(top[0][:2],top[1][:2])+math.dist(top[3][:2],top[2][:2]))/2
            width=(math.dist(top[0][:2],top[3][:2])+math.dist(top[1][:2],top[2][:2]))/2
            repeat=2.4 if solid.kind in ('apron','driveway') else 1.2
            start=paving_run.get(solid.kind,0.)
            across=2. if width>3. else 1.
            uv=((0.,start/repeat),(0.,(start+length)/repeat),
                (across,(start+length)/repeat),(across,start/repeat))
            paving_run[solid.kind]=start+length
        mesh.quad(*top, *uv, surface_mat)
        for a, c in zip(top, top[1:]+top[:1]):
            if edges[tuple(sorted((a,c)))]>1:
                continue
            width = math.dist(a[:2], c[:2]) / 2.
            mesh.quad((*a[:2], solid.bottom), (*c[:2], solid.bottom), c, a,
                      (0., solid.bottom/2), (width, solid.bottom/2), (width, c[2]/2), (0., a[2]/2), surface_mat)
    if not collision:
        landscaping.draw(mesh,spec,detail)
        from .site_layout import draw_markings
        draw_markings(mesh,spec)
    if detail and not collision:
        from .sitework import draw_details
        draw_details(mesh,spec)


def boxes(spec, x0, y0):
    if spec.access is not None:
        for solid in spec.access.solids:
            p = np.asarray(solid.top)
            yield [float(p[:, 0].min()+x0), float(p[:, 1].min()+y0), solid.bottom,
                   float(p[:, 0].max()+x0), float(p[:, 1].max()+y0), float(p[:, 2].max()),
                   [[[float(x+x0), float(y+y0)] for x, y, _ in solid.top]]]
