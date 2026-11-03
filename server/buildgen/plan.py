"""Immutable compiler input shared by building representations.

Planning still uses buildings.Spec while resolving doors, terrain and infrastructure.
At the compilation boundary it becomes a BuildingPlan: near, lite and collision
builders share the same detached values. Ordinary v2 plans also carry auditable
contextual inference; a persistent global plan store is still separate work.
"""
from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING

import numpy as np
from .evidence import BuildingEvidence
from .topology import Footprint
from .inference import Resolution
from .facades import FacadeLayout
from .access import AccessPlan
from .site_data import Site
from .garages import GarageAccess
from .churches import ChurchArchitecture
from .city import Architecture as CityArchitecture

if TYPE_CHECKING:
    from sitegen.adapters import LegacySiteAdapter


SCHEMA_VERSION = 30


@dataclass(frozen=True, slots=True)
class FrozenMapping(Mapping):
    """Small, pickleable immutable map (special structures carry nested metadata)."""

    entries: tuple

    def __getitem__(self, key):
        for name, value in self.entries:
            if name == key:
                return value
        raise KeyError(key)

    def __iter__(self):
        return (key for key, _ in self.entries)

    def __len__(self):
        return len(self.entries)


def _freeze(value):
    # Local import avoids the buildgen package / site-record topology cycle.
    from sitegen.adapters import LegacySiteAdapter
    if isinstance(value, LegacySiteAdapter):
        return value
    if isinstance(value, (BuildingEvidence, Footprint, Resolution, FacadeLayout, AccessPlan, Site, GarageAccess, ChurchArchitecture, CityArchitecture)):
        return value
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject:
            raise TypeError("building plans cannot contain object arrays")
        # A bytes-backed array cannot be made writeable again with setflags().
        # Merely clearing WRITEABLE on a copied owning array does not guarantee this.
        return np.frombuffer(value.tobytes(order="C"), dtype=value.dtype).reshape(value.shape)
    if isinstance(value, Mapping):
        return FrozenMapping(tuple((k, _freeze(v)) for k, v in value.items()))
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, np.generic):
        return value.item()
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f"unsupported building plan value: {type(value).__name__}")


@dataclass(frozen=True, slots=True, eq=False)
class BuildingPlan:
    """Resolved dimensions and appearance in the caller's stable tile frame.

    Field names intentionally match Spec so the existing geometry kernels can
    consume this plan. Local coordinates are not a global cache identity; source
    evidence, topology and context manifests have their own versioned contracts.
    """

    ring: np.ndarray
    floors: int | None = None
    floor_h: float | None = None
    height: float | None = None
    roof: str | None = None
    roof_mat: str | None = None
    facade: str | None = None
    band: tuple | None = None
    shop: bool | None = None
    plain: bool | None = None
    min_h: float | None = None
    wall: str | None = None
    door: tuple | None = None
    windows: bool | None = None
    front: int | None = None
    steeple: bool | None = None
    stoop: tuple | None = None
    sign: int | None = None
    porch: bool | None = None
    cls: str | None = None
    seed: float | None = None
    deck: bool | None = None
    pitch: float | None = None
    portal: bool | None = None
    gring: np.ndarray | None = None
    ship: Mapping | None = None
    evidence: BuildingEvidence | None = None
    footprint: Footprint | None = None
    diagnostics: tuple = ()
    inference: Resolution | None = None
    facades: FacadeLayout | None = None
    garage_opening: tuple | None = None
    access: AccessPlan | None = None
    site: "Site | LegacySiteAdapter | None" = None
    garage_access: GarageAccess | None = None
    terminal: Mapping | None = None
    church: ChurchArchitecture | None = None
    city: CityArchitecture | None = None
    roof_outline: Footprint | None = None
    weather_exposure: tuple | None = None
    property_identity: Mapping | None = None
    physical_mode: str | None = None

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name in ("ring", "gring") and value is not None:
                value = np.asarray(value, np.float64)
            object.__setattr__(self, field.name, _freeze(value))
        if self.ring.ndim != 2 or self.ring.shape[1] != 2 or len(self.ring) < 3:
            raise ValueError("a building ring must have at least three XY vertices")
        if not np.isfinite(self.ring).all():
            raise ValueError("a building ring must be finite")
        if self.footprint is not None and not np.array_equal(self.ring, self.footprint.outer):
            raise ValueError("plan ring must match the canonical footprint exterior")
        if self.gring is not None and (self.gring.shape != (len(self.ring),) or
                                      not np.isfinite(self.gring).all()):
            raise ValueError("ground samples must be finite and match the building ring")
        if self.physical_mode not in (None, 'compact', 'standard'):
            raise ValueError('unknown accepted physical recipe')

    @classmethod
    def from_spec(cls, spec):
        if isinstance(spec, cls):
            return spec
        return cls(**{field.name: getattr(spec, field.name) for field in fields(cls)})

    def __reduce__(self):
        # Pickle normally restores dataclass slots without __post_init__; numpy
        # arrays would then be writeable again after a worker boundary.
        return type(self), tuple(getattr(self, field.name) for field in fields(self))


def freeze_items(items):
    """Snapshot the complete compiler input, including its ground height ranges."""
    from dataclasses import replace
    from . import facades
    from .minimum import visual_enabled as enabled
    from .minimum import enabled as minimum_enabled
    compact = enabled()
    result = []
    for spec, gmin, gmax in items:
        frozen = BuildingPlan.from_spec(spec)
        if frozen.physical_mode is None:
            frozen = replace(frozen, physical_mode='compact' if minimum_enabled() else 'standard')
        if frozen.physical_mode!='compact' and not (compact or enabled(frozen)) and frozen.inference is not None and frozen.footprint is not None and frozen.facades is None:
            frozen = replace(frozen, facades=facades.plan(frozen, gmin, gmax))
        result.append((frozen, float(gmin), float(gmax)))
    return tuple(result)
