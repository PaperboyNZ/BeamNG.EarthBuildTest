"""Pinned imagery roof colours: prepare with tools/sample_roof_colours.py.

No image IO in workers. The digest enters generated-content cache keys and a
geometric revision cannot reuse a colour measured from an older footprint.
"""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Sample:
    rgb: tuple[float, float, float]
    source: str
    geometry_digest: str
    imagery_digest: str
    metres_per_pixel: float


def geometry_digest(components):
    return hashlib.sha256(repr(tuple(k for k, _ in components)).encode()).hexdigest()


def load(path):
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    if data.get('schema') != 1 or data.get('method') != 'eroded-roof-v1':
        raise ValueError('unsupported roof-colour catalogue')
    records = {}
    for row in data['records']:
        rgb = tuple(float(c) for c in row['rgb'])
        if len(rgb) != 3 or not all(math.isfinite(c) and 0 <= c <= 255 for c in rgb):
            raise ValueError('invalid roof RGB')
        mpp = float(row['mpp'])
        if not 0 < mpp <= 2 or row.get('status') != 'accepted' or row.get('pixels', 0) < 24 \
                or not .6 <= row.get('usable_share', 0) <= 1 or not 0 <= row.get('spread_de76_p80', math.inf) <= 25:
            raise ValueError('roof evidence failed quality thresholds')
        for field in ('source_id', 'source', 'geometry_digest', 'imagery_digest'):
            if not isinstance(row.get(field), str) or not row[field]:
                raise ValueError('roof evidence lacks provenance')
        key = (row['source_id'], row['geometry_digest'])
        if key in records:
            raise ValueError('duplicate roof evidence')
        records[key] = Sample(tuple(c/255 for c in rgb), row['source'], row['geometry_digest'],
                              row['imagery_digest'], mpp)
    return hashlib.sha256(raw).hexdigest(), records


@lru_cache(maxsize=1)
def catalogue():
    path = os.environ.get('BNE_BUILDING_ROOF_COLOURS')
    return load(path) if path else ('none', {})


def query(source_id, components):
    records = catalogue()[1]
    return records.get((source_id, geometry_digest(components))) if records else None
