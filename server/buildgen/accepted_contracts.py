"""Auditable dependencies for accepted plans, independent of presentation work.

The compatibility compiler still consumes BuildingPlan. These projections make
its semantic and physical commitments explicit at the persistent store boundary;
they do not convert old quality-dependent products into shared plans.
"""
from dataclasses import dataclass
import hashlib
import math
import re

from productcache import Codec, canonical

CONTRACT_VERSION = 1
_REVISION = re.compile(r'^[a-f0-9]{64}$')

# Presentation-only values (weather tint, diagnostics and material embellishment)
# are deliberately absent. Accepted aperture positions are architectural identity.
SEMANTIC_FIELDS = ('evidence', 'footprint', 'ring', 'floors', 'floor_h', 'height',
                   'roof', 'roof_mat', 'facade', 'wall', 'band', 'shop', 'plain',
                   'min_h', 'door', 'windows', 'front', 'cls', 'seed', 'deck',
                   'pitch', 'portal', 'ship', 'terminal', 'church', 'city',
                   'property_identity')
PHYSICAL_FIELDS = ('ring', 'footprint', 'gring', 'height', 'floors', 'floor_h',
                   'min_h', 'roof', 'pitch', 'roof_outline', 'door', 'front',
                   'garage_opening', 'access', 'site', 'garage_access', 'deck',
                   'portal', 'ship', 'terminal', 'church', 'city', 'stoop', 'porch', 'physical_mode')


def digest(value):
    """Content hash including checked numeric streams, without pickle/repr."""
    codec = Codec()
    tree = codec.encode(value)
    return hashlib.sha256(canonical(dict(tree=tree, blobs={
        name: hashlib.sha256(blob).hexdigest() for name, blob in codec.blobs.items()
    })).encode()).hexdigest()


def _apertures(spec):
    layout = spec.facades
    if layout is None:
        return ()
    return tuple((e.boundary, e.edge, e.length, e.role,
                  tuple((o.kind, o.floor, o.left, o.right, o.bottom, o.top,
                         o.columns, o.variant, o.depth, o.assembly) for o in e.openings))
                 for e in layout.elevations)


def _roof(spec):
    r = spec.inference
    return None if r is None else (r.roof_variant, r.roof_rise, r.roof_solver,
                                   r.dwelling_structure, r.modifiers)


def _identity(spec):
    r = spec.inference
    return None if r is None else (r.use, r.architecture, r.facade, r.roof,
                                   r.height, r.floors, r.selection, r.house_style)


@dataclass(frozen=True, slots=True)
class SemanticPlan:
    revision: str
    building_count: int
    schema: int

    def __post_init__(self):
        if not isinstance(self.revision, str) or not _REVISION.fullmatch(self.revision):
            raise ValueError('invalid semantic revision')
        if type(self.building_count) is not int or not 1 <= self.building_count <= 100000:
            raise ValueError('invalid accepted building count')
        if type(self.schema) is not int or self.schema < 30:
            raise ValueError('legacy plans require rebuilding, not relabelling')


@dataclass(frozen=True, slots=True)
class PhysicalPlan:
    revision: str
    semantic_revision: str
    input_revision: str
    frame_revision: str
    initial_site_policy: int

    def __post_init__(self):
        if not isinstance(self.revision, str) or not re.fullmatch(r'[a-f0-9]{16}', self.revision):
            raise ValueError('invalid physical publication revision')
        for value in (self.semantic_revision, self.input_revision, self.frame_revision):
            if not isinstance(value, str) or not _REVISION.fullmatch(value):
                raise ValueError('invalid physical dependency revision')
        if type(self.initial_site_policy) is not int or self.initial_site_policy not in (-1, 0, 1, 2):
            raise ValueError('invalid initial physical site policy')


def capture(items, physical_revision, frame, initial_site_policy):
    """Capture the exact frozen inputs and actual published physical stream hash.

    No inference, layout planning, terrain sampling or geometry compilation runs.
    Physical input identity is a separate check from the final encoded hash.
    """
    from .plan import BuildingPlan, SCHEMA_VERSION
    if not isinstance(items, tuple) or not items:
        raise ValueError('accepted plans must be a complete nonempty tuple')
    for item in items:
        if (not isinstance(item, tuple) or len(item) != 3 or type(item[0]) is not BuildingPlan or
                item[0].physical_mode not in ('compact','standard') or
                any(type(z) not in (int, float) or not math.isfinite(z) for z in item[1:])):
            raise ValueError('invalid accepted plan item')
    semantic = tuple((tuple(getattr(s, f) for f in SEMANTIC_FIELDS), _identity(s), _roof(s), _apertures(s))
                     for s, _, _ in items)
    physical = tuple((tuple(getattr(s, f) for f in PHYSICAL_FIELDS), _roof(s), _apertures(s), lo, hi)
                     for s, lo, hi in items)
    sem = SemanticPlan(digest((CONTRACT_VERSION, semantic)), len(items), SCHEMA_VERSION)
    phy = PhysicalPlan(physical_revision, sem.revision, digest((CONTRACT_VERSION, physical)),
                       digest(frame), initial_site_policy)
    return sem, phy


def valid(value, dependencies):
    """Reject missing contracts, stale frames and mutated accepted inputs."""
    try:
        sem, phy = value['semantic_plan'], value['physical_plan']
        if type(sem) is not SemanticPlan or type(phy) is not PhysicalPlan:
            return False
        if dependencies['plan_schema'] != sem.schema:
            return False
        expected = capture(value['plans'], value['physical_revision'], dependencies['frame'],
                           dependencies['building_site_policy'])
        return (sem, phy) == expected
    except (KeyError, ValueError, TypeError, AttributeError):
        return False
