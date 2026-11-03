"""Detached M1 contracts. Association records do not establish physical clearance."""
from dataclasses import dataclass, fields
from itertools import islice
import json
import math

from buildgen.topology import Footprint
from .identity import CanonicalFrame, GeographicFrame, SourceIdentity, SourceRevision


SCHEMA_VERSION = 1
MAX_ITEMS = 10000
_TYPES = {}
_EXTERNAL = {c.__name__: c for c in
             (CanonicalFrame, GeographicFrame, SourceIdentity, SourceRevision)}


def _encode(value):
    if type(value) in _EXTERNAL.values():
        return {"type": type(value).__name__, "value": value.to_dict()}
    if isinstance(value, Record):
        return {"type": type(value).__name__, "value":
                {f.name: _encode(getattr(value, f.name)) for f in fields(value)}}
    if isinstance(value, tuple):
        return [_encode(v) for v in value]
    return value


def _decode(value):
    if isinstance(value, list):
        return tuple(_decode(v) for v in value)
    if isinstance(value, dict):
        if set(value) != {"type", "value"}:
            raise ValueError("invalid site record envelope")
        name, body = value["type"], value["value"]
        if name in _EXTERNAL:
            return _EXTERNAL[name].from_dict(body)
        if name not in _TYPES or not isinstance(body, dict):
            raise ValueError("unknown site record type")
        cls = _TYPES[name]
        if set(body) != {f.name for f in fields(cls)}:
            raise ValueError("site record fields do not match version")
        return cls(**{k: _decode(v) for k, v in body.items()})
    return value


def _key(value):
    return json.dumps(_encode(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


class Record:
    """JSON payloads are detached; decoding always reruns contract validation."""
    __slots__ = ()

    def to_dict(self):
        return {"schema_version": SCHEMA_VERSION, "record": _encode(self)}

    def to_json(self):
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or set(value) != {"schema_version", "record"}:
            raise ValueError("invalid site contract envelope")
        if type(value["schema_version"]) is not int or value["schema_version"] != SCHEMA_VERSION:
            raise ValueError("unsupported site contract schema")
        result = _decode(value["record"])
        if type(result) is not cls:
            raise ValueError("unexpected site contract type")
        return result

    @classmethod
    def from_json(cls, value):
        return cls.from_dict(json.loads(value))


def _record(cls):
    cls = dataclass(frozen=True, slots=True)(cls)
    _TYPES[cls.__name__] = cls
    return cls


def _text(value, name):
    if (type(value) is not str or not value.strip() or len(value) > 512 or len(value.encode("utf-8")) > 512
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError(name + " must be bounded nonempty text without control characters")


def _choice(value, choices, name):
    if value not in choices or type(value) is not str:
        raise ValueError("unsupported " + name)


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("coordinates and intervals require finite numbers")
    return float(value) + 0.


def _expect(value, cls):
    if type(value) is not cls:
        raise TypeError("expected " + cls.__name__)


def _bounded(values, limit, name):
    values = tuple(islice(iter(values), limit + 1))
    if len(values) > limit:
        raise ValueError(name + " exceeds the record budget")
    return values


def _many(obj, name, cls, unique=True):
    values = _bounded(getattr(obj, name), MAX_ITEMS, name)
    for value in values:
        _expect(value, cls)
    values = tuple(sorted(values, key=_key))
    if unique and len(set(values)) != len(values):
        raise ValueError("duplicate " + name)
    object.__setattr__(obj, name, values)
    return values


@_record
class EntityRef(Record):
    identity: SourceIdentity
    kind: str

    def __post_init__(self):
        _expect(self.identity, SourceIdentity)
        _choice(self.kind, ("site", "building", "building_part", "lot", "station"), "entity kind")


@_record
class VerticalInterval(Record):
    """Inclusive endpoints. Heights are ellipsoidal metres, levels source labels."""
    minimum: float
    maximum: float
    basis: str = "level"

    def __post_init__(self):
        _choice(self.basis, ("level", "ellipsoidal_height"), "interval basis")
        object.__setattr__(self, "minimum", _number(self.minimum))
        object.__setattr__(self, "maximum", _number(self.maximum))
        if self.minimum > self.maximum:
            raise ValueError("reversed vertical interval")


@_record
class Polygon(Record):
    outer: tuple
    holes: tuple = ()

    def __post_init__(self):
        # Existing topology validation retains holes and rejects invalid geometry.
        footprint = Footprint(self.outer, self.holes)
        object.__setattr__(self, "outer", footprint.outer)
        object.__setattr__(self, "holes", footprint.holes)


@_record
class FrameContext(Record):
    """Exact coordinate declaration; legacy projected XY is never canonical ENU."""
    kind: str
    frame: CanonicalFrame | GeographicFrame
    x0: float = 0.
    y0: float = 0.

    def __post_init__(self):
        _choice(self.kind, ("canonical_enu", "legacy_projected_xy"), "coordinate space")
        _expect(self.frame, CanonicalFrame if self.kind == "canonical_enu" else GeographicFrame)
        object.__setattr__(self, "x0", _number(self.x0))
        object.__setattr__(self, "y0", _number(self.y0))
        if self.kind == "canonical_enu" and (self.x0 != 0. or self.y0 != 0.):
            raise ValueError("canonical ENU cannot contain a tile offset")

    def require_canonical(self):
        if self.kind != "canonical_enu":
            raise ValueError("legacy XY requires original source geometry/heights and explicit reprojection")
        return self.frame


@_record
class Membership(Record):
    member: EntityRef
    role: str = "member"
    interval: VerticalInterval | None = None

    def __post_init__(self):
        _expect(self.member, EntityRef)
        _choice(self.role, ("member", "owner", "anchor", "tenant", "part", "parking",
                            "fuel", "service", "pedestrian", "shared"), "membership role")
        if self.interval is not None:
            _expect(self.interval, VerticalInterval)


@_record
class PhysicalExtent(Record):
    """Observed physical surface, separate from the site's association envelope."""
    identity: str
    boundary: Polygon
    interval: VerticalInterval | None = None

    def __post_init__(self):
        _text(self.identity, "physical extent identity")
        _expect(self.boundary, Polygon)
        if self.interval is not None:
            _expect(self.interval, VerticalInterval)


@_record
class InterfaceRecord(Record):
    identity: str
    owner: EntityRef
    kind: str
    endpoints: tuple
    status: str = "observed"

    def __post_init__(self):
        _text(self.identity, "interface identity")
        _expect(self.owner, EntityRef)
        _choice(self.kind, ("service", "parking", "pedestrian", "vehicle", "fuel"), "interface kind")
        _choice(self.status, ("observed", "proposed", "connected", "crossing_only",
                              "pedestrian_only", "rejected"), "interface status")
        points = tuple(tuple(_number(v) for v in _bounded(p, 3, "endpoint coordinates"))
                       for p in _bounded(self.endpoints, 2, "endpoints"))
        if len(points) != 2 or any(len(p) != 3 for p in points):
            raise ValueError("interfaces require two XYZ endpoints in the declared frame")
        object.__setattr__(self, "endpoints", points)


@_record
class ResourceRecord(Record):
    """Declarative ownership/reference contract, not an M2 lifetime scheduler."""
    identity: str
    kind: str
    producer: EntityRef
    consumers: tuple = ()
    retention: str = "while_referenced"

    def __post_init__(self):
        _text(self.identity, "resource identity")
        _choice(self.kind, ("surface", "circulation", "shared_circulation", "pump",
                            "refuelling_trigger", "canopy", "marking", "reservation"), "resource kind")
        _expect(self.producer, EntityRef)
        _many(self, "consumers", EntityRef)
        _choice(self.retention, ("while_referenced", "producer_resident"), "retention policy")
        if self.kind in ("pump", "refuelling_trigger") and self.producer.kind != "station":
            raise ValueError("station must produce pumps and refuelling triggers")
        if self.kind == "shared_circulation" and self.producer.kind != "site":
            raise ValueError("site must produce shared circulation")
        if self.kind == "shared_circulation" and self.retention != "while_referenced":
            raise ValueError("shared circulation must remain while consumers reference it")


@_record
class SiteEvidence(Record):
    identity: SourceIdentity
    frame: FrameContext
    revisions: tuple
    memberships: tuple = ()
    association_extent: Polygon | None = None
    physical_extents: tuple = ()
    exclusions: tuple | None = None
    extent_basis: str = "mapped_association"

    def __post_init__(self):
        _expect(self.identity, SourceIdentity)
        _expect(self.frame, FrameContext)
        _many(self, "revisions", SourceRevision)
        for revision in self.revisions:
            _expect(revision.identity, SourceIdentity)
        if not self.revisions:
            raise ValueError("site evidence requires source revisions")
        if len({r.identity for r in self.revisions}) != len(self.revisions):
            raise ValueError("conflicting dependency revisions")
        members = _many(self, "memberships", Membership)
        if any(m.member == self.ref for m in members):
            raise ValueError("site cannot contain itself")
        if self.association_extent is not None:
            _expect(self.association_extent, Polygon)
        extents = _many(self, "physical_extents", PhysicalExtent)
        if len({p.identity for p in extents}) != len(extents):
            raise ValueError("duplicate physical extent identity")
        if self.exclusions is not None:
            _many(self, "exclusions", Polygon, unique=False)
        _choice(self.extent_basis, ("mapped_association", "surveyed_property", "mapped_lot"), "extent basis")

    @property
    def ref(self):
        return EntityRef(self.identity, "site")


@_record
class SitePlan(Record):
    evidence: SiteEvidence
    interfaces: tuple = ()
    resources: tuple = ()
    diagnostics: tuple = ()
    surface_validation: str = "unresolved"

    def __post_init__(self):
        _expect(self.evidence, SiteEvidence)
        interfaces = _many(self, "interfaces", InterfaceRecord)
        resources = _many(self, "resources", ResourceRecord)
        if len({r.identity for r in resources}) != len(resources):
            raise ValueError("conflicting or duplicate resource producers")
        if len({i.identity for i in interfaces}) != len(interfaces):
            raise ValueError("duplicate interface identity")
        participants = {self.evidence.ref, *(m.member for m in self.evidence.memberships)}
        if any(i.owner not in participants for i in interfaces):
            raise ValueError("interface owner must be a declared participant")
        if any(r.producer not in participants or any(c not in participants for c in r.consumers)
               for r in resources):
            raise ValueError("resource producers/consumers must be declared participants")
        diagnostics = tuple(sorted(_bounded(self.diagnostics, MAX_ITEMS, "diagnostics")))
        for value in diagnostics:
            _text(value, "diagnostic")
        object.__setattr__(self, "diagnostics", diagnostics)
        if self.surface_validation != "unresolved":
            raise ValueError("M1 records cannot claim physical surface conflict validation")


@_record
class SiteGraph(Record):
    """A resident subset; all declared members/references survive missing residency."""
    sites: tuple

    def __post_init__(self):
        sites = _many(self, "sites", SitePlan)
        by_id = {s.evidence.identity: s for s in sites}
        if len(by_id) != len(sites):
            raise ValueError("duplicate site identity")
        produced = set()
        for site in sites:
            for resource in site.resources:
                if resource.identity in produced:
                    raise ValueError("conflicting or duplicate resource producers")
                produced.add(resource.identity)
        visiting, visited = set(), set()
        for root in by_id:
            stack = [(root, False)]
            while stack:
                identity, leaving = stack.pop()
                if leaving:
                    visiting.remove(identity)
                    visited.add(identity)
                    continue
                if identity in visiting:
                    raise ValueError("cyclic site associations")
                if identity in visited or identity not in by_id:
                    continue
                visiting.add(identity)
                stack.append((identity, True))
                stack.extend((m.member.identity, False)
                             for m in by_id[identity].evidence.memberships
                             if m.member.kind == "site")
