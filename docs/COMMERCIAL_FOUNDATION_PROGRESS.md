# Shared commercial composition foundation

Implemented 1 November 2026 after the first commercial composition slice. This
adds shared M4 planning and bounded detail to existing accepted families. It does
not complete M4 or establish game/performance acceptance.

## Shared programme and geometry

Commercial fitting consumes `buildgen.programme` floor datums, merged straight
elevation runs, fitted grids and semantic seed channels. Each facade plan derives
the programme once and passes it to commercial/terminal adapters. Eligible
facades emit one existing `Elevation` per merged run. Actual door reservations
are lifted from unchanged source-edge coordinates into that run before fitting;
drawing and obstruction reservations use its full start/end basis.

Office floors share one lattice. Entrance fragments stay within their original
bays and retain the mullion phase. Collinear source segmentation no longer
restarts composition or adds window returns at artificial seams. Trade modules
retain their existing function/staff-threshold positions while adopting shared
bounded grids. Logistics service and supermarket display groups use the shared
fitter too.

`commercial_detail.py` derives frozen detail proposals over accepted openings:
aligned piers, ribbon-office spandrels, pane transoms and terminating wall-plane
roof-edge trim. Structure seeds choose coherent widths; vocabulary seeds choose
one consistent existing trim tone. Major subdivisions remain in near and lite;
small transoms and shallow closed returns simplify in lite. These are inferred
facade subdivisions, not observed structural systems, measured roof shapes or
construction eras. Missing structure/era/condition provenance remains unknown.

Footprints, heights, roofs, roof direction and primary facade materials remain
authoritative. No canopy, interior, route, site, tower/hotel eligibility or new
collision producer is added. Detail stays inside existing visual bounds. All six
comparison fixtures retain **identical before/after collision hashes**.

## Fitting, bounds and compatibility

Detail reserves clearance around accepted entrances and glazing. Courtyard and
explicit party-wall runs receive no new detail. If obstruction fitting rejects
an opening, `ci_obstruction_run:B:E` identifies the affected run. Continuous
structural detail there is declined because intervening gaps have not been proved
clear; other clear elevations can retain detail.

Each source is limited to 192 accepted detail components, 32 per elevation and
512 clipped-panel capacity; the component cap is stricter in current output.
Existing opening/floor/source limits remain. Exhaustion is diagnosed without
truncating mapped outlines or source members.

Rejected optional programme descriptors retain generic geometry with
`architecture_programme_existing_geometry_fallback`. One
`can_public_entry(spec)` gate controls supermarket opening, threshold width and
stock-door suppression. It checks the unchanged accepted door against the full
run's real corners/headroom. Near-corner doors on short final source fragments
keep ordinary width and their stock prop; no door is relocated to fit detail.

Facade record shapes/building schema are unchanged. Recursive source hashing
includes the new modules. Explicit site/dock consumers must translate source
service-edge addresses into run offsets before replacing a merged elevation;
this does not move the physical portal. That integration belongs to the site
adapter and is reviewed separately.

## Review and synthetic measurements

Original owned runtime/tool files are under
`build/architecture-foundations/original`. Visually reviewed before/after sheets
are `build/architecture-foundations/commercial-before.png` and
`commercial-after.png`, with matching JSON containing layouts, detail proposals,
source/mesh hashes, first passes and five warm samples. All comparison sources
use 30 × 20 m footprints and stable seeds; offices have three floors/12 m supplied
height, others one floor/6 m.

Visual review shows aligned punched-office piers, coherent ribbon-office
pier/spandrel frames, and distinct shop/trade modules with restrained
terminations. Curtain bays retain vertical glazing and an opaque end zone.
These synthetic closed-shell renders use approximate colours, not game textures
or lighting, and do not establish observed-site or unlabelled recognition gates.

| Fixture | Near vertices before → after | Warm plan/access median ms | Warm near/lite/collision compile median ms |
| --- | ---: | ---: | ---: |
| Workshop/trade | 1,010 → 1,190 | 3.78 → 4.61 | 2.92 → 3.83 |
| Strip shops | 812 → 1,052 | 4.14 → 4.94 | 2.50 → 3.19 |
| Supermarket | 950 → 1,150 | 4.13 → 4.31 | 3.01 → 3.07 |
| Punched office | 5,260 → 7,020 | 7.47 → 7.44 | 7.74 → 11.08 |
| Ribbon office | 2,788 → 4,444 | 4.96 → 5.70 | 5.78 → 10.11 |
| Curtain office | 3,434 → 3,362 | 5.52 → 5.01 | 6.47 → 7.02 |

Before PNG SHA-256:
`cb31c8056ddd41345bdc5cf6187d60995c9a5b018bed278ea4713239bd3fcfa8`.
After PNG SHA-256:
`176fe0432395c0f88e62173a4b99a0e275ba7ee83d61e3e57181797c8a2b0e58`.

Added near detail costs compile time, especially punched/ribbon offices. Concurrent
work and five samples do not establish a release-grade regression estimate. This
slice neither passes nor redefines generation/driving frame gates. Import,
collision activation, memory, driving and small-machine calibration remain open.
Dedicated long-span roof topology is deferred; no visual trim is labelled a
measured roof assembly.

## Verification

```powershell
$python = '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe'
$env:TEMP = (Resolve-Path build/architecture-foundations/tmp).Path
$env:TMP = $env:TEMP
& $python tools/run_tests.py test_buildgen_commercial_foundation test_buildgen_commercial_architecture test_buildgen_commercial test_buildgen_facades test_buildgen_foundation_integration test_buildgen_terminals test_buildgen_programme --par 3 --timeout 120 --logs build/architecture-foundations/tests-final
& $python tools/commercial_preview.py --comparison --repeats 5 --out build/architecture-foundations/commercial-after.png
```

Result: **75 tests passed** across seven modules. New module
`test_buildgen_commercial_foundation` has eight tests covering actual near/lite
facade equivalence under collinear densification across seven families with an
unchanged door; aligned lattices; corner-entry consistency across all consumers;
safe programme fallback; once-per-plan derivation; frozen bounded detail;
unchanged collision/visual bounds; and suppression at courtyard, party-wall and
unresolved obstructed runs. Existing seed/rebase, height/roof/topology, workshop,
supermarket and facade regressions pass. Root's broader integration checks are
recorded separately.
