# Four staged PRs: dev preparation, 2 November 2026

All four PR branches include upstream `TecnaGamer/BeamNG.Earth:dev` at
`b41b4b04edffab6083e78b0c2ef41982869287b2`. The fork's dev remains aligned with
that upstream commit. These are preparation PRs, not a release or native acceptance.

| PR | Scope | Review base | Validated code revision |
| --- | --- | --- | --- |
| [1](https://github.com/PaperboyNZ/BeamNG.EarthBuildTest/pull/1) | Resource-tab profiler | dev | `a7b1c024` |
| [2](https://github.com/PaperboyNZ/BeamNG.EarthBuildTest/pull/2) | Building/site generation, lean quality tiers and parking protection | testing/runtime-profiler | `1e2ad48b` |
| [3](https://github.com/PaperboyNZ/BeamNG.EarthBuildTest/pull/3) | Lane-input and bridge preparation reuse | dev | `739ceca8` |
| [4](https://github.com/PaperboyNZ/BeamNG.EarthBuildTest/pull/4) | Shared decoded map inputs and road-job telemetry | dev | `e248ff78` |

## Latest work retained

- PR #2 includes `c47142dc`: Low defaults for new settings, direct Very Low/Low
  tile batches, essential/path/full physical cache identities, retained regional
  architecture, and cheaper site geometry and planting work. Explicit saved
  quality choices survive. [Measurements and limits](LEAN_BUILDINGS_20261102.md).
- Parking protection reuses bounded source-road preparation and rejects remote
  envelopes before buffering. Projection, buffers, clipping, point/width budgets
  and incomplete-data rejection retain their original rules. Faulted preparations
  never enter the new cache. The isolated 100-road/49-patch comparison retained
  byte-identical protection geometry; its roughly 6x preparation reduction is not
  a whole-world or frame-rate measurement.
- PR #4 aligns its shared bridge-cache implementation with PR #3. Optional
  dependency telemetry now tolerates absent worker state so it cannot replace the
  original build exception or bypass existing failure cleanup.
- The older dirty playtest checkout was inventoried without rewriting it. Its
  quality/site work is preserved in the published history; its earlier profiler
  and weathering variants are superseded by the current resource tabs and organic
  weathering. Copying those older files over the current branches would regress
  the newer implementations.

## Combined merge preparation

The staging branch `prepare/20261102-final-integration` preserves all four PR
histories. Its validated production-code commit is
`f948b5a0d4aac40c8480996f3988bfb7ef9bd47d`; later documentation-only commits may
advance the branch without changing that code. It is separate from dev.

PRs #1 and #3 can land independently. Review #2 against the profiler branch,
then retarget it to dev after #1 lands. If #1 is squash-merged, remove the
already-landed profiler commits before submitting #2 upstream.

PR #4 also targets dev, but overlaps #2's worker API and cache timing. The
prepared merge `bd6d4084` resolves that overlap explicitly: retain the building
progress token, detail and view arguments, append `submitted_at`, forward all
four from the server, and start one stage clock before cache lookup while retaining
the building refinement path. Do not resolve either side by dropping the other
feature. The combined branch contains this resolution and the subsequent fixes.
Its regression evidence applies to that resolved code, not an arbitrary manual
merge. #3/#4's former shared-docstring conflict is eliminated in #4 itself.

To reproduce the prepared combined source, fetch the staging branch and inspect
the diff from the pinned upstream dev. Keep dev unchanged until review and the
remaining acceptance gates are complete. A merge of the staging branch preserves
the resolved combination; separate squash merges require reapplying/revalidating
the documented overlap resolution.

## Validation

The local audit is `artifacts/pr-final-preparation-20261102` in the workspace.
It records immutable source snapshots, per-module logs, the local-change inventory,
exact branch ancestry, failure logs and focused reruns. Broad checks cover 142
Python modules plus affected-module and worker reruns: 1,871 cases across 146
modules, 1,861 passed and 10 optional skips. The 4,113 combined Lua assertions
include LuaJIT scoping. The independent profiler also passes 1,034 Lua assertions.
These are selected regressions, not the full repository suite. Counts deduplicate
module reruns within each branch; branch counts must not be added as unique coverage.

| Independent branch | Latest focused Python pass / skip |
| --- | ---: |
| Profiler #1 | 39 / 0 |
| World generation #2 | 221 / 0 |
| Road preparation #3 | 139 / 0 |
| Shared decoding/telemetry #4 | 304 / 3 |

The telemetry integration initially failed two existing progressive/streaming
checks; the production fix and its additional regression pass. One terrain-photo
ordering assertion failed under parallel load, then passed unchanged in isolated
runs on exact dev, standalone PR #2 and the combined build. The parallel credits
session timed out awaiting far-field completion; its complete module passes
unchanged on serial reruns of exact dev (26 cases) and the combination (27 cases).
Both complete detail suites also pass serially (9 cases each). Initial failures
remain in the audit, rather than being erased from the record.

All six pool tests, including the previously intermittent executor-timeout case,
pass in this run on exact dev and the combined build. This does not prove the
underlying executor-admission timing limitation is fixed. Five worker tests pass
on each with an external Windows test-only adapter that closes test-owned revisit
sidecar handles before cleanup; original assertions are unchanged. Optional
real-cache/executable tests remain skips. GitHub reported no PR status checks,
PR-triggered workflow runs or inline review threads at the initial audit heads.

## Remaining acceptance

Draft status is retained. Latest native visual, profiler mouse-interaction,
streaming and driving acceptance must be recorded separately. A cold Christchurch
playtest exposed expensive repeated parking-road protection preparation and worker
backpressure; the new parking fix requires a fresh native run before acceptance.
PR #4's repeated cold/warm benchmarks, expanded geometry corpus, attribution and
memory measurements remain open as described in
[ROAD_PREPARATION_STAGE_ONE.md](ROAD_PREPARATION_STAGE_ONE.md). No FPS claim follows
from the offline building or parking microbenchmarks.
