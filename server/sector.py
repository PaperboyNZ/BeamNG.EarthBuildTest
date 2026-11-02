"""Bounded manifests for existing geotile content products.

The producer is the existing global grid sector, NOT a relabelled building/site
identity. Shared sites still need complete source membership and canonical frames.
No new playable topology is enabled by negotiating this manifest version.
"""
import hashlib
import json
import math
import re
from sitegen.identity import SourceIdentity

VERSION = 1
MAX_PARTS = 4096
NAMESPACE = 'beamng-earth/geotile'


def negotiated(road_geo, requested):
    return bool(road_geo) and type(requested) is int and requested == VERSION


def manifest(data):
    key = data.get('key')
    if not isinstance(key, str) or not re.fullmatch(r'g17_\d{1,6}_\d{1,6}', key):
        raise ValueError('sector requires a global zoom-17 key')
    _, x, y = key.split('_')
    if not (0 <= int(x) < 2**17 and 0 <= int(y) < 2**17):
        raise ValueError('sector outside global grid')
    origin = data.get('frame')
    if (not isinstance(origin, list) or len(origin) != 2 or
            any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in origin)
            or not -90 <= origin[0] <= 90 or not -180 <= origin[1] <= 180):
        raise ValueError('sector requires a finite geographic origin')
    revision = data.get('physicalHash')
    if not isinstance(revision, str) or not re.fullmatch(r'[a-f0-9]{16}', revision):
        raise ValueError('sector requires the physical product revision')
    hashes = data.get('shapeHashes')
    if not isinstance(hashes, dict) or len(hashes) > MAX_PARTS:
        raise ValueError('oversized or missing sector shape inventory')
    shapes = {k for k, v in data.items() if isinstance(v, dict) and 'shape' in v}
    if shapes != set(hashes):
        raise ValueError('sector shape inventory must be complete')
    visuals = set((data.get('buildingChunks') or {}).get('visual', ())) if 'bldcol' in shapes else set()
    if not visuals <= shapes:
        raise ValueError('visual resource is not resident in this sector')
    physical, visual = [], []
    for what, digest in sorted(hashes.items()):
        if (not isinstance(what, str) or not re.fullmatch(r'[a-z][a-z0-9]{0,31}', what) or
                not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest)):
            raise ValueError('invalid resource name or content digest')
        (visual if what in visuals else physical).append(dict(part=what, sha256=digest))
    visual_revision = hashlib.sha256(json.dumps(visual, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return dict(v=VERSION, producer=SourceIdentity(NAMESPACE, key).to_dict(),
                frame=dict(type='geotile-world-v1', origin=origin), topology='closed-v1',
                physical=dict(revision=revision, parts=physical),
                visual=dict(revision=visual_revision, depends_on=revision, parts=visual))
