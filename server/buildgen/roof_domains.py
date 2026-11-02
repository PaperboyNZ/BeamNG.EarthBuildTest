"""Bounded roof-local offsets; never reinterpret a polygon as a rectangle.

Holes retain their exact source boundary. Narrow projections and recesses limit
the offset rather than allowing a roof to bridge neighbouring building wings.
"""
from functools import lru_cache
import numpy as np
from .topology import Footprint, InvalidFootprint


@lru_cache(maxsize=512)
def widths(fp, eave, rake):
    from shapely.geometry import Polygon
    # Ignore sub-centimetre survey segments for this safety estimate only. The
    # geometry emitted below still uses every source vertex.
    outer = Polygon(fp.outer).simplify(.02, preserve_topology=True)
    clearance = float(outer.minimum_clearance)
    cap = max(0., clearance * .40)
    factor = min(1., cap / max(eave, rake, 1e-9))
    return eave * factor, rake * factor


@lru_cache(maxsize=512)
def offset(fp, kind, variant, eave, rake, inward=False):
    import buildings as b
    from shapely.affinity import affine_transform
    from shapely.errors import GEOSException
    from shapely.geometry import Polygon
    from .topology import MAX_VERTICES
    if max(eave, rake) <= 1e-8:
        return fp
    end = eave if kind == 'hipped' and variant in ('standard', 'mansard', 'flared_hip') else rake
    centre, u, _, _ = b.oriented_box(np.asarray(fp.outer))
    v = np.array([-u[1], u[0]])
    # Work around an origin near the building, including far translated fixtures.
    origin = np.asarray(fp.outer[0])
    outer = Polygon(np.asarray(fp.outer) - origin)
    end, side = max(end, 1e-6), max(eave, 1e-6)
    local = affine_transform(outer, [u[0]/end, u[1]/end, v[0]/side, v[1]/side, 0., 0.])
    try:
        expanded = local.buffer(-1. if inward else 1., join_style='mitre', mitre_limit=2.)
        if expanded.geom_type != 'Polygon' or expanded.is_empty or expanded.interiors:
            return None
        expanded = affine_transform(expanded, [u[0]*end, v[0]*side, u[1]*end, v[1]*side,
                                                float(origin[0]), float(origin[1])])
        if len(expanded.exterior.coords) + sum(map(len, fp.holes)) > min(MAX_VERTICES, 512):
            return None
        result = Footprint(expanded.exterior.coords, fp.holes)
        if inward and (result.area < 4. or result.shape().buffer(-.75).is_empty):
            return None
        # No new courtyard or source footprint may be silently filled.
        if not inward and fp.shape().difference(result.shape()).area > max(1e-7, fp.area*1e-9):
            return None
        return result
    except (GEOSException, InvalidFootprint):
        return None
