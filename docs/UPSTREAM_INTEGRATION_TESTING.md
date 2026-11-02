# Current dev integration and testing

Prepared 2 November 2026 against `TecnaGamer/BeamNG.Earth` dev
`11cc55572fd5b828f52a0cf0edf0cf449cba1ac0`.

The three PRs include this upstream commit. The performance and profiler PRs can
be reviewed independently against dev. The world-generation PR builds on the
profiler PR. A separate local integration branch combines all three for testing.

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

The default generator is legacy. The v2 dependencies include `shapely>=2.1,<3`.
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
