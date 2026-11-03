"""Conservative, cached Places associations for building planning.

Place points establish occupants, never an exclusive building use.  The grid is
built once per decoded cell; all output is bounded and carries source lineage.
"""
from collections import OrderedDict, defaultdict
import hashlib
import json
import math
import numbers
import os
import threading

import mapgeom
from shapely.geometry import Polygon
from shapely import contains_xy

GRID = .001
MAX_OCCUPANTS = 32
MAX_BUCKETS = 4096
MAX_CACHE_CELLS = 8
MAX_CACHE_RECORDS = 100_000
REVISION = 'property-identity-v1'
_LOCK = threading.Lock()

# Exact building classes, not substring matches or an Overture Places taxonomy.
CLASSES = {'grocery_store': 'grocery_store', 'supermarket': 'grocery_store',
           'convenience': 'grocery_store', 'convenience_store': 'grocery_store',
           'strip_shops': 'strip_shops', 'shopping_parade': 'strip_shops',
           'trade_units': 'trade_units', 'clinic': 'clinic', 'hospital': 'hospital'}
COMPATIBLE_SUBTYPES = {
    'commercial': {'grocery_store', 'supermarket', 'convenience', 'convenience_store', 'strip_shops', 'shopping_parade'},
    'retail': {'grocery_store', 'supermarket', 'convenience', 'convenience_store', 'strip_shops', 'shopping_parade'},
    'industrial': {'trade_units'},
    'civic': {'clinic', 'hospital'},
    'healthcare': {'clinic', 'hospital'},
}


def _text(value):
    if value is None:
        return None
    if isinstance(value, numbers.Real) and not math.isfinite(value):
        return None
    return str(value).strip() or None


def _number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) and value >= 0 else None
    except (TypeError, ValueError):
        return None


def _confidence(value):
    value = _number(value)
    return value if value is not None and value <= 1 else None


def _col(f, name, i):
    a = f.attrs.get(name)
    return a[i] if a is not None else None


def index(f):
    """Immutable normalized records and a geographic point grid for one cell."""
    cached = f.__dict__.get('_property_identity_index')
    if cached is not None:
        return cached
    buckets = defaultdict(list)
    records = []
    for i in range(len(f)):
        try:
            p = f.lonlat[f.coord_off[f.ring_off[f.part_off[i]]]]
            lon, lat = float(p[0]), float(p[1])
            if not math.isfinite(lon) or not math.isfinite(lat):
                continue
        except (IndexError, TypeError, ValueError):
            continue
        record = (str(f.ids[i]), lon, lat, _text(_col(f, 'name', i)),
                  _text(_col(f, 'brand_name', i)), _text(_col(f, 'basic_category', i)),
                  _text(_col(f, 'taxonomy', i)), _text(_col(f, 'operating_status', i)),
                  _confidence(_col(f, 'confidence', i)), _text(_col(f, 'src_dataset', i)),
                  _text(_col(f, 'src_record', i)), _text(_col(f, 'brand_wikidata', i)))
        buckets[(math.floor(lon / GRID), math.floor(lat / GRID))].append(len(records))
        records.append(record)
    result = (tuple(records), {k: tuple(v) for k, v in buckets.items()})
    f.__dict__['_property_identity_index'] = result
    return result


def cached_layers(md, keys):
    """Read only existing decoded or on-disk Places cells; never trigger network.

    The separate bounded LRU is invalidated on file modification. Missing or
    corrupt files simply leave identity unavailable for this generation.
    """
    out = []
    # Some callers supply lightweight map providers rather than MapData.
    # Places are optional: never call their potentially fetching cell() API.
    if not callable(getattr(md, 'path', None)):
        return out
    import inputwatch
    for key in keys:
        path = md.path(key, 'places')
        # Missing cells matter too: a later cache fill invalidates the accepted
        # plan at its next ordinary regeneration boundary. No fetch is started.
        if inputwatch.ACTIVE.get() is not None:
            inputwatch.paths((path,))
        lock, memory = getattr(md, '_mem_lock', None), getattr(md, '_mem', None)
        entry = None
        if lock is not None and memory is not None:
            with lock:
                entry = memory.get((str(key), 'places'))
        if entry is not None:
            if entry[0] is not None:
                entry[0].__dict__['_property_release'] = getattr(md, 'release', None)
                out.append(entry[0])
            continue
        try:
            stat = os.stat(path)
            stamp = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            continue
        with _LOCK:
            cache = md.__dict__.setdefault('_property_places_cache', OrderedDict())
            hit = cache.get(path)
            if hit is not None and hit[0] == stamp:
                cache.move_to_end(path)
                out.append(hit[1])
                continue
        load = getattr(md, '_load', None)
        if not callable(load):
            continue
        arrays = load(path)
        if arrays is None or 'missing' in arrays:
            continue
        try:
            f = mapgeom.Features.from_arrays('places', arrays, '')
            f.__dict__['_property_release'] = getattr(md, 'release', None)
            index(f)
        except (ValueError, KeyError, IndexError, TypeError):
            continue
        with _LOCK:
            cache[path] = (stamp, f)
            cache.move_to_end(path)
            while len(cache) > MAX_CACHE_CELLS or sum(len(v[1]) for v in cache.values()) > MAX_CACHE_RECORDS:
                cache.popitem(last=False)
        out.append(f)
    return out


def _building_kind(attrs):
    cls = _text(attrs.get('class'))
    sub = _text(attrs.get('subtype'))
    cls_key, sub_key = (cls or '').lower(), (sub or '').lower()
    kind = CLASSES.get(cls_key)
    if kind is None and (not cls_key or sub_key in COMPATIBLE_SUBTYPES.get(cls_key, ())):
        kind = CLASSES.get(sub_key)
    if attrs.get('_part') and 'class' in attrs.get('_inherited_fields', ()):
        kind = None
    return kind


def resolve_many(rings, attributes, frame, x0=0, y0=0, layers=()):
    """Resolve a tile together, batching coordinate conversions and retaining
    exact point-in-footprint checks. Returns one identity or None per building.
    """
    import numpy as np

    entries = []
    for ring, attrs in zip(rings, attributes):
        kind = _building_kind(attrs)
        if not kind and not layers:
            entries.append(None)
            continue
        footprint = attrs.get('_footprint')
        polygon = footprint.shape() if footprint is not None else Polygon(ring)
        if polygon.is_empty or not polygon.is_valid:
            entries.append(None)
            continue
        entries.append((attrs, kind, polygon, polygon.bounds))
    results = [None] * len(entries)
    active = [(i, entry) for i, entry in enumerate(entries) if entry is not None]
    if not active:
        return results
    if not layers:
        for i, (attrs, kind, polygon, _) in active:
            results[i] = _finish(attrs, kind, polygon, [], layers)
        return results

    # Four corners per footprint, transformed in one native call instead of
    # one call per building. The same corner envelope is used by resolve().
    bounds = np.asarray([entry[3] for _, entry in active], dtype=np.float64)
    xs = np.stack((bounds[:,0], bounds[:,0], bounds[:,2], bounds[:,2]), axis=1) + x0
    ys = np.stack((bounds[:,1], bounds[:,3], bounds[:,1], bounds[:,3]), axis=1) + y0
    lat, lon, _ = frame.enu_to_geodetic(xs, ys, np.zeros_like(xs))
    lat, lon = np.asarray(lat), np.asarray(lon)
    lo_x = np.floor(lon.min(axis=1) / GRID).astype(np.int64)
    hi_x = np.floor(lon.max(axis=1) / GRID).astype(np.int64)
    lo_y = np.floor(lat.min(axis=1) / GRID).astype(np.int64)
    hi_y = np.floor(lat.max(axis=1) / GRID).astype(np.int64)
    indexes = [index(f) for f in layers]
    candidate_keys = []
    needed = {}
    pair_count = 0
    for k in range(len(active)):
        keys = []
        bx0, bx1, by0, by1 = int(lo_x[k]), int(hi_x[k]), int(lo_y[k]), int(hi_y[k])
        if (bx1-bx0+1)*(by1-by0+1) <= MAX_BUCKETS:
            for li, (records, buckets) in enumerate(indexes):
                for bx in range(bx0, bx1+1):
                    for by in range(by0, by1+1):
                        for j in buckets.get((bx, by), ()):
                            key = (li, j)
                            keys.append(key)
                            needed[key] = records[j]
        candidate_keys.append(keys)
        pair_count += len(keys)
        if pair_count > 200_000 and len(entries) > 1:
            # Bound temporary pair buffers in unusually dense or overlapping
            # tiles while keeping exactly the same containment semantics.
            middle = len(entries) // 2
            return (resolve_many(rings[:middle], attributes[:middle], frame, x0, y0, layers) +
                    resolve_many(rings[middle:], attributes[middle:], frame, x0, y0, layers))
    if needed:
        keys = list(needed)
        records = [needed[key] for key in keys]
        east, north, _ = frame.geodetic_to_enu(
            np.asarray([r[2] for r in records]), np.asarray([r[1] for r in records]),
            np.zeros(len(records)))
        xy = {key: (float(e)-x0, float(n)-y0) for key, e, n in zip(keys, east, north)}
    else:
        xy = {}
    # GEOS evaluates all candidate points in one vectorized call. Input order
    # stays unchanged, including duplicates in overlapping source cells.
    pair_polygons, pair_x, pair_y = [], [], []
    for (_, entry), keys in zip(active, candidate_keys):
        for key in keys:
            pair_polygons.append(entry[2])
            x, y = xy[key]
            pair_x.append(x)
            pair_y.append(y)
    contained = iter(contains_xy(np.asarray(pair_polygons, dtype=object), pair_x, pair_y))
    for (i, entry), keys in zip(active, candidate_keys):
        attrs, kind, polygon, _ = entry
        candidates, seen = [], set()
        for key in keys:
            inside = next(contained)
            rec = needed[key]
            if inside and rec[0] not in seen:
                seen.add(rec[0])
                candidates.append(rec)
        results[i] = _finish(attrs, kind, polygon, candidates, layers)
    return results


def resolve(ring, attrs, frame, x0=0, y0=0, layers=()):
    """Resolve a single footprint; tile callers should use resolve_many."""
    return resolve_many((ring,), (attrs,), frame, x0, y0, layers)[0]


def _finish(attrs, kind, polygon, candidates, layers):
    candidates.sort(key=lambda r: r[0])
    occupants = tuple({'id': r[0], 'name': r[3], 'brand': r[4], 'basic_category': r[5],
                       'taxonomy': r[6], 'operating_status': r[7], 'confidence': r[8],
                       'source_dataset': r[9], 'source_record': r[10], 'brand_wikidata': r[11],
                       'association': 'contained'} for r in candidates[:MAX_OCCUPANTS])
    name = _text(attrs.get('name'))
    if not kind and not occupants:
        return None
    area, basis, modifier = None, None, None
    if kind == 'grocery_store':
        # A mapped single-floor exclusive grocery building is a footprint proxy;
        # unknown floor counts and mixed-use buildings do not establish area.
        floors = _number(attrs.get('num_floors'))
        grocery_categories = {'grocery_store', 'convenience_store'}
        exclusive = not candidates or (len(candidates) == 1 and
                    any((candidates[0][j] or '').lower() in grocery_categories for j in (5, 6)))
        if floors == 1 and exclusive and not attrs.get('_part'):
            area, basis = float(polygon.area), 'exclusive_single_storey_footprint_proxy'
            if area >= 400:
                kind = 'supermarket'
                modifier = 'large' if area >= 2500 else None
        else:
            kind = 'food_retail_size_unresolved'
    # The mapped host use/name and the interpretation of contained points are
    # independent: multiple tenants do not invalidate an explicit host class.
    status = 'supported' if kind else 'ambiguous'
    occupant_association = 'ambiguous' if len(candidates) > 1 else ('contained' if candidates else 'unmatched')
    releases = sorted({str(f.__dict__['_property_release']) for f in layers
                       if f.__dict__.get('_property_release')})
    provenance = {'building_id': _text(attrs.get('seed_id')),
                  'places_releases': tuple(releases),
                  'building_source': _text(attrs.get('src_dataset')),
                  'building_record': _text(attrs.get('src_record')),
                  'places': 'overture:places', 'association': 'point_containment_only',
                  'occupants_truncated': len(candidates) > MAX_OCCUPANTS}
    result = {'kind': kind, 'display_name': name, 'occupants': occupants, 'area_basis': basis,
              'premises_area': area, 'status': status, 'occupant_association': occupant_association,
              'provenance': provenance, 'size_modifier': modifier}
    result['revision'] = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    return result
