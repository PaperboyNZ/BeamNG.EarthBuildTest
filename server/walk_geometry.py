"""Pure plan geometry shared by sidewalk corner constructors.

Heights are raw road datums. The native corner mesh adds its 2.5 m cross-slope
datum; callers retain the actual width alongside each rear point for that
separate correction. No terrain sampling or worker state belongs here.
"""
from dataclasses import dataclass

import numpy as np
from shapely import is_valid, make_valid, polygons, union_all
from shapely.geometry import LineString, Polygon

ENDPOINT_JOIN_TOLERANCE_M = .01
# Separate geodetic point transforms and normalized vector rotations can leave
# millimetre tangential residuals in transported corner evidence. This validates
# the supplied join only: never snap endpoints or alter widths/normals to fit it.


@dataclass(frozen=True)
class CornerRear:
    outer: np.ndarray
    widths: np.ndarray
    stations: np.ndarray | None
    merged_inner: bool = False


class MergedCornerRequired(ValueError):
    """Exact end caps cross, so a simple paired strip cannot represent the walk."""


def _cross(a, b):
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def _valid_strip(front, rear):
    """Both the outline and individual station cells must keep their winding."""
    shape = Polygon(np.vstack((front, rear[::-1])))
    if not shape.is_valid or shape.area <= 1e-10:
        return False
    a, b, c, d = front[:-1], front[1:], rear[1:], rear[:-1]
    areas = (_cross(b-a, c-a) + _cross(c-a, d-a)) / 2
    nonzero = np.linalg.norm(b-a, axis=1) > 1e-9
    if not nonzero.any():
        return False
    if np.any(np.linalg.norm(c-d, axis=1)[nonzero] <= 1e-9):
        return False  # A consumed inner radius is a merged solid, not paired cells.
    if not np.all(is_valid(polygons(np.stack((a[nonzero], b[nonzero], c[nonzero], d[nonzero]), axis=1)))):
        return False
    orient = np.sign(areas[nonzero][0])
    return bool(orient and np.all(areas[nonzero] * orient > 1e-10))


def _polygons(shape):
    if shape.geom_type == 'Polygon':
        yield shape
    elif hasattr(shape, 'geoms'):
        for part in shape.geoms:
            yield from _polygons(part)


def _merged_rear(arc, normals, rear, widths, stations):
    """Collapse consumed inner offsets only when the walk union is unchanged.

Fixed end caps can cross when the walk is wider than the return radius. The
curb-side component is then a solid corner; the opposite offset loop belongs
to the adjoining full-width straight walks. Never discard a loop unless those
unchanged approach strips cover it, and never alter any curb segment.
    """
    origin = arc[0, :2]
    front, back = arc[:, :2]-origin, rear[:, :2]-origin
    pieces = list(_polygons(make_valid(Polygon(np.vstack((front, back[::-1]))))))
    curb = LineString(front)
    tol = 1e-8
    candidates = [p for p in pieces if not p.interiors and p.area > 1e-10
                  and curb.difference(p.boundary.buffer(tol)).length <= tol]
    if len(candidates) != 1:
        raise MergedCornerRequired('offset merge cannot retain the entire curb as one simple boundary')
    shape = candidates[0]
    # Endpoint normals encode exact branch joins; sampled circular chords do not.
    delta = np.diff(front, axis=0)
    nonzero = delta[np.linalg.norm(delta, axis=1) > 1e-9]
    tangent = np.c_[normals[[0, -1], 1], -normals[[0, -1], 0]]
    for j, direction in enumerate((nonzero[0], nonzero[-1])):
        if tangent[j] @ direction < 0:
            tangent[j] *= -1
    reach = max(stations[-1], float(widths.max())) * 2 + 1.
    approaches = union_all([
        Polygon([front[0], back[0], back[0]-tangent[0]*reach, front[0]-tangent[0]*reach]),
        Polygon([front[-1], back[-1], back[-1]+tangent[1]*reach, front[-1]+tangent[1]*reach])])
    discarded = union_all([p for p in pieces if p is not shape])
    if discarded.difference(approaches.buffer(tol)).area > 1e-8:
        raise MergedCornerRequired('offset merge would remove pavement outside unchanged approach walks')
    # Read the two exterior routes between the curb endpoints. One must be the
    # unchanged complete curb; the other is the rear chain, including any merged
    # cap intersections. No original arc station is changed or fabricated.
    ring = np.asarray(shape.exterior.coords)[:-1]
    ids = [np.flatnonzero(np.linalg.norm(ring-p, axis=1) <= tol) for p in (front[0], front[-1])]
    if any(len(k) != 1 for k in ids):
        raise MergedCornerRequired('offset merge lost a curb endpoint')
    start, end = int(ids[0][0]), int(ids[1][0])
    def path(a, b, step):
        return ring[(a+np.arange((b-a)*step % len(ring)+1)*step) % len(ring)]
    routes = (path(start, end, 1), path(start, end, -1))
    matches = [LineString(p).hausdorff_distance(curb) <= tol for p in routes]
    if sum(matches) != 1:
        raise MergedCornerRequired('offset merge has no unique unchanged curb route')
    outer_xy = routes[1 if matches[0] else 0][::-1][1:-1]
    if not len(outer_xy):
        raise MergedCornerRequired('offset merge has no positive pavement rear')
    # An exactly consumed circular offset can retain several machine-epsilon
    # copies of its center after make_valid. Collapse those zero-length edges.
    clean = []
    for point in outer_xy:
        if not clean or np.linalg.norm(point-clean[-1]) > tol:
            clean.append(point)
    outer_xy = np.asarray(clean)
    if len(outer_xy) > 1 and np.max(np.linalg.norm(outer_xy-outer_xy[0], axis=1)) <= tol:
        outer_xy = outer_xy.mean(axis=0, keepdims=True)
    # New cap-intersection points retain the raw height/width at their closest
    # original station. Equal-distance circle-center ties use the median station,
    # keeping reversal/translation symmetry instead of selecting an arbitrary arc.
    seg = np.diff(front, axis=0)
    seg2 = np.einsum('ij,ij->i', seg, seg)
    along = np.diff(stations)
    zs, ws = [], []
    for point in outer_xy:
        t = np.clip(np.einsum('ij,ij->i', point-front[:-1], seg) / np.maximum(seg2, 1e-30), 0., 1.)
        distance = np.linalg.norm(front[:-1]+t[:, None]*seg-point, axis=1)
        nearest = np.median((stations[:-1]+t*along)[distance <= distance.min()+tol])
        zs.append(np.interp(nearest, stations, arc[:, 2]))
        ws.append(np.interp(nearest, stations, widths))
    outer = np.c_[outer_xy+origin, zs]
    final = Polygon(np.vstack((arc[:, :2], outer[:, :2])))
    if not final.is_valid or final.area <= 1e-10:
        raise MergedCornerRequired('merged pavement boundary is not simple and positive')
    return CornerRear(outer, np.asarray(ws), None, merged_inner=True)


def corner_rear(arc, inward, start_width, end_width, rear_start, rear_end, *, station_widths=None):
    """Return the curved rear in reverse arc order, preserving exact joins.

``rear_start`` joins arc[0], and ``rear_end`` joins arc[-1]. Ordinary
corners retain one rear point for every existing arc station, with linearly
interpolated width and the same station's raw Z. Endpoint values are copied
exactly, including Z, rather than recomputed from normals. Input arrays are
never modified. A merged topology is explicitly distinguished from a strip.
    A caller with an already sampled profile can supply ``station_widths``;
    otherwise width changes linearly along the arc between its two joins.
    """
    arc = np.asarray(arc, np.float64)
    inward = np.asarray(inward, np.float64)
    ends = np.asarray((rear_start, rear_end), np.float64)
    if (arc.ndim != 2 or arc.shape[1] != 3 or len(arc) < 2
            or inward.shape != (len(arc), 2) or ends.shape != (2, 3)
            or not np.isfinite(arc).all() or not np.isfinite(inward).all()
            or not np.isfinite(ends).all()
            or not np.isfinite((start_width, end_width)).all()
            or min(start_width, end_width) <= 0):
        raise ValueError('finite corner arc, directions, endpoints and positive widths required')
    lengths = np.linalg.norm(inward, axis=1)
    if np.any(lengths < 1e-9):
        raise ValueError('corner inward directions must be nonzero')
    normals = inward / lengths[:, None]
    expected_ends = arc[[0, -1], :2] + normals[[0, -1]] * np.asarray((start_width, end_width))[:, None]
    if np.any(np.linalg.norm(ends[:, :2]-expected_ends, axis=1) > ENDPOINT_JOIN_TOLERANCE_M):
        raise ValueError('rear endpoint does not match its adjoining walk width and direction')
    stations = np.r_[0., np.cumsum(np.linalg.norm(np.diff(arc[:, :2], axis=0), axis=1))]
    if stations[-1] <= 1e-9:
        raise ValueError('corner arc has no length')
    if station_widths is None:
        widths = start_width + (end_width-start_width) * stations / stations[-1]
    else:
        widths = np.asarray(station_widths, np.float64).copy()
        if (widths.shape != (len(arc),) or not np.isfinite(widths).all()
                or np.any(widths <= 0)
                or np.any(np.abs(widths[[0, -1]]-(start_width, end_width)) > 1e-9)):
            raise ValueError('station widths must be positive and match the endpoint widths')
    rear = arc.copy()
    rear[:, :2] += normals * widths[:, None]
    rear[0], rear[-1] = ends
    if not _valid_strip(arc[:, :2], rear[:, :2]):
        return _merged_rear(arc, normals, rear, widths, stations)
    return CornerRear(rear[::-1].copy(), widths[::-1].copy(), stations[::-1].copy())
