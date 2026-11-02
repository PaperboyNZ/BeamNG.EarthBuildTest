# Garage access and traversal repair

Implemented 1 November 2026 in the active source snapshot. Introduced in building
plan schema **13** (current schema **14** also adds church/terminal metadata):
frozen `garage_access` records retain the accepted entrance, ground
route and physical apron through workers and all building representations.

The garage code repair is closed out. The continuation passed all 107 garage,
building and topology checks before moving onto other architecture and pavement
work. Local landscape coordination now also reserves accepted garage aprons.
The native driving/streaming checks below remain open; no universal drivability
or game-performance claim is made from these geometry tests.

The repair addresses actual baseline failures:

- A later bridge-clearance constant overwrote the intended 3.6 m garage ramp lane
  with 1 m. The bridge inset now has its own name.
- The old driveway was a terrain-draped visual ribbon. It neither joined the
  raised deck physically nor reserved an opening through piers/columns.
- Garage lite meshes could close a playable structure into a box. Near, lite and
  collision now use the same open-deck geometry and accepted apron.
- Ramp/deck junctions had instantaneous grade changes and tightly separated
  switchback lanes. Ramps now have 3 m quadratic transition zones, 3.6 m lanes,
  10 m landings and lane centres 10 m apart for a 5 m turning radius, with straight
  run-outs before turns. These are gameplay fitting dimensions, not code claims.

## What the adapter accepts

`buildings.garage_drives` now delegates to `buildgen.garages.resolve`. Both worker
and local-server road paths provide generated-ground samples, sidewalk runs and
tile bounds. It evaluates at most four entrance candidates, fits a full vehicle
route to the first ramp and returns parking-exclusion records only. The building
mesh owns the apron surface; no duplicate terrain-draped road ribbon is emitted.

Straight ordinary-road approaches can meet the garage directly or cross a fitted
dropped curb. The curb preserves the rear pedestrian strip and existing pedestrian
ramps. Its garage-specific road lip is 2 mm; residential crossing profiles retain
their existing default. The apron shares exact rear-sidewalk and deck heights,
has eased end grades, and uses the same vertices for visible and collision meshes.

A 5.2 m by 2.1 m vehicle envelope with 0.2 m clearance is swept through the accepted
ground route and upper U-turns. Columns, facade piers and the optional stair tower
respect those reservations. The tower's whole footprint must fit. Source holes
remain holes in every deck; unsupported layouts fall back without adding a drive.

Other source buildings, raised volumes and existing access/landscape solids are
conservative obstacles. Until level-aware source clearance is available, an
overhead building is not assumed high enough just because `min_height > 0.5`.
Interior routes and external approaches both check obstacles. Road contact is
probed across the complete mouth (17 stations), rejecting a nonplanar edge that
would leave a step above 5 mm at those probes. Terrain fitting uses up to 464
samples over four alternatives, with a 15% grade and 0.6 m fill limit.

Replanning removes only the adapter's previous curb reservations, then replaces
them with the newly accepted cuts. Residential crossings survive. Failed new
terrain or a blocked route cannot leave an orphan dropped curb behind.

## Validation and remaining limits

Focused tests cover road/apron/deck seam heights, upward-facing surfaces,
near/lite/collision equality, dropped curbs and protected pedestrian ramps,
full-body clearance against the emitted structure, upper-deck U-turns, source
holes, obstacles inside the garage, low overhangs, uneven road mouths, missing or
rough terrain, repeated planning, worker round trips and translated frames.

`tools/garage_access_preview.py` produces a mesh/route review sheet and a JSON
report for level roads, a dropped-curb approach and a sloping road. The accepted
fixture has about 4,000 vertices, below one 20,000-vertex import target; larger
structures still use the existing complete chunk path. Timings in that report
are synthetic observations, not a driving-performance gate.

Current limitations are explicit:

- **BeamNG vehicle handling, tyre contact and streaming while occupied are not
  yet tested.** The geometry checks do not establish universal drivability.
- Curved/oblique or narrow sidewalk crossings, unsupported turn envelopes,
  excessive slopes, missing ground and controlled-access roads can be rejected.
- Inferred approaches crossing the owning tile boundary are deferred until shared
  site ownership/residency is integrated. Existing interior decks are retained;
  a rejected connection does not create an entrance arrow or a fake drive.
- The collision contact target is validated at finite terrain probes, not against
  every possible unseen terrain detail. No terrain excavation/retaining system,
  traffic simulation or regional engineering certification is introduced.
- The new immutable garage access record is a local compatibility adapter. It is
  not a completed canonical multi-site planner or resource-lifetime implementation.

Reproduce from the source root using the existing sibling Python environment:

```powershell
$python = '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe'
New-Item -ItemType Directory -Force build/garage-access/tmp | Out-Null
$env:TEMP = (Resolve-Path build/garage-access/tmp).Path
$env:TMP = $env:TEMP
& $python tools/run_tests.py test_buildgen_garages test_buildings test_buildgen test_buildgen_topology test_buildgen_chunks test_buildgen_progressive test_buildgen_driveways test_sidewalk_collision test_parking --par 2 --timeout 120 --logs build/garage-access/tests
& $python tools/garage_access_preview.py
```

See [the integrated checklist](GENERATION_IMPLEMENTATION_CHECKLIST.md) for the
shared-site migration and the outstanding in-game acceptance gates.
