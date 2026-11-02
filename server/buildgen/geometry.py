"""Geometry compilers for validated building footprints.

Ordinary v2 volumes share planned openings and clipped pitched roof envelopes.
Specialised structures retain their existing geometry kernels.
"""
from dataclasses import replace

import numpy as np

from .plan import BuildingPlan
from .topology import triangles


def horizontal(mesh, footprint, z, material, scale=6., down=False):
    for tri in triangles(footprint):
        if down:
            tri = tri[::-1]
        points = [(x, y, z) for x, y in tri]
        # Fixed footprint origin: UVs do not restart at triangle boundaries.
        ox, oy = footprint.outer[0]
        uv = [((x - ox) / scale, (y - oy) / scale) for x, y in tri]
        mesh.tri(*points, *uv, material)


def draw(mesh, spec, gmin, gmax, collision=False, lite=False, texture_facades=False):
    import buildings as b
    from . import regional_blocks
    from .quality import current
    quality = current()
    fp = spec.footprint
    ring = np.asarray(fp.outer, np.float64)
    mats = b._Looks(spec.seed)
    mh = spec.min_h or 0.
    base = b.base_z(spec, gmin, gmax) + mh
    bottom = (gmin - (b.FOUNDATION_M if collision else b.SKIRT_LITE_M if lite else b.SKIRT_M)
              if mh <= .5 else base)
    top = base + spec.height
    from . import regional_supports
    regional_supports.draw(mesh,spec,gmin,gmax,mats[spec.facade])
    if collision:
        wall = (b.MATERIALS.index(b.PANEL), (128, 128, 128, 255))
        from .regional_facade_details import draw_collision_bays
        draw_collision_bays(mesh,spec,gmin,gmax,wall)
        for boundary in (fp.outer, *fp.holes):
            for a, c in zip(boundary, boundary[1:] + boundary[:1]):
                mesh.quad((*a, bottom), (*c, bottom), (*c, top), (*a, top), *((0., 0.),) * 4, wall)
    elif spec.inference is not None:
        from .facades import draw as draw_facades
        draw_facades(mesh, spec, gmin, gmax, bottom, lite=lite, textured=texture_facades)
    else:
        b._walls(mesh, spec, ring, bottom, top, mats, lite)
        if fp.holes:
            inner = replace(BuildingPlan.from_spec(spec), door=None, front=None, sign=None, shop=False,
                            porch=False, stoop=None)
            for hole in fp.holes:
                b._walls(mesh, inner, np.asarray(hole, np.float64), bottom, top, mats, lite)
        # The existing window kernel skips edges below 5 cm. Preserve those
        # source segments as plain wall strips so a bevel cannot leave a crack.
        for boundary in (fp.outer, *fp.holes):
            for a, c in zip(boundary, boundary[1:] + boundary[:1]):
                length = float(np.linalg.norm(np.asarray(c) - a))
                if length < .05:
                    uv = ((0., 0.), (length / b.SIDING_UV_M, 0.),
                          (length / b.SIDING_UV_M, (top - bottom) / b.SIDING_UV_M),
                          (0., (top - bottom) / b.SIDING_UV_M))
                    mesh.quad((*a, bottom), (*c, bottom), (*c, top), (*a, top), *uv, mats[spec.facade])
    if spec.roof != "flat" and spec.inference is not None:
        from .roofs import draw as draw_roof
        # Decorative eaves do not alter the mapped collision envelope.
        draw_roof(mesh, spec, top, mats, overhang=not collision)
    elif spec.roof != "flat" and fp.is_rectangle():
        b._roof(mesh, spec, ring, top, mats)
    else:
        from . import regional_roof_details as roof_details
        horizontal(mesh, fp, top-(.9 if roof_details.recessed_deck(spec) else 0.), mats[spec.roof_mat], b.ROOF_UV_M)
        roof_details.draw(mesh,spec,top,roof_details.looks(spec,mats))
    if spec.inference is not None and spec.roof != "flat" and not collision:
        from .roofs import eaves
        eaves(mesh, spec, top, mats)
        from .attics import draw_windows
        draw_windows(mesh, spec, top, mats, lite=lite)
        from .regional_facade_details import draw_gable_frame
        draw_gable_frame(mesh,spec,top,mats)
    if spec.inference is not None and spec.roof != "flat" and not collision and not lite:
        from .details import rainwater,roof_caps
        if quality.rank >= 4:rainwater(mesh,spec,top,mats,gmin,gmax,detail=quality.rank >= 5)
        if quality.rank >= 5:roof_caps(mesh,spec,top,mats)
    if mh > .5:
        horizontal(mesh, fp, bottom, mats[spec.facade], down=True)
    if spec.access is not None:
        from .access import draw as draw_access
        draw_access(mesh, spec, collision, detail=not lite and quality.rank >= 3)
    from . import commercial_roofs
    if not collision:
        commercial_roofs.draw(mesh, spec, top, mats, lite=lite)
    # The legacy rooftop clutter and cornices assume a simple solid outline.
    # Use them only on rectangles, where none can bridge a courtyard or recess.
    if not collision and not lite and fp.is_rectangle() and getattr(spec, 'city', None) is None:
        block=regional_blocks.profile(spec)
        if not block and spec.roof == "flat" and not spec.plain and spec.floors <= 6:
            from .regional_architecture import coping
            if not coping(mesh,spec,top,mats):b._cornice(mesh, spec, ring, top, mats)
        from . import regional_roof_details as roof_details
        if quality.rank >= 5 and not block and not roof_details.recessed_deck(spec) and not commercial_roofs.eligible(spec):
            b._clutter(mesh, spec, ring, top, mats)
        if spec.stoop:
            b._stoop(mesh, spec, ring, gmin, gmax, mats)
        if spec.porch and spec.door:
            b._porch(mesh, spec, gmax, mats)
        if spec.steeple:
            b._steeple(mesh, spec, top, mats)
        if spec.sign is not None and spec.roof == "flat":
            z = (min(gmax + b.GROUND_FLOOR_SHOP_M + 1.15, top) if spec.windows is False else
                 top - (spec.floors - 1) * spec.floor_h if spec.floors > 1 else top)
            b._signs(mesh, spec, ring, z, mats)


def sky_vertex_count(spec):
    fp = spec.footprint
    underside = 3 * len(triangles(fp)) if (spec.min_h or 0.) > .5 else 0
    church = getattr(spec, 'church', None)
    extra = 0
    from . import regional_supports
    extra += regional_supports.vertex_count(spec)
    from . import regional_roof_details as roof_details
    extra += roof_details.vertex_count(spec)
    if church is not None and church.accepted:
        from .churches import spire_vertex_count
        extra += spire_vertex_count(spec)
    if (spec.inference is not None or church is not None and church.accepted) and spec.roof != "flat":
        from .roofs import for_spec
        roof = for_spec(spec)
        sides = sum(0 if p[2] <= 1e-8 and q[2] <= 1e-8 else
                    3 if min(p[2], q[2]) <= 1e-8 else 4 for p, q in roof.boundary)
        surface=roof
        if getattr(spec,'roof_outline',None) is not None:
            from .roof_edges import for_spec as surface_for_spec
            surface=surface_for_spec(spec)
        from .attics import vertex_count
        return 4 * fp.vertex_count + underside + 3 * len(surface.triangles) + sides + extra + vertex_count(spec)
    return 4 * fp.vertex_count + underside + 3 * len(triangles(fp)) + extra


def sky(mesh, spec, gmin, gmax):
    """Far silhouette with the existing skyline material and window-light mapping."""
    import buildings as b
    fp = spec.footprint
    mi = b.MATERIALS.index(b.MARBLE)
    f = 1. + b.JITTER * (2. * b._hash01(spec.seed, "jit") - 1.)
    windows = spec.windows is not False
    wall = (b.MATERIALS.index(b.SKY_WALL) if windows else mi, b._sky_colour(spec.facade, f))
    from . import regional_blocks
    block=regional_blocks.profile(spec)
    if block:
        wall=(wall[0],b._sky_colour(regional_blocks.wall_looks(spec,block)[1],f))
    roof = (mi, b._sky_colour(spec.roof_mat or b.ROOF_FLAT, f))
    mh = spec.min_h or 0.
    base = b.base_z(spec, gmin, gmax) + mh
    bottom = gmin - b.SKIRT_LITE_M if mh <= .5 else base
    top = base + spec.height
    fh = float(spec.floor_h or b.FLOOR_M) * b.SKY_WIN_FLOORS
    from . import regional_supports
    regional_supports.draw(mesh,spec,gmin,gmax,wall)
    v0, v1 = (bottom - gmin) / fh, (top - gmin) / fh
    for boundary in (fp.outer, *fp.holes):
        u = 0.
        for a, c in zip(boundary, boundary[1:] + boundary[:1]):
            du = float(np.linalg.norm(np.asarray(c) - a)) / (b.SKY_BAY_M * b.SKY_WIN_BAYS)
            uv = ((u, v0), (u + du, v0), (u + du, v1), (u, v1)) if windows else (b.SKY_UV,) * 4
            mesh.quad((*a, bottom), (*c, bottom), (*c, top), (*a, top), *uv, wall)
            u += du
    church = getattr(spec, 'church', None)
    if church is not None and church.accepted and (spec.roof != 'flat' or church.spire is not None):
        from .churches import draw_roof
        draw_roof(mesh, spec, top, {spec.facade: (mi, b._sky_colour(spec.facade, f)), spec.roof_mat: roof})
    elif spec.inference is not None and spec.roof != "flat":
        from .roofs import draw as draw_roof
        draw_roof(mesh, spec, top, {spec.facade: (mi, b._sky_colour(spec.facade, f)), spec.roof_mat: roof},
                  overhang=getattr(spec,'roof_outline',None) is not None)
    else:
        from . import regional_roof_details as roof_details
        horizontal(mesh, fp, top-(.9 if roof_details.recessed_deck(spec) else 0.), roof)
        roof_details.draw(mesh,spec,top,{k:wall for k in ('wall','brick','stone','tank')})
    if mh > .5:
        horizontal(mesh, fp, bottom, (mi, b._sky_colour(spec.facade, f)), down=True)
