"""Flush atlas details fitted wholly inside a paved furnishing strip.

Reuse the original cover artwork and its normal/roughness maps. A cover's quad is
visual only; no raised collision or street-furniture prop is invented for it.
"""
import numpy as np

# Source pixel rectangles in the installed 4096 x 1024 sidewalk1 atlas, including
# a small concrete rim. These retain the cover, label, wear and matching normals.
COVERS = ((546, 248, 684, 344), (464, 650, 558, 748), (3124, 452, 3244, 572),
          (2720, 632, 2826, 782), (3810, 668, 3964, 774))
PIXEL_M = .0045
CLEAR_WALK_M = 1.5
EDGE_MARGIN_M = .12
END_MARGIN_M = 2.0
SPACING_M = 24.0
MAX_PER_RUN = 16
LIFT_M = .002
MATERIAL = 5


def _quads(centres, dirs, rect, heights, origin):
    import sidewalks as sw
    count = len(rect)
    across = (rect[:, 3] - rect[:, 1]) * PIXEL_M
    offsets = sw.CURB_W + EDGE_MARGIN_M + np.c_[np.zeros((count, 2)), np.repeat(across[:, None], 2, axis=1)]
    P = centres[:, [0, 1, 1, 0]].copy()
    P[:, :, :2] += dirs[:, [0, 1, 1, 0]] * offsets[:, :, None]
    P[:, :, 2] += np.asarray(heights).reshape(-1, 1) + offsets * sw.CROSS_SLOPE + LIFT_M
    P -= origin
    T = np.tile([[0, 1, 2], [0, 2, 3]], (count, 1, 1)) + 4 * np.arange(count)[:, None, None]
    ab, ac = P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]
    reverse = ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0] < 0
    T[reverse] = T[reverse, :, ::-1]
    UV = np.stack((rect[:, [0, 2, 2, 0]] / 4096, 1 - rect[:, [3, 3, 1, 1]] / 1024), axis=2)
    return P.reshape(-1, 3), T.reshape(-1, 3), UV.reshape(-1, 2), np.full(2 * count, MATERIAL, np.int64)


def meshes(pieces, origin):
    import sidewalks as sw
    from vehicle_crossings import combine
    result = []
    origin = np.asarray(origin)
    atlas = np.asarray(COVERS)
    straight, remaining = [], []
    for piece in pieces:
        kind, curb, outward, _, ramps, width, height, _, slab = piece
        if kind != 0 or slab not in (1, sw.BRICK, sw.STONE) or width < sw.CURB_W + EDGE_MARGIN_M + .7 + CLEAR_WALK_M:
            continue
        delta = curb[-1] - curb[0]
        length = float(np.linalg.norm(delta[:2]))
        if length < 1e-8:
            continue
        # Drape samples along a straight, constant-grade section need no
        # per-cover interpolation. Batch all such runs in a single operation.
        flat = len(curb) == 2 or np.max(np.abs(curb - curb[0] -
            (((curb[:, :2] - curb[0, :2]) @ delta[:2]) / length**2)[:, None] * delta)) < 1e-6
        if not ramps and flat and np.max(np.abs(outward - outward[0])) < 1e-6:
            straight.append((curb[0], delta, outward[0], length, width, height))
        else:
            remaining.append(piece)
    if straight:
        start = np.array([p[0] for p in straight])
        delta = np.array([p[1] for p in straight])
        direction = np.array([p[2] for p in straight])
        length, widths, heights = np.array([p[3:] for p in straight]).T
        at = np.broadcast_to(8. + SPACING_M * np.arange(MAX_PER_RUN), (len(straight), MAX_PER_RUN))
        seed = (np.floor(start[:, 0] / 17) + np.floor(start[:, 1] / 17)).astype(int)
        rect = atlas[(seed[:, None] + np.arange(MAX_PER_RUN)) % len(atlas)]
        along = (rect[:, :, 2] - rect[:, :, 0]) * PIXEL_M
        across = (rect[:, :, 3] - rect[:, :, 1]) * PIXEL_M
        lo, hi = at - along / 2, at + along / 2
        keep = (lo >= END_MARGIN_M) & (hi <= length[:, None] - END_MARGIN_M)
        keep &= widths[:, None] - sw.CURB_W - EDGE_MARGIN_M - across >= CLEAR_WALK_M
        runs, candidates = np.nonzero(keep)
        if len(runs):
            fractions = np.c_[lo[keep], hi[keep]] / length[runs, None]
            centres = start[runs, None, :] + fractions[:, :, None] * delta[runs, None, :]
            dirs = np.broadcast_to(direction[runs, None, :], (len(runs), 2, 2))
            result.append(_quads(centres, dirs, rect[keep], heights[runs], origin))
    for kind, curb, outward, _, ramps, width, height, _, slab in remaining:
        if kind != 0 or slab not in (1, sw.BRICK, sw.STONE) or width < sw.CURB_W + EDGE_MARGIN_M + .7 + CLEAR_WALK_M:
            continue
        lengths = np.linalg.norm(np.diff(curb[:, :2], axis=0), axis=1)
        stations = np.r_[0., np.cumsum(lengths)]
        at = np.arange(8., stations[-1] - END_MARGIN_M, SPACING_M)[:MAX_PER_RUN]
        if not len(at):
            continue
        seed = int(np.floor(curb[0, 0] / 17) + np.floor(curb[0, 1] / 17))
        rect = atlas[(seed + np.arange(len(at))) % len(atlas)]
        along, across = ((rect[:, 2:] - rect[:, :2]) * PIXEL_M).T
        lo, hi = at - along / 2, at + along / 2
        keep = (lo >= END_MARGIN_M) & (hi <= stations[-1] - END_MARGIN_M)
        keep &= width - sw.CURB_W - EDGE_MARGIN_M - across >= CLEAR_WALK_M
        for a, b in ramps:
            keep &= (hi <= a - sw.RAMP_FLARE - END_MARGIN_M) | (lo >= b + sw.RAMP_FLARE + END_MARGIN_M)
        first = np.clip(np.searchsorted(stations, lo, side='right') - 1, 0, len(lengths) - 1)
        last = np.clip(np.searchsorted(stations, hi, side='left') - 1, 0, len(lengths) - 1)
        tangent = np.diff(curb[:, :2], axis=0) / np.maximum(lengths[:, None], 1e-9)
        slopes = np.diff(curb[:, 2]) / np.maximum(lengths, 1e-9)
        # Prefix counts reject any bend or height kink covered by a patch,
        # while allowing the ordinary 0.5/2 m drape samples of a straight run.
        breaks = np.r_[0, np.cumsum((np.linalg.norm(np.diff(tangent, axis=0), axis=1) > .03) |
                                   (np.abs(np.diff(slopes)) > .002))]
        keep &= breaks[first] == breaks[last]
        if not keep.any():
            continue
        rect, across, lo, hi = rect[keep], across[keep], lo[keep], hi[keep]
        ends = np.c_[lo, hi].ravel()
        centres = np.column_stack([np.interp(ends, stations, curb[:, i]) for i in range(3)]).reshape(-1, 2, 3)
        dirs = np.column_stack([np.interp(ends, stations, outward[:, i]) for i in range(2)]).reshape(-1, 2, 2)
        result.append(_quads(centres, dirs, rect, np.full(len(lo), height), origin))
    return [combine(result[0], result[1:])] if result else []
