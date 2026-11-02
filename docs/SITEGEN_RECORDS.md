# Site/complex M1 record boundary

Implemented 1 November 2026 in `server/sitegen/plan.py` and `adapters.py`.
These are data contracts; they do not activate shared geometry, change catalogue
acceptance, resolve physical contact, or implement resource streaming/lifetimes.
Canonical geographic identity and dependency rules are specified separately in
`SITEGEN_IDENTITY_CONTRACT.md` and `server/sitegen/identity.py`.

`SiteEvidence` is the common site/complex aggregate. A complex is a site with
memberships. `SitePlan` carries that evidence plus interfaces and resource
ownership. `SiteGraph` checks a resident subset of plans. Standalone mapped lots
may have no building members. Every evidence record has pinned `SourceRevision`
dependencies; contradictory revisions for one dependency are rejected.

`EntityRef` pairs `SourceIdentity(namespace, feature_id)` with a type: site,
building, building part, lot or station. `Membership` adds an explicit role and
an optional inclusive `VerticalInterval`. Intervals declare either source level
labels or WGS84 ellipsoidal heights in metres. Unknown vertical placement is
`None`; unknown is not equivalent to a ground-floor interval. Multiple roles and
overlapping intervals are retained. Membership alone does not mean residency.

`association_extent` describes the association/property/lot envelope, including
holes. It does not declare a physical paved surface. `PhysicalExtent` describes
observed physical surfaces separately. `exclusions=None` means the exclusion
inventory is unknown; `exclusions=()` means the inventory is complete and empty.
Duplicate exclusions are retained because the legacy catalogue permits them.
Existing polygon validation rejects invalid geometry rather than repairing holes.

Nested site memberships form a directed acyclic association graph. `SiteGraph`
rejects self-membership, cycles among resident sites and duplicate site identities.
Referenced sites that are not resident remain explicit references. A cycle through
an unavailable site's unknown edges cannot be diagnosed until those edges arrive;
the expanded graph must be validated again before use.

`ResourceRecord` gives every generated resource one stable semantic name, one
producer, explicit consumer references and a retention policy. A graph rejects
repeated resource identities, including conflicting producers. The record must be
carried once by its producing plan; consumers reference its identity through that
record, rather than copying another producer record into their own plan. Producers,
consumers and interface owners must be declared site participants. Pumps and
refuelling triggers require a station producer; shared circulation requires a site
producer. Shared circulation requires `while_referenced` retention; producer-only
residency cannot retire a resource while another member still consumes it. Default
retention is `while_referenced`; `producer_resident` is available for other kinds
as an explicit declaration. Actual reference counts, pins, readiness and retirement are
M2 work. Combining only part of a graph cannot prove global producer uniqueness;
validate the combined set before admitting generated resources.

`InterfaceRecord` keeps owner, semantic kind, two XYZ endpoints and explicit status.
Observed or proposed interfaces are not accepted connections. The records do not
yet describe a road station interval, vehicle sweep, terrain fit or grade profile.

`surface_validation` is always `unresolved` in M1. Even physically overlapping
same-level surfaces can be represented, but they cannot be labelled validated.
Neither vertically overlapping memberships nor unique resource producers prove
that physical surfaces are conflict-free. Surface fitting/contact validation is a
later planning gate.

All records are frozen, slotted dataclasses with recursively detached tuple values;
they contain no caller-owned arrays, lists, mappings, meshes or engine handles.
Collections that express sets are sorted deterministically. Polygon ring rotation,
winding and hole order are canonicalized using the existing topology validator.
`to_json()/from_json()` and `to_dict()/from_dict()` use schema version 1 and explicit
record types. Decoding reruns validation, rejects unsupported versions/fields/types,
and returns detached values. Mutating a returned dictionary cannot mutate a record.
Pickle worker round trips are tested but are not a persistent storage format.
Collection fields are limited to 10,000 records and bounded before exhausting
iterables; interface endpoints enforce two triples, and text fields allow up to
512 UTF-8 bytes without control characters. Polygons retain the existing
4,096-vertex bound. These caps do not establish runtime workload admission budgets.

## Legacy one-owner compatibility

`adapt_validated_legacy_site(site, owner=..., frame=..., source_namespace=...)`
requires an already validated `buildgen.site_data.Site`, an explicit building owner,
and an explicit `FrameContext('legacy_projected_xy', GeographicFrame(...), x0, y0)`.
The source namespace identifies the supplied catalogue's identity domain.

The caller must run the existing `catalogue()` and `project()` validation path
before adaptation. `Site` carries no validation token, owner ID or original frame;
the adapter cannot independently attest these missing facts. It accepts no raw
GeoJSON and adds no catalogue loader. Existing provenance, complete exclusions,
coordinate limits, measured ports, overlap rejection and one-owner rules remain
unchanged. There is no relaxation of the legacy source catalogue.

The frame descriptor must match the original geodesy projection, including its
longitude, latitude and ellipsoidal origin height. Its offsets mean legacy polygon
XY are `(source_ENU_east - x0, source_ENU_north - y0)`; port Z is unchanged source
ENU up. Coordinate units are metres. The adapter retains those values and records
exactly one owner membership. It does not infer shared consumers, physical paving,
or generated resource declarations from the supplied property boundary.

`LegacySiteAdapter.to_legacy_site()` reconstructs the original emitter input,
including the dock rise, owner footprint, duplicate exclusions and exclusion order.
Ports retain the legacy validated `(kind, a, b)` ordering. Interface names use a
`legacy-frame-interface-v1:` content hash over namespaced site identity, the
complete legacy frame declaration, kind and endpoint coordinates. Inserting an
earlier-sorting unrelated port does not rename unchanged interfaces. Identical
duplicate ports retain distinct occurrence suffixes within their shared content
identity, preserving legacy acceptance. These IDs are explicitly frame-bound:
reprojection, rebasing or changed endpoint content changes the ID. They are not
persistent canonical mapped-entrance identities; those require source port IDs
that the old catalogue does not supply.
The new evidence/plan
serialize independently; compatibility-only values on `LegacySiteAdapter` support
pickle round trips, not a separate persistent JSON schema.

`FrameContext('canonical_enu', CanonicalFrame(...))` is a distinct coordinate
declaration and forbids tile offsets. `require_canonical()` rejects legacy projected
XY. Recovering source rings/heights and explicitly reprojecting is required before
claiming canonical geometry; no conversion is attempted from the old polygon XY
because its vertical coordinates were discarded. Supplying a new frame descriptor
alone does not make existing tile coordinates canonical.

## Verification

Run from the source root with the existing sibling environment:

```powershell
New-Item -ItemType Directory -Force build/sitegen-contracts/tmp | Out-Null
$env:TEMP = (Resolve-Path build/sitegen-contracts/tmp).Path
$env:TMP = $env:TEMP
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/run_tests.py test_sitegen_contracts test_buildgen_sites --par 2 --timeout 120 --logs build/sitegen-contracts/tests
```

Result: **34 tests passed**: 18 contract/adapter tests and 16 existing site tests.
Coverage includes immutable detachment, JSON/pickle round trips, ordering/ring
permutations, unknown/empty inventories, standalone lots, mixed/overlapping uses,
unresolved same-level surfaces, missing resident members, graph cycles, duplicate
producers, station identity/ownership and exact legacy reconstruction after real
catalogue projection. The unchanged loader still rejects overlapping properties
and unknown exclusion inventories. No game geometry, collision, performance,
multi-tile emitter integration or physical-lifecycle acceptance is claimed.
