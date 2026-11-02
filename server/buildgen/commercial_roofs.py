"""Sparse-use roof recipes and bounded, batched rooftop equipment.

Visual priors only: no inferred business, machinery simulation or new assets.
Mapped roof geometry wins. Equipment has full support, edge setbacks and a
shared near/middle layout; collision and skyline retain the primary shell.
"""
from dataclasses import dataclass
from functools import lru_cache
import numpy as np

from . import materials
from .commercial_forms import BROAD_CLASSES

MAX_DETAILS = 8
MAX_CANDIDATES = 24
EDGE_SETBACK = 1.0
GAP = .65


def options(use, classes, footprint, floors, height):
    from .regional_roofs import supported_form
    if (use not in ('industrial', 'commercial') or
            any(c not in BROAD_CLASSES for c in classes) or
            floors > 3 or height > 16. or footprint.area < 60. or
            not supported_form(footprint)):
        return ()
    import buildings as b
    _, _, hl, hw = b.oriented_box(np.asarray(footprint.outer))
    if hw < 3.:
        return ()
    result = [('flat', 5. if use == 'commercial' else 2.),
              ('standard', 3.), ('shed', 2.), ('saltbox', .7)]
    if hw >= 7. and hl / hw >= 1.3 and floors <= 2:
        result.append(('industrial_barrel', 1.2 if use == 'industrial' else .35))
    return tuple(result)


def eligible(spec):
    return (spec.inference is not None and
            spec.inference.use.value in ('industrial', 'commercial') and
            spec.cls in BROAD_CLASSES and not spec.deck and
            not spec.church and not spec.terminal and not spec.city and
            spec.footprint.vertex_count <= 64 and spec.footprint.area >= 60. and
            'unmapped_part_roof' != spec.inference.roof.source and
            'commercial_roof_part_omitted' not in spec.inference.diagnostics)


@dataclass(frozen=True, slots=True)
class Detail:
    kind: str
    corners: tuple
    bottom: tuple
    top: tuple


def plan(spec):
    if not eligible(spec):
        return ()
    # Regional terrace/tank recipes own their occupied roof area.
    from . import regional_roof_details, roof_edges
    if regional_roof_details.plan(spec) or regional_roof_details.recessed_deck(spec):
        return ()
    surface = roof_edges.for_spec(spec) if spec.roof != 'flat' else None
    return _plan(spec.footprint, spec.roof, spec.inference.roof_rise,
                 spec.seed, spec.inference.use.value, surface)


@lru_cache(maxsize=512)
def _plan(footprint, kind, rise, seed, use, roof):
    import buildings as b
    from shapely.geometry import Polygon
    from .roof_edges import height
    occupied = footprint.shape().buffer(-EDGE_SETBACK, join_style=2)
    if occupied.is_empty:
        return ()
    centre, u, hl, hw = b.oriented_box(np.asarray(footprint.outer))
    v = np.array([-u[1], u[0]])
    # Functional groups: service plant, daylight strips or occasional PV.
    recipe = materials.choose(seed, 'ci-roof-equipment-v1',
                              (('plant', 4), ('daylight', 4 if use == 'industrial' else 2), ('solar', 1)))
    flat = kind == 'flat'
    kinds = (('hvac', 'duct', 'vent', 'hatch') if recipe == 'plant' and flat else
             ('solar', 'solar', 'vent', 'hatch') if recipe == 'solar' else
             ('rooflight', 'rooflight', 'vent', 'vent'))
    sizes = {'hvac': (2.8, 1.8, .95), 'duct': (3.2, .65, .45),
             'vent': (1., .8, .55), 'hatch': (1.2, .9, .16),
             'solar': (4., 2., .12), 'rooflight': (3.6, 1.1, .20)}
    limit = min(MAX_DETAILS, max(2, int(footprint.area / 180.)))
    accepted, footprints = [], []
    # Fixed work bound, evenly spaced rows aligned to the building's long axis.
    # Offset rows keep pitched equipment off ridges and valley seams.
    cols = min(6, max(2, int(2 * hl / 7.)))
    rows = min(4, max(2, int(2 * hw / 6.)))
    candidates = [(i, j) for j in range(rows) for i in range(cols)]
    shift = int(materials.unit(seed, 'ci-roof-layout-v1') * len(candidates))
    candidates = candidates[shift:] + candidates[:shift]
    for i, j in candidates[:MAX_CANDIDATES]:
        detail_kind = kinds[len(accepted) % len(kinds)]
        length, width, lift = sizes[detail_kind]
        p = centre + u * ((i + .5) / cols * 2 - 1) * hl + v * ((j + .5) / rows * 2 - 1) * hw
        xy = tuple(tuple(map(float, p + u * s * length / 2 + v * t * width / 2))
                   for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1)))
        shape = Polygon(xy)
        if not occupied.covers(shape) or any(shape.distance(other) < GAP for other in footprints):
            continue
        z = tuple(height(roof, p) * rise for p in xy) if roof else (0.,) * 4
        if roof:
            # One analytical plane must support the entire component. This
            # excludes ridges and slope breaks, including the barrel facets.
            for ax, ay, offset in roof.planes:
                plane_z = tuple(((x-roof.centre[0])*ax + (y-roof.centre[1])*ay + offset) * rise / roof.peak for x,y in xy)
                if all(abs(a-b) < 1e-6 for a,b in zip(z, plane_z)):
                    break
            else:
                continue
            if max(z)-min(z) > .65:
                continue
        # Curbs intersect the roof slightly, avoiding floating equipment.
        bottom = tuple(a - .025 for a in z)
        top = (tuple(a + lift for a in z) if detail_kind in ('rooflight', 'solar', 'hatch')
               else (max(z) + lift,) * 4)
        accepted.append(Detail(detail_kind, xy, bottom, top))
        footprints.append(shape)
        if len(accepted) >= limit:
            break
    return tuple(accepted)


def draw(mesh, spec, base, mats, lite=False):
    import buildings as b
    from .quality import current
    lite = lite or current().rank < 5
    items = plan(spec)
    if not items:
        return
    uv = ((0., 0.), (1., 0.), (1., 1.), (0., 1.))
    metal = mats[b.custom_look(b.METALWALL, (.58, .60, .60))]
    dark = mats[b.custom_look(b.METALWALL, (.19, .22, .23))]
    glass = mats[b.custom_look(b.ROOF_METAL, (.28, .39, .43))]
    solar = mats[b.custom_look(b.ROOF_METAL, (.10, .17, .23))]
    for item in items:
        # Middle distance retains the large plant silhouette and broad roof
        # panels. Tiny vents, access hatches and ducts contribute little there.
        if lite and item.kind in ('vent', 'hatch', 'duct'):
            continue
        low = [(*xy, base + z) for xy,z in zip(item.corners, item.bottom)]
        high = [(*xy, base + z) for xy,z in zip(item.corners, item.top)]
        if not lite or item.kind == 'hvac':
            for i in range(4):
                j = (i + 1) % 4
                mesh.quad(low[i], low[j], high[j], high[i], *uv, metal)
        cap = glass if item.kind == 'rooflight' else solar if item.kind == 'solar' else metal
        mesh.quad(*high, *uv, cap)
        if lite:
            continue
        # Near-only inset top panels: bounded louvers/fan grilles and PV seams.
        # No transparent materials, cylinders, hidden bottom faces or props.
        p = np.asarray(high)
        a, along, across = p[0], p[1]-p[0], p[3]-p[0]
        count = 2 if item.kind in ('hvac', 'vent') else 3 if item.kind == 'solar' else 1
        for k in range(count):
            s0, s1 = ((k+.16)/count, (k+.84)/count)
            t0, t1 = (.16, .84) if item.kind in ('hvac', 'vent') else (.06, .10)
            panel = [a+along*s+across*t+np.array((0.,0.,.008))
                     for s,t in ((s0,t0),(s1,t0),(s1,t1),(s0,t1))]
            mesh.quad(*panel, *uv, dark)
