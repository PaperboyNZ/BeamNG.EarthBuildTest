# Specialist compatibility and diagnostic adapter

Implemented 1 November 2026 in `server/buildgen/specialized.py` as an M1
compatibility foundation. This does not complete the specialist geometry tickets
or the M1 milestone. This compatibility module itself adds no architectural geometry.
The later schema-14 planning integration separately enables bounded
[church](CHURCH_IMPLEMENTATION_STATUS.md) and
[terminal](TERMINAL_IMPLEMENTATION_STATUS.md) architecture. Its evidence adapters
run around the unchanged legacy predicate, including correction of name-only
church/terminal routing. The compatibility claims below describe the predicate,
not the complete current planning entry point.

## API and compatibility

`legacy_route(attrs, area, *, rules=None) -> bool` is the lightweight replacement
for `compiler.specialised`. It executes the existing dispatch rules without
constructing diagnostic records. The compiler now delegates to this function;
changing eligibility is a later, separately tested step.

`select(attrs, area, *, rules=None) -> SpecializedSelection` (also exposed as
`selectable`) returns frozen selection, capability and source-observation records.
Use `.legacy_route` for compatible dispatch; do not use the record's truthiness.
`.to_dict()` returns detached data and `.to_json()` produces deterministic sorted
JSON with nonfinite JSON numbers prohibited. Records also support pickle worker
round trips. They are not added to `BuildingPlan` or its serialized schema.

`LegacyRules` detaches the three class sets and two dimensional thresholds from
`buildings.py`. Default calls load those constants lazily; callers can pass an
explicit record to avoid importing buildings. No dimensional defaults are
duplicated here. Compatibility deliberately retains:

- Existing flag truthiness and first-match short-circuit order.
- Lowercased but **untrimmed** legacy classes, substring name checks, and the
  original case-sensitive `roof_shape == "pyramidal"` test.
- Existing parking/pyramid thresholds and the strict name-based garage `> 800`
  check, including NaN comparison behavior.
- Keyword false positives such as Terminal Hotel, Concourse Coffee and Church
  Street Shop. Structured diagnostics identify their uncertainty while their
  legacy routing remains unchanged.

`legacy_reasons` records the first satisfied condition, not every potentially
matching branch. This preserves short-circuit behavior even when a later branch
would reject an invalid area value. Changing an existing exception into a route
decision is also outside this adapter's scope.

## Evidence and ownership boundaries

The classifier distinguishes current `facility_use`, `architectural_fabric` and
`transport_mode`. Optional caller-supplied semantic keys include `building`,
`building_use`, `use`, `amenity`, `religion`, `terminal_use`, `transport_mode`,
`aeroway` and `railway`, alongside existing class/subtype/name evidence. These are
**not a declaration that production ingestion retains those fields**. Their feed,
cache, normalized evidence and worker lineage must be audited before activation.

`building_use` and `use` explicitly override class-based current-use selection;
conflicting supplied current uses remain diagnosed. A class/building tag for
church fabric can coexist with residential or retail use. A generic religious
class, a place-of-worship amenity or a religion tag does not establish church
fabric, active Christian worship or a denomination. Family and vocabulary remain
`None`: no era, style, tower, symbol or material is selected.

Direct passenger/freight classes, `terminal_use=passenger/freight/cargo`, and
explicit bus/ferry/rail passenger-facility tags distinguish passenger, freight and
unknown terminal use. A plain terminal/concourse class or `aeroway=terminal`
without passenger/freight evidence remains `terminal_unknown`. An airport terminal
class confirms airport passenger use; an aeroway terminal tag alone confirms only
air mode. Explicit modes and direct transport tags establish mode, while names,
airport proximity, geography and brands do not. Conflicts remain unknown with
reasons; no arbitrary mode wins.

`owner` is an advisory **workstream** boundary, not a canonical resource producer
or cross-tile identity. Confirmed freight remains `commercial_industrial`.
Direct fuel-station use remains `gasstations`; this adapter does not discover
stations, interpret brands, create pumps/triggers, suppress canopies or replace
any station behavior. Legacy ship/pier/bridge routes retain infrastructure
ownership. Other records belong to `buildgen`.

`observations` contains supplied scalar source values as strings, with invalid
nonfinite values and unsupported value types marked. These are detached from
caller-owned objects. `reasons` contains **classifier conclusions**, such as
keyword ambiguity or conflicting modes; those conclusions are not source
observations. This diagnostic classification does not resolve part roles or
infer transport/site relationships.

## Capability limits

Every record declares `adapter=diagnostics_only`, `geometry_accepted=False` and
`fallback_topology_verified=False`. A legacy route is compatibility, never proof
that its geometry can preserve the source. Nonlegacy records report
`fallback=existing_route`; the classifier cannot establish which caller-specific
route will run.

Observed source holes, positive minimum height, mapped parent relationship and
special curved/domed roof tags produce explicit unsupported feature requirements.
The source `_planning_footprint` takes precedence over a clipped `_footprint` for
hole diagnostics. Requirement tuples contain only observed positive requirements;
an empty tuple is not an assertion that all topology is known or supported. A
positive minimum height is reported as an elevated volume, not proof of a
traversable passage. Source geometry is never stored, modified or generated.

Part-role resolution, topology-safe legacy/shell fallback, actual specialist
compilers, source lineage retention, resource identities and physical lifecycle
capability negotiation remain later work. The adapter neither promises playable
topology nor silently chooses ordinary office geometry for a failed specialist.

## Validation

```powershell
New-Item -ItemType Directory -Force build/specialist-contracts/tmp | Out-Null
$env:TEMP = (Resolve-Path build/specialist-contracts/tmp).Path
$env:TMP = $env:TEMP
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/run_tests.py test_buildgen_specialized --par 1 --timeout 120 --logs build/specialist-contracts/tests
```

Result: **14 tests passed**. The compatibility matrix covers 1,260 class/name/area
combinations against a frozen copy of the pre-adapter dispatch expression and the
compiler entry point, plus flag/roof/garage boundaries and lazy short-circuiting.
Other tests cover keyword false positives, converted and generic religious
buildings, passenger/freight/unknown terminals, direct modes, conflicting evidence,
fuel ownership, source void/elevation/part/roof limitations, immutability, detached
serialization, pickle round trips and deterministic attribute ordering.

Logs are in `build/specialist-contracts/tests/test_buildgen_specialized.log`.
No game, collision, streaming, visual-family or performance acceptance is claimed
by these diagnostic tests. Compiler delegation is integrated; current geometry
regression results are recorded in the integrated implementation checklist.
