"""Fitted attic glazing and bounded dormers inside the resolved roof envelope.

No extra floor is inferred. Dormers are modest style priors, not source evidence.
Their solid cheeks/caps are shared by near, reduced, collision and skyline meshes.
"""
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from . import house_styles, materials, regional_architecture, roofs, roof_edges


@dataclass(frozen=True)
class Window:
    centre: tuple
    direction: tuple
    bottom: float
    width: float
    height: float


@dataclass(frozen=True)
class Dormer:
    walls: tuple
    caps: tuple
    window: Window


def plan(spec):
    r = spec.inference
    if getattr(r, 'roof_solver', 'detailed') == 'fast':return (), ()
    if (r is None or spec.roof == 'flat' or r.use.value not in ('residential', 'unknown')
            or spec.windows is False or spec.plain or spec.floors > 3
            or spec.height > 12. or spec.church or spec.terminal or spec.city
            or r.roof_rise < 2.1 or spec.footprint.holes or spec.footprint.vertex_count > 24):
        return (), ()
    profile = regional_architecture.profile(house_styles.profile_region(r)) or {}
    dormer_style = profile.get('attic_dormers', 'gabled') if 'dormers' in r.modifiers else ''
    return _plan(spec.footprint, spec.roof_outline, spec.roof, roofs.variant(spec),
                 r.roof_rise, dormer_style, spec.seed)


@lru_cache(maxsize=256)
def _plan(fp, outline, kind, variant, rise, dormer_style, seed):
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    roof = roofs.envelope(outline or fp, kind, variant, solver='detailed')
    windows = []
    # Fit glazing against both upper corners of each actual wall edge. This
    # handles saltbox/broken gables without assuming a symmetric triangle.
    for a, c in zip(fp.outer, fp.outer[1:] + fp.outer[:1]):
        a, c = np.asarray(a), np.asarray(c)
        length = float(np.linalg.norm(c - a))
        if length < 2.4:
            continue
        d = (c - a) / length
        centre = (a + c) / 2.
        width, bottom, height = 1., .60, 1.05
        if min(roof_edges.height(roof, centre + d * s) * rise
               for s in (-width / 2. - .18, 0., width / 2. + .18)) < bottom + height + .20:
            continue
        windows.append(Window(tuple(centre), tuple(d), bottom, width, height))
        if len(windows) == 2:
            break
    dormers = []
    if (not dormer_style or rise < 2.2 or variant not in ('standard', 'gambrel', 'mansard', 'saltbox')):
        return tuple(windows), ()
    # A dormer must fit wholly inside one actual roof face, clear of ridges,
    # hips, valleys, eaves and holes. No bounding-box placement across joins.
    groups = {}
    for tri, index in zip(roof.triangles, roof.triangle_planes):
        groups.setdefault(index, []).append(Polygon([p[:2] for p in tri]))
    used = []
    for index, pieces in sorted(groups.items()):
        ax, ay, offset = roof.planes[index]
        normal = np.array((ax, ay))
        gradient = float(np.linalg.norm(normal))
        slope = gradient * rise / roof.peak
        if not .50 <= slope <= 2.2:
            continue
        inward = normal / gradient
        direction = np.array((inward[1], -inward[0]))
        face = unary_union(pieces)
        point = np.array(face.centroid.coords[0])
        front_z = min(.12 * rise, .42)
        current = (float(normal @ (point - roof.centre)) + offset) * rise / roof.peak
        front = point + inward * ((front_z - current) / slope)
        # Room-sized fronts: the earlier 1.56 m-wide units read as roof vents
        # on ordinary 12-18 m houses. Broken lower slopes need a slightly lower
        # gable, but still receive a full attic window and substantial cheeks.
        broken = variant in ('gambrel', 'mansard')
        shoulder = front_z + (1.55 if broken else 1.70)
        peak = shoulder + (.35 if dormer_style == 'gabled' else .15)
        depth = (peak - front_z) / slope
        if peak > rise - .18 or depth > 4.2:
            continue
        half = 1.30 if dormer_style == 'gabled' else 1.65
        def p(x, y, z):
            xy = front + direction * x + inward * y
            return (float(xy[0]), float(xy[1]), z)
        a, b = p(-half, 0., front_z), p(half, 0., front_z)
        c, d = p(-half, 0., shoulder), p(half, 0., shoulder)
        if dormer_style == 'gabled':
            rear_side = (shoulder - front_z) / slope
            e, f = p(-half, rear_side, shoulder), p(half, rear_side, shoulder)
            tip, rear = p(0., 0., peak), p(0., depth, peak)
            walls = ((a, b, d, c), (c, d, tip), (a, c, e), (b, f, d))
            caps = ((c, tip, rear, e), (tip, d, f, rear))
            footprint = Polygon([a[:2], b[:2], f[:2], rear[:2], e[:2]])
        else:
            e, f = p(-half, depth, peak), p(half, depth, peak)
            walls = ((a, b, d, c), (a, c, e), (b, f, d))
            caps = ((c, d, f, e),)
            footprint = Polygon([a[:2], b[:2], f[:2], e[:2]])
        if (not face.covers(footprint.buffer(.16)) or not fp.shape().covers(footprint.buffer(.16))
                or any(footprint.distance(other) < 1. for other in used)):
            continue
        windowspec = Window(tuple(front), tuple(direction), front_z + .22,
                            1.35 if dormer_style == 'gabled' else 2.05,
                            1.10 if broken else 1.25)
        dormers.append(Dormer(walls, caps, windowspec))
        used.append(footprint)
        if len(dormers) == 2:
            break
    return tuple(windows), tuple(dormers)


def vertex_count(spec):
    return sum(len(face) for dormer in plan(spec)[1] for face in (*dormer.walls, *dormer.caps))


def draw_structure(mesh, spec, top, wall, covering):
    for dormer in plan(spec)[1]:
        for faces, material in ((dormer.walls, wall), (dormer.caps, covering)):
            for face in faces:
                points = [(x, y, top + z) for x, y, z in face]
                # Physical metre-scale mapping, independent of world position.
                a = np.array(face[0]); u = np.array(face[1]) - a
                u /= np.linalg.norm(u)
                n = np.cross(u, np.array(face[2]) - a); n /= np.linalg.norm(n)
                v = np.cross(n, u)
                scale = materials.roof_scale(spec.inference.roof_material.value)[0] if faces is dormer.caps else 3.
                uv = [(float((np.array(p) - a) @ u) / scale, float((np.array(p) - a) @ v) / scale) for p in face]
                if len(face) == 3:
                    mesh.tri(*points, *uv, material)
                else:
                    mesh.quad(*points, *uv, material)


def draw_windows(mesh, spec, top, mats, lite=False):
    import buildings as b
    windows, dormers = plan(spec)
    if not windows and not dormers:
        return
    profile = regional_architecture.profile(house_styles.profile_region(spec.inference)) or {}
    trim = mats[b.custom_look(b.PANEL, tuple(profile.get('trim', (.90, .90, .87))))]
    glass = mats['bne_bld_fac_white']
    for w in (*windows, *(d.window for d in dormers)):
        d = np.array(w.direction); n = np.array((d[1], -d[0]))
        def panel(left, right, bottom, upper, material, depth, uv):
            corners = ((left, bottom), (right, bottom), (right, upper), (left, upper))
            points = [(*tuple(np.array(w.centre) + d * x + n * depth), top + z) for x, z in corners]
            mesh.quad(*points, *uv, material)
        l, r, z, h = -w.width / 2., w.width / 2., w.bottom, w.bottom + w.height
        uv = ((0., 0.), (1., 0.), (1., 1.), (0., 1.))
        offset=.055 if 'stepped_gable' in spec.inference.modifiers else .018
        panel(l - .065, r + .065, z - .065, h + .065, trim, offset, uv)
        u0, u1, v0, v1 = b.WIN_UV
        panel(l, r, z, h, glass, offset+.005, ((u0, v0), (u1, v0), (u1, v1), (u0, v1)))
        if not lite:
            panel(-.018, .018, z, h, trim, offset+.012, uv)
