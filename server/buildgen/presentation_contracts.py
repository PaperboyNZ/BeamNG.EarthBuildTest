"""Versioned identities for independently cached presentation components.

The compatibility building compiler uses these records in the product store.
A component key identifies immutable inputs, never a camera or scheduler state.
"""
from dataclasses import dataclass
import hashlib
import json
import re
import math


COMPONENT_SCHEMA = 1
VARIANTS = frozenset(('speed', 'fast', 'detailed', 'enriched'))
_NAME = re.compile(r'^[a-z][a-z0-9_]{0,63}$')


def _identifier(value, label):
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ValueError(f'{label} must be a nonempty bounded string')


@dataclass(frozen=True, slots=True)
class ComponentIdentity:
    """Dependencies shared by a cached geometry/material component.

    ``group`` is a stable spatial/ownership identity in the accepted frame.
    A physical revision is required when attachment or geometry depends on it;
    callers may use None only for components independent of physical state.
    """
    semantic_revision: str
    physical_revision: str | None
    system: str
    group: str
    recipe_version: str
    variant: str
    material_revision: str

    def __post_init__(self):
        for field in ('semantic_revision', 'group', 'recipe_version', 'material_revision'):
            _identifier(getattr(self, field), field)
        if self.physical_revision is not None:
            _identifier(self.physical_revision, 'physical_revision')
        if not isinstance(self.system, str) or not _NAME.fullmatch(self.system):
            raise ValueError('invalid component system')
        if self.variant not in VARIANTS:
            raise ValueError('unknown presentation variant')

    def key(self):
        payload = {'schema': COMPONENT_SCHEMA, 'semantic': self.semantic_revision,
                   'physical': self.physical_revision, 'system': self.system,
                   'group': self.group, 'recipe': self.recipe_version,
                   'variant': self.variant, 'material': self.material_revision}
        data = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
        return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True, slots=True)
class PresentationRequest:
    """Ephemeral demand; epoch rejects work after a reset or superseding request."""
    component: ComponentIdentity
    epoch: int

    def __post_init__(self):
        if not isinstance(self.component, ComponentIdentity):
            raise TypeError('component must be a ComponentIdentity')
        if type(self.epoch) is not int or self.epoch < 0:
            raise ValueError('epoch must be a nonnegative integer')


@dataclass(frozen=True, slots=True)
class ComponentCost:
    encoded_bytes: int
    vertices: int
    primitives: int
    scene_objects: int
    estimated_import_ms: float

    def __post_init__(self):
        for name in ('encoded_bytes', 'vertices', 'primitives', 'scene_objects'):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 2**40:
                raise ValueError('invalid component resource cost')
        if (type(self.estimated_import_ms) not in (float, int) or
                not math.isfinite(self.estimated_import_ms) or self.estimated_import_ms < 0):
            raise ValueError('invalid estimated import work')


@dataclass(frozen=True, slots=True)
class ComponentProduct:
    """Detached immutable complete-group payload, stored by ComponentIdentity.

    The canonical JSON manifest and byte streams cannot mutate after worker
    completion. Decoding creates a fresh publication copy for each VFS location.
    The compatibility system is explicitly named legacy_building until the
    individual mirrors and their replacement ownership have been validated.
    """
    component: ComponentIdentity
    manifest: bytes
    files: tuple
    cost: ComponentCost
    bounds: tuple
    replaces: tuple

    def __post_init__(self):
        if type(self.component) is not ComponentIdentity or type(self.cost) is not ComponentCost:
            raise TypeError('invalid component product records')
        if type(self.manifest) is not bytes or len(self.manifest) > 8 << 20:
            raise ValueError('invalid component manifest')
        manifest = json.loads(self.manifest, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite manifest')))
        if not isinstance(manifest, dict):
            raise ValueError('component manifest must be an object')
        if type(self.files) is not tuple or len(self.files) > 4096:
            raise ValueError('invalid component file inventory')
        names = set()
        for row in self.files:
            if not isinstance(row, tuple) or len(row) != 2:
                raise ValueError('invalid component file')
            name, blob = row
            if (not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,255}', name) or
                    name in ('.', '..') or name in names or type(blob) is not bytes):
                raise ValueError('invalid component file name/stream')
            names.add(name)
        if sum(len(blob) for _, blob in self.files) != self.cost.encoded_bytes:
            raise ValueError('component byte count mismatch')
        if (type(self.bounds) is not tuple or len(self.bounds) != 6 or
                any(type(x) not in (float, int) or not math.isfinite(x) for x in self.bounds) or
                any(self.bounds[i] > self.bounds[i+3] for i in range(3))):
            raise ValueError('invalid component bounds')
        if type(self.replaces) is not tuple or len(self.replaces) > 4096:
            raise ValueError('invalid replacement ownership')
        if len(set(self.replaces)) != len(self.replaces):
            raise ValueError('duplicate replacement ownership')
        for name in self.replaces:
            _identifier(name, 'replacement owner')

    def publication(self):
        """Each caller receives its own manifest and file dictionary."""
        return dict(json.loads(self.manifest), files=dict(self.files))
