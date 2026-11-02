"""Validated, immutable planar building polygons and courtyard-safe triangulation.

Coordinates are metres in a stable caller-supplied frame. Source geometry is not
automatically repaired: filling a hole or changing a boundary is not a safe repair.
Shapely/GEOS is imported only when the experimental topology path is used.
"""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math

import numpy as np

MAX_VERTICES = 4096


class InvalidFootprint(ValueError):
    pass


def check_runtime():
    try:
        import shapely
        from shapely import constrained_delaunay_triangles
        if shapely.geos_version < (3, 10, 0):
            raise ImportError("GEOS 3.10 or newer is required")
    except ImportError as exc:
        raise RuntimeError("Building generator v2 requires Shapely >=2.1 with GEOS >=3.10; install server/requirements.txt") from exc


def canonical_ring(points, ccw=True):
    p = np.asarray(points, np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3 or not np.isfinite(p).all():
        raise InvalidFootprint("ring must contain finite XY coordinates")
    if len(p) > MAX_VERTICES + 1:
        raise InvalidFootprint("ring exceeds the vertex budget")
    keep = np.empty(len(p), dtype=bool)
    keep[0] = True
    np.any(p[1:] != p[:-1], axis=1, out=keep[1:])
    p = p[keep]
    if len(p) > 1 and np.array_equal(p[0], p[-1]):
        p = p[:-1]
    if len(p) < 3:
        raise InvalidFootprint("ring has fewer than three distinct consecutive vertices")
    # Subtract an origin before the shoelace sum to avoid cancellation far from 0.
    local = p - p[0]
    # The closing term is zero after subtracting p[0]. Keep the original
    # reduction length/order, without allocating two rolled coordinate arrays.
    cross = np.empty(len(local), dtype=np.float64)
    cross[:-1] = local[:-1, 0] * local[1:, 1] - local[:-1, 1] * local[1:, 0]
    cross[-1] = 0.
    area2 = float(np.sum(cross))
    if area2 == 0:
        raise InvalidFootprint("ring has zero area")
    if (area2 > 0) != ccw:
        p = p[::-1]
    start = int(np.lexsort((p[:, 1], p[:, 0]))[0])
    result = tuple((float(x) + 0., float(y) + 0.) for x, y in p)
    return result[start:] + result[:start]


@dataclass(frozen=True, slots=True)
class Footprint:
    outer: tuple
    holes: tuple = ()

    def __post_init__(self):
        outer = canonical_ring(self.outer)
        holes = tuple(sorted(canonical_ring(h, ccw=False) for h in self.holes))
        if len(outer) + sum(map(len, holes)) > MAX_VERTICES:
            raise InvalidFootprint("polygon exceeds the vertex budget")
        object.__setattr__(self, "outer", outer)
        object.__setattr__(self, "holes", holes)
        shape = self.shape()
        if not shape.is_valid or shape.is_empty or shape.area <= 0:
            from shapely import is_valid_reason
            raise InvalidFootprint(str(is_valid_reason(shape)))

    @lru_cache(maxsize=1024)
    def shape(self):
        from shapely.geometry import Polygon
        return Polygon(self.outer, self.holes)

    @property
    def area(self):
        return float(self.shape().area)

    @property
    def vertex_count(self):
        return len(self.outer) + sum(map(len, self.holes))

    def component_key(self):
        """Hash already validated canonical rings without validating them twice."""
        return _component_digest((self.outer, self.holes))

    def translated(self, dx, dy):
        return Footprint(tuple((x + dx, y + dy) for x, y in self.outer),
                         tuple(tuple((x + dx, y + dy) for x, y in h) for h in self.holes))

    def clipped(self, ring):
        from shapely.geometry import Polygon
        return polygons(self.shape().intersection(Polygon(ring)))

    def half(self, point, normal):
        """Clip to dot(x - point, normal) >= 0 without bridging concavities."""
        from shapely.geometry import Polygon
        n = np.array(normal, np.float64, copy=True)
        n /= np.linalg.norm(n)
        u = np.array([-n[1], n[0]])
        p = np.asarray(point, np.float64)
        r = np.asarray(self.outer) - p
        reach = float(np.max(np.linalg.norm(r, axis=1))) + 1.
        clip = Polygon([p - u * reach, p + u * reach,
                        p + u * reach + n * reach, p - u * reach + n * reach])
        return polygons(self.shape().intersection(clip))

    def road_length(self, lines):
        from shapely.geometry import LineString
        shape = self.shape()
        return math.fsum(shape.intersection(LineString(np.asarray(line)[:, :2])).length
                         for line in lines if len(line) >= 2)

    @lru_cache(maxsize=512)
    def is_rectangle(self):
        if self.holes or len(self.outer) != 4:
            return False
        shape = self.shape()
        return shape.minimum_rotated_rectangle.area - shape.area <= max(1e-8, shape.area * 1e-8)


def polygons(shape):
    """Polygonal components of a clipping result; lines/points have no volume."""
    if shape.is_empty:
        return ()
    if shape.geom_type == "Polygon":
        return (Footprint(shape.exterior.coords, tuple(h.coords for h in shape.interiors)),)
    if shape.geom_type in ("MultiPolygon", "GeometryCollection"):
        return tuple(sorted((p for g in shape.geoms for p in polygons(g)), key=lambda p: (p.outer, p.holes)))
    return ()


@lru_cache(maxsize=512)
def triangles(footprint, min_area=0.):
    """Deterministic CCW triangles covering only the occupied polygon area."""
    from shapely import constrained_delaunay_triangles
    shape = footprint.shape()
    result = constrained_delaunay_triangles(shape)
    # Intersecting roof planes can leave roundoff-sized slivers. Callers may
    # discard those within the same area-preservation tolerance checked below.
    out = tuple(sorted(canonical_ring(g.exterior.coords) for g in result.geoms if g.area > min_area))
    if not out or any(len(t) != 3 for t in out):
        raise InvalidFootprint("polygon triangulation failed")
    area = math.fsum(abs((t[1][0] - t[0][0]) * (t[2][1] - t[0][1]) -
                         (t[2][0] - t[0][0]) * (t[1][1] - t[0][1])) * 0.5 for t in out)
    if not math.isclose(area, shape.area, rel_tol=1e-8, abs_tol=1e-8):
        raise InvalidFootprint("triangulation does not preserve occupied area")
    return out


def component_key(rings):
    """Stable source-coordinate identity under winding and ring-start changes.

    This is used on original source coordinates, never anchor-local coordinates.
    Do not use it as a cross-dataset building identity.
    """
    canonical = (canonical_ring(rings[0]), tuple(sorted(canonical_ring(h, False) for h in rings[1:])))
    return _component_digest(canonical)


def _component_digest(canonical):
    return hashlib.sha256(json.dumps(canonical, separators=(",", ":"), allow_nan=False).encode()).hexdigest()[:24]
