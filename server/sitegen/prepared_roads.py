"""Immutable road geometry prepared once per detached frontage planning job.

Sidewalk cuts and site obstacles remain live caller inputs. This only reuses
source road segments and their geometry; candidate order and budgets stay with
the consumer. No process-global or cross-frame cache is involved.
"""
import math

import numpy as np
from shapely import STRtree
from shapely.geometry import LineString, Point, box


class PreparedRoads:
    def __init__(self, lines, offset):
        self.offset = np.asarray(offset, float).copy()
        self.offset.flags.writeable = False
        detached = []
        for line in lines:
            source = np.asarray(line[0], float)
            points = np.frombuffer(source.tobytes(), dtype=float).reshape(source.shape)
            detached.append((points, *line[1:]))
        self.lines = tuple(detached)
        self._raw = self._simple = None
        self._corridors = {}

    def raw(self):
        if self._raw is None:
            rows = []
            for line in self.lines:
                points = np.asarray(line[0], float)
                for a, b in zip(points[:-1, :2]-self.offset, points[1:, :2]-self.offset):
                    v = b-a
                    rows.append((a, b, v, np.linalg.norm(v), (a+b)/2, line))
            self._raw = tuple(rows)
        return self._raw

    def nearby(self, portal, reach):
        if self._simple is None:
            from .portals import simplified_lines
            rows, shapes = [], []
            widest = 0.
            for line in simplified_lines(self.lines):
                points = np.asarray(line[0], float)[:, :2]-self.offset
                half = float(line[1])
                if not math.isfinite(half) or half <= 0:
                    continue
                widest = max(widest, half)
                for a, b in zip(points[:-1], points[1:]):
                    rows.append((a, b, half, line))
                    shapes.append(LineString([a, b]))
            self._simple = tuple(rows), tuple(shapes), STRtree(shapes), widest
        rows, shapes, tree, widest = self._simple
        point = Point(portal)
        radius = reach+widest
        # This query is only a broad phase. Round outward so a segment accepted
        # by the original exact distance comparison cannot be lost at an edge.
        lo = np.nextafter(np.asarray(portal)-radius, -np.inf)
        hi = np.nextafter(np.asarray(portal)+radius, np.inf)
        area = box(lo[0], lo[1], hi[0], hi[1])
        return [(i, rows[i]) for i in sorted(map(int, tree.query(area)))
                if shapes[i].distance(point) <= reach+rows[i][2]]

    def corridor(self, index):
        if index not in self._corridors:
            rows, shapes, _, _ = self._simple
            self._corridors[index] = shapes[index].buffer(rows[index][2], cap_style=2)
        return self._corridors[index]
