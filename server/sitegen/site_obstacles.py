"""Cache-only exclusions for automatically generated site surfaces.

All supplied road and map geometry is in the current frame; output is clipped
and translated to the building tile's local coordinates. Unresolvable input or
budget exhaustion excludes the whole tile rather than silently missing hazards.
"""
from itertools import islice

import numpy as np
from shapely.affinity import translate
from shapely.geometry import LineString, Polygon, box

MAX_INPUTS = 10000
MAX_FEATURES = 10000
MAX_VERTICES = 131072
MAX_POLYGONS = 8192
RAIL_HALF_WIDTH = 4.0


def cached_water(mapdata, keys):
    """Read available water features without invoking a network-capable cell load."""
    import mapgeom
    tables=[]
    for index, key in enumerate(islice(iter(keys),65)):
        if index >= 64:raise ValueError('water cell budget')
        # Reuse decoded arrays whenever the ordinary terrain pass loaded them.
        with mapdata._mem_lock:
            cached=mapdata._mem.get((str(key),'water'))
        if cached is not None:
            if cached[0] is not None:tables.append(cached[0])
            continue
        # _load is a disk-only reader. Unlike cell(), it never rebuilds a miss.
        arrays=mapdata._load(mapdata.path(key,'water'))
        if arrays is not None and 'missing' not in arrays:
            tables.append(mapgeom.Features.from_arrays('water',arrays,''))
    return tuple(tables)


def for_items(items,mapdata,frame,bounds,*,chunks=(),fuel_pads=(),surface=None,cells=(),drives=(),keys=()):
    """Avoid any extra inventory work on tiles without an eligible frontage."""
    import os
    from buildgen.automatic_sites import eligible
    from buildgen.quality import site_level
    # Only automatic frontage consumes this inventory. Lower policies retain
    # installed sites without proposing replacements, so need no new hazards.
    if site_level() < 2 or os.environ.get('BNE_BUILDING_PATHS','auto')=='off' or not any(eligible(s) for s,_,_ in items):
        return ()
    try:
        water=cached_water(mapdata,keys)
        return collect(frame,bounds,chunks=chunks,fuel_pads=fuel_pads,surface=surface,
                       cells=(*cells,*water),drives=drives)
    except (ValueError,TypeError,OSError,AttributeError):
        return (box(0,0,bounds[2]-bounds[0],bounds[3]-bounds[1]),)


def collect(frame, bounds, *, chunks=(), fuel_pads=(), surface=None, cells=(), drives=()):
    """Return tile-local exclusion polygons using only supplied/cached sources.

    ``cells`` accepts CellData objects or already loaded water/roads Features.
    Missing layers are not fetched. Mapped water polygon holes remain usable land.
    """
    bounds = tuple(map(float, bounds))
    if len(bounds) != 4 or not np.isfinite(bounds).all() or bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
        raise ValueError('site obstacles require finite ordered bounds')
    clip = box(*bounds)
    fallback = (box(0, 0, bounds[2]-bounds[0], bounds[3]-bounds[1]),)
    result = []
    vertices = 0

    def limited(values, limit):
        out = tuple(islice(iter(values), limit + 1))
        if len(out) > limit:
            raise ValueError('site obstacle budget')
        return out

    def add(shape):
        nonlocal vertices
        if shape.is_empty or not shape.is_valid:
            raise ValueError('invalid site obstacle')
        shape = shape.intersection(clip)
        pieces = (shape,) if shape.geom_type == 'Polygon' else getattr(shape, 'geoms', ())
        for part in pieces:
            if part.geom_type != 'Polygon' or part.area <= 1e-8:
                continue
            vertices += len(part.exterior.coords) + sum(len(r.coords) for r in part.interiors)
            if vertices > MAX_VERTICES or len(result) >= MAX_POLYGONS:
                raise ValueError('site obstacle geometry budget')
            result.append(translate(part, xoff=-bounds[0], yoff=-bounds[1]))

    try:
        chunks = limited(chunks or (), MAX_INPUTS)
        drives = limited(drives or (), MAX_INPUTS)
        fuel_pads = limited(fuel_pads or (), MAX_INPUTS)
        cells = limited(cells or (), MAX_INPUTS)
        # Guard before the existing ribbon solver's allocations.
        source_vertices = 0
        for chunk in chunks:
            p = np.asarray(chunk.get('n', ()), dtype=float)
            poly = chunk.get('poly')
            if poly is not None:
                polygon = np.asarray(poly, dtype=float)
                if polygon.ndim != 2 or polygon.shape[1] < 2 or len(polygon) < 3 or not np.isfinite(polygon).all() or not Polygon(polygon[:, :2]).is_valid:
                    raise ValueError('invalid road polygon')
                source_vertices += len(polygon)
            # Polygon-only road chunks intentionally have empty n and zero width.
            if p.size == 0 and poly is not None:
                continue
            if p.ndim != 2 or p.shape[1] < 2 or len(p) < 2 or not np.isfinite(p).all():
                raise ValueError('invalid road chunk')
            width = float(chunk.get('w', 0))
            if not np.isfinite(width) or width <= 0:
                raise ValueError('invalid road width')
            source_vertices += len(p)
        for drive in drives:
            p = np.asarray(drive.get('n', ()), dtype=float)
            width = float(drive.get('w', 0))
            if p.ndim != 2 or p.shape[1] < 2 or len(p) < 2 or not np.isfinite(p).all() or not np.isfinite(width) or width <= 0:
                raise ValueError('invalid driveway')
            source_vertices += len(p)
        for _, polygons in fuel_pads:
            for lat, lon in limited(polygons, MAX_POLYGONS):
                lat, lon = np.asarray(lat, dtype=float), np.asarray(lon, dtype=float)
                if lat.ndim != 1 or lon.ndim != 1 or len(lat) < 3 or len(lat) != len(lon) or not np.isfinite(lat).all() or not np.isfinite(lon).all():
                    raise ValueError('invalid fuel pad')
                source_vertices += len(lat)
        if source_vertices > MAX_VERTICES:
            raise ValueError('site obstacle source vertex budget')
        from .hardscape import collect as hardscape
        data = hardscape(chunks=chunks, drives=drives, frame=frame, fuel_pads=fuel_pads, bounds=bounds)
        for record in data['polygons']:
            rings = record['rings']
            add(Polygon(rings[0], rings[1:]))
        from .mapped_surfaces import collect as mapped
        for _, shape in mapped(frame, bounds, surface):
            add(shape)

        import mapgeom
        count = 0
        for cell in cells:
            tables = tuple(getattr(cell, 'layers', {}).get(k) for k in ('water', 'roads')) if hasattr(cell, 'layers') else (cell,)
            for table in tables:
                if table is None:
                    continue
                count += len(table.kind)
                if count > MAX_FEATURES:
                    raise ValueError('site obstacle feature budget')
                layer = getattr(table, 'layer', '')
                sub = table.attrs.get('subtype', ())
                for i, kind in enumerate(table.kind):
                    water = layer == 'water' and kind == mapgeom.POLYGON
                    rail = layer == 'roads' and kind == mapgeom.LINE and len(sub) > i and str(sub[i]) == 'rail'
                    if not (water or rail):
                        continue
                    for part in limited(table.parts(i), MAX_POLYGONS):
                        rings = limited(part, MAX_POLYGONS)
                        if not rings:
                            raise ValueError('missing obstacle geometry')
                        converted = []
                        for ring in rings:
                            ring = np.asarray(ring, dtype=float)
                            if ring.ndim != 2 or ring.shape[1] != 2 or len(ring) > MAX_VERTICES or not np.isfinite(ring).all():
                                raise ValueError('invalid obstacle ring')
                            source_vertices += len(ring)
                            if source_vertices > MAX_VERTICES:
                                raise ValueError('site obstacle source vertex budget')
                            x, y = mapgeom.enu_xy(table, frame, ring)
                            xy = np.column_stack((x, y))
                            if not np.isfinite(xy).all():
                                raise ValueError('invalid projected obstacle')
                            converted.append(xy)
                        if water:
                            add(Polygon(converted[0], converted[1:]))
                        else:
                            add(LineString(converted[0]).buffer(RAIL_HALF_WIDTH, cap_style='flat', join_style='mitre'))
    except Exception:
        return fallback
    return tuple(result)
