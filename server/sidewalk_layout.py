"""Indexed whole-footprint protection of carriageways from raised sidewalks.

Centreline-only tests miss a slab's edge at a skew crossing and beside islands.
Trim the sidewalk's length where it conflicts; never narrow the source road.
"""
import numpy as np
from shapely import STRtree, get_coordinates
from shapely.geometry import LineString, Polygon

TOLERANCE_M = .02
AREA_TOL = 1e-6


class CarriagewayGuard:
    def __init__(self, carriageways):
        self.shapes = [LineString(np.asarray(line)[:, :2]).buffer(max(.001, half - TOLERANCE_M),
                       cap_style=2, join_style=2) for line, half in carriageways if len(line) >= 2]
        self.tree = STRtree(self.shapes)

    def intersections(self, points, skip=()):
        shape = Polygon(np.asarray(points)[:, :2])
        if not shape.is_valid:
            shape = shape.buffer(0)
        for i in self.tree.query(shape, predicate='intersects'):
            if i in skip:
                continue
            overlap = shape.intersection(self.shapes[i])
            if overlap.area > AREA_TOL:
                yield overlap

    def clear(self, points, skip=()):
        return next(self.intersections(points, skip), None) is None

    def trim(self, run):
        import sidewalks as sw
        points = np.asarray(run['pts'], np.float64)
        width = float(run['w'])
        curb, outward = sw.run_geometry(points, run['side'], width)
        # Include the sloped rear face, which is also raised and collidable.
        back = width + sw.BACK_RUN * (float(run.get('curb_h', .18)) + width * sw.CROSS_SLOPE + sw.SINK)
        rear = curb[:, :2] + outward * back
        outline = np.vstack((curb[:, :2], rear[::-1]))
        if self.clear(outline):
            return [run]
        chains, chain = [], []
        for j in range(len(points) - 1):
            a, b = points[j], points[j + 1]
            delta = b[:2] - a[:2]
            length2 = float(delta @ delta)
            if length2 < 1e-12:
                continue
            quad = [curb[j, :2], curb[j + 1, :2], rear[j + 1], rear[j]]
            bad = []
            for overlap in self.intersections(quad):
                coordinates = get_coordinates(overlap)
                along = (coordinates - a[:2]) @ delta / length2
                pad = .025 / np.sqrt(length2)
                bad.append((max(0., float(along.min()) - pad), min(1., float(along.max()) + pad)))
            safe, start = [], 0.
            for lo, hi in sorted(bad):
                if lo > start:
                    safe.append((start, lo))
                start = max(start, hi)
            if start < 1:
                safe.append((start, 1.))
            for lo, hi in safe:
                if hi - lo < 1e-8:
                    continue
                p, q = a + lo * (b - a), a + hi * (b - a)
                if chain and np.linalg.norm(chain[-1] - p) > 1e-6:
                    chains.append(np.asarray(chain)); chain = []
                if not chain:
                    chain.append(p)
                chain.append(q)
            if not safe or safe[-1][1] < 1:
                if chain:
                    chains.append(np.asarray(chain)); chain = []
        if chain:
            chains.append(np.asarray(chain))
        result = []
        for p in chains:
            if np.linalg.norm(p[-1, :2] - p[0, :2]) < .05:
                continue
            c, out = sw.run_geometry(p, run['side'], width)
            if not self.clear(np.vstack((c[:, :2], (c[:, :2] + out * back)[::-1]))):
                continue
            first = np.linalg.norm(p[0] - points[0]) < 1e-6
            last = np.linalg.norm(p[-1] - points[-1]) < 1e-6
            result.append({**run, 'pts': p, 'j': (first and run['j'][0], last and run['j'][1]),
                           'open': (run['open'][0] if first else True, run['open'][1] if last else True),
                           'clearance_trimmed': True})
        return result
