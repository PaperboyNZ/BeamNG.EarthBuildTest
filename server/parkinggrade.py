"""Small, slope-preserving terrain corrections beneath parking footprints.

Fixed feature-local grids make block, road mesh and far-field queries agree, regardless
of query order, anchor or tile size. Road grading runs afterwards so entrances keep
matching their driving aisles. No terrace or constant-height pad is introduced.
"""
from collections import OrderedDict
import json
import logging
import time
import threading

import numpy as np
from shapely import contains_xy, distance, points, from_wkb
from shapely.geometry import Polygon, LineString

import geodesy
import mapcells
import roads

STEP_M = 2.0
SIGMA_M = 3.0
FALLOFF_M = 4.0
MAX_CHANGE_M = 0.35
STRENGTH = 0.75
MAX_GRID_POINTS = 300000
CACHE_SIZE = 256
CACHE_BYTES = 64 * 1024 * 1024
log = logging.getLogger("earthd.parkinggrade")


def _smooth(z):
    radius = int(np.ceil(3 * SIGMA_M / STEP_M))
    x = np.arange(-radius, radius + 1) * STEP_M
    kernel = np.exp(-.5 * (x / SIGMA_M)**2)
    kernel /= kernel.sum()
    # Linear continuation preserves an existing slope, including at the grid edge.
    out = z
    for axis in (0, 1):
        a = np.moveaxis(out, axis, 0)
        left = a[0] + np.arange(-radius, 0)[:, None] * (a[1] - a[0])
        right = a[-1] + np.arange(1, radius + 1)[:, None] * (a[-1] - a[-2])
        padded = np.concatenate((left, a, right))
        out = np.moveaxis(sum(w * padded[i:i+len(a)] for i, w in enumerate(kernel)), 0, axis)
    return out


class Patch:
    def __init__(self, frame, shape, elev):
        self.frame, self.shape = frame, shape
        x0, y0, x1, y1 = shape.bounds
        # Coarse geographic rejection before converting potentially millions of block samples.
        pad = FALLOFF_M + 1.
        a, b, _ = frame.enu_to_geodetic(np.array([x0-pad, x1+pad, x0-pad, x1+pad]),
                                       np.array([y0-pad, y0-pad, y1+pad, y1+pad]), 0.)
        self.bounds_ll = (float(np.min(a)), float(np.min(b)), float(np.max(a)), float(np.max(b)))
        halo = FALLOFF_M + 3 * SIGMA_M + STEP_M
        self.x0, self.y0 = np.floor((np.array([x0, y0]) - halo) / STEP_M) * STEP_M
        nx, ny = np.ceil((np.array([x1, y1]) + halo - [self.x0, self.y0]) / STEP_M).astype(int) + 1
        if nx * ny > MAX_GRID_POINTS:
            raise ValueError("parking footprint too large for a local smoothing patch")
        xx, yy = np.meshgrid(self.x0 + np.arange(nx)*STEP_M, self.y0 + np.arange(ny)*STEP_M)
        la, lo, _ = frame.enu_to_geodetic(xx, yy, 0.)
        z = np.asarray(elev(la.ravel(), lo.ravel()), np.float64).reshape(xx.shape)
        if not np.isfinite(z).all():
            raise ValueError("non-finite parking elevations")
        # Smoothly limit cut/fill rather than clipping to a new hard height plateau.
        self.delta = MAX_CHANGE_M * np.tanh(STRENGTH * (_smooth(z) - z) / MAX_CHANGE_M)

    def corrections(self, lat, lon):
        a0, b0, a1, b1 = self.bounds_ll
        coarse = np.flatnonzero((lat >= a0) & (lat <= a1) & (lon >= b0) & (lon <= b1))
        if not len(coarse):
            return coarse, np.zeros(0), np.zeros(0)
        x, y, _ = self.frame.geodetic_to_enu(lat[coarse], lon[coarse], 0.)
        x, y = np.asarray(x), np.asarray(y)
        x0, y0, x1, y1 = self.shape.bounds
        select = np.flatnonzero((x >= x0-FALLOFF_M) & (x <= x1+FALLOFF_M) &
                               (y >= y0-FALLOFF_M) & (y <= y1+FALLOFF_M))
        if not len(select):
            return select, np.zeros(0), np.zeros(0)
        x, y = x[select], y[select]
        inside = contains_xy(self.shape, x, y)
        d = np.zeros(len(x))
        d[~inside] = distance(self.shape, points(x[~inside], y[~inside]))
        t = np.clip(1 - d/FALLOFF_M, 0., 1.)
        weight = t*t*(3-2*t)
        gx, gy = (x-self.x0)/STEP_M, (y-self.y0)/STEP_M
        ix, iy = np.floor(gx).astype(int), np.floor(gy).astype(int)
        fx, fy = gx-ix, gy-iy
        z = self.delta
        change = ((1-fy)*((1-fx)*z[iy, ix] + fx*z[iy, ix+1]) +
                  fy*((1-fx)*z[iy+1, ix] + fx*z[iy+1, ix+1]))
        return coarse[select], change, weight


def _sources(feats):
    """Feature ids and geodetic geometry; only actual ground-level parking."""
    if feats is None:
        return
    cls = feats.attrs.get("class")
    specs = roads.road_specs(feats) if feats.layer == "roads" else None
    for i in range(len(feats)):
        if specs is not None:
            sp = specs[i]
            if sp is None or roads._rule_value(feats.rules.get("subclass"), i) != "parking_aisle":
                continue
            parts = [[ring] for ring in roads.ground_parts(feats, i)]
            width = sp.width / 2 + 5.5
        else:
            if cls is None or str(cls[i]) != "parking" or feats.kind[i] != 3:
                continue
            parts, width = feats.parts(i), None
        for j, part in enumerate(parts):
            if not part or len(part[0]) < (2 if width else 3):
                continue
            ll = np.asarray(part[0], np.float64)
            frame = geodesy.EnuFrame(float(ll[:, 1].mean()), float(ll[:, 0].mean()))
            rings = []
            for ring in part:
                ring = np.asarray(ring)
                x, y, _ = frame.geodetic_to_enu(ring[:, 1], ring[:, 0], 0.)
                rings.append(np.c_[x, y])
            shape = (LineString(rings[0]).buffer(width, cap_style=2) if width else
                     Polygon(rings[0], rings[1:]).buffer(0))
            if not shape.is_empty:
                yield (str(feats.layer), str(feats.ids[i]), j, shape.wkb), frame, shape


class ParkingGrader:
    def __init__(self, md, elev):
        self.md, self.elev = md, elev
        self.cache = OrderedDict()
        self.cache_bytes = 0
        self.cells = OrderedDict()
        self.road_features = {}
        self.failed = {}
        self.lock = threading.RLock()

    def _cell(self, key, shared):
        # Reuse source footprints across workers and revisits, like road plans. Only
        # complete map reads are persisted; correction grids stay in the bounded LRU.
        import revisit
        persist = getattr(shared, "persist", None)
        cache_key = revisit.key("parking", *persist[1], str(key)) if persist else None
        if persist:
            saved = revisit.load(persist[0], "parking", cache_key)
            if saved is not None:
                try:
                    rows = json.loads(saved[0]["footprints.json"])
                    return [((layer, fid, part, bytes.fromhex(wkb)), geodesy.EnuFrame(lat, lon),
                             from_wkb(bytes.fromhex(wkb))) for layer, fid, part, wkb, lat, lon in rows]
                except (KeyError, ValueError, TypeError):
                    pass
        before = revisit.faults()
        cd = self.md.cell(key, layers=("infrastructure", "roads"), kind="demand")
        cell = list(_sources(cd.layers.get("infrastructure"))) + list(_sources(cd.layers.get("roads")))
        if revisit.faults() != before:
            raise ValueError("incomplete parking map data")
        self.road_features[str(key)] = cd.layers.get("roads")
        if persist:
            rows = [[*ident[:3], ident[3].hex(), frame.lat0, frame.lon0] for ident, frame, _ in cell]
            revisit.store(persist[0], "parking", cache_key, {"footprints.json": json.dumps(rows).encode()})
        return cell

    def apply(self, lat, lon, base, planned_only=False, shared=None):
        shape = np.shape(base)
        la, lo = np.asarray(lat).ravel(), np.asarray(lon).ravel()
        if not len(la):
            return base
        pad = 20./111320.
        pad_lon = pad/max(.05, np.cos(np.radians(la.mean())))
        keys = mapcells.cells_for_points(la, lo, pad, pad_lon)
        if len(keys) > 8:
            keys = mapcells.cells_near_points(la, lo, pad, pad_lon)
        patches = {}
        # Building each small patch once also avoids concurrent duplicate DEM reads.
        with self.lock:
            for key in sorted(keys, key=str):
                cell = self.cells.get(str(key))
                if cell is None:
                    if planned_only or time.monotonic() - self.failed.get(str(key), -1e9) < 30.:
                        continue
                    try:
                        cell = self._cell(key, shared)
                    except Exception as exc:
                        import revisit
                        revisit.fault()
                        self.failed[str(key)] = time.monotonic()
                        if len(self.failed) > 64:
                            self.failed.pop(next(iter(self.failed)))
                        log.debug("parking smoothing cell %s: %s", key, exc)
                        continue
                    self.cells[str(key)] = cell
                    while len(self.cells) > 64:
                        old, _ = self.cells.popitem(last=False)
                        self.road_features.pop(old, None)
                for ident, frame, footprint in cell:
                    if ident in patches:
                        continue
                    patch = self.cache.get(ident)
                    if patch is None:
                        try:
                            patch = Patch(frame, footprint, self.elev)
                        except ValueError as exc:
                            log.debug("parking smoothing skipped: %s", exc)
                            continue
                        self.cache[ident] = patch
                        self.cache_bytes += patch.delta.nbytes
                        while len(self.cache) > CACHE_SIZE or self.cache_bytes > CACHE_BYTES:
                            _, old = self.cache.popitem(last=False)
                            self.cache_bytes -= old.delta.nbytes
                    else:
                        self.cache.move_to_end(ident)
                    patches[ident] = patch
        if not patches:
            return base
        total, weights, strength = np.zeros(len(la)), np.zeros(len(la)), np.zeros(len(la))
        for patch in patches.values():
            idx, change, weight = patch.corrections(la, lo)
            total[idx] += change*weight
            weights[idx] += weight
            strength[idx] = np.maximum(strength[idx], weight)
        delta = total / np.maximum(weights, 1e-12) * strength
        return np.asarray(base) + delta.reshape(shape)
