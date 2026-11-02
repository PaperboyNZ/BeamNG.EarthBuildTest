"""Share complete observed neighbourhoods between workers and revisits.

The existing product store bounds disk use, checks every payload and publishes
atomically. No pickle or generated architectural choices enter this cache.
Source arrays, code and every catalogue remain dependencies. A failed cache
write still returns the freshly built complete neighbourhood.
"""
import json

import numpy as np

from .evidence import BuildingEvidence

VERSION = 1


def address(key, cells, revision):
    import mapdata
    import productcache
    import revisit
    from . import context, regional_architecture, regional_geography, roof_colours, site_data, zones
    sources = []
    for cell in cells:
        for layer in context.LAYERS:
            features = cell.layers.get(layer)
            if features is None:
                raise ValueError(f"building context lacks required {layer} in {cell.key}")
            arrays = features.to_arrays("")
            arrays.pop("en", None)  # derived coordinates are not source evidence
            sources.append((str(cell.key), layer, mapdata.digest_arrays(arrays)))
    return productcache.identity((VERSION, context.PROFILE, str(key), revision,
        sorted(sources), revisit.code_key(), context.climate_identity(),
        zones.catalogue()[0], site_data.catalogue()[0], roof_colours.catalogue()[0],
        regional_geography.identity(), regional_architecture.identity()))


def encode(bundle):
    # Pool observation tuples: most neighbouring buildings share the same small
    # set of observed attributes. Geometry remains exact WKB, with bounded raw
    # arrays rather than millions of recursively encoded scalar nodes.
    styles, style_ids, records, shapes = {}, [], [], []
    for sid, shape, evidence in bundle.buildings:
        style_ids.append(styles.setdefault(evidence.observations, len(styles)))
        records.append((sid, evidence.source_id, evidence.parent_id, evidence.source_record))
        shapes.append(shape.wkb)
    return dict(manifest=bundle.manifest,
        frame=(bundle.frame.lat0, bundle.frame.lon0, bundle.frame.h0),
        records=json.dumps(records, separators=(",", ":"), allow_nan=False).encode(),
        observations=tuple(styles), styles=np.asarray(style_ids, np.int32),
        shapes=b"".join(shapes), lengths=np.asarray([len(b) for b in shapes], np.int64),
        centres=bundle.centres, land=tuple((name, shape.wkb) for name, shape in bundle.land),
        coverage=bundle.coverage.wkb)


def decode(value):
    import geodesy
    from shapely import STRtree, from_wkb
    from .context import _Bundle
    rows = json.loads(value['records'])
    lengths, indices = value['lengths'], value['styles']
    if (len(rows) != len(lengths) or len(rows) != len(indices)
            or value['centres'].shape != (len(rows), 2)
            or np.any(lengths < 0) or int(lengths.sum()) != len(value['shapes'])):
        raise ValueError('invalid cached context layout')
    bundle = _Bundle.__new__(_Bundle)
    bundle.frame = geodesy.EnuFrame(*value['frame'])
    bundle.manifest = value['manifest']
    buildings, offset = [], 0
    for row, size, index in zip(rows, lengths, indices):
        sid, source, parent, record = row
        if not isinstance(sid, str) or not 0 <= index < len(value['observations']):
            raise ValueError('invalid cached context evidence')
        end = offset + int(size)
        shape = from_wkb(value['shapes'][offset:end])
        buildings.append((sid, shape, BuildingEvidence(source, parent, record, value['observations'][index])))
        offset = end
    bundle.buildings = tuple(buildings)
    bundle.tree = STRtree([b[1] for b in buildings])
    bundle.centres = value['centres']
    bundle.land = tuple((name, from_wkb(wkb)) for name, wkb in value['land'])
    bundle.coverage = from_wkb(value['coverage'])
    return bundle


def get(md, key, cells, revision, build, *, background=False):
    import productcache
    from shapely.errors import GEOSException
    cache_dir = getattr(md, 'cache_dir', None)
    if not cache_dir:
        return build()
    store = productcache.Store(cache_dir)
    ident = address(key, cells, revision)
    built = []
    def produce():
        bundle = build()
        built.append(bundle)
        return encode(bundle)
    result = store.get_or_build('building-context', ident, produce,
                                wait_s=0. if background else 30.)
    if built:
        return built[0]  # do not decode our own freshly built spatial index
    try:
        return decode(result.value)
    except (ValueError, KeyError, TypeError, IndexError, GEOSException):
        # A checksum-valid but structurally incompatible record never becomes
        # inferred evidence. Replace it only after a successful complete build.
        bundle = build()
        store.put('building-context', ident, encode(bundle))
        return bundle
