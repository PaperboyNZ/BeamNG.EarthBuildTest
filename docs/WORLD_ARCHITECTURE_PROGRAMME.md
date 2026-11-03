# World architecture and roof repair — private playtest r6

The new r6 private playtest freezes schema 23, including the source work after
r5: accepted-plan reuse across near/middle/far/skyline products, retained-coverage
refreshes, deep middle-tier openings, cost-aware progressive imports, bounded
physical sector handovers and immutable live site records. The explicit shared
ground-court pilot is bundled but disabled in the normal launcher. It supports
one-sector source-linked courts; broader shared ownership remains unfinished.
The architecture suite passes 675 tests across 72 modules. Native acceptance
remains pending; this is not a release candidate. The original checklist target
remains 16/28 implemented rows. Earlier checkpoints below remain historical.

The activated private r5 playtest uses schema 22: 617 tests across 66 frozen
modules, 112 overlapping streaming Python tests, 719 Lua assertions, matching
archive/extracted hashes and an isolated offline startup handshake passed.
Native acceptance remains pending. The matching source includes joined-wing roof
massing and the corrected close-tier recessed generic windows. The intermediate
r4 playtest is retained as a historical checkpoint.

Roof investigation found that real building polygons were rejected by an exact
rectangle check. In Auckland and Luganville, none of 456 nearby pitched building
fixtures received exterior eaves. Eaves now follow actual polygon outlines,
preserve courtyard holes and include closed fascia and downward-facing soffits.
Imagery roof outlines retain their source extent while compatible walls inset.
Ten saved real-source outlines supplement the synthetic regression cases.
Investigation: parent `artifacts/roof-overhang-investigation-20261102`.

Geographic dwelling structure is selected independently of the earlier cladding
mixture. The 26 structural families cover all 64 regions, with stable alternative
room-bay arrangements, deep enclosed galleries/recesses, privacy apertures,
lattices, breeze screens, framed elevations and appropriate inferred roof forms.
Mapped footprint, courtyard holes, height, roof evidence and accepted access win.
The generator does not claim to know interiors or invent courtyard voids from a
style prior. Catalogue sources and scope are recorded in
`server/buildgen/catalog/residential_structures.json`. Production geometry review
sheets are under `build/world-architecture-programme`; these are offline renders,
not game captures.

The schema 22 continuation adds an unequal cross-gable roof composition for
compatible inferred Japanese/Korean residential options. Two room-wing ridge
fields form continuous valleys over the actual source footprint, with the mapped
total height retained. Observed roof shapes still override the style prior.

The checklist baseline contains 57 remaining rows; the target is about 28 completed
rows. `build/world-architecture-programme/programme.json` retains those original
rows so subsequent additions do not change the denominator.

Sixteen original rows are implemented so far. Their evidence is attached to the
tracker; the approximately-half target is still in progress.

The subsequent [physical resource continuation](PHYSICAL_RESOURCE_LIFETIME_PROGRESS.md)
adds negotiated sector manifests, session-qualified file references, delayed
collision-file retirement and occupied resource guards in editable source.
It now stages whole physical revisions hidden/noncolliding, retains accepted
coverage through import/rebuild failure, counts metadata owners separately and
claims road source folders across reconnects. Standalone skin/exact updates replace
only changed resources and preserve unchanged structure/props, including merged,
reversed and failed requests. Two concurrent physical transactions share the
existing import governor and wait for deletion debt to drain. Verification passes
112 streaming Python tests, 1,724 Lua assertions and six focused protocol tests.
This completes the M2 sector/lifetime implementation row. Shared-site ownership,
oversized-sector admission and native memory/contact gates remain open. These
changes are not in the r5 build.

Implemented checklist foundations:

- P1: independent persisted accepted plans, physical products and visual products.
  Safe typed storage, checksums, atomic writes, source-file dependencies,
  generator/material/schema identities, bounded quota and producer coalescing.
  An offline real Auckland tile built in 27.4 seconds; its visual-only full upgrade
  took 0.46 seconds. Upgrade tests forbid combined planning, terrain fitting,
  access and collision regeneration. Physical hashes and native shape bytes match.
  This measures worker work and publication, not game import or driving FPS.
- P4: typed mesh streams, bounded component batches and cached oriented templates.
  The retained seven-repeat cold/warm report checks exact native byte parity for
  512 regional representations. Complete resolved worker cost includes near/lite,
  collision, encoding and writes; source fetching and terrain/access fitting are
  excluded. Tower/fallback medians improve substantially; small cases show little
  gain and some regress slightly. Encoding still dominates peak memory.
- M2 dependency-cache row: the same product store tests missing/corrupt/incompatible
  storage, quota eviction, failed atomic writes, equivalent producers, cancellation
  and dead-producer recovery. This does not close the wider physical-lifetime gate.

Further implementation currently under verification:

- The schema 22 generic close tier retains every pane at its accepted recess
  depth, with four closed bevelled surround faces replacing repeated trim/sills
  on shallow upper apertures. Street rows and deep/structural openings keep their
  original construction. The 49-floor case drops from 107,426 to 46,514 vertices,
  courtyard 48-floor from 141,340 to 61,852, and complex 49-floor from 102,312 to
  44,784. The remaining 2.1x near cost at 48/49 floors is explained by 1,764 versus
  193 accepted apertures, all retained. Middle geometry is much cheaper. Collision
  is unchanged. Native import costs remain pending. The intermediate r4 trial's
  flat upper panes are superseded by this close-detail correction in source.
- City middle-distance facades replace repeated wall fragments with an opaque
  backing while retaining pane rows, piers and floor bands. The 80-floor glass
  case retains the exact pane UV/light pattern with less than 60% of close vertices.
- Middle-distance generic facades now retain recesses at least 0.30 m deep,
  including privacy slots without a gallery/screen assembly. They cut the wall,
  retain the accepted pane depth and add four closed plain returns; shallow
  openings still use cheap overlays. Deep arches retain returns with a cheaper
  curve. The 26-family encoded review retains 128 such openings; affected
  Maghreb/Sahel examples use 314/394 middle vertices versus 662/1,062 close.
  Collision and pane UV/colour remain unchanged. Review and source evidence are
  in `p3-deep-middle-checkpoint/manifest.json` and `p3-deep-middle-review-r2`.
  Verification passes 624 Python tests across 67 modules, plus a separate run of
  119 overlapping Python tests and 3,191 Lua assertions. One initial module-load
  error was corrected by supplying the required server import path; its three
  tests pass on rerun. At that checkpoint common accepted-plan reuse and native
  LOD transition/grazing-angle acceptance remained open. The later integration
  below completes the shared-plan implementation; native acceptance stays open.
- [Far plan reuse](DISTANT_PLAN_REUSE_PROGRESS.md) now compiles far building
  tiles directly from accepted near plans, with revision-qualified paths, cold
  fallback, bounded reference history and coalesced retained-coverage refreshes.
  The matching run passes 641 Python tests across 69 modules, plus 137 overlapping
  streaming Python tests and 3,191 Lua assertions; six protocol and eight graphics/
  coverage tests pass separately. This describes the preceding far-building slice.
- Skyline aggregates now mix accepted and cold child sectors, excluding accepted
  source owners before planning. They load one cached plan at a time and transform
  only emitted geometry into the parent frame. Complete-building selection and
  the parent's 4,000-light cap remain bounded; pending cold data publishes no
  partial replacement. Corrupt/missing child products use diagnosed fallback and
  cannot claim an all-accepted revision. Parent refreshes use the existing queue,
  retained coverage and compact reference inventory. The P3 common-plan row is
  now implemented: close, middle and distant outputs reuse the accepted immutable
  plan, with provisional cold coverage until it becomes available. Verification
  passes 656 Python tests across 70 modules, 152 overlapping streaming Python tests,
  3,191 Lua assertions, six protocol and eight graphics/coverage tests. Production
  three-tier meshes and a reviewed four-region sheet are retained in
  `p3-accepted-representations-r2`; exact source/log evidence is in
  `p3-sky-plan-checkpoint/manifest.json`. These remain source changes after r5;
  native transitions, night textures, import timing and memory calibration stay open.
- Progressive client prioritizes missing coverage, then approaching-camera benefit
  per import cost using bytes, vertices, primitives and observed durations. Imports
  retain the existing shared frame cap, collision priority and complete replacement.
  Chunk prices now enter the existing frame governor; waiting expensive chunks
  can accumulate its tokens. Five-second fairness applies within a coverage class.
  Wall-clock import/queue percentiles retain 256 samples, with aggregate visible
  coverage latency and hidden wasted-work counters. The matching regression run
  passes 112 Python tests and 3,191 Lua assertions, including 1,015 pricing/saturation
  assertions. These are deterministic engine-model results, not measured native
  imports or frame times. See `p6-priced-import-checkpoint/manifest.json` under the
  programme artifacts. The P6 route/native measurement row remains open.
- Projected facade demand uses the existing pose camera FOV/resolution, travel
  speed and hysteresis. A free camera can demand detail independently of the car.
- The experimental shared aggregate admission gate was removed after it starved
  idle road workers when distant jobs held queued reservations. Worker scheduling
  again follows upstream; existing process/cache budgets, low-priority queues,
  cancellation and recycling remain. A replacement aggregate scheduler is deferred
  until it has measured costs and demonstrated fairness under native loading.
- The offline exact-vertex experiment writes new content-addressed candidates
  after normals/tangents are finalized. Every triangle-corner record and primitive
  is retained, including hard edges, both UV sets and colours. Extra rewrite work
  was approximately 6–30 ms for 1–12% smaller files in this run. Production stays
  disabled without demonstrated native import/rendering benefit.

The feed/evidence path now retains presence masks beside existing boolean arrays.
Fresh false observations remain false; missing values remain unknown. Legacy
caches that discarded nullability keep their old rendering behavior and record
false values as unknown evidence. No forced worldwide cache download is required.
Both flags are documented by the [Overture building schema](https://docs.overturemaps.org/schema/reference/buildings/building/).
No construction-era or specialist-part role is inferred from these flags; wider
M1 station/shared-site integration remains open.

The subsequent schema 23 source continuation moves validated one-owner catalogue
sites through the immutable M1 records in the live fitting path. Exact accepted
solids and near/middle/collision mesh parity are preserved; frozen worker and
typed-cache round trips retain the records. Unsupported shared resources and
unvalidated interfaces cannot dispatch through the compatibility adapter. This
foundation passes 663 Python tests across 71 architecture modules. See
[runtime site-record migration](SITE_RECORD_RUNTIME_PROGRESS.md); the M1 shared
fitting/emission row stays open, and the completed target count remains 16/28.
The r6 playtest now includes this continuation at schema 23; r5 is retained.

The isolated native process has ended with its log still at BeamNG's existing
third-party DLL warning; the exit cause is unknown. Approval to press OK on
relaunch remains pending, keeping future warnings enabled. No claim of native
roof, lighting, collision-contact or performance acceptance is made.
