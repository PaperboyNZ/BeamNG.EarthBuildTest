# PR integration audit — 2 November 2026

This is the earlier three-PR audit. The subsequent four-PR preparation and
fresh verification results are in
[PR_DEV_PREPARATION_20261102.md](PR_DEV_PREPARATION_20261102.md), including current
passing pool checks, serial session reruns and the latest parking fix.

All three draft branches include upstream dev through
`b41b4b04edffab6083e78b0c2ef41982869287b2`. Performance and the profiler remain
independent against dev; world generation includes the latest profiler as its
review base. A local combined branch includes all three. No upstream PR is
created or merged by this update.

## Findings addressed

- The combined playtest omitted the published profiler resource-tab update
  `ddfc3e0c`. The current profiler and world-generation sources retain it, and
  the combined integration includes it.
- Live building switching checked an active peer's road-geotile capability but
  omitted its building-chunk capability. The server now rejects either missing
  capability before changing the mode or generation epochs. Regressions check
  rejection of an active older peer and acceptance with an inactive older peer.
- Live mode requests, replies and hello capabilities were missing from the
  protocol agreement table and CLI golden assertions. The actual message fields
  are now checked, including emitted mode-switch replies. Geometry, terrain and
  existing protocol checks are retained.
- Distant facade textures and mode-specific output names had stale expected
  writer calls and paths in two tests. Expectations now use the intended texture
  representation and the actual mode-aware filename function; exported bytes,
  accepted-plan identity and vegetation exclusions remain asserted.
- The lane benchmark counted endpoint arrays but omitted the retained upstream
  row offsets. It now counts all retained arrays once, including shared attributes.
- Upstream's `1a9b4e1f` packed mirror supersedes our small-array bundle.
  Performance's `server/mapdata.py` matches upstream exactly. Tests retain dtype,
  shape, bitwise data, read-only mapped large arrays, writable small copies,
  old per-array compatibility and damaged-cache recovery checks.

## Verification

| Branch scope | Python passed | Optional skips | Lua assertions |
|---|---:|---:|---:|
| Independent road/cache selection | 510 | 3 | Shared upstream client changes checked with the other branches |
| Independent profiler and affected map code | 217 | 5 | 1,034 |
| World generation and latest affected modules | 1,817 | 10 | 4,110 |

These selections combine the broad audit with affected modules rerun after the
latest dev merge. They are not a fresh run of every repository test. The separate
upstream pool timeout failure below is excluded from the passing totals and is
not hidden by a skip or an altered assertion.

The lane implementation matches exact upstream for all 16,480 decisions across
nine cached Auckland cells, drawing from 49 source cells and 57,935 features.
This establishes fixture decision equivalence, not an FPS claim. The earlier
performance measurements retain their original baselines.

Worker assertions use the existing external Windows descriptor-cleanup adapter.
Lua scoping assertions run through the installed LuaJIT library's actual bytecode
and constant traversal, adapting the test's POSIX subprocess commands. Fixed
test tokens initially shared staging tombstones because the test TEMP path
contained a lowercase `temp` component; isolated `scratch` folders remove that
test-environment collision without changing production cancellation behavior.

## Remaining finding

**P2, inherited from upstream: process timeout is not measured from confirmed
worker execution.** `server/pools.py:result_running` uses `Future.running()`, which
Python's process executor can set while the call is still queued for a worker.
Queue delay can therefore consume some of the timeout. The upstream
`test_timeout_counted_from_its_start` fails on exact unmodified upstream as well
as these branches in the current Windows/Python environment. The production
timeout is much longer than the regression's short timeout; this is not evidence
of a new game failure. No production workaround or weakened assertion is included.

## Scope and acceptance limits

The audit concentrates on upstream conflict resolution, branch separation,
cache representation and recovery, protocol agreement, generator-mode isolation,
stale-job rejection, worker admission, geometry/collision contracts and profiler
telemetry. It does not establish a line-by-line proof of the entire generation
system. Optional real-map data, Lua executable and group-network fixtures remain
unavailable where the test reports a skip. Native appearance, shader behavior,
profiler mouse interaction and driving acceptance remain pending.
