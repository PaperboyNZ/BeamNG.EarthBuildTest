# Integrated building and site implementation checklist

Current regional detail authoring: [25 architectural modifiers and spawn rates](REGIONAL_ARCHITECTURAL_MODIFIERS.md).

Current roof authoring: [roof proportions, attic windows and dormers](ROOF_PROPORTIONS_AND_ATTICS.md). Shared inference limits apply across all 64 regional profiles and five contemporary families; tall eligible roofs receive fitted attic details. Historical checkpoint statements below retain their original scope.

Reviewed against `BeamNG.EarthBuildTest` on 2 November 2026. This is the execution
index for the [commercial brief](COMMERCIAL_GENERATION_OVERHAUL_PROMPT.md),
[pavement plan](PAVEMENT_AND_SITE_ACCESS_PLAN.md) and
[specialist plans](SPECIALIZED_BUILDING_IMPLEMENTATION_PLANS.md). Their detailed
geometry and evidence requirements still apply. Checked tasks below mean the
specific task is implemented; they do not imply that a whole milestone passed.

## Source continuation — schema 22, 2 November 2026

Roof polygon eaves and geographic dwelling structures are implemented in editable
source. P1/P4 product and emission work is verified, with further representation
and scheduling work in progress. See [programme status](WORLD_ARCHITECTURE_PROGRAMME.md)
for retained evidence and limitations. The root launcher selects private schema
22 r5 (617 frozen Python tests and 719 Lua assertions passed), including joined-wing
roofs and retained close-tier recesses. Native acceptance remains open.

## Previous consolidated playtest — schema 20, 2 November 2026

`BeamNG.Earth-v2-consolidated-r3-20261102` consolidates the previous integrated
streetscape package with the 16-color expansion for all 64 regional themes,
seeded surface weathering, whole-assembly lamp fixes, furniture relocation and
spatial progressive building coverage. See [playtest instructions](INTEGRATED_PLAYTEST.md)
and [investigation, limitations and next work](ROADSIDE_STREAMING_WEATHERING.md).
The parent `CURRENT_PLAYTEST.json` records the activated build and exact gates.
Native visual/performance acceptance remains pending. Separate generation
revisions still swap atomically; enabling the completed shape's static renderer
path does not establish a general revision-dithering implementation.

Next: native acceptance/profiling, then P1 persistent plan/product separation
and P4 typed encoding; use measurements to calibrate P6 and guide P2/P3.
The earlier package descriptions below are historical.

## Previous house-variety playtest — schema 19, 1 November 2026

`BeamNG.Earth-v2-house-variety-20261101` is selected by the parent
`Play latest buildings.bat` at that checkpoint. Eligible houses use stable 70% regional / 20%
contemporary / 10% other-global styling. Five shared contemporary families
(earlier suburban mix, timber, brick, rendered, mixed infill) reuse existing
materials; broader fallback roof/paint colours retain sampled/mapped precedence.
See [house-style implementation](HOUSE_STYLE_MIX.md) and
[playtest instructions](HOUSE_VARIETY_PLAYTEST.md).

This package adds the house changes to the verified schema 18 checkpoint below.
Concurrent driveway/roadside changes are preserved in editable source and excluded
pending their own validation. Exact overlays and base are recorded in
`build/house-variety-playtest-r2/provenance.json`.

Verification: 727 Python tests passed, one skipped across 62 modules; separate
streaming checks passed 102 overlapping Python tests and 708 Lua assertions.
Frozen/package geometry matches the previous fixture groups plus 24 mixed houses.
Archive hashes, dependencies and isolated offline startup negotiation pass.
See parent `artifacts/BeamNG.Earth-v2-house-variety-20261101-verification.json`.
Native visual/performance acceptance remains pending; facade baking is disabled.

## Previous integrated playtest — schema 18, 1 November 2026

`BeamNG.Earth-v2-schema18-integrated-20261101` was selected by the parent
`Play latest buildings.bat` and `CURRENT_PLAYTEST.json`. It contains the
city buildings, regional blocks, preset variation, component reuse, geometry
encoding optimizations and adaptive streaming changes. Experimental facade baking
and reduced-shadow modes remain disabled; the subsequent architectural proposals
have not been implemented. The earlier schema 16 checkpoint below is historical.

The frozen checkpoint is `build/schema18-playtest/checkpoint`. Verification:
719 Python tests passed and one skipped across 61 modules (the skip requires a
standalone LuaJIT executable); the separate streaming runner passed 102 Python
tests, overlapping the broad run, and 708 Lua assertions via bundled LuaJIT/Lupa.
Package/source geometry matches for 12 architecture, nine access, nine city,
four frontage, six terrain, 64 regional and 192 block fixtures. Archive/extracted
file hashes, dependencies and isolated offline server capability negotiation pass.
See the parent `artifacts/BeamNG.Earth-v2-schema18-integrated-20261101-verification.json`
and [performance playtest instructions](SCHEMA18_PLAYTEST.md).

Native game performance, appearance, driving and occupied streaming acceptance
remain pending. The previous dated packages are retained. Runtime source/mod files
were frozen together; this status entry was added after package verification.

## City architecture first slice — schema 18

- [x] Compile all 64 city regional briefs from descriptive/geographic text only,
  independently of existing regional style parameters.
- [x] Add frozen city programme/run descriptors and five bounded tall-office/hotel
  facade compositions, reusing current access, pavement and landscape planners.
- [x] Refit city runs after street/sidewalk clipping; preserve surviving party
  walls, collision/access geometry, courtyard holes and progressive chunking.
- [x] Verify 508 tests across 38 relevant modules and inspect the nine-case
  geometry review. Existing low-office control fingerprints remain unchanged.
- [ ] Finish dedicated city materials, roof/entrance assemblies, shared arrival
  spaces and mapped podium integration, then packaged/native-game acceptance.

See [city implementation status](CITY_BUILDINGS_IMPLEMENTATION_STATUS.md).
The source changes above are included in the current schema 18 playtest. The
older regional playable checkpoint below predates this slice.

## Building performance architecture tasks — 1 November 2026

These tasks follow the architectural review of the editable source, ahead of the
default playable checkpoint. Extend the existing progressive loading, immutable
plans, roof/component caches, reduced LODs, speed-aware refinement and import
limits; those foundations are already present. Completion and retained evidence
for the current continuation are recorded below and in the programme status.
Integrate scheduling and cache changes with M1/M2 and measurement with M0/M8;
do not create a separate resource governor or bypass physical-lifecycle gates.

The review's short warm synthetic measurements found 22,174 detailed vertices
and approximately 25 ms compilation for the 48-floor regional apartment versus
107,426 vertices and approximately 101 ms for its 49-floor fallback. The 80-floor
glass tower retained 5,270 of 5,574 vertices in lite mode. Component stamping and
list-to-array conversion accounted for roughly 45% of a mixed synthetic generation
profile that included the expensive fallback. These are diagnostic observations,
not release baselines or FPS claims: planning, downloads, disk publication and
native rendering were excluded. Capture reproducible source hashes and full-pipeline
baselines before implementation. Existing evidence and experiments are described
in [building cost optimization](BUILDING_COST_OPTIMIZATION.md) and
[progressive buildings](PROGRESSIVE_BUILDINGS.md); their older timings must not be
treated as measurements of every subsequent source revision.

### P1 — independent building refinement products (M1/M2)

- [x] Separate resolved building/site plans, physical surfaces/collision and
  visual representations into independently reusable products. On a full-quality
  cache miss, a lite-to-full upgrade must reuse the accepted plan instead of
  rerunning the combined road-content `_tile_parts` pipeline.
- [x] Define product dependency identities covering source revisions, terrain,
  street clearance, access, materials and generator versions. Use the canonical
  identity contract; do not promote tile-local coordinates to persistent identity.
- [x] Cache and schedule visual refinements independently, coalesce equivalent
  requests and publish only changed building visuals. Preserve essential road,
  access and collision resources through stale results, cancellation and failure.
- [x] Verify identical appearance/physics for equivalent inputs, reduced repeated
  planning and physical generation, bounded cache storage and faster upgrades.
  Entry points: `server/blockworker.py`, `server/roads.py`, `buildgen/plan.py`.

### P2 — bounded representation cost across fallback paths (M4/M8)

- [ ] Add complexity fixtures around generator eligibility boundaries, including
  48/49 floors, courtyard/complex outlines and specialist exclusions; record
  vertices, triangles, materials, generation time and import cost.
- [x] Give generic and unsupported-style fallbacks bounded-cost representations.
  Preserve footprint, height, roof silhouette, window positions and floor rhythm;
  represent repeated shallow detail more cheaply where its depth is imperceptible.
  Retain nearby entrances, deep recesses, balconies and silhouette features as
  geometry. Do not merely raise the regional floor limit or remove windows.
- [ ] Verify that crossing an eligibility boundary does not cause an unexplained
  complexity spike or alter access/collision. Establish calibrated budgets with
  diagnosed representation choices, without truncating mapped building members.
  Entry points: `buildgen/regional_blocks.py`, `buildgen/facades.py`.

### P3 — projected-size detail and a cheaper middle representation (M4/M8)

- [x] Derive close, middle and distant representations from the same resolved
  architectural plan. The middle tier retains facade pattern, major recesses,
  roofs and access surfaces while replacing shallow construction detail cheaply.
- [x] Use projected feature size, camera FOV/resolution and travel demand with
  hysteresis; support free-camera movement. Integrate with the existing scheduler
  and native LOD instead of adding an independent visibility controller.
- [ ] Make chunks spatially coherent and calibrate LOD bounds/transitions without
  holes or partial-building disappearance. Retain shared conservative bounds
  where oversized building pieces must change LOD together.
- [ ] Demonstrate meaningful middle-tier simplification for tall glass buildings
  as well as ordinary houses, with matching window/light patterns and acceptable
  grazing-angle transitions. Entry points: `buildgen/city.py`, `buildings.py`.

### P4 — batched typed/native geometry emission (M4/M8)

- [x] Build on the existing component-template caches: batch transforms and
  stamping for many components into preallocated typed buffers or the existing
  native module, avoiding per-component Python expansion and final list copies.
  Keep architectural decisions in Python and use substantial numeric batches.
- [x] Preserve dimensions and output semantics without quantization. Compare
  positions, UVs, normals, tangent handedness, colours, winding and material
  assignments against the reference path; retain hard edges and texture seams.
- [x] Measure complete worker cost and peak memory on houses, towers, fallbacks
  and dense mixed tiles, including cold/warm template caches. Entry points:
  `buildgen/components.py`, `buildings.Mesh`, `native/earthfast`.

### P5 — fewer material submissions in middle/distant meshes (M4/M8)

- [ ] Record material primitives and actual native draw submissions alongside
  geometry counts. Lite retained each tested fixture's material count; the older
  240-house benchmark reduced material primitives only from 310 to 307.
- [ ] Prototype shared atlases for compatible middle/distant facade surfaces,
  retaining vertex tint and architectural variation. Preserve separate glass,
  emissive and other shading behavior where combining it would change appearance.
- [ ] Combine material consolidation with spatially compact batching; measure the
  tradeoff between object count, culling effectiveness and synchronous import cost.
  Bound atlas memory, bake work and mip padding; avoid unique textures per building.
- [ ] Validate day/night appearance, reflections, roof identity and oblique views;
  prove a native rendering benefit before rollout. Entry points: `server/cdae.py`,
  building material assets and the representation emitters.

### P6 — benefit- and cost-aware progressive work (M2/M8)

- [x] Replace fixed twelve-building work groups with bounded, spatially coherent
  groups informed by estimated generation/import cost, retaining complete-group
  replacement and stable group identities within a generation revision.
- [x] Prioritize missing nearby coverage and approaching-camera demand over
  arrival-order refinement. Coalesce stages and suppress intermediate publication
  unlikely to become visible before its successor; retain the last complete stage.
  Missing-coverage and nearest-tile priority, all-lite-first generation and
  retained cheap pending coverage are implemented in the 2 November pass.
  Approaching-camera demand and measured benefit/cost ordering are implemented
  in source; native cost calibration and route measurements remain open.
- [x] Supplement vertex limits with measured import time, bytes and material
  primitives. Retain the shared import cap, essential collision priority, far
  coverage, final-stage adoption and correct pooled-slot/resource retirement.
- [ ] Verify queue saturation, rapid movement/reversal, cancellation, failed
  imports and stale revisions. Measure time to visible coverage, wasted work and
  worst synchronous import. Entry points: `buildgen/progressive.py`, client
  `buildingprogress.lua` and `roads.lua`.

### Secondary experiment and common acceptance (M0/M8)

- [x] Evaluate native or idle-cache exact vertex deduplication after final normals
  and tangents. Preserve complete vertex records and first-use order; publish a
  new content identity rather than modifying a live shape. The existing 6–14%
  attribute-payload opportunity does not reduce triangles or material submissions;
  enable only if complete generation/import/memory measurements justify its cost.
- [ ] Record source/tool hashes and reproducible cold/warm route, dense-city,
  highway, teleport and refinement benchmarks on small-machine/desktop hardware.
  Measure upgrade latency, repeated work, queue age, CPU/GPU p50/p95/p99 frame
  times, worst imports, output coverage, peak memory and texture residency.
- [ ] Review close street views, grazing angles, night lighting, roofs, courtyards,
  access surfaces, rapid camera turns and LOD transitions. Retain source identity,
  visible architectural character and physical coverage; no noticeable quality
  loss or collision change may be hidden by aggregate performance improvements.
- [ ] Apply the existing M0/M8 acceptance gates to the matching integrated package;
  distinguish synthetic generation improvements from verified in-game gains.

Recommended implementation order: P1 and P4 first for output-preserving gains,
then P2/P3, followed by P5/P6 using native measurements to calibrate tradeoffs.
The secondary deduplication experiment follows the larger structural work.

## Historical checkpoint and next work — 1 November 2026

The regional update is `BeamNG.Earth-v2-regional-themes-balanced-20261101` (schema 16).
It adds 64 polygon-routed themes, personally audited trim and facade details,
and proportional window spacing. Existing street clearance, automatic commercial
frontages, stock planting and terrain transitions are retained.
Verification: **482 Python tests** pass in the relevant building and package suites.
Source/package geometry and offline startup results are recorded in the parent
`artifacts/BeamNG.Earth-v2-regional-themes-balanced-20261101-verification.json`; the active
launcher selection is recorded in parent `CURRENT_PLAYTEST.json`.
See [the regional playtest checklist](REGIONAL_THEMES_PLAYTEST.md).
Native BeamNG appearance, driving, streaming and performance acceptance is pending.

The continuation sections below record the implemented local slices. They do
not complete canonical shared-site ownership, the physical-resource lifecycle,
large complexes or fuel integration. Earlier schema/count/status paragraphs are
historical checkpoints; use this section for the current execution position.

Resume the unified programme in this order:

1. **M1 runtime ownership:** connect existing immutable site/interface/resource
   records to a bounded runtime adapter. Establish canonical producer/consumer
   identity and revisions; verify load order, rebases and partial membership.
2. **M2 resource limits and lifetime:** add aggregate admission/backpressure,
   bounded sector checkpoints and cancellation; retain occupied essential
   collision resources through replacement and retirement. Validate failures
   before admitting larger shared sites.
3. **M3/M5 shared circulation:** collect building, lot and station interfaces
   before fitting common surfaces; validate complete vehicle sweeps and receiving
   areas. Extend current local connectors to shared pedestrian/customer/service
   routes, then standalone lots and commercial courts with one physical owner.
4. **M5 fuel integration:** coordinate forecourt, pumps, stopping areas and
   refuelling triggers from accepted heights before expanding station identities.
5. **M4/M6 architecture and the city expansion:** continue repeated roofs,
   supported specialist parts and city families after their shared-site/lifetime
   prerequisites. All 64 ordinary regional themes are now active; city-specific
   interpretations use their written/geographic descriptions and require their
   own checks, without inheriting the existing defined styles.

Run M0/M8 game measurements and the garage driving checks alongside this work.
They remain required for release acceptance, but do not prevent implementing and
testing the next bounded runtime foundation. No new architecture family or
multi-level topology is the immediate next task.

The [city buildings implementation plan](CITY_BUILDINGS_IMPLEMENTATION_PLAN.md)
extends this sequence for skyscrapers, offices and hotels. Its target baseline
assumes completion of the ongoing pavement, landscaping and shared-site work,
as requested by the user. It includes connected arrival spaces and planting,
reconciles the finished interfaces before implementation, and retains this
checklist's physical-lifecycle and performance gates. The city expansion is
partially implemented; the city status section identifies the completed slice.

Its [64 regional city briefs](CITY_REGIONAL_DESIGN_BRIEFS.md) cover every existing
regional ID and include relevant facade, material, entrance, paving and landscape
directions. Per the user's clarification, these are text-derived proposals;
compiled regional profiles and their numeric/style recipes are not the city
authoring source. Geographic identity and source-evidence precedence are reused.

## Regional diversity source continuation — schema 16

- [x] Add 14 bounded facade grammars, grouped and deep openings, material
  zones, and arched/segmental aperture masks with a 32-arch per-building cap.
- [x] Add five optional roof profiles: gambrel, mansard, saltbox, shed and
  broad-eave. These apply to compatible rectangular pitched footprints and
  otherwise fall back to existing roof geometry.
- [x] Preserve mapped footprint, height, roof and appearance evidence; regional
  material zones are fallback-only. Recessed panels are visual composition,
  not walkable verandas or invented courtyards.
- [x] Verify the matching schema 16 regional package and frozen-checkpoint consistency (balanced-window verification report).
- [ ] Validate native BeamNG appearance, driving, streaming and performance.

The older checkpoint and test results below are historical; they do not establish
package or native-game acceptance for this source continuation.

## Active regional architecture — 1 November 2026

- [x] Activate all 64 regional profiles with bundled country/province/locality polygons.
- [x] Have three Terra agents inspect online architectural photographs and author individual palettes, roof/window rules and facade details.
- [x] Preserve mapped evidence, explicit overlay priority, stable source identity, detail budgets and shared near/far/collision contracts.
- [x] Check all 64 routing examples, generated mesh fingerprints and regional regressions.
- [ ] Native BeamNG global visual/driving/performance acceptance; additional local variants and specialized heritage geometry.

See [runtime behavior and all photographic references](REGIONAL_THEME_RUNTIME.md).

## Review findings and decisions

| Gap or conflict | Decision / required closure |
| --- | --- |
| Frame-time gates disagree: specialist plan retains 5% p95, commercial brief permits 10% p95/p99. | Use the stricter **5% total steady-driving p95** gate; p99 must stay within 10%. Worker generation and collision p95 retain their separate 10% gates. Architecture contribution targets 1 ms p95 within the shared governor. Record synchronous outliers and no new repeatable architecture stall above 50 ms. All require fixed hardware, route and equivalent coverage. |
| Eight sectors is a total-site bound in pavement/specialist text but an admission bound in the commercial brief. | Eight is the **maximum newly admitted sectors per complex at a time**, further constrained by the global queue. Larger evidenced sites require incremental partitioning and compact deferred descriptors. Until that scheduler exists, decline optional oversized layouts explicitly; never truncate mapped members. |
| `SitePlan` and `ComplexPlan`, `SiteEvidence` and `ComplexEvidence` overlap. | Use one site/complex aggregate in `sitegen`, with separate evidence and resolved-plan records. A complex is a site with memberships, not a second planning engine. Buildings/parking/stations remain adapters and emitters. Final names are chosen in M1. |
| Cross-tile canonical identity is a prerequisite, not a field that can be populated from current tile XY. | Specify source namespace/revision, deterministic frame anchor, units, horizontal/vertical datums, longitude wrap, quantization and boundary ownership before persistent caching. Test geodetic rebases, ring rotation/winding and reversed load order. Never hash raw tile-local arrays as persistent identity. |
| Old site catalogue rejects every overlapping property and requires complete exclusions; new model permits overlapping levels/associations. | Keep legacy validation intact through an explicit one-owner adapter. New schema distinguishes association extent from physical occupancy and unknown from empty exclusions. Add cycle, duplicate-producer, partial-member and same-level surface-conflict tests before enabling new inputs. Do not merely loosen old validation. |
| Door/site planning order can emit contradictory access and landscape choices. | Coordinator collects proposals, reserves essential routes, fits surfaces/levels and commits interfaces atomically; only then fit parking, markings, fences and planting. Maximum four layouts and three total coordination passes per sector. |
| Independent crossing acceptance requires information not measured today. | Track eligibility, segment rejections, final drive outcomes and provisional crossing selection separately. A selected mouth with a failed driveway is an **untested receiving-area case**, not a validated crossing-only opportunity. Add receiving-area grading/clearance validation in M3. |
| Specialist dispatch relies on name keywords; freight/passenger terminals and false-positive shops/hotels overlap. | Preserve baseline dispatch for now. Add evidence/capability adapters with auditable fallback reasons, then change dispatch. Freight belongs to commercial/industrial; petrol stays in `gasstations.py`. Ordinary office fallback cannot silently replace unsupported specialist topology. |
| Source attributes required for era, parts, levels and transport use are not all retained by `evidence.ATTRIBUTE_FIELDS`. | Audit feed → cached features → normalized evidence → planner → worker for each new field. Unknown data stays unknown; a style prior is not observed construction history. Do not activate unverified regional packs. |
| Progressive visual shells and collider lifetime are not yet safe for complex passages and shared decks. | M2 must establish capability negotiation, topology-safe proxies, producer ownership/reference lifetime, stale-result rejection and occupied-resource pinning before M7 expands playable topology. Decorations cannot trigger physical rebuilds. |
| Proposed budgets do not define measured memory/import readiness or engine capabilities. | Baseline each stage separately; calibrate aggregate limits on a small machine and desktop. Use oversized synthetic workloads early. Offline compile timing does not establish driving, collision activation, tyre contact or refuelling acceptance. |
| Church ticket 1 wording also claims the three-family visual slice; fuel first slice depends on shared surfaces listed in a later ticket. | Separate specialist adapter parity from visual-family acceptance. Build shared surfaces first, then fuel surface/trigger parity, then identity expansion. Garage circulation and fuel function precede decorative expansion. |
| Current recovery/playtest instructions point at several historical packages; this source has no Git metadata. | Modify this source snapshot, preserve original touched files, record content hashes and exact commands. Do not restore the old bundle over it. Package only matching server/mod/assets after integrated gates. |

Regional dimension references in the original plans have **not** been reverified
in this code review. Retrieve their current applicable primary drawings before
authoring those profiles; this first slice changes no dimensional defaults.

## Dependency order and acceptance

### M0 — baseline and diagnostics (started)

- [x] Audit current schema (12), dispatch, immutable boundary, site catalogue,
  source identity, access ordering and available local test environment.
- [x] Preserve the touched runtime files under `build/overhaul-baseline/original`.
- [x] Capture the existing nine-building commercial sheet and synthetic timings.
- [x] Add optional bounded aggregate driveway diagnostics without storing them in
  compilation plans or changing geometry decisions.
- [x] Deliver reproducible architecture/access fixtures with source/tool hashes,
  cold-process versus warm measurements, mesh fingerprints and a review sheet.
- [x] Verify diagnostics parity and relevant regression suites; record skips and
  environmental failures independently.
- [ ] Capture real-map selection/evidence distributions, fixed-camera specialist
  references, game import/collision timings, memory and repeatable driving routes.

**Gate:** automated baseline may proceed independently; M0 remains incomplete
until real-data and game measurements exist. No performance-release claim from
synthetic results. M1 runtime integration and M2 remain the next shared-system
dependencies; completed bounded local extensions are recorded below.

### M1 — common records, identity and compatibility

- [x] Specify canonical frame/identity and dependency revision contracts.
- [x] Implement immutable site evidence/membership/interface/resource records;
  deterministic serialization and detached worker round trips.
- [x] Adapt validated existing one-owner sites with identical reconstruction;
  export optional versioned records from the existing offline validator.
- [x] Represent standalone lots, mixed uses, nested acyclic associations and level
  intervals; reject cycles, duplicate producers and missing referenced resources.
- [ ] Integrate those records into runtime shared-site fitting and emission.
  The schema 23 source continuation routes validated one-owner catalogue sites
  through immutable records and the existing fitter with exact mesh parity.
  A bounded canonical shared-ground-court pilot now fits/emits one-sector sites;
  broader shared fitting, cross-sector references and native acceptance remain open. See
  [runtime site-record migration](SITE_RECORD_RUNTIME_PROGRESS.md).
- [x] Establish record-level one-producer rules and explicit consumers/retention;
  station owns pumps/triggers, shared site owns common circulation.
- [x] Add specialist selection/capability diagnostics and a parity-tested legacy
  dispatch adapter, recording unsupported topology and classification ambiguity.
- [ ] Connect verified feed fields, specialist part roles and live station records.
- [x] Carry the already fetched numeric floor/level labels through cached features,
  ordinary/part evidence and frozen worker plans. Keep them separate from physical
  elevations; nullable boolean provenance and construction-era fields remain open.
- [x] Include `sitegen` code/profile data in source signatures and packaging
  configuration. Garage access introduced schema 13; church/terminal plans now
  advance building plan serialization to schema 14.
- [x] Verify the current local runtime package, source/mod/data hashes,
  dependencies, synthetic geometry and server capability handshake.
- [ ] Verify canonical shared-site cross-tile emission, residency and station
  identity through the live pipeline.

**Gate:** legacy parity, ordering/rebase determinism, no duplicate producer or
lost station identity; incomplete evidence cannot masquerade as free space.

### M2 — bounded resources and physical lifecycle

- [x] Cancel optional building previews on rebase, distant retirement, failure and
  disconnect; preserve essential final geometry and reject stale token completion.
- [x] Bound and validate preview manifests before delivery; test cancellation,
  malformed/oversized metadata and unchanged final geometry.
- [x] Extend existing worker/budget infrastructure with aggregate admission,
  backpressure, cancellation tokens and bounded stage/sector checkpoints.
- [x] Add versioned dependency cache with atomic/checksummed writes, quota,
  coalescing and stale-producer recovery; distinguish fetch failure from absence.
- [x] Introduce sector manifests and client capability negotiation; preserve
  physical routes through refinement, retention and delayed engine-debt accounting.
- [ ] Test oversized complexes, slow/dead workers, full/corrupt caches, obsolete
  revisions, unload/revisit, queue saturation and occupied collision resources.

**Gate:** bounded global work and memory; essential existing physical state stays
valid under failure. Do this before generating many new families or large sites.

### M3 — shared access and pavement foundation

- [x] Reuse exact terrain samples across current entrance/driveway/commercial/site
  passes with a bounded job-local cache; preserve unknown terrain and batch limits.
- [x] Coordinate optional groundcover against all accepted local physical surfaces,
  building footprints/holes, parking and garage aprons; preserve essential solids.
- [ ] Collect building/site/station portal proposals before committing geometry.
- [x] Rank at most four local routes from an existing eligible garage entrance;
  batch full-strip terrain checks and commit only an accepted route and curb cut.
  Preserve pedestrian ramps, controlled roads, exclusions and prior valid routes.
- [ ] Extend those proposals to mapped vehicle entrances and shared-site/station
  interfaces, with complete inventories and canonical runtime ownership.
- [ ] Validate independent crossing + receiving area, then full internal route;
  report `connected`, `crossing_only`, `pedestrian_only`, `rejected` separately.
- [x] Validate receiving slabs and full road connectors for bounded automatic
  commercial parking; retain matching sidewalk cuts and atomic previous results.
- [x] Fit local bed curb rings, shared frontage planes and bounded pedestrian
  stair/landing transitions; test rotated, translated and uneven terrain seams.
- [ ] Add tangent corner/flare tessellation, shared boundary samples, grade
  transitions and one physical contact owner per surface cell across shared sites.
- [ ] Reuse terrain batches and reservations in parking, planting and props;
  verify surface seams/holes, grades, tyre material and native collision contact.

**Gate:** 1 mm computational seam target, no unintended lip above 5 mm in collision
fixtures, bounded work, representative car traversal in BeamNG. Existing 18 m/15%
residential limits stay until measured rejection evidence justifies changes.

### M4 — first architecture releases

- [x] Derive bounded immutable elevation runs, grids, datums and fitted opening
  groups for existing church, terminal and commercial families; separate function,
  structure, era, vocabulary and condition seed channels with a legacy seed bridge.
- [ ] Extend programme allocation to mixed uses, tenants and mapped specialist
  parts/levels after shared physical lifecycle gates pass.
- [x] Implement bounded chapel/parish/modern church closed shells with fitted
  openings and source outline/height preservation; retain diagnosed unsupported
  assembly fallbacks. Add three decorated spire styles on a stable eligible subset,
  contained within the supplied footprint and total height; mapped roof height wins.
- [x] Implement strip-shop frontage and punched, ribbon and curtain office
  compositions beside existing trade units/supermarkets in a six-building sheet.
  These are material-compatible style priors; construction era remains unknown.
- [x] Add conservative regional airport hall and linear-concourse facade adapters
  with different public/service compositions; name-only terminals stay ordinary.
- [ ] Complete real-reference recognition, native texture/lighting, grounded
  approach and performance/streaming acceptance for the first architecture slice.
- [ ] Add verified era evidence and source-field lineage before calling the office
  styles observed historic/mid-century/contemporary architecture.
- [x] Add fitted commercial piers, roof-edge trim, spandrels and window transoms
  aligned to accepted openings and datums, with bounded component counts.
- [ ] Add repeated roofs, further trim/material assets and coherent history/wear after
  fitted geometry passes. Whole-envelope projections and collision remain aligned.

**Gate:** at least three compositions, three footprints and three stable seeds
per applicable family; sparse/constrained cases and observed references; unlabelled
street/roof recognition, topology-safe LOD and equal-workload regression budgets.

### M5 — shared commercial sites and functional integration

- [ ] Fit customer/service/pedestrian circulation before parking, using validated
  full-vehicle sweeps; preserve source holes and vertical separation.
- [ ] Deliver standalone lots, supermarket, retail park, outdoor mall and industrial
  court, with explicit common resources and level-aware membership.
- [x] Integrate a conservative garage road portal, physical apron, aisle and edge
  ramps into one frozen plan; verify source holes, vehicle sweeps, eased grades,
  headroom and matching near/lite/collision geometry in synthetic fixtures.
- [ ] Validate garage tyre contact and every advertised deck in BeamNG, including
  entry and exit, representative vehicles and occupied streaming transitions.
- [ ] Integrate fuel pavement, pumps, stopping zones and triggers from the same
  accepted heights; suppress mapped canopies only after replacement is ready.
- [ ] Add regional paint/accessibility profiles, complete access aisles and
  pedestrian links; only mark routes that passed fitting.

**Gate:** shared resources emit once across load order/rebase/partial residency;
all accepted pumps refuel and playable garage routes work in design/check vehicles.

### M6 — broader identity and evidenced assemblies

- [ ] Garage concrete/masonry/screen facades; compact/neighbourhood fuel layouts
  and three coherent reviewed pilot identities, followed by further regional packs.
- [ ] Mapped church aisles/transepts/towers; main terminal halls and linked parts;
  commercial long-span roofs and supported part-level alterations.
- [ ] Rural/supermarket-linked stations, then service/truck sites with fit evidence;
  preserve neutral fallbacks and current gasoline/diesel compatibility defaults.

**Gate:** observed and held-out reference review, stable semantic identity, no
functional coverage loss hidden by decorative improvement.

### M7 — multi-level and advanced topology

- [ ] Split/internal/external/helical garage circulation in that order of capability;
  enclosed-mall passages/atria, supported podiums, bridges and terraces.
- [ ] Multi-level terminal access and other passenger modes only with mapped
  connections, complete clearance/support and physical lifecycle validation.
- [ ] Verify partial residency, cold teleport and retirement with player and
  supported AI/multiplayer vehicles occupying routes/decks.

**Gate:** playable topology and essential readiness in game before broad activation;
unsupported structures retain a topology-preserving diagnosed representation.

### M8 — calibration and private integrated package

- [ ] Run small-machine/desktop cold approach, warm revisit, dense driving, large
  complexes, highway approach and teleport: at least three repeats plus a soak.
- [ ] Measure all gates above, output coverage, memory, queue age, collision,
  texture residency, import cost, p50/p95/p99 and worst synchronous operations.
- [ ] Review game captures by day/night and near/far/oblique/rear/overhead views.
- [x] Produce matching private testing packages with source/mod/data manifests,
  dependency and startup checks, playtest instructions and retained older builds.
- [ ] Produce the release-candidate package after the native-game/performance
  gates, with measured acceptance, capability flags and explicit deferred features.

Publication is a separate task. Full interiors, passenger simulation, lifts,
dynamic fuel delivery and unsupported excavations remain outside these milestones.

## First-slice reproduction and status

Use the existing sibling environment, not system Python (which lacks NumPy):

```powershell
$python = '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe'
New-Item -ItemType Directory -Force build/overhaul-baseline/tmp | Out-Null
$env:TEMP = (Resolve-Path build/overhaul-baseline/tmp).Path
$env:TMP = $env:TEMP
& $python tools/commercial_preview.py --out build/overhaul-baseline/commercial-before.png
& $python tools/generation_baseline.py --preview --repeats 5
& $python tools/run_tests.py test_generation_baseline test_buildgen_driveways test_buildgen_access test_buildgen_sites test_buildgen_commercial test_buildgen_facades test_buildgen_progressive test_codefiles --par 2 --timeout 120 --logs build/overhaul-baseline/tests-after
& $python tools/run_tests.py test_gasstations --par 1 --timeout 120 --logs build/overhaul-baseline/tests-fuel-local-runtime
```

Initial test errors from the sandbox default temporary directory disappeared when
using workspace-local TEMP/TMP. Keep their initial logs separate from actual code
failures. The fuel suite also stalled in Windows `socket._fallback_socketpair`
during asyncio loop initialization in the sandbox; rerunning in the local runtime
outside that sandbox completed successfully. No generator workaround was needed.

Completed first slice:

- Eight focused modules: **81 tests passed**. Fuel suite: **114 passed, five
  skipped** for unavailable real-map caches (119 total). No game tests were run.
- `build/overhaul-baseline/generation.json` records twelve architectural fixtures,
  nine access cases, source/tool hashes, library/runtime versions, retained
  evidence fields, dispatch, mesh fingerprints/counts and per-stage timings.
  Each case gets a first process pass followed by five warm samples. This small
  synthetic sample is instrumentation, not a statistically supported release gate.
- `build/overhaul-baseline/generation.png` is the reviewed contact sheet. The six
  commercial controls expose the current office material variants; they are not
  evidence that new era grammars have been implemented. Chapel/church both have
  steeples; passenger terminal, Terminal Hotel and freight terminal all select
  legacy specialist dispatch. The garage fixture yields a deck plan, which still
  needs driving validation.
- `commercial-before.png` and `commercial-after.png` have identical SHA-256
  `b68917b8fa01a04a056b3a05cd651b4af59526614ada54ee4a65bb8eb42c40c1`.
  Existing nine-case layouts/geometry counts are unchanged. Before/after preview
  timings used different concurrent workloads and are not a performance comparison.
- Access fixtures distinguish connected/no-footpath/no-garage/narrow/protected
  ramp/obstructed/missing-terrain/steep/no-roads. Enabled/disabled telemetry yields
  identical near and collision fingerprints, access notes and terrain work.
  Translated-frame parity is tested. Candidate rejection counters currently cover
  the first failed **sidewalk-segment** check; road-segment visits are counted but
  their rejection causes are not yet subdivided.
- A provisional crossing whose internal driveway fails is explicitly recorded
  as `internal_route_failed_receiving_area_untested`. No crossing-only feasibility,
  new entrance, shared-site ownership or architectural family is claimed here.

The runtime integration is optional `buildings.doors(..., driveway_audit=audit)`
with `buildgen.diagnostics.DrivewayAudit`. It retains aggregate counts only and
does not change `BuildingPlan` serialization, schema 12, generation switches or
mesh behavior. Persistent cache identities already include the new module through
existing recursive `buildgen` source discovery. Source manifest hashes in each
report identify the precise version measured.

The paragraphs above describe the original M0 snapshot (schema 12). The following
foundation checkpoint used schema 13; the current implementation uses schema 14.
Original baseline artifacts remain unchanged.

## Foundation and garage continuation

The next implementation slice is documented in:

- [Identity contract](SITEGEN_IDENTITY_CONTRACT.md): namespaced semantic identity,
  separate revisions, bounded canonical frames, longitude wrap/quantization and
  deterministic ownership. Legacy tile XY is never relabelled canonical.
- [Shared records](SITEGEN_RECORDS.md): immutable evidence, memberships,
  interfaces, resources, graph validation and the exact legacy one-owner adapter.
- [Specialist adapter](SPECIALIZED_ADAPTER_STATUS.md): diagnostic-only evidence
  selection and current dispatch parity; new architecture is not activated.
- [Garage repair](GARAGE_ACCESS_IMPLEMENTATION.md): physical road connections,
  structural route clearance and the remaining in-game driving checks.
- [Preview lifecycle](GENERATION_RESOURCE_PROGRESS.md): bounded optional previews
  and cancellation; aggregate admission and occupied collision retention remain open.

An offline shared-record export can be reproduced with:

```powershell
& $python tools/validate_building_sites.py docs/examples/building-sites.synthetic.geojson --records-out build/sitegen-validation/synthetic-records.json --site-namespace fixture-sites --owner-namespace fixture-buildings
```

This first runs all existing catalogue/project validation, verifies exact adapter
and serialization round trips, and exports explicit legacy-frame records. It
reports canonical migration and physical surface validation as pending.

Current integrated validation: **284 tests passed across 18 focused modules**,
including garage structure/access, complete chunks, preview publication failure,
tracker cancellation, atomic reuse, legacy dispatch, identity, contracts, sites and
offline export. Logs: `build/shared-foundations/final-tests`. Source SHA-256 hashes:
`build/shared-foundations/source-manifest.json`. All touched runtime entry points
also passed Python syntax compilation. The garage review sheet is
`build/garage-access/review.png` with fixture metadata in `review.json`.

The additional `test_roadgeo` run passed seven synthetic/rebase tests. Its two
real-data checks failed because the offline cache lacks the required Overture
transportation parquet blocks; both raised `netfetch.Offline`. These are unresolved
real-map validation gates, not passes or skipped assertions. Original logs are in
`build/shared-foundations/integrated-tests/test_roadgeo.log`. No BeamNG driving,
occupied streaming, packaged executable or performance-release validation occurred.

```powershell
& $python tools/run_tests.py test_buildgen_garages test_buildings test_buildgen test_buildgen_topology test_buildgen_chunks test_buildgen_progressive test_buildgen_driveways test_sidewalk_collision test_parking test_codefiles test_sitegen_identity test_sitegen_contracts test_buildgen_specialized test_validate_site_contracts test_buildgen_sites test_buildgen_commercial test_buildgen_inference test_sitegen_progress_lifecycle --par 3 --timeout 120 --logs build/shared-foundations/final-tests
```

## Architecture and pavement continuation

At the user's request, the garage code repair is closed out and subsequent work
prioritizes bounded building facades and local pavement/landscape coordination.
Large complexes, expanded playable topology and fuel-site replacement still wait
for the M2/M3 physical-lifecycle gates. Garage driving acceptance remains separate
from its completed code/geometry checks; no new garage eligibility or skins were
added in this continuation.

- [Church status](CHURCH_IMPLEMENTATION_STATUS.md): three fitted shell compositions,
  three decorated spire types, source height/roof/holes, unsupported assembly
  diagnostics and keyword correction.
- [Terminal status](TERMINAL_IMPLEMENTATION_STATUS.md): explicit airport evidence,
  two facade families, neutral ambiguous modes and corrected freight/hotel routing.
- [Commercial status](COMMERCIAL_ARCHITECTURE_PROGRESS.md): strip shop fronts and
  three office grammars, with unchanged physical envelopes and existing site scope.
- [Pavement/landscape status](PAVEMENT_LANDSCAPE_PROGRESS.md): shared exact terrain
  samples and local groundcover reservations; no claim of full shared-site fitting.
- [Vegetation exclusions](VEGETATION_SURFACE_EXCLUSIONS.md): full-footprint source
  masks and generated hardscape metadata; lawn/garden detail encourages bushes and
  rocks while keeping their complete geometry inside accepted soft patches.

Current review sheets are under `build/church-stage1/church-review.png`,
`build/architecture-next/terminals.png`, `build/commercial-next/comparison-after.png`
and `build/pavement-landscape/frontages.png`. They are generated mesh previews,
not BeamNG screenshots. The schema 13 foundation results above remain historical.

The completed continuation has **447 distinct Python tests passing**: 404 across
28 integrated modules (`build/architecture-next/final-integrated`), four additional
hardscape regressions and ten mapped-surface tests (final affected modules in
`build/architecture-next/mapped-final`), plus the complete 29-test vegetation run
(`build/architecture-next/vegetation-local-runtime`). Modified runtime entry points
also pass syntax compilation. The vegetation run needed the local runtime outside
the sandbox because Windows asyncio socket setup stalled inside the sandbox.

Client tests pass **411 Lua checks** across surface exclusions, trees, geographic
roads, roads, building progress/staging, rebasing and collision foci. These include
retaining exclusions until queued pavement deletion finishes, and protecting a
replacement tile from an old pending cleanup. The roads suite uses a deterministic test clock; its default
Windows clock failure was reproduced against the unchanged baseline. See the
vegetation status for the exact command and baseline evidence. Source hashes are
in `build/architecture-next/source-manifest.json`. Native BeamNG driving, visual
appearance, occupied streaming and release performance gates remain open.

The next continuation below implements numeric source-field retention, shared
elevation foundations and bounded local driveway proposals. Regional/reference
review, nullable boolean evidence, broader roof modules and coordinated physical
pavement/fuel surfaces remain open. Aggregate admission/backpressure, canonical
runtime ownership and occupied-resource lifetime remain mandatory before large
sites or new playable assemblies. Garage in-game acceptance remains required
before expanding it.

## Shared architecture and ranked access continuation

Three parallel GPT-6.1 Sol tracks implemented specialist composition, commercial
detail and local street-interface proposals; root integrated source-field lineage
and cross-family/site consumers. See [foundation progress](ARCHITECTURE_FOUNDATION_PROGRESS.md),
[programme contract](ARCHITECTURE_PROGRAMME_CONTRACT.md) and
[commercial detail](COMMERCIAL_FOUNDATION_PROGRESS.md).

- Numeric source floor labels survive cache, part provenance and worker planning,
  without creating physical basements or changing source heights.
- Churches, terminals and commercial facades share bounded continuous elevation
  runs, floor datums and fitted grids. Existing three decorated spire selections
  use a legacy seed bridge. Loading courts and parking rows also use full runs.
- Commercial piers, spandrels, transoms and roof-edge caps fit accepted openings.
  A single supermarket entry predicate aligns facade, threshold and door props.
- Existing eligible garage entrances receive up to four complete local route
  proposals, with batched terrain fitting, protected neighboring curb openings
  and atomic accepted replacement. Green beds remain subject to accepted route
  reservations; bushes and rocks remain eligible inside accepted soft patches.

These are bounded extensions to existing families and local access, not completion
of M2, full M3 shared-site fitting or M4 native visual/performance acceptance.
Current serialization remains schema 14. Synthetic review sheets are under
`build/architecture-foundations`: `churches.png`, `terminals.png`,
`commercial-after.png` and `driveway-proposals.png`.

Final integrated validation: **488 distinct Python tests pass across 35 modules**
in `build/architecture-foundations/final-integrated`. All twelve architecture
fixtures retain collision fingerprints/body heights; all nine access fixtures
retain crossing counts, with original-resolver geometry differences below
`3.6e-15 m`. Alternatives and added facade detail have measurable extra cost;
no performance improvement or release gate is claimed. The 172-file source
manifest and per-fixture/test verification are in the same artifact directory.
All Python sources in that manifest pass syntax compilation. See foundation
progress for commands, source hash, invocation-error accounting and remaining
native-game/real-data gates. The 447 Python and 411 Lua counts above describe the
preceding continuation, not additional tests counted in this 488 total.

## Default visible frontage continuation

- [x] Automatic bounded commercial/office/industrial frontages in the ordinary
  runtime, with no external site catalogue required.
- [x] Fitted paving, planted beds, bed-edge curbs and entrance links.
- [x] Parking only with enough stall/aisle space and a verified road connection;
  matching raw/draped sidewalk cuts, neighbor openings and atomic rollback.
- [x] Cache-only road, mapped pavement, fuel, rail and water obstacle inventory.
- [x] Existing stock shrubs and rocks in accepted planted areas. No bespoke
  shrub/rock mesh generation; measured asset bounds plus clearance, deterministic
  placements and natural-prop exclusion in the client.
- [x] Final runtime fixtures for shallow retail, office, supermarket and workshop,
  including retained beds after entrance coordination and native placement counts.
- [ ] Native game visuals, driving, occupied streaming and performance acceptance.
- [ ] Full surveyed/shared property reconstruction, large complexes and fuel sites.

See [visible-site playtest](VISIBLE_SITES_PLAYTEST.md). Current evidence lives in
`build/visible-sites`: `runtime-frontages.png` shows actual accepted top surfaces
and native placement centres, not an in-game rendering of the assets. The earlier
`landscaping-geometry-preview.*` and `landscaping-integrated-preview.png` in that
directory are superseded intermediate work; their bespoke planting was removed.
Schema remains 14; changed runtime source fingerprints invalidate generated caches.

## Street clipping, terrain and organic planting continuation

- [x] Clip grounded building bodies behind streets and actual sidewalk edges,
  including painted roads and sidewalk corners. Preserve valid footprint holes,
  source identity and resolved appearance; omit unusable fragments.
- [x] Apply source-road clipping to near/far/sky generation; publish progressive
  shells only after the near actual-surface check. Remove invented above-road lift.
- [x] Clear and rebuild geometry-dependent door/access/facade plans after a cut;
  preserve supported garages and re-fit decorated church spires.
- [x] Irregular native-asset planting with separated full envelopes and multiple
  rows on wide beds, using whole-footprint support over rendered terrain triangles.
- [x] Joined bed curb rings with consistently inset soft areas and access openings.
- [x] Bounded pedestrian steps/landings for entrance height differences, validated
  shared paving planes, and numerical tolerances for rotated/offset geometry.
- [x] Runtime terrain fixtures: flat, slope, translated slope, rotated slope,
  gentle ripples and excessive-slope suppression.
- [ ] Native-game road clearance, driving, appearance and performance acceptance.

Read [the new playtest checklist](SITE_REFINEMENT_PLAYTEST.md). Evidence is under
`build/site-refinement`; previous packaged checkpoints remain unchanged. Far and
skyline clipping uses source carriageway widths; exact sidewalk trimming applies
when near geometry replaces them. These changes remain schema 14 and use the
existing native game shrub/rock assets.

The 2 November texture compatibility correction is documented in [the weathering hotfix](WEATHERING_HOTFIX.md). Native loading and performance acceptance remain pending.

The latest pass removes unsupported facade posts and synchronizes relocated prop collision: [facade and collision fix](FACADE_PROP_COLLISION_FIX.md).
