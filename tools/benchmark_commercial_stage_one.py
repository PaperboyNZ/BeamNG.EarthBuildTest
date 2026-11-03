"""Offline synthetic stage-one identity/inference/programme batch benchmark.

Run from any directory: python tools/benchmark_commercial_stage_one.py
Reported times exclude import and are local measurements, not game frame times.
"""
import json
from pathlib import Path
import statistics
import sys
import time
from types import SimpleNamespace

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
import mapgeom
import property_identity
from buildgen import inference, property_programme
from buildgen.topology import Footprint


class Frame:
    def enu_to_geodetic(self, east, north, up):
        return np.asarray(north)/100000, np.asarray(east)/100000, up

    def geodetic_to_enu(self, lat, lon, height):
        return np.asarray(lon)*100000, np.asarray(lat)*100000, height


def run(count=500, repeats=3):
    families = ('grocery_store', 'supermarket', 'strip_shops', 'trade_units', 'clinic', 'hospital')
    rows = []
    for i in range(count):
        x, y = (i % 25) * 100., (i // 25) * 100.
        cls = families[i % len(families)]
        # Exact one-storey grocery dimensions cover small, medium and large.
        side = (15., 25., 50.)[(i // len(families)) % 3] if cls in ('grocery_store', 'supermarket') else 24.
        ring = np.array(((x, y), (x+side, y), (x+side, y+side), (x, y+side)))
        rows.append((ring, {'class': cls, 'num_floors': 1, 'height': 6., 'seed_id': str(i)}))
    f = mapgeom.Features('places', np.array([str(i) for i in range(count)]), np.ones(count, np.uint8),
                         np.arange(count+1), np.arange(count+1), np.arange(count+1),
                         np.array([[(r[0][0, 0]+5)/100000, (r[0][0, 1]+5)/100000] for r in rows]),
                         attrs={'name': np.array(['Example']*count),
                                'basic_category': np.array(['grocery_store' if r[1]['class']=='supermarket' else r[1]['class'] for r in rows])})
    start = time.perf_counter()
    property_identity.index(f)
    index_ms = (time.perf_counter()-start)*1000
    timings = []
    counts = {}
    for _ in range(repeats):
        counts = {}
        start = time.perf_counter()
        identities = property_identity.resolve_many([r[0] for r in rows], [r[1] for r in rows], Frame(), layers=(f,))
        for (ring, attrs), ident in zip(rows, identities):
            if not ident or ident['status'] != 'supported':
                raise AssertionError('synthetic building should resolve as supported')
            fp = Footprint(ring)
            result = inference.resolve(dict(attrs, _property_identity=ident), fp, 10.)
            programme = property_programme.for_spec(SimpleNamespace(inference=result, property_identity=ident, seed=attrs['seed_id']))
            if programme is None or programme.kind != ident['kind']:
                raise AssertionError((attrs['class'], ident['kind'], result.selection.preset.id))
            counts[programme.kind] = counts.get(programme.kind, 0) + 1
        timings.append((time.perf_counter()-start)*1000)
    return {'buildings': count, 'repeats': repeats, 'index_ms': round(index_ms, 2),
            'batch_ms': [round(t, 2) for t in timings], 'median_batch_ms': round(statistics.median(timings), 2),
            'families': counts, 'scope': 'synthetic identity + inference + programme; excludes geometry and game runtime'}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
