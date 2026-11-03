"""Pinned, normalized zoning overlay; no network requests in the planner.

catalog/zones.json is a GeoJSON FeatureCollection in WGS84 longitude/latitude.
An empty collection is intentional: the shipped baseline has observed land use,
not worldwide statutory zoning. Importers must resolve local codes explicitly.
"""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path

import numpy as np


PATH = Path(__file__).with_name("catalog") / "zones.json"
USES = frozenset("residential commercial industrial agricultural civic religious transport ancillary mixed unknown".split())
PROJECTED_COORDINATE_BUDGET = 65536


def _projected(frame, digest, index, polygon):
    """Frame-owned LRU: at most 64 boundaries / 65,536 coordinate pairs.

    Array transforms avoid Python coordinate tuples. Prepared boundaries make
    the usual wholly-contained footprint cheap; partial overlaps remain exact.
    """
    from collections import OrderedDict
    from threading import RLock
    from shapely import transform, get_num_coordinates, prepare
    lock, cache, count = frame.__dict__.setdefault('_building_zones', (RLock(), OrderedDict(), [0]))
    key = (digest, index)
    with lock:
        if key in cache:
            cache.move_to_end(key)
            return cache[key][0]
        def project(xy):
            xx, yy, _ = frame.geodetic_to_enu(xy[:,1], xy[:,0], 0.)
            return np.column_stack((xx, yy))
        projected = transform(polygon, project)
        prepare(projected)
        size = int(get_num_coordinates(projected))
        if size <= PROJECTED_COORDINATE_BUDGET:
            while cache and (len(cache) >= 64 or count[0]+size > PROJECTED_COORDINATE_BUDGET):
                _, (_, removed) = cache.popitem(last=False)
                count[0] -= removed
            cache[key] = (projected, size)
            count[0] += size
        return projected


@dataclass(frozen=True, slots=True)
class Zone:
    source_id: str
    release: str
    lineage: str
    raw_code: str
    meaning: str
    uses: tuple[str, ...]
    overlap: float
    status: str = "effective"
    environment: str = ""
    region: str = ""


@lru_cache(maxsize=1)
def catalogue():
    return load(os.environ.get('BNE_BUILDING_ZONES') or PATH)


def load(path):
    from shapely.geometry import shape
    raw = Path(path).read_bytes()
    geometries = None
    if Path(path).suffix.lower()=='.npz':
        import io
        from shapely import from_wkb
        with np.load(io.BytesIO(raw),allow_pickle=False) as packed:
            if int(packed['schema'])!=1:raise ValueError('unsupported packed zones')
            data=json.loads(str(packed['metadata']))
            offsets=packed['offsets'];blob=packed['geometry'].tobytes()
        if offsets.ndim!=1 or len(offsets)!=len(data['features'])+1 or offsets[0]!=0 \
                or offsets[-1]!=len(blob) or np.any(np.diff(offsets)<=0):
            raise ValueError('invalid packed zone offsets')
        geometries=from_wkb([blob[int(a):int(b)] for a,b in zip(offsets,offsets[1:])])
    else:
        data = json.loads(raw)
    if data.get("type") != "FeatureCollection" or data.get("crs"):
        raise ValueError("zone catalogue must be RFC 7946 WGS84 GeoJSON")
    records = []
    for index, feature in enumerate(data["features"]):
        p = feature["properties"]
        for key in ("source_id", "release", "lineage", "raw_code", "meaning", "status"):
            if not isinstance(p.get(key), str) or not p[key].strip():
                raise ValueError(f"zone lacks {key}")
        uses = tuple(sorted(set(p["uses"])))
        if not uses or not set(uses) <= USES:
            raise ValueError("zone has unmapped normalized use")
        if p["meaning"] not in ("observed", "statutory", "planned", "modelled"):
            raise ValueError("unknown zone meaning")
        if p["status"] not in ("effective", "proposed", "superseded"):
            raise ValueError("unknown zone status")
        g = geometries[index] if geometries is not None else shape(feature["geometry"])
        if g.geom_type not in ("Polygon", "MultiPolygon") or not g.is_valid or g.is_empty:
            raise ValueError("invalid zone polygon")
        west, south, east, north = g.bounds
        if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90) or east-west > 180:
            raise ValueError("invalid geographic zone bounds; split dateline polygons")
        from .environments import catalogue as environments
        environment, region = p.get('environment', ''), p.get('region', '')
        if environment and environment not in environments()['environments']:
            raise ValueError('unknown zone environment')
        if region and region not in environments()['regions']:
            raise ValueError('unknown architectural region')
        records.append((g, Zone(*(p[k] for k in ("source_id", "release", "lineage", "raw_code", "meaning")),
                                uses, 0., p["status"], environment, region)))
    from shapely import STRtree
    return hashlib.sha256(raw).hexdigest(), tuple(records), STRtree([g for g, _ in records])


def query(target, frame):
    """Project candidate polygons into the same metric frame before overlap."""
    from dataclasses import replace
    from shapely.geometry import box
    digest, records, tree = catalogue()
    if not records:
        return ()
    x0, y0, x1, y1 = target.bounds
    lat, lon, _ = frame.enu_to_geodetic(np.array([x0,x1,x1,x0]), np.array([y0,y0,y1,y1]), 0.)
    if np.ptp(lon) > 180:
        candidates = range(len(records))
    else:
        candidates = tree.query(box(min(lon), min(lat), max(lon), max(lat)))
    result = []
    for i in candidates:
        polygon, zone = records[int(i)]
        projected = _projected(frame, digest, int(i), polygon)
        if not projected.intersects(target):
            continue
        overlap = 1. if projected.covers(target) else projected.intersection(target).area / target.area
        if overlap > 1e-8:
            result.append(replace(zone, overlap=min(1., float(overlap))))
    return tuple(sorted(result, key=lambda z: (z.source_id, z.release, z.raw_code, z.overlap)))


def support(zones):
    """Correlated overlays contribute once; permissions alone cannot prove use."""
    groups = {}
    for zone in zones:
        if zone.status != "effective" or zone.meaning == "planned" or zone.overlap < .6:
            continue
        weight = {"observed": 3., "modelled": 1.6, "statutory": .65}[zone.meaning]
        for use in zone.uses:
            if use == "unknown":
                continue
            key = (zone.lineage, use)
            score = weight * zone.overlap / len(zone.uses)
            reason = f"zone:{zone.source_id}:{zone.release}:{zone.raw_code}:{zone.meaning}"
            if key not in groups or (score, reason) > groups[key]:
                groups[key] = score, reason
    # Cap all layers for a use as well: several permissions cannot become facts.
    for use in sorted({use for _, use in groups}):
        values = [v for (_, u), v in groups.items() if u == use]
        yield use, max(v[0] for v in values), tuple(sorted(v[1] for v in values))
