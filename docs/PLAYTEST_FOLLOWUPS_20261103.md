# Playtest follow-ups, 3 November 2026

The three current drafts include upstream dev `711e45a3`. PR #3 incorporates the
former PR #4. PR #2 remains based on the profiler branch; the combined staging
branch retains both the building worker arguments and road timing instrumentation.

## Implemented fixes

- Keep textured distant buildings until equivalent near facades are complete.
  Skip obsolete shells and prevent late skyline tiles from hiding finer buildings.
- Remove the grey facade overlay overlapping the persistent front-door prop.
- Remove coincident rear-edge vertices from sidewalk corners. Check native slab
  triangulation area and repair incomplete triangulation using the same XYZ/UV
  vertices. The captured Auckland corner at -36.913884, 174.903233 previously
  lacked 4.25 square metres of pavement and collision; both now cover its outline.
- Fit intersecting pavement portions to the upper envelope of their original
  surface and the drawn terrain plus 1 cm. The existing native terrain splitter
  locates lattice boundaries; intersections of the two height planes preserve
  continuous shared edges. Clear pavement and curb heights remain unchanged.
  Corrected tiles use matching visible/collision geometry, excluding utility-cover
  decoration. Collision activation guards include the corrected heights.
- Reject parking footprints before road-protection and DEM-grid preparation when
  their existing geographic envelope contains no requested terrain samples.
  Patch shape, margins, corrections, cache budgets and invalid-data rules remain
  unchanged. No worker timeout or admission limit was raised.
- Hash validated canonical building rings directly instead of canonicalizing
  them twice. Keep upstream's narrower revisit dependency closure while including
  nested generator code and bundled catalogues in development and release hashes.

## Captured workload comparison

Fresh processes used the same copied Christchurch inputs: 35,996 building rows
and 4,062 land-use rows across nine cells. Both produced 35,436 accepted buildings
with identical context manifests, projected geometry and evidence digests.

| Work | Before | After |
| --- | ---: | ---: |
| Context construction | 24.28 s | 20.83 s |
| One parking sample, cold | 2.581 s | 0.221 s |
| Same parking sample, repeated | 1.755 s | 0.018 s |
| Parking patches prepared over both queries | 1,074 | 0 |

Parking outputs were identical. The sample intersects none of the parking
footprints, so zero patches is the expected result. Regression fixtures also
exercise contributing/overlapping footprints and split queries. These are single
offline comparisons using analytic terrain for parking, not FPS, full-world
loading, native driving or controlled release benchmarks. Source input datasets
are retained locally, not published in the repository.

## Verification and remaining acceptance

The captured corner, flat control, transverse slope and descending 6/8/10 percent
corner cases are covered by `test_outstanding_regressions`. The formerly buried
corner surfaces clear the drawn lattice, while the flat mesh remains byte-identical.
The suite also verifies collision agreement, unchanged canonical identities,
invalid-hole rejection and avoidance of irrelevant patch preparation.

Focused building, geometry, parking, road, cache, worker and protocol regressions
ran 312 cases (311 passed, one optional skip), and all 17 streaming Lua suites
passed 3,415 assertions. Standalone profiler and consolidated road
draft checks passed independently. Workspace evidence and per-module logs are in
`artifacts/outstanding-20261103/verification-summary.json` and the adjacent reports.
Windows tests close only their own revisit sidecar handles before temporary
directory cleanup. Local socket tests run outside the sandbox. Protocol fixtures
use their intended default generator mode.

Native visual review, quality switching, driving over corrected corners and
startup acceptance remain pending on this revision. Corrected sidewalk tiles use
more collision triangles to match the visible surface; measure collision rebuild
cost in game before merging. The earlier nearby-loading timeouts are not declared
resolved by these offline improvements. Existing game/settings are preserved;
the refreshed source is used on the next playtest launch.

An isolated 20 m sidewalk microcheck measured 0.81 ms without clearance, 0.90 ms
for a flat clearance check and 1.36 ms for a corrected transverse slope. Visual
triangles were 28/28/32 and collision triangles 14/14/30 respectively. This is a
small synthetic CPU check, not a claim about full-tile physics rebuild cost.
