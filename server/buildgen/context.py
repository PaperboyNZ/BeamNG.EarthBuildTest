"""Observed neighbourhood evidence in a fixed geographic frame.

The profile is deliberately small: buildings, land use and the bundled climate
grid. It never learns from generated buildings. All required cells must load;
fetch errors propagate rather than producing a cacheable partial context.
"""
from collections import OrderedDict
from concurrent.futures import Future
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import threading

import numpy as np

from .evidence import ATTRIBUTE_FIELDS, BuildingEvidence, normalise_attributes
from . import ingest
from . import zones
from . import roof_colours
from . import site_data
from . import regional_geography
from . import regional_architecture
from .topology import InvalidFootprint


PROFILE = "observed-buildings-landuse-climate-v1"
LAYERS = ("buildings", "land_use")
RADIUS_M = 250.0
LOCAL_M = 75.0
MAX_CELLS = 24


@dataclass(frozen=True, slots=True)
class ContextManifest:
    profile: str = "footprint-only-v1"
    owner: str | None = None
    sources: tuple[tuple[str, str], ...] = ()
    digest: str = ""


@dataclass(frozen=True, slots=True)
class Neighbour:
    source_id: str
    distance_m: float
    area_m2: float
    evidence: BuildingEvidence


@dataclass(frozen=True, slots=True)
class Context:
    manifest: ContextManifest = ContextManifest()
    neighbours: tuple[Neighbour, ...] = ()
    # Occupied target overlap, by observed land-use class (not a probability).
    land_use: tuple[tuple[str, float], ...] = ()
    climate: int = 0
    diagnostics: tuple[str, ...] = ()
    zones: tuple[zones.Zone, ...] = ()
    roof_colour: roof_colours.Sample | None = None
    location: tuple[float, float] | None = None  # source latitude/longitude, never render-tile centre


class ContextPending(Exception):
    """A background request must retry once its complete context is available."""


@lru_cache(maxsize=MAX_CELLS)
def _frame(owner):
    import geodesy
    import mapcells
    return geodesy.EnuFrame(*mapcells.parse(owner).center(), 0.)


def planning_footprint(rings, context):
    """Measure source geometry in its context cell, never a render-tile frame."""
    if context is None or context.manifest.owner is None:
        return None
    return ingest.project(None, _frame(context.manifest.owner), rings)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


@lru_cache(maxsize=1)
def climate_identity():
    import climate
    return hashlib.sha256(Path(climate.PATH).read_bytes()).hexdigest()


def _observations(evidence):
    return tuple((o.field, o.value, o.status, o.source, o.reason) for o in evidence.observations)


def halo(key):
    """Cell bounds plus 250 m, including wrapped longitude and high latitudes."""
    import mapcells
    west, south, east, north = key.bounds()
    # 110 km/degree is a conservative bound at these latitudes; a little extra
    # prevents the tangent-plane and geodetic distance difference dropping a cell.
    dy = (RADIUS_M + 5.0) / 110000.0
    dx = dy / max(math.cos(math.radians(max(abs(south), abs(north)) + dy)), 0.08)
    return tuple(sorted(mapcells.cells_for_bbox(max(-mapcells.MAX_LAT, south - dy), west - dx,
                                                min(mapcells.MAX_LAT, north + dy), east + dx)))


class _Bundle:
    """Private spatial index; public query results contain only immutable facts."""

    def __init__(self, key, cds, revision):
        import geodesy
        from shapely import STRtree
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        self.frame = geodesy.EnuFrame(*key.center(), 0.0)
        buildings, land, source_records = {}, {}, []
        coverage = []
        for cd in cds:
            west, south, east, north = cd.key.bounds()
            x, y, _ = self.frame.geodetic_to_enu(np.array([south, south, north, north]),
                                                np.array([west, east, east, west]), 0.)
            coverage.append(Polygon(np.column_stack((x, y))))
            records = []
            for layer in LAYERS:
                f = cd.layers.get(layer)
                if f is None:
                    raise ValueError(f"building context lacks required {layer} in {cd.key}")
                for i in range(len(f.kind)):
                    cc = ingest.components(f, i)
                    if not cc:
                        continue
                    source = str(f.ids[i]) if f.ids is not None and str(f.ids[i]) else \
                        "geometry:" + ":".join(k for k, _ in cc)
                    at = {k: f.attrs[k][i] for k in ATTRIBUTE_FIELDS if k in f.attrs}
                    at["seed_id"] = source
                    evidence = normalise_attributes(at)
                    # Ancillary data filtering is part of the context identity.
                    underground = bool(f.attrs["is_underground"][i]) if "is_underground" in f.attrs else False
                    level = f.attrs["level"][i] if "level" in f.attrs else 0.
                    below = underground or (level is not None and float(level) < 0)
                    records.append((layer, source, cc, _observations(evidence), below))
                    if below:
                        continue
                    try:
                        shape = unary_union([ingest.project(f, self.frame, rings).shape() for _, rings in cc])
                    except InvalidFootprint:
                        continue  # invalid geometry never contributes inferred evidence
                    if layer == "buildings":
                        # Source features can repeat in adjoining cells; deterministic
                        # content ordering also resolves a malformed conflicting duplicate.
                        rank = _digest((cc, _observations(evidence)))
                        if source not in buildings or rank < buildings[source][0]:
                            buildings[source] = (rank, shape, evidence)
                    else:
                        cls = evidence.get("class").value or evidence.get("subtype").value
                        if cls:
                            land.setdefault(str(cls).lower(), []).append(shape)
            source_records.append((str(cd.key), _digest(sorted(records, key=repr))))
        unique, seen_geometry = [], set()
        for sid, (_, shape, ev) in sorted(buildings.items()):
            geometry = shape.normalize().wkb
            if geometry not in seen_geometry:
                unique.append((sid, shape, ev))
                seen_geometry.add(geometry)
        self.buildings = tuple(unique)
        self.tree = STRtree([b[1] for b in self.buildings])
        self.centres = np.array([shape.centroid.coords[0] for _, shape, _ in self.buildings]).reshape(-1, 2)
        # Union clipped/repeated polygons before measuring overlap. Holes stay open.
        self.land = tuple((cls, unary_union(shapes)) for cls, shapes in sorted(land.items()))
        self.coverage = unary_union(coverage)
        sources = tuple(sorted(source_records)) + (("revisions", revision), ("climate", climate_identity()),
                                                   ("zones", zones.catalogue()[0]), ("sites", site_data.catalogue()[0]),
                                                   ("roof_colours", roof_colours.catalogue()[0]),
                                                   ("regional_geography", regional_geography.identity()),
                                                   ("regional_architecture", regional_architecture.identity()))
        self.manifest = ContextManifest(PROFILE, str(key), sources, _digest((PROFILE, str(key), sources)))

    def query(self, f, i):
        import climate
        from shapely.geometry import Point
        from shapely.ops import unary_union
        cc = ingest.components(f, i)
        shapes = [ingest.project(f, self.frame, rings).shape() for _, rings in cc]
        target = unary_union(shapes)
        # The same point chooses the owner cell and centres the evidence radius.
        # An area centroid can lie outside that cell for large concave footprints.
        lon, lat = np.asarray(cc[0][1][0], np.float64).mean(axis=0)
        x, y, _ = self.frame.geodetic_to_enu(float(lat), float(lon), 0.)
        point = Point(float(x), float(y))
        source = str(f.ids[i]) if f.ids is not None and str(f.ids[i]) else \
            "geometry:" + ":".join(k for k, _ in cc)
        neighbours = []
        candidates = self.tree.query(point.buffer(RADIUS_M))
        distances = np.linalg.norm(self.centres[candidates] - [point.x, point.y], axis=1)
        overlaps = set(self.tree.query(target, predicate="intersects"))
        for j, distance in zip(candidates, distances):
            if distance > RADIUS_M:
                continue
            sid, shape, ev = self.buildings[int(j)]
            # Source geometry is the self-exclusion authority, including duplicates
            # with another ID (common when providers overlap).
            if sid == source or (j in overlaps and shape.intersection(target).area > .5 * min(shape.area, target.area)):
                continue
            neighbours.append(Neighbour(sid, float(distance), float(shape.area), ev))
        diagnostics = ()
        # Very large/disconnected buildings may extend beyond their owner's
        # context halo. Partial land-use coverage is not whole-building evidence.
        if self.coverage.covers(target):
            lu = tuple((cls, min(1., float(shape.intersection(target).area / target.area)))
                       for cls, shape in self.land if shape.intersects(target))
        else:
            lu, diagnostics = (), ("land_use_target_exceeds_context_extent",)
        return Context(self.manifest, tuple(sorted(neighbours, key=lambda n: n.source_id)), lu,
                       climate.koppen_at(float(lat), float(lon)), diagnostics, zones.query(target, self.frame),
                       roof_colours.query(source, cc), (float(lat), float(lon)))


class Provider:
    """Bounded per-MapData cache, independent of tile size, anchor or LOD.

    A Future coalesces concurrent builds without holding the cache lock during IO.
    Failed entries are removed so a later retry can obtain complete evidence.
    """

    def __init__(self, md):
        self.md = md
        self._lock = threading.Lock()
        self._cache = OrderedDict()

    def query(self, f, i, *, background=False):
        import mapcells
        cc = ingest.components(f, i)
        lon, lat = np.asarray(cc[0][1][0], np.float64).mean(axis=0)
        key = mapcells.cell_of(float(lat), float(lon))
        revision = _digest(self.md.versions())
        cache_key = (key, revision)
        keys = halo(key)
        # A skyline request must not block its queue or finalise a partial plan.
        if background and not all(self.md.has(k, layer) for k in keys for layer in LAYERS):
            for k in keys:
                self.md.prefetch(k, layers=LAYERS)
            raise ContextPending()
        with self._lock:
            future = self._cache.get(cache_key)
            build = future is None
            if build:
                future = Future()
                self._cache[cache_key] = future
            self._cache.move_to_end(cache_key)
        if build:
            try:
                cds = [self.md.cell(k, layers=LAYERS, kind="background" if background else "demand") for k in keys]
                from . import contextcache
                bundle = contextcache.get(self.md, key, cds, revision,
                    lambda: _Bundle(key, cds, revision), background=background)
            except BaseException as exc:
                future.set_exception(exc)
                with self._lock:
                    self._cache.pop(cache_key, None)
                raise
            else:
                future.set_result(bundle)
                with self._lock:
                    for old in list(self._cache):
                        if len(self._cache) <= MAX_CELLS:
                            break
                        if old != cache_key and self._cache[old].done():
                            del self._cache[old]
        elif background and not future.done():
            raise ContextPending()
        return future.result().query(f, i)


_provider_lock = threading.Lock()


def provider(md):
    # The MapData object owns the cache lifetime; no global references retain a
    # closed world. Geometry workers each construct their own MapData/provider.
    with _provider_lock:
        if not hasattr(md, "_building_context"):
            md._building_context = Provider(md)
        return md._building_context
