# Current dev integration and testing

Local combined integration updated 2 November 2026 through `TecnaGamer/BeamNG.Earth`
dev `0c790738f3ab0ddc2bb7330ee3be23cd875caaf7`. The published draft PRs remain at
their earlier `11cc55572fd5b828f52a0cf0edf0cf449cba1ac0` baseline.

The three published PRs include that earlier upstream commit. The performance and profiler PRs can
be reviewed independently against dev. The world-generation PR builds on the
profiler PR. A separate local integration branch combines all three for testing.

## Latest local dev merge

The combined branch includes all four dev commits since `11cc5557`: ready-block
and stand-in fixes, provisional follow blocks in workers and separate request
threads, lower-priority vegetation jobs with timeout measured after queueing,
and cached lane-flow rows with NumPy neighbourhood assembly.

Before merging, all existing combined-playtest follow-ups were checkpointed at
`09df47ff` and retained on `archive/pre-dev-0c790738-20261102`. This includes the
live Simple/Advanced switch, weathering, texture/geometry fixes and terrain/curb
protection. The source checkout matched every playtest source file before merging.

Lane-flow conflict resolution uses upstream's cached rows, road-class defaults,
ID selection and NumPy assembly while retaining endpoint-only native inputs,
short-feature semantics, no-op solve avoidance and lane-column invalidation.
Offline comparison with exact upstream gives identical results for 16,480 road
decisions in nine Auckland cells (49 source cells, 57,935 source features).

Worker conflict resolution retains per-job building mode and progressive detail
arguments, combines optional prebuild admission with upstream's low-priority
queue, and uses the new running-time timeout. Two integration regressions check
those combinations.

Latest targeted validation: 277 Python cases, 272 passed and five optional skips;
990 Lua assertions passed in six suites. Four skips need complete real-map
fixtures; the fifth needs a LuaJIT executable. Lua assertions instead ran through
the installed LuaJIT library. The five worker tests use the existing external
Windows descriptor-cleanup adapter without changing their assertions. Localhost
and asyncio tests run outside the Windows sandbox; temporary files use a writable
workspace folder. Native game appearance and driving acceptance remain pending.

This merge is local. Published draft branches and their existing validation
records have not been changed by this update.

## What belongs in each PR

- Performance (`perf/road-generation-audit`): reuse decoded map data, lane inputs
  and bridge graph work. It does not introduce new buildings or profiler controls.
- Profiler (`testing/runtime-profiler`): optional frame, worker, network and disk
  measurements; Essential and Full modes; continuous collection; a resizable
  window, compact view, frozen display and snapshot export. It defaults to off.
- World generation (`testing/building-system`): the v2 building and site system,
  regional architecture, progressive streaming, collision/resource lifetime,
  shared worker budgets, six building-quality settings, adaptive refinement,
  commercial roofs, curved driveways, parking surfaces, source-linked shared
  sites, weathering and sidewalk refinements. The v2 building generator remains
  opt-in; supporting road, surface and clearance changes also affect legacy mode.

The latest local source and newer package-only fixes were preserved before
integration. No personal cache, roof-colour catalogue, zoning file or shared-site
input is bundled. Those external datasets remain optional.

## Integration checks

The final broad combined run covers 136 Python test modules: 1,804 cases run,
1,794 passed, 10 optional skips, no failures or errors. It includes the latest
upstream terrain/photo planning changes and final road-fallback fixes. This is a
selected regression suite, not every test in the repository. Client checks cover 3,970 Lua assertions in
25 suites, including collision/resource handling, building streaming, settings,
profiler controls, follow and rebase. Lua runs use a stubbed game environment.

Real localhost CLI checks exercise matching protocol/capability negotiation,
both profiler modes, probe replies, I/O telemetry and all six quality-setting
messages. They do not substitute for native game testing.

The final review removed a duplicate profiler publisher from the world-generation
branch and connected upstream's photo worker to the shared worker budget. The
road-worker test now also calls the actual server fallback and compares its
output byte for byte, including the new vegetation-clearance records.

On Windows, two unchanged worker tests hit an upstream temporary-directory
cleanup error because cached file descriptors remain open. This reproduces on
unmodified upstream dev at `50e41cac`. An external test-only cleanup adapter closes
those descriptors before deleting the temporary folders; all five worker tests
then pass. No production workaround or weakened assertion is included.

## Review and submission order

1. Review performance against dev; it can merge independently.
2. Review the profiler against dev; it can also merge independently.
3. Review world generation against `testing/runtime-profiler` to see its own changes.

These are preparation PRs in the contributor's fork. For upstream, submit the
performance and profiler branches to `TecnaGamer/BeamNG.Earth:dev`. After the
profiler lands, update world generation onto the actual resulting dev commit and
submit it there. If the profiler is squash-merged, remove the already-landed
profiler commits while rebasing world generation so they do not appear twice.
Keep the fork's dev branch aligned with upstream; do not merge these draft PRs
into it as a shortcut for combined testing.

## Native playtest still required for the latest combined build

The contributor reported a successful native performance playtest at `ea58fcba`.
That predates the latest upstream merge and does not establish native acceptance
of the profiler or world-generation changes. No new in-game FPS claim is made.

Use matching server and mod sources in an isolated test installation. Install
with `python install.py`, then start the server with one of:

```powershell
python start.py
python start.py -- --building-generator v2
python start.py -- --building-generator legacy
```

Playtesters can choose **Simple** (legacy) or **Advanced** (v2) in Pause menu >
BeamNG.Earth > World > Building generation. The selection persists independently
of graphics presets and switches live in the current gameplay session. Existing
buildings remain until their replacements are ready; changed collisions use the
existing staged handover. Terrain, imagery, vegetation and distant bridges remain.
Building-dependent driveways, sidewalk cuts, parking and masks refresh with their
building tile. Old in-flight jobs cannot publish after a switch; Simple and
Advanced products have separate cache identities and generated filenames.
The active-mode row shows what the connected server is using. At startup, CLI
overrides take precedence over `BNE_BUILDING_GENERATOR`, then the saved setting;
with none set, the default is Simple. The combined playtest initially selects
Advanced and thereafter reads the saved choice.
The v2 dependencies include `shapely>=2.1,<3`.
Optional roof-colour, zoning and shared-site inputs should be passed explicitly
when testing those features. Merely enabling v2 does not supply shared-site data.

In the game, enable the profiler in Pause menu > BeamNG.Earth > Interface >
Detailed performance profiler. Try Essential and Full, resize it, use compact
view, freeze/resume, export a snapshot, then stop profiling. Drive and teleport
with v2 enabled; inspect roofs, parking, driveways and sidewalks, and check that
wheels remain supported as nearby detail changes. Compare with legacy mode.

Building dissolve and weathering hooks are generated locally from compatible
installed game shaders; engine shader files are not redistributed. If discovery
or compatibility checks fail, installation disables the relevant effect. Native
appearance, shader behavior and driving acceptance remain separate from the
automated checks.
