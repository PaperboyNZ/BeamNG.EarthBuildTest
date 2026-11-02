# Specialist implementation readiness

Reviewed 1 November 2026 against the editable `BeamNG.EarthBuildTest` source.

The design briefs and staged requirements exist for churches, terminals, parking
garages and petrol stations. Preparation is sufficient to begin the bounded
foundation work below. It is not complete for the full architectural expansion:
live shared-site integration, source-part lineage, reference/asset validation and
native-game acceptance remain open. Existing implemented slices must be retained.

This is a preparation checkpoint, not a new runtime implementation or playtest
release. The [integrated checklist](GENERATION_IMPLEMENTATION_CHECKLIST.md) remains
the execution authority; the [specialist brief](SPECIALIZED_BUILDING_IMPLEMENTATION_PLANS.md)
and each type's detailed plan retain their geometry and evidence requirements.

## Verified current position

| Type | Already implemented | Remaining planned work |
| --- | --- | --- |
| Churches | Three bounded chapel/parish/modern compositions, fitted openings, three decorated spire variants on an eligible subset, immutable shared facade programme | Source-linked aisles, transepts, towers and complex parts; classical/landmark treatments; grounded approaches and churchyard exclusions; reference and game review |
| Terminals | Two bounded airport hall/concourse facade treatments, evidence-based routing and shared opening grids | Linked halls/parts, broader supported transport modes, evidenced passenger interfaces and multi-level access |
| Parking garages | Coordinated entrances, physical aprons, ramp transitions, swept vehicle clearance and matching open-deck representations | Concrete/masonry/screen identity expansion, advanced circulation and native driving/occupied-streaming checks |
| Petrol stations | Existing station confirmation/merging, regional stock assets, local layouts, tile records, staged props and refuelling areas | Immutable station-plan integration with shared physical surfaces, coherent modular identities, compact/neighbourhood families and later rural/service/truck facilities |

Read [church status](CHURCH_IMPLEMENTATION_STATUS.md),
[terminal status](TERMINAL_IMPLEMENTATION_STATUS.md),
[garage status](GARAGE_ACCESS_IMPLEMENTATION.md) and the
[petrol plan](PETROL_STATION_GENERATOR_PLAN.md) before changing their adapters.
Church admission remains bounded; mapped towers/assemblies and unsupported roofs
are not made safe merely by retaining legacy fallback.

Source inspection found building `SCHEMA_VERSION = 17`. Older briefs mentioning
schema 12–14 or saying `server/sitegen` does not exist describe historical
checkpoints. Re-read the live version before changing serialization; other
architecture work is active in this shared source. Do not reserve a future version
number or overwrite those changes. This snapshot has no Git metadata: preserve
original touched files and hashes when implementation begins.

`sitegen.plan` already defines immutable membership/interface/resource records,
including station ownership of pumps and triggers. Its `SitePlan` explicitly
keeps physical surface validation unresolved. `sitegen.surfaces` provides
job-local samples/reservations, not canonical streaming ownership.

`gasstations._record` still samples terrain at each prop and interaction-area
position. `tile_sites` still supplies station records, canopy suppression, access
cuts and painted forecourt pads through the existing road-tile path. Those are
concrete integration points, not an already completed common physical surface.

## Implementation sequence

1. **Freeze the current compatibility baseline.** Record hashes and fixtures for
   station IDs, source canopy membership, accepted pump counts, asset manifests,
   props and interaction areas, plus the existing specialist meshes. Preserve
   station confirmation/closure/convenience-brand rules and gasoline/diesel
   compatibility. Capture real-map source examples separately from synthetic cases.
2. **Connect shared ownership and lifetime.** Use the existing `sitegen` identity,
   records and legacy adapter boundary. Implement canonical runtime producers,
   consumers and revisions, bounded admission/cancellation and retention of
   occupied essential collision resources. Verify reversed tile order, rebases,
   partial membership, replacement failure and retirement before larger sites.
3. **Adapt station records without changing accepted appearance.** Keep
   `gasstations.py` as the entry point. Introduce detached versioned station
   decisions with stable component IDs and explicit surface dependencies. Carry
   them through cache/worker/server/Lua compatibility boundaries. Shared circulation
   belongs to the site; pumps and refuelling triggers belong to the station.
4. **Deliver one complete fuel surface slice.** Collect road/shop/pump interfaces
   before fitting pavement. Fit complete stopping/vehicle envelopes and pedestrian
   reservations. Derive pavement, island/pump bases and interaction heights from
   the accepted surfaces, with one collision owner. Commit replacement readiness
   and source-canopy suppression together; failed replacements retain visible,
   functional fallback. Recheck coverage against the baseline.
5. **Expand visual families after functional parity.** Start with compact and
   neighbourhood fuel layouts and three coherent identities in a reviewed pilot
   pack. Validate real asset bounds, modular canopy bays, materials and regional
   references before activation. Preserve mapped operator metadata and neutral
   fallback; do not stretch dispensers or infer a brand from geography.
6. **Extend specialist assemblies through retained evidence.** Audit feed → cache
   → normalized evidence → frozen worker plan for source parts, roles, heights,
   roofs and current use. Implement mapped church parts and terminal assemblies
   through shared roof/access contracts after their prerequisites pass. Keep
   full-envelope fit and conservative unsupported-case diagnostics. Garage facade
   expansion must retain the accepted portals and swept circulation reservations.

Steps 1–3 can begin as bounded foundation work. New shared physical sites depend
on step 2; fuel identity expansion depends on step 4. Broader church/terminal
assemblies require the part-evidence and physical-lifecycle gates. Native baseline
measurements can proceed alongside implementation; they are still release gates.

## Outstanding preparation and acceptance

- Select observed reference fixtures for each new family and held-out locations
  for regional packs. Review at least three footprints and three stable seeds per
  family. Existing synthetic church sheets do not establish real-map recognition.
- Verify applicable primary dimensional references before authoring regional
  profiles; the original plans explicitly leave that verification open.
- Inventory usable canopy/pump/sign/material assets and their actual bounds;
  complete pilot identity combinations before adding executable catalogue rows.
- Test duplicate/closed/missing-data stations, neighbouring sites, multiple or
  absent canopies, slopes, road conflicts, tile-boundary source canopies and
  missing assets. Explain changes in accepted station/pump counts.
- In BeamNG, approach, stop and refuel at every accepted pump in the test matrix;
  repeat after rebase, relayout and neighbouring tile load/unload. Check actual
  garage entry, all advertised decks, exit and occupied streaming with vehicles.
- Measure fixed-route generation/collision and frame-time gates from the integrated
  checklist; verify day/night materials and near/far transitions. Package matching
  server/mod/assets only after applicable integration checks. Native acceptance
  remains distinct from tests and private test-package availability.

## Verification during this preparation review

Fresh runs passed **201 focused tests**: 14 specialist compatibility tests, 78
across churches, terminals, garages, site contracts and canonical identity, and
109 fuel classification/layout/canopy/region/pad/lane/tile tests. The fuel async
switch and real-map-cache classes were not included in this review. Commands ran from the
source folder using the sibling progressive package's Python environment, with
workspace-local TEMP/TMP and `server;server/tests` on PYTHONPATH:

```powershell
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' -m unittest discover -s server/tests -p test_buildgen_specialized.py
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' -m unittest test_buildgen_churches test_buildgen_terminals test_buildgen_garages test_sitegen_contracts test_sitegen_identity
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' -m unittest test_gasstations.ClassifyTest test_gasstations.MergeTest test_gasstations.CanopyTest test_gasstations.LayoutTest test_gasstations.RegionTest test_gasstations.PadTest test_gasstations.LanesTest test_gasstations.LaneLayoutTest test_gasstations.TileTest
```

These are focused source checks, not full regression, package, reference-photo or
native-game acceptance. The source may continue changing in other active chats;
rerun affected suites against the frozen implementation baseline.
