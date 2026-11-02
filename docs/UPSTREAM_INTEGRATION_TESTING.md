# Current dev integration and testing

Prepared 2 November 2026 against original `TecnaGamer/BeamNG.Earth` dev
`992e11fdad0ccf20531d0768c1c47d73dced5c34` (rechecked before publication).

## Review and merge order

1. `testing/runtime-profiler` into `dev`: opt-in Frames, Workers, and Network & Disk
   profiling, Essential/Full modes, bounded telemetry, and instrumentation hooks.
   It has no `buildgen` or `sitegen` dependency. The default is off.
2. `testing/building-system` into `testing/runtime-profiler`: the complete current
   building/site source and supporting road, sidewalk, vegetation, worker-budget,
   cache, collision-lifetime, progressive streaming, and dissolve changes.

Review the second PR against the first branch to see only the building work.
After the first merges, retarget the second PR to `dev`. If the first is squash
merged, rebase the second onto that new dev head to remove duplicated history.
The original source snapshot and old playtest packages remain available locally.

## Test in BeamNG

Use the server and mod from the same branch. Close the previous server and game,
run `python install.py` to install dependencies and the matching mod, then:

```powershell
# PR 1: upstream world generation with the new profiler
python start.py

# PR 2: new buildings and all integrated changes
python start.py -- --building-generator v2

# PR 2: legacy buildings for comparison on the same current upstream terrain
python start.py -- --building-generator legacy
```

V2 remains explicitly selected; the default generator is `legacy`. V2 adds
`shapely>=2.1,<3`. Prepared roof-colour, zoning, and site datasets remain optional
CLI inputs; no personal cache or local imagery catalogue is included. The 64
regional themes and versioned architecture catalogues are included in source.
Normal source/dependency hashing invalidates generated caches as needed.

Open Pause menu > BeamNG.Earth > Interface > Detailed performance profiler.
Compare disabled, Essential, and Full modes while driving and teleporting; check
worker stages, network/disk counters, export, close/reopen, and persistence.
For V2, inspect courtyards, roofs, commercial sites, driveways and sidewalks;
drive across generation boundaries and check collision continuity, progressive
shell/detail replacement, far/near coverage, and restart/rebase behavior.

The 0.4 s building dissolve uses mod-local hooks generated from the installed
game's shaders. No engine shader files are redistributed or modified. If shader
discovery/compatibility fails, the installer disables the dissolve; set
`BNGE_GAME_DIR` when the game is outside a discovered Steam library.

The historical r13 whole-server old/new selector is a local comparison package
against `55ddc418`, not a second old server bundled into these PRs. The commands
above compare generators on the new dev terrain. Existing playtest launchers
and packages are retained locally.

## Validation

These are offline results, not native game acceptance or an FPS claim.

| Check | Result |
| --- | --- |
| Profiler-only Python | 180 run, 6 optional cases skipped; no failures/errors |
| Profiler-only Lua | 738 assertions passed across 8 suites |
| Integrated profiler Python | 180 run, 6 optional cases skipped; no failures/errors |
| Integrated profiler Lua | 754 assertions passed across 8 suites |
| Building/site and related Python | 1,137 tests passed across 95 modules |
| V2 streaming integration | 154 Python tests and 3,351 Lua assertions passed |
| Broad integrated Lua | 85 of 89 suites pass; 10,273 assertions in passing suites |

Counts overlap between targeted and broad runs; do not sum them as unique tests.
The four broad Lua failures reproduce on an unmodified checkout of the exact
upstream commit: `test_follow` (11 assertions), `test_rebase` (2 assertions),
`test_scoping` (Windows file enumeration), and `test_sky` (missing module).
The follow/rebase tests still expect earlier terrain timing constants. These
are recorded limitations; the broad run is not represented as completely green.

Integration fixes preserve upstream's 1 m terrain and terrain assets, split
collision encoding alongside shared building LOD bounds, missing-file recovery,
and furniture restoration after reconnect. Retained source folders include both
upstream shape paths and the new parked/pending/physics resources. New regression
coverage checks combined collision/bounds encoding and missing old-session files
despite unchanged content/physical hashes. Standalone Python import/environment
fixtures and Lua fixtures were updated for bounded imports, inverse transforms,
prop residency, and deferred collision retirement.

Reproduction entry points (with server requirements and optional `lupa` LuaJIT
available; `check_runtime_profiler.py` accepts `--lua-runtime PATH`):

```text
python -B tools/check_runtime_profiler.py
python -B tools/check_building_streaming.py
python -B tools/run_tests.py test_cdae test_building_streaming test_sector_manifest test_buildgen_band_frame
```

The broad Python run includes every `test_buildgen*` and `test_sitegen*` module,
the other new server tests, and related buildings, roads, roadmesh, roadcorners,
furniture, vegetation, terrain, surface, cache, and worker-admission regressions.
It is not the entire server suite. Native appearance, driving, shader behavior,
occupied streaming, and performance acceptance are still required before release.
