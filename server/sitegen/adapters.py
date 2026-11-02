"""Explicit legacy one-owner compatibility; no catalogue validation bypass."""
from dataclasses import dataclass
import hashlib
import math
from itertools import islice

from buildgen.site_data import Port, Site
from buildgen.topology import Footprint
from .identity import SourceIdentity, SourceRevision, canonical_json
from .plan import (EntityRef, FrameContext, InterfaceRecord, Membership, Polygon,
                   SiteEvidence, SitePlan)


@dataclass(frozen=True, slots=True)
class LegacySiteAdapter:
    """Detached versioned records plus exact legacy-only compatibility values."""
    evidence: SiteEvidence
    plan: SitePlan
    dock_rise: float | None
    owner_footprint: Polygon | None
    legacy_exclusions: tuple = ()

    # The live one-owner fitter consumes these views of the versioned records.
    # No second mutable Site is retained beside the source-linked evidence.
    @property
    def id(self):
        return self.evidence.identity.feature_id

    @property
    def revision(self):
        return self.evidence.revisions[0].revision

    @property
    def boundary(self):
        p = self.evidence.association_extent
        return Footprint(p.outer, p.holes)

    @property
    def exclusions(self):
        return tuple(Footprint(p.outer, p.holes) for p in self.legacy_exclusions)

    @property
    def ports(self):
        return tuple(sorted((Port(i.kind, *i.endpoints) for i in self.plan.interfaces),
                            key=lambda p: (p.kind, p.a, p.b)))

    def __post_init__(self):
        if type(self.evidence) is not SiteEvidence or type(self.plan) is not SitePlan:
            raise TypeError("legacy adapter requires detached site records")
        if self.plan.evidence != self.evidence:
            raise ValueError("legacy adapter records disagree")
        if (self.evidence.frame.kind != "legacy_projected_xy"
                or self.evidence.association_extent is None
                or self.evidence.exclusions is None
                or len(self.evidence.revisions) != 1
                or self.evidence.revisions[0].identity != self.evidence.identity
                or self.evidence.physical_extents
                or self.evidence.extent_basis != "surveyed_property"
                or len(self.evidence.memberships) != 1
                or self.evidence.memberships[0].role != "owner"
                or self.evidence.memberships[0].member.kind != "building"):
            raise ValueError("legacy adapter requires complete one-owner legacy evidence")
        owner = self.evidence.memberships[0].member
        if self.plan.resources or any(i.owner != owner or i.status != "observed" or
                i.kind not in ("service", "parking", "pedestrian") for i in self.plan.interfaces):
            raise ValueError("legacy adapter cannot dispatch shared resources or unvalidated interfaces")
        if self.owner_footprint is not None and type(self.owner_footprint) is not Polygon:
            raise TypeError("legacy owner footprint must be a detached polygon")
        exclusions = tuple(islice(iter(self.legacy_exclusions), 33))
        if len(exclusions) > 32:
            raise ValueError("legacy exclusion inventory exceeds catalogue budget")
        if any(type(p) is not Polygon for p in exclusions):
            raise TypeError("legacy exclusions must be detached polygons")
        if sorted(p.to_json() for p in exclusions) != sorted(p.to_json() for p in self.evidence.exclusions):
            raise ValueError("legacy exclusion order must retain the complete inventory")
        object.__setattr__(self, "legacy_exclusions", exclusions)
        if self.dock_rise is not None:
            if (isinstance(self.dock_rise, bool) or not isinstance(self.dock_rise, (int, float))
                    or not math.isfinite(self.dock_rise) or not .8 <= self.dock_rise <= 1.5):
                raise ValueError("legacy dock rise must remain 0.8–1.5 m")
            object.__setattr__(self, "dock_rise", float(self.dock_rise))

    def to_legacy_site(self):
        """Reconstruct detached old emitter input without coordinate conversion."""
        evidence = self.evidence
        polygon = evidence.association_extent
        footprint = self.owner_footprint
        return Site(evidence.identity.feature_id, evidence.revisions[0].revision,
                    Footprint(polygon.outer, polygon.holes),
                    tuple(Footprint(p.outer, p.holes) for p in self.legacy_exclusions),
                    tuple(sorted((Port(i.kind, *i.endpoints) for i in self.plan.interfaces),
                                 key=lambda p: (p.kind, p.a, p.b))),
                    self.dock_rise, None if footprint is None else Footprint(footprint.outer, footprint.holes))


def adapt_validated_legacy_site(site, *, owner, frame, source_namespace):
    """Consume only the output of the existing validated catalogue/project path.

    Callers attest that catalogue() AND project() have succeeded. This function
    neither reads a raw feature nor substitutes for those validators. Site itself
    carries no validation token, owner identity or original projection context;
    those missing facts must be supplied explicitly. Original XY/XYZ are retained
    exactly, so no invented polygon heights or datum conversion are needed.
    """
    if type(site) is not Site:
        raise TypeError("requires an already validated buildgen.site_data.Site")
    if type(owner) is not EntityRef or owner.kind != "building":
        raise TypeError("legacy site requires one explicit building owner")
    if type(frame) is not FrameContext or frame.kind != "legacy_projected_xy":
        raise ValueError("legacy site requires original source projection frame and tile offsets")
    identity = SourceIdentity(source_namespace, site.id)
    evidence = SiteEvidence(
        identity=identity, frame=frame,
        revisions=(SourceRevision(identity, site.revision),),
        memberships=(Membership(owner, "owner"),),
        association_extent=Polygon(site.boundary.outer, site.boundary.holes),
        # The old catalogue guarantees complete exclusions. It does not declare
        # that every square metre within the property is physical pavement.
        exclusions=tuple(Polygon(p.outer, p.holes) for p in site.exclusions),
        extent_basis="surveyed_property")
    interfaces = []
    occurrences = {}
    for port in site.ports:
        endpoints = tuple(tuple(float(v) + 0. for v in p) for p in (port.a, port.b))
        # This is deliberately a local content identity, not a canonical mapped
        # entrance identity. Include the full frame declaration to prevent an
        # identical tile-local coordinate pair in another frame aliasing it.
        payload = {"site": identity.to_dict(), "frame": frame.to_dict(),
                   "kind": port.kind, "endpoints": endpoints}
        digest = hashlib.sha256(canonical_json(payload).encode("ascii")).hexdigest()
        local_id = "legacy-frame-interface-v1:" + digest
        occurrence = occurrences.get(local_id, 0)
        occurrences[local_id] = occurrence + 1
        # Identical duplicate ports are permitted by the old catalogue. Count
        # duplicates only within the same content identity, never all ports.
        if occurrence:
            local_id += f":duplicate:{occurrence}"
        interfaces.append(InterfaceRecord(local_id, owner, port.kind, endpoints))
    interfaces = tuple(interfaces)
    plan = SitePlan(evidence, interfaces=interfaces,
                    diagnostics=("legacy_one_owner", "legacy_projection_requires_source_context"))
    footprint = site.owner_footprint
    return LegacySiteAdapter(evidence, plan, site.dock_rise,
                             None if footprint is None else Polygon(footprint.outer, footprint.holes),
                             tuple(Polygon(p.outer, p.holes) for p in site.exclusions))
