# Shared worker admission rollback and native observations

PR #2 commit `96a906de4c6be3b86b7bccab1cf2a086a8db3e8f` removes
`WorkAdmission`, `Backpressure` and the shared admission arguments from worker
pools. `budget.py` now matches upstream dev `b41b4b04` exactly; `pools.py` matches
the profiler branch, retaining its instrumentation over upstream scheduling.
Existing process/cache budgets, priority queues, cancellation and recycling remain.

The removed gate reserved estimated memory at submission, including time spent
queued. Distant work could therefore reject nearby road work despite idle road
workers. A regression queues 16 distant jobs and verifies independent terrain and
road submission/completion. Aggregate admission is deferred, not marked complete.

## Verification

Fresh fetches of upstream and fork dev both remained at
`b41b4b04edffab6083e78b0c2ef41982869287b2`. All four staged branches contain it.
The independent PR #2 revision passes 34 focused Python cases; the resolved
combination `410b4b2f460cc990664fc650b26bdea43f775951` passes 39, including road
job timing. These cover pools, machine budgets, scheduling isolation, live building
switching and profiler integration. The earlier broad 1,861-Python/4,117-Lua run
predates this rollback; it was not rerun or relabelled as current full coverage.

The native server used an immutable export of the combined commit. Preflight
verified 1,235 source files and 213 installed mod files plus five generated shader
hooks. Server port: 47624. BeamNG: 0.40.4.0.296339. Saved caches were reused;
this was not a cold-cache benchmark.

## Native result: loading observed, acceptance remains incomplete

- At Christchurch (-43.5312, 172.6366), 45 samples through 236.17 seconds showed
  no nearby road meshes or building tiles. Terrain imported and distant building
  parts reached 105. Settings: Advanced/Low, adaptive off, terrain detail x1,
  fixed requested view 20 km, ground photo **4096 px**, profiler off.
- The harness attempted numeric `1024` for the photo enum, which was rejected;
  the recorded actual setting is 4096. Do not compare this as a 1k-photo run.
- The user teleported to Auckland at 23:53:39 NZDT before the 240-second
  deadline. Thus the scripted assertion failed, but the full fixed-location
  deadline was interrupted. No controlled startup pass is claimed.
- A subsequent read-only observation during manual play recorded **two road
  tiles, one road mesh and two nearby building tiles**, plus 33 distant building
  parts. This confirms real native road/building imports after the rollback.
- The captured server log contains **zero `Backpressure` occurrences**. Four
  original Christchurch jobs nevertheless reached the existing 300-second worker
  timeout and caused pool recycling. Their earlier stacks include building
  neighbourhood-context construction and entrance terrain sampling through
  parking protection/grading. These are investigation leads, not cost attribution
  from a controlled profile.

Quality handovers, resident Simple/Advanced replacement, driving/collision,
profiler UI interaction and FPS acceptance remain unverified. All four PRs remain
drafts. The user requested the active game be left running; settings and server
were left alone after that instruction.

Workspace evidence: `artifacts/admission-removal-20261102/verification.json`,
`native-acceptance.json`, `extended-observation.json`, `playtest-result.json`,
`native-server-snapshot.log` and `native-game-snapshot.log`. The earlier failed
gate-enabled run remains separately preserved under `artifacts/lean-buildings-20261102`.

Further performance auditing should measure repeated neighbourhood construction
and parking-patch preparation on isolated fixtures before proposing changes.
Do not raise the timeout or add a larger shared budget as a substitute for this work.
