# Accepted-plan reuse in distant building products — source continuation

This continuation follows `p3-deep-middle-checkpoint`. It is editable source,
now bundled in the schema 23 r6 private playtest. The tracker is at 16 of its
28-row target. P3's common close/middle/distant representation implementation row
is complete; native visual, transition, import and memory acceptance remains open.

## Implemented: far building tiles

After both accepted-plan and physical products publish successfully, near content
reports a detached `{key, revision}` reference in its internal worker result.
Lite-to-full refinement reports the same reference. The reference is not a native
shape path or a new building identity. It selects the existing versioned global
geotile plan product, whose dependencies include source, geographic frame,
generator/schema, terrain and street/access/material revisions.

`products.load_accepted` checks the requested revision, product dependency key,
geographic frame and sector identity, current generator, watched input files,
physical revision and detached building/height records. Missing, corrupt, stale,
malformed or wrong-sector products are normal misses. Source revisions and frames
cannot be silently substituted. Geometry still uses the product store's complete
typed decoding and checksum checks.

The far-building worker compiles the exact accepted immutable items into the
middle representation. It does not rerun building inference, terrain/access
fitting, door planning, collision generation or the combined tile pipeline.
Existing street-light generation remains separate and reads only road records.
If an accepted product is unavailable, the existing cold far-generation path
still supplies coverage. Cold and accepted representations have separate cache
identities. Accepted revisions publish distinct shape **and metadata** paths,
preserving previously published bytes and avoiding concurrent metadata aliases.

The road tracker retains at most 2,048 compact references beyond near residency.
They do not keep native files, engine instances or whole plans in memory; cache
eviction remains allowed and leads to a cold fallback. A newer near result without
a usable product clears its old reference. Connection far builders consult the
current accepted reference, and the server's existing memo distinguishes plan
revisions.

When a near result completes, an already sent or in-flight far tile receives one
latest desired refresh. The existing far tracker/pool/admission limits schedule
missing coverage first, then refreshes. No drop is sent to prepare a refresh.
The existing client far replacement retains its previous complete mesh through
import. Desired revisions coalesce, including reversal during a running job.
Failed jobs retain sent coverage and wait one second before retrying. Retirement,
stale futures and tracker closure cannot resurrect an obsolete tile. A rebase
retains the running global-grid job and sends its completion for the current
anchor. Repeated unchanged references do not rebuild or resend distant content.

These are source contracts, not measured native frame/contact behavior. The
experimental aggregate worker admission was removed after native loading stalls;
upstream process/cache budgets and scheduling remain in use.

## Verification at the preceding far-building checkpoint

The matching architecture run passes **641 Python tests across 69 modules**.
The separate streaming run passes **137 overlapping Python tests and 3,191 Lua
assertions**. Focused checks include byte-identical encoded middle geometry from
the accepted near plan, strict guards forbidding repeated planning/physics,
worker-cache restoration, distinct immutable revision paths, cold fallback,
wrong-frame/source/revision rejection, lifecycle supersession, failure, reversal,
rebase, unload/revisit and the production near-completion callback.

Six synthetic localhost protocol tests and eight graphics/coverage tests pass.
An initial graphics run blocked in Windows asyncio's sandboxed socket-pair setup;
the test process ended and was confirmed absent before the corrected run. An old
session hello fixture also timed out when invoked with v2 instead of its required
legacy-generator format. Corrected runs use localhost access and the expected
fixture format. Initial logs remain retained; neither issue is counted as a
passing check. Native BeamNG acceptance remains pending.

Sources and exact successful log hashes are retained at
`build/world-architecture-programme/p3-far-plan-checkpoint/manifest.json`.

## Skyline aggregates — implemented

`buildgen/distant.py` handles a mix of accepted and cold children within each
sixteen-sector skyline parent. Accepted products are source/frame/revision checked
one at a time. Their complete source-owned sectors are excluded **before** source
clipping/planning; ownership does not come from a clipped plan's centre. This also
preserves accepted omissions, such as a canopy replaced by station props, instead
of reintroducing it in fallback. A corrupt/missing child stays eligible for cold
generation. If required cold data is pending, no partial replacement publishes.

Accepted children compile in their original frames. The emitted vertices move
into the parent frame using the exact existing world transform; immutable plans
are not mutated/rebased. The tallest-first complete-building prefix remains
within the existing vertex bound while candidates arrive from different children.
An overflow changes the cutoff; it never slices a selected building. A weak-reference
test checks release of each decoded plan array before the next child loads.
Courtyard/roof geometry, UVs, colours and indices match independent per-child
production geometry and geodetic conversion; close plans and physics are unchanged.
Child street lights transform from their declared frames and share the parent's
existing 4,000-light cap with cold sectors. This is a count bound, not measured RSS.

Near completion refreshes a sent/in-flight parent through the same coalesced far
queue. Connection history supplies its bounded inventory of accepted references.
Server memoization distinguishes those inventories. Actual output metadata names
only the accepted subset read, with its physical revisions. Publication identity
also includes unresolved file dependencies and actual geometry/light output, and
uses distinct immutable metadata/shape paths. Hybrid outputs use the session memo;
they are deliberately not stored in the old source-only revisit slot. A fallback
cannot poison a future all-accepted lookup. This does not claim a new optimized
persistent hybrid cache. An attempted target that safely falls back is acknowledged
for scheduling, preventing a bad child cache from causing a continuous refresh loop;
a new near revision still triggers a new target.

Current verification passes **656 Python tests across 70 modules**, plus **152
overlapping streaming Python tests and 3,191 Lua assertions**. Six protocol and
eight graphics/coverage tests pass separately. Thirteen skyline tests cover fully
accepted and mixed parents, exclusions before planning, corrupt children, pending
sources, immutable publication, frame conversion, sequential product release,
order-independent complete-building budgets, lamp bounds, source dependencies,
small distant visibility choices and server memo refresh. Lifecycle tests also
exercise the production parent notification and safe fallback acknowledgement.

The reviewed production three-tier sheet is
`build/world-architecture-programme/p3-accepted-representations-r2/representations.png`.
Its Japanese joined gable and Korean flared hip use forced supported inferred
options; mapped roof evidence still overrides priors in production. The Sahel
fixture has a supplied courtyard; no style-generated void is invented. This
offline render approximates colours and clips subsurface skirts only for display.
Native grazing-angle, roof, night-texture and LOD transition review remains required.
Exact source/log/shape hashes are retained at
`build/world-architecture-programme/p3-sky-plan-checkpoint/manifest.json`.
