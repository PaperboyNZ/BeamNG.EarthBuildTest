"""Direct, bounded plan-view corner arcs for sidewalk ends and island rings.

Only true exposed ends are inset. Arc stations and corner templates are fixed;
the original complete piece is returned when preflight or geometry validation
fails. The native sweep builds both visible and lean physics from this outline.
"""
from functools import lru_cache
import numpy as np

REVISION = 'plan-corners-v2-coarse4'
CAP_RADIUS_M = .6
ARC_SPANS = 4


def limits(quality):
    return {'very_low': (64, 12), 'low': (128, 24), 'medium': (256, 32)}.get(quality, (512, 64))


@lru_cache(maxsize=1)
def _cap_template():
    theta = np.linspace(0., np.pi/2, ARC_SPANS+1)
    return 1.-np.cos(theta), 1.-np.sin(theta)


def permitted(points, ramps, quality, extra=0):
    """Preflight the actual native ramp-refinement upper bound before solving."""
    if quality == 'minimum':
        return False
    max_stations, _ = limits(quality)
    if len(points)+extra > max_stations or len(ramps) > 8:
        return False
    length = np.linalg.norm(np.diff(points[:, :2], axis=0), axis=1).sum()
    estimated = len(points)+extra
    for start, end in ramps:
        if not np.isfinite([start, end]).all() or end < start:
            return False
        estimated += max(0, int(np.ceil((min(length, end+1.6)-max(0., start-1.6))/.5)))+4
    return estimated <= max_stations


def run(points, outward, width, caps, ramps, quality):
    """Return source-preserving curve/UV metadata, or None for full fallback."""
    if not permitted(points, ramps, quality, extra=ARC_SPANS*sum(caps)):
        return None
    points, outward = np.asarray(points), np.asarray(outward)
    if (not np.isfinite(points).all() or not np.isfinite(outward).all() or width <= .15):
        return None
    if not any(caps):
        return points, outward, ramps, None
    station = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points[:, :2], axis=0), axis=1))]
    if np.any(np.diff(station) < 1e-8):
        return None
    radius = min(CAP_RADIUS_M, width*.45, station[-1]*.15)
    # Keep the fillet inside the endpoint's original segment. This also avoids
    # altering a bend or a tile join beyond the actual corner being rounded.
    radius = min(radius, *(station[1] if i == 0 else station[-1]-station[-2]
                           for i, cap in enumerate(caps) if cap))
    if radius < .01:
        return None
    template, _ = _cap_template()
    samples = [station]
    for end, cap in enumerate(caps):
        if cap:
            samples.append(radius*template if end == 0 else station[-1]-radius*template)
    at = np.unique(np.concatenate(samples))
    centre = np.column_stack([np.interp(at, station, points[:, i]) for i in range(3)])
    normal = np.column_stack([np.interp(at, station, outward[:, i]) for i in range(2)])
    inset = np.zeros(len(at))
    for end, cap in enumerate(caps):
        if cap:
            distance = at if end == 0 else station[-1]-at
            local = np.clip(distance, 0., radius)
            inset = np.maximum(inset, radius-np.sqrt(np.maximum(0., radius**2-(radius-local)**2)))
    scale = 1.-2.*inset/width
    centre[:, :2] += inset[:, None]*normal
    normal *= scale[:, None]
    # Native path stations now follow the curved front edge. Keep texture
    # coordinates and ramp locations in their original source station frame.
    curved = np.r_[0., np.cumsum(np.linalg.norm(np.diff(centre[:, :2], axis=0), axis=1))]
    mapped_ramps = [(float(np.interp(a, at, curved)), float(np.interp(b, at, curved))) for a, b in ramps]
    if not permitted(centre, mapped_ramps, quality):
        return None
    return centre, normal, mapped_ramps, (curved, at, inset, scale)


def island_ring(ring, width, quality):
    """Round convex polygon corners before tile clipping; no outward bulges."""
    if quality == 'minimum':
        return ring
    max_points, max_corners = limits(quality)
    if len(ring) < 3 or len(ring) > max_points or not np.isfinite(ring).all():
        return ring
    original = ring
    original_xy = np.asarray(ring)[:, :2]
    xy = np.asarray(ring)[:, :2]
    incoming = xy-np.roll(xy, 1, axis=0)
    lengths = np.linalg.norm(incoming, axis=1)
    if np.any(lengths < 1e-7):
        return ring
    incoming /= lengths[:, None]
    outgoing = np.roll(incoming, -1, axis=0)
    cross = incoming[:, 0]*outgoing[:, 1]-incoming[:, 1]*outgoing[:, 0]
    angle = np.arctan2(cross, np.einsum('ij,ij->i', incoming, outgoing))
    # Map clipping can leave many collinear ray/edge samples beside a true
    # ninety-degree corner. Remove only exact redundant samples before fitting
    # the fixed arc; the fitting distance is to the next real corner, not the
    # next arbitrary sample. Preserve any independent height breakpoint.
    fraction = lengths/(lengths+np.roll(lengths, -1))
    linear_z = np.roll(ring[:, 2], 1)+fraction*(np.roll(ring[:, 2], -1)-np.roll(ring[:, 2], 1))
    keep = (np.abs(angle) > 1e-7) | (np.abs(ring[:, 2]-linear_z) > 1e-6)
    if np.count_nonzero(keep) >= 3 and not np.all(keep):
        ring = ring[keep]
        xy = ring[:, :2]
        incoming = xy-np.roll(xy, 1, axis=0)
        lengths = np.linalg.norm(incoming, axis=1)
        incoming /= lengths[:, None]
        outgoing = np.roll(incoming, -1, axis=0)
        cross = incoming[:, 0]*outgoing[:, 1]-incoming[:, 1]*outgoing[:, 0]
        angle = np.arctan2(cross, np.einsum('ij,ij->i', incoming, outgoing))
    orientation = np.sign(np.sum(xy[:, 0]*np.roll(xy[:, 1], -1)-xy[:, 1]*np.roll(xy[:, 0], -1)))
    corners = np.flatnonzero((angle*orientation > np.deg2rad(30.)) & (np.abs(angle) < np.deg2rad(150.)))
    if not len(corners):
        return original
    if len(corners) > max_corners or len(ring)+ARC_SPANS*len(corners)+1 > max_points:
        return original
    # The native band must fit inside each fillet, otherwise its inner edge
    # folds. Reject the whole ring instead of publishing a partial outline.
    radius = max(2., width+.8)  # includes the native band's sloped rear toe
    cuts = radius*np.tan(np.abs(angle[corners])/2.)
    if np.any(cuts > .4*np.minimum(lengths[corners], np.roll(lengths, -1)[corners])):
        return original
    selected = dict(zip(corners.tolist(), cuts.tolist()))
    output = []
    for i, point in enumerate(ring):
        if i not in selected:
            output.append(point)
            continue
        cut = selected[i]
        first = xy[i]-incoming[i]*cut
        centre = first+orientation*radius*np.array([-incoming[i, 1], incoming[i, 0]])
        radial = first-centre
        theta = np.linspace(0., angle[i], ARC_SPANS+1)
        coords = centre+np.c_[np.cos(theta)*radial[0]-np.sin(theta)*radial[1],
                              np.sin(theta)*radial[0]+np.cos(theta)*radial[1]]
        za = ring[i-1, 2]+(point[2]-ring[i-1, 2])*(1.-cut/lengths[i])
        zb = point[2]+(ring[(i+1)%len(ring), 2]-point[2])*cut/lengths[(i+1)%len(ring)]
        output.extend(np.c_[coords, np.linspace(za, zb, ARC_SPANS+1)])
    result = np.asarray(output)
    # Start a closed sweep on a straight section, where the open-path endpoint
    # normals agree exactly. Starting at the first arc tangent would give the
    # native ring two different endpoint normals and leave a closure seam.
    edge_length = np.linalg.norm(np.roll(result[:, :2], -1, axis=0)-result[:, :2], axis=1)
    start = int(np.argmax(edge_length))
    midpoint = (result[start]+result[(start+1)%len(result)])/2.
    result = np.vstack((midpoint, result[start+1:], result[:start+1]))
    # Convex arcs lie inside the source polygon. This small native predicate
    # check covers concave survey rings without constructing a detailed buffer.
    import fast
    if not all(fast._ef.point_inside(np.ascontiguousarray(original_xy), float(p[0]), float(p[1])) or
               np.min(np.linalg.norm(original_xy-p[:2], axis=1)) < 1e-7 for p in result):
        # Exact tangent points can be on a source edge, where even/odd is
        # ambiguous. Test only the inserted interior arc samples instead.
        from shapely.geometry import Polygon
        shape = Polygon(original_xy)
        if not shape.is_valid or not shape.buffer(1e-7).covers(Polygon(result[:, :2])):
            return original
    return result
