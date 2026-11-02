"""Prepare imagery-first v2 roof evidence from an existing cache, without network.

Run again after downloading another area. Output is pinned at server startup;
never run against an output file in use by a running server. No map tags guide
sampling, and rejected samples are not stored. Live cache files are read only.
"""
from pathlib import Path
import argparse
from collections import Counter
import hashlib
import json
import math
import sys
import tempfile
import time
import zipfile
import numpy as np
from shapely.geometry import Polygon, MultiPolygon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'server'))
import imagery
import mapgeom
from buildgen import ingest, roof_colours
from buildgen.roof_sampling import CachedTiles, mercator_pixels, sample


def prepare(cache, max_buildings=0):
    cache = Path(cache)
    tiles = CachedTiles(cache/'imagery')
    indices, cells = {}, set()
    for source in imagery.DEFAULT_CHAIN:
        if imagery.SOURCES[source].max_zoom < 16:
            continue
        for zoom in (17, 16):
            keys = {(int(p.parent.name), int(p.stem)) for p in (cache/'imagery'/source/str(zoom)).glob('*/*.jpg')}
            if keys:
                indices[source, zoom] = keys
                cells.update((x//2**(zoom-14), y//2**(zoom-14)) for x,y in keys)
    records, seen, counts = [], set(), Counter()
    paths = sorted((cache/'mapdata').glob('v*/overture/*/buildings/14/*/*.npz'), reverse=True)
    start = time.perf_counter()
    for path in paths:
        if (int(path.parent.name), int(path.stem)) not in cells:
            continue
        try:
            with np.load(path, allow_pickle=False) as f:
                feats = mapgeom.Features.from_arrays('buildings', {k:f[k] for k in f.files}, '')
        except (OSError, ValueError, EOFError, zipfile.BadZipFile):
            counts['unreadable_cells'] += 1
            continue
        counts['cells'] += 1
        for i, fid in enumerate(feats.ids):
            fid = str(fid)
            if fid in seen: continue
            seen.add(fid)
            if max_buildings and counts['considered'] >= max_buildings:
                break
            counts['considered'] += 1
            raw_parts = feats.parts(i)
            if not raw_parts or not len(raw_parts[0][0]): continue
            centre = np.mean(raw_parts[0][0], axis=0)
            candidates = []
            for zoom in (17,16):
                mpp = imagery.ground_res(float(centre[1]), zoom)
                if mpp > 2: continue
                xy = mercator_pixels([centre], zoom)[0]
                key = tuple((xy//256).astype(int))
                candidates.extend((s,zoom,mpp) for s in imagery.DEFAULT_CHAIN if key in indices.get((s,zoom), ()))
            if not candidates:
                counts['no_cached_source'] += 1
                continue
            cc = ingest.components(feats, i)
            if not cc:
                counts['invalid_footprint'] += 1
                continue
            result = {'status':'no_cached_source'}
            for source,zoom,mpp in candidates:
                pp = [[mercator_pixels(r,zoom) for r in rings] for _,rings in cc]
                polys = [Polygon(p[0],p[1:]) for p in pp]
                poly = polys[0] if len(polys)==1 else MultiPolygon(polys)
                tiles.used.clear()
                result = sample(poly,mpp,tiles,source,zoom)
                if result['status'] == 'accepted':
                    digest = hashlib.sha256(repr(sorted((k,tiles.digests[k]) for k in tiles.used)).encode()).hexdigest()
                    records.append(dict(result,source_id=fid,geometry_digest=roof_colours.geometry_digest(cc),
                                        imagery_digest=digest,source=source,zoom=zoom,mpp=mpp))
                    break
            counts[result['status']] += 1
        if counts['cells'] % 10 == 0:
            print(f"{counts['cells']} cells, {counts['considered']} buildings, {len(records)} colours",flush=True)
        if max_buildings and counts['considered'] >= max_buildings:
            break
    return dict(schema=1,method='eroded-roof-v1',records=sorted(records,key=lambda r:r['source_id']),
                sources={s:imagery.SOURCES[s].attribution for s in sorted({r['source'] for r in records})},
                statistics=dict(counts),elapsed_seconds=time.perf_counter()-start,
                bounded_run=bool(max_buildings and counts['considered']>=max_buildings))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cache',type=Path,default=Path.home()/'.cache/beamng-earth')
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--max-buildings',type=int,default=0,help='0 for all cached overlapping cells')
    args = ap.parse_args()
    if args.max_buildings < 0: ap.error('--max-buildings must be nonnegative')
    result = prepare(args.cache,args.max_buildings)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=args.out.parent,suffix='.json',delete=False) as f:
            json.dump(result,f,separators=(',',':'),allow_nan=False)
            temporary = Path(f.name)
        digest,records = roof_colours.load(temporary)
        temporary.replace(args.out)
        print(json.dumps({'records':len(records),'sha256':digest,'statistics':result['statistics'],
                          'seconds':result['elapsed_seconds'],'bounded':result['bounded_run']},indent=2))
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


if __name__ == '__main__': main()
