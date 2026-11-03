# Commercial generation overhaul implementation prompt

Execution order, resolved cross-plan conflicts and current progress are tracked in
[the integrated implementation checklist](GENERATION_IMPLEMENTATION_CHECKLIST.md).

Prepared 1 November 2026. This is an implementation brief for a future coding task. Creating this brief does not change generator behaviour or establish performance results.

## Mission

Overhaul BeamNG Earth's commercial building and shared-site generation so commercial areas have convincing functional, structural, regional and historical variety. Implement a coordinated procedural system for workshops, strip shops, retail parks, supermarkets, enclosed and outdoor malls, offices across construction eras, parking structures, and complex mixed-use developments. Support many buildings, several uses and shared spaces within one complex, including vertically overlapping uses and connected multi-level structures.

The result must work during driving with bounded CPU, memory, GPU, storage and network costs. Protect gameplay through scheduling, prefetch, stable physical geometry, progressive visual refinement and measured admission limits. Background workers alone do not establish smooth gameplay. Treat synchronous import and collision costs as release constraints.

Implement the work in dependency-ordered milestones below. Audit the current checkout first, maintain an implementation checklist, and continue through implementation and available validation when this prompt is invoked as a coding task. Reconcile changes made since this brief. Preserve unrelated work. Keep implementation and validation reports honest about unavailable data or in-game checks.

## Starting point and integration constraints

Use the active source checkout, currently `BeamNG.EarthBuildTest`, rather than an older extracted playtest package. The inspected snapshot is schema 12 and is not an initialized Git checkout. Do not replace it with the original recovery bundle, which omits later changes. Reconcile versions before changing serialization or packaging.

Read these existing documents and coordinate their responsibilities:

- `docs/PAVEMENT_AND_SITE_ACCESS_PLAN.md`: proposed common site system, roads, access, parking, fuel stations and shared complexes. Implement one common system with this plan; do not create competing site planners.
- `docs/BUILDINGS_V2_IMPLEMENTATION.md`: current implementation and historical limitations.
- `docs/COMMERCIAL_BUILDINGS_STAGE1.md`, `docs/COMMERCIAL_SITES_STAGE2.md`, and `docs/BUILDING_LANDSCAPING.md`.
- `../building_generation_research/COMMERCIAL_INDUSTRIAL_PRESET_PLAN.md` and its proposed catalogue: use the functional coverage as input, not as an executable architectural engine.

Verified architectural constraints at preparation time:

| Location | Existing behaviour and required treatment |
| --- | --- |
| `server/buildgen/commercial.py` | Three specialised generators: logistics hall, supermarket and trade units. Replace limited frontage composition with shared architectural grammars while retaining adapters. |
| `server/buildgen/plan.py` | Immutable building compilation input, currently in caller tile coordinates. Introduce canonical persistent identity without breaking existing emitters. |
| `server/buildgen/site_data.py` | One owner building per optional surveyed site; overlapping sites rejected. Migrate to explicit membership and resource ownership. |
| `server/buildgen/context.py`, `evidence.py`, `inference.py` | Provenance, mapped attributes, neighbourhood/land-use/climate context, zoning and roof-colour inputs. Extend field retention and coverage deliberately. |
| `server/buildgen/compiler.py` | Specialised parking and infrastructure dispatch. Preserve it until a verified replacement supports its geometry and collision. |
| `server/buildgen/progressive.py` | Current source groups twelve buildings through shell/lite/detail stages. Optional previews now have cancellation and bounded manifest validation; see `GENERATION_RESOURCE_PROGRESS.md`. Generalise grouping to bounded spatial and dependency units. |
| `server/buildings.py` | Existing v2 import chunks use a 20,000-vertex cap. Vertex count is only one predictor of actual import cost. |
| `server/earthd.py`, `blockworker.py`, `budget.py` | Existing workers, priorities, machine profiles and resource constraints. Extend these instead of adding uncontrolled worker pools. |
| `server/plancache.py` | Road-plan cache, not a ready-made persistent building/site-plan cache. Reuse appropriate infrastructure, not its road-specific assumptions or blocking waits. |
| Client `buildingprogress.lua`, `roads.lua`, `governor.lua` | Staged imports, revision checks, shared frame governor and synchronous collision rebuilding. Integrate all new work with these mechanisms. |
| `server/codefiles.py` | Recurses through `buildgen` source/catalogues. Include any new package and assets in source identity, packaged distribution and cache invalidation. |

The governor currently has a 2 ms default streaming target and an 8 ms loading target. Those are scheduling targets, not hard upper bounds on individual synchronous engine calls. Its existing engine-debt accounting matters because some import work occurs in subsequent frames. Preserve and extend that accounting.

## Architectural identity and evidence

Resolve identity through compatible, separately stored dimensions:

`function + spatial organisation + structural system + construction era + regional vocabulary + architectural ambition + alteration history + condition`.

Do not equate old with neglected, modern with glass, large with office, or low-budget with random ugliness. A clean utilitarian workshop, maintained historic office, reclad mid-century block and ambitious contemporary mall must all be expressible.

Keep observed constraints distinct from procedural choices. Record field-level source, revision, status, conflict and supporting evidence. Rule scores are not calibrated probabilities. Preserve observed footprint, holes, building parts, heights, materials and roof characteristics unless an explicit conflict-resolution rule documents why a value cannot be used.

Audit upstream feeds and caches before assuming a source attribute reaches the planner. Extend adapters for verified construction dates, heritage/style observations, mixed uses by part/level, mapped entrances, shop/office POIs, parking decks, pedestrian passages and site relations where available. Spatial joins must account for containment, level, source reliability and ambiguous association; nearest POI alone cannot classify an entire mall.

Use four capability tiers:

1. Footprint and broad use: produce a convincing conservative envelope, facade composition and construction details.
2. Parts, dimensions and stronger use evidence: resolve wings, vertical zones, tenancy rhythms and structural systems.
3. Shared-site extent and access evidence: resolve courtyards, common circulation, parking, loading and shared amenities.
4. Detailed level/connectivity evidence: support traversable decks, ramps, bridges and complex public passages.

Allow bounded procedural authorship within supported envelopes. Missing exact architecture must not force every building back to an identical box. Inferred era/vocabulary remains labelled as authored or inferred, not a claim about the real property. New towers, external bridges, excavations, vehicle entrances and removed floor areas require stronger support than colour or window-rhythm choices.

Offline preprocessing may enrich cached evidence. Ordinary generation must not require paid services, online AI inference, per-building imagery downloads or repeated analysis. Reuse cached map/terrain sources and record licensing/attribution for added datasets and assets.

## Shared complexes and ownership

Replace the single-owner property model with a site-level identity independent of any building. Separate source membership, legal ownership when actually known, generated resource ownership, and spatial overlap. Generated ownership means responsibility for emitting and maintaining a resource; it is not an assertion of cadastral title.

Introduce immutable records along these lines; adjust names to fit existing conventions:

| Record | Required content |
| --- | --- |
| `ComplexEvidence` | Stable complex ID, source revisions, optional extent with holes, extent semantics, members, exclusions, confidence and unresolved conflicts. |
| `Membership` | Building/part/lot/station/space reference, relationship, functional role, level or height interval, evidence and revision. |
| `ComplexPlan` | Canonical frame, members, shared identity, topology summary, sector references, interfaces, reservations and diagnostics. |
| `SpacePlan` | Polygon or volume, level interval, public/customer/staff/service role, use, access policy, supporting surface and owning resource. |
| `BuildingProgram` | Uses by part/floor/zone, tenancy divisions, public/service interfaces, identity and feature eligibility. |
| `StructurePlan` | Grid, floor/deck datums, supports, spans, cores, load-path relationships and physical voids. |
| `CirculationPlan` | Nodes/edges for pedestrian, passenger vehicle and service movement, width, direction, elevation, clearance and connected destinations. |
| `Interface` | Stable ID, participants, shared boundary/level constraints, portal/crossing/attachment role and revision. |
| `ResourceOwnership` | Exactly one producer for each physical mesh/surface/marking/prop resource, with all consuming members and retention references. |
| `SectorPlan` | Bounded spatial work unit, dependency/interface versions, payload limits and independent residency state. |

Support a building participating in several associations without being emitted repeatedly: for example, a street retail row belonging to a wider precinct, a supermarket sharing a car park with a fuel station, and offices above a retail podium sharing parking and service access.

Permit nested complexes through an acyclic membership hierarchy, with shared resources represented by explicit references. Reject cycles and unresolved competing producers. Horizontal extent overlap is valid when sources describe different associations or separate vertical spaces; actual same-level surface conflicts still need resolution. Keep unrelated neighbouring sites separate.

Provide a backward-compatible adapter from `owner_id` to a one-member complex. Preserve old evidence semantics and validation guarantees. Support standalone parking/plazas without buildings, and members whose building geometry has not streamed in. Unknown or partial exclusions must be explicit; allow only work justified within the known area.

Each resource gets a stable ID from source/member/interface identity and semantic role, not discovery order, tile index or random runtime state. A deterministic canonical owner emits it once. Tile consumers reference-count it; unloading one member cannot delete shared circulation still needed by another member or vehicle. Resolve ownership even when the designated member is outside the visible tile.

Plan connectivity at complex scale, then partition geometry. A large complex must not require one giant mesh, one all-or-nothing import or a full-site rebuild for a tenant-sign change.

## Procedural architectural grammar

Replace whole-building template selection with compatible assemblies and bounded composition rules. Keep function, massing, structure, frontage, roof, material and history independently configurable. Do not materialise their Cartesian product into thousands of duplicated presets.

Resolve in this order:

1. Authoritative envelope, holes, parts and shared attachments.
2. Building programme and floor/zone allocation.
3. Site/part interfaces and public/service orientation.
4. Structural grid, cores, support hierarchy and clear spans.
5. Floor/deck levels and vertical circulation reservations.
6. Facade runs, tenancy modules, entrances, major openings and solid zones.
7. Roof assemblies, drainage intent and service zones.
8. Materials, architectural detail, alterations and weathering.

Merge collinear facade edges into physical runs; digitisation vertices must not restart window grids. Respect corners, actual party-wall contact heights, courtyard-facing walls and multiple entrances. One elevation can contain several roles. Fit complete bays and preserve dimensional ranges; reduce count before compressing doors or stalls below the selected profile's minima.

Use structural construction families: load-bearing masonry with appropriate openings; steel portal-frame halls; concrete frames with infill; precast panel/frame systems; long-span roofs; and compatible modern facade systems. Foundations appear through credible ground contact, plinths, slab edges and supported retaining/stepped conditions. Do not spend resources generating invisible underground footings or performing structural simulation.

Columns and piers align through levels or meet an explicitly supported transfer assembly. Slabs have thickness, openings have lintels/frames, canopies have attachments or columns, and bridges have supported endpoints. Unsupported cantilevers and floating facade fragments fail validation. Numeric span/dimension ranges are authored plausibility profiles unless backed by a cited regional source; do not label them engineering certification.

Keep clear hall height separate from occupied floor count. Introduce ground-floor, mezzanine, office-floor, parking-deck, atrium and plant-zone datums. Share these datums with facade, ramp, roof and collision geometry.

Required initial families and composition options:

| Family | Required variation beyond materials |
| --- | --- |
| Workshops and trade units | Single workshop, joined bays, courtyard estate, showroom/workshop split; shutters paired with staff entries; clerestories; gable and portal-frame rhythms. |
| Strip shops and shopping parades | Attached street row, recessed suburban row, corner emphasis, arcaded frontage; coherent upper floors with independently altered shopfronts. |
| Supermarkets and large retail | Concentrated entrance, multiple supported entrances, showroom frontage, quieter sales-volume walls and receiving edges. |
| Historic offices | Masonry pier rhythm, base/middle/roofline composition, restrained cornices, recessed openings, corner entries and later ground-floor alterations. |
| Dated and mid-century offices | Concrete grids, ribbon windows, precast spandrels, deeper reveals, projecting stairs/cores where supported, later recladding. |
| Contemporary offices | Curtain-wall modules, mixed opaque/glazed fields, shading assemblies, recessed lobbies, supported podium/tower relationships and screened plant. |
| Enclosed malls | Anchor and smaller retail roles, entrance hierarchy, mapped concourses/atria, separate back-of-house edges and compatible roof spans. |
| Outdoor malls and retail parks | Facing shop groups, pedestrian spines, courtyards, covered links and shared amenities with separate service access. |
| Parking structures | Open slab/frame, screened facade, split levels, internal ramps and supported external ramps; real deck and clearance logic. |
| Mixed and exceptional complexes | Retail below offices, linked wings, parking podiums, bridges, stepped terraces and long-span halls, gated by available geometry and support rules. |

First author a review matrix of at least three materially different compositions per applicable core family, each across multiple footprint shapes and seeds. These are grammar tests, not a promise to use every combination on every real building. Require differences in silhouette where evidence permits, bay grouping, frontage depth, entrance composition or organisation. Palette changes alone do not count.

Architectural ambition changes composition and detailing within the evidence envelope. Ordinary buildings should remain common. Avoid forced alternation or generating a landmark on every parcel.

## Construction history and visual assets

Store original architectural vocabulary independently from current use and alteration state. A warehouse converted to offices may retain its structural rhythm; a historic upper facade can sit above newer shopfronts. Extensions only change massing where supported by parts/evidence; surface-level alterations can be authored within the known envelope.

Use separate deterministic seed channels for structure, facade, roof, tenant fit-out, palette and wear. Neighbourhood preferences use observed context and regional profiles, never generated neighbours or tile load order. A new wear pass must not move entrances or alter structural geometry.

Create reusable trim sheets, tiling materials and small modular detail assets. Coordinate real-world texture scale, roughness, glazing, normal detail and facade depth. Use atlas regions and shared material parameters where supported; verify the engine path before depending on instancing or parameter features. Batch repeated modules if native instancing is unavailable. Avoid one material/texture per tenant or building.

Place wear by exposure, drainage and material: streaking beneath runoff points, sheltered recesses, patch repairs and replacement panels. Fine dirt, cracks and joints belong in materials or shallow visual geometry, not driving collision. Keep signs within reserved panels; preserve source names where appropriate and use coherent fictional identities for authored tenants without claiming real occupancy.

## Site coordination and multi-level circulation

Implement the common `sitegen` model proposed by the pavement plan. Building emitters, parking, gas stations, road crossings and landscaping consume the same accepted reservations and surface ownership.

Use a bounded proposal/resolve/commit process rather than mutually recursive planners:

1. Read site membership and authoritative envelopes. Buildings propose ranked public/service portals and fixed level constraints.
2. Reserve mapped connections, shared structural interfaces, emergency/service constraints where supported, and essential pedestrian/vehicle corridors.
3. Evaluate up to four candidate layouts per sector against these reservations. Candidate scoring prioritises connectivity and feasibility before parking capacity or decoration.
4. Fit surface levels, supported ramps and building thresholds from shared constraints. At most two additional local conflict-resolution passes; no unbounded convergence loop.
5. Commit accepted access, surfaces and portals together. Suppress optional features on unresolved conflict; retain valid existing access.
6. Fit parking, markings, landscaping and optional props into remaining validated space.

Split pedestrian, customer-vehicle and servicing graphs while modelling their crossings explicitly. Separate adjacency from reachability: spaces at the same XY position may be several levels apart. Record direction, vehicle envelope, width, grade, transition profile, headroom and surface continuity on traversable edges.

Parking ramps require vertical curves or tested transitions, complete landings, suitable headroom and a route to usable decks. Bridges and elevated walks require explicit endpoint connections and supports. Public mall passages and arcades need real voids. Reserve drains/plant/services coherently, without inventing underground networks.

Use bounded swept-envelope checks and spatial indexes for design vehicles; do not add continuous per-frame traffic simulation. Reuse the project's selected driving-side and regional dimensions/markings. Do not invent road access from mere proximity, replace public roads with private paving, or infer a whole asphalt parcel from zoning.

Initial interiors are limited to useful/visible spaces: parking decks, arcades, passages, entrance recesses, supported atria and bridge connections. Full tenant interiors, crowds and business simulation are outside this overhaul.

## Canonical plans, caching and invalidation

Introduce canonical complex/building plans in a stable geographic frame with a defined precision/error policy. Translate to render tiles at emission. Verify anchor changes, tile boundaries, dateline cases and large-site precision. Partition oversized extents without truncating legitimate members or connections.

Cache evidence, semantic plans, physical plans and render products separately. Keys include source revisions, relevant evidence/context fingerprints, grammar/profile versions, geometry dependencies and applicable schema. Cosmetic quality tiers may select different render products from the same physical plan. Hardware pressure must not change building identity, passages, driving routes or collision topology.

Use dependency-scoped invalidation: a sign/wear change regenerates affected visual resources; a changed deck height invalidates connected ramps/interfaces; an updated source polygon invalidates dependent geometry. Unaffected buildings and shared resources remain cached.

Coalesce concurrent requests for the same canonical plan. Use atomic writes, checksums/schema validation, bounded retry and stale-producer recovery. Cache waits belong off the event loop and must be cancellable; do not copy the road cache's long blocking wait into a gameplay-critical path. Corrupt entries rebuild locally. Source fetch failures must not be stored as complete evidence or permanent negative findings.

Persist compact arrays and metadata, avoiding untrusted pickle for disk records. Keep one bounded shared cache where practical; account for actual per-worker duplication where sharing is unavailable. Store revision manifests and reusable stage products; temporary preview files need quota-limited cleanup after acknowledgements and cancelled revisions.

## Generation scheduling and gameplay protection

Use the existing server budget and process infrastructure. No extra process per site, nested pools or unbounded futures. CPU-heavy geometry runs outside the main server event loop and game thread; cap library-internal threads to prevent oversubscription. Low process priority alone is insufficient because workers also compete for memory bandwidth and I/O.

Schedule these priorities through one resource coordinator:

1. Existing essential terrain/roads and imminent physical continuity.
2. Building/site physical plans and colliders needed along the likely vehicle path.
3. Visible structural silhouettes and lite facades.
4. Near architectural detail.
5. Distant optional detail, wear and idle preprocessing.

Use speed, heading, route evidence when available, distance and measured p95 readiness latency to estimate time to need. Bound lookahead and add hysteresis. Never let decorative jobs delay existing essential work. Deduplicate work already in flight. Apply backpressure before mesh generation, serialization and delivery when downstream queues are full.

Make jobs resumable at bounded stage/sector boundaries. Check cancellation before terrain requests, candidate batches, triangulation, mesh emission, file writes and publication. A cancelled future does not stop a running worker: use revision/generation tokens and cooperative cancellation. Reject stale results after teleport/rebase/revision changes and release their buffers, files and shape slots.

Limit native geometry calls by input complexity as well as task time. A Python cancellation flag cannot interrupt one long native call. Partition before expensive operations, validate complexity and fall back/defer a feature when bounds cannot be met. Preserve essential topology in fallbacks.

For huge sites, compute a small coarse membership/interface summary, then request relevant sectors incrementally. Do not fetch every member's full mesh or solve the entire site before presenting its first useful portion. Each sector has bounded work, but the scheduler must also bound aggregate per-tile, per-complex and global work.

## Progressive visuals and physical continuity

Keep separate physical and visual lifecycles:

- Physical plan: stable envelope, openings, traversable surfaces and collision resources prepared ahead of use.
- Visual refinement: silhouette, structural/lite facade, near details and optional surface treatment.

All visual tiers preserve physical holes, open decks and bridge clearances. Never use a solid proxy over an arcade, drive-through passage or parking entrance. If no topology-safe proxy exists, retain the last valid representation or omit the optional visual refinement. The current ordinary-building shell must be extended or excluded for newly complex types.

Make progressive groups spatially bounded and weighted by estimated import bytes, material count, vertices and measured engine cost. Four buildings is not a reliable work unit when one is a mall. Keep connected physical interface groups atomic, while independent decorative sectors can commit separately. Do not expose half a required ramp/landing connection.

Prepare imports off-thread where supported, but assume object creation and collision rebuilds can remain synchronous until measured otherwise. Integrate creation, reveal, retirement, deletion, material setup and cleanup into the existing governor. Use calibrated cost classes and charge delayed engine work. No independent 2 ms budget for each subsystem, and no forced decorative import every frame.

Keep old visuals until their replacements are complete, with a bounded overlap-memory reserve. Maintain spatially corresponding LOD partitions and hysteresis. Render quality may drop under pressure; physical topology must remain stable.

Collision updates use the existing road/terrain coordination and heavy-operation scheduling. Do not rebuild collision for decorative upgrades. Check all relevant active vehicles, including AI/multiplayer vehicles supported by the runtime, using swept volumes and level-aware occupancy. Never remove a deck supporting a vehicle, seal a passage around one, or activate a solid inside it. Pin necessary resources until clearance is verified.

Measure collision activation cost separately. If the engine cannot activate required geometry within the gameplay target, reduce activation scope where supported, preactivate farther ahead, or defer the unsupported feature; record an engine limitation rather than claiming worker threading fixes it. On a cold teleport, integrate essential readiness with the existing loading/readiness policy. Do not pause ordinary driving to finish cosmetic generation or silently permit driving onto unavailable collision.

## Initial resource budgets

These are proposed admission limits and release targets, not measured guarantees. Make them configurable through the existing machine profiles. Tighten or revise them from representative measurements with recorded reasons; do not loosen them merely to hide a failing design.

| Resource | Small-machine starting policy | Desktop starting policy |
| --- | --- | --- |
| Extra worker pools | None | None |
| Concurrent optional architecture jobs | At most 1 within existing pool/headroom | At most 2 within existing pool/headroom |
| New incremental CPU residency across all processes | 256 MiB target envelope | 768 MiB target envelope |
| Breakdown of that envelope | 64 MiB cached plans, 128 MiB in-flight/working buffers, 32 MiB queued payloads, 32 MiB other overhead | 192 MiB cached plans, 384 MiB in-flight/working buffers, 128 MiB queued payloads, 64 MiB other overhead |
| New texture residency | 128 MiB ceiling, subject to shared-memory headroom | 256 MiB ceiling, subject to GPU headroom |
| Pending optional jobs | At most 8 admitted descriptors | At most 16 admitted descriptors |
| Worker cancellation/checkpoint interval | Target 25 ms of CPU work between boundaries | Target 25 ms of CPU work between boundaries |
| Architecture contribution to main-thread work while driving | Target p95 at most 1 ms/frame, inside existing shared budget | Target p95 at most 1 ms/frame, inside existing shared budget |
| Additional persistent generated cache | Initial 1 GiB LRU quota | Initial 4 GiB LRU quota |

Measure actual RSS/working set, shared allocations, decoded objects, serialization copies and old/new replacement overlap. The table's sub-budgets sum to one aggregate envelope, not an allowance per worker. GPU/shared-memory consumption also participates in total machine pressure. Include existing generator memory in the headroom decision.

If an essential physical job cannot fit, defer lower-priority jobs, evict unpinned derived products and retain existing valid physical state. Never solve a memory overflow by silently dropping necessary collision or source members. Oversized assets require a partitioned path or a diagnosed unsupported feature.

Additional algorithmic bounds:

- Up to four layout candidates and three total coordination passes per sector.
- Start with the existing simple-site 512 unique terrain samples and 24 base surface patches per sector; deduplicate interface samples across consumers. Schedule further sectors incrementally.
- At most eight newly admitted sectors per complex at a time, also constrained by the global queue. This is an in-flight cap, not a maximum site size.
- Start at the existing 20,000-vertex import ceiling; lower chunks according to measured import cost, material count and bytes. Also cap aggregate scene objects/draw calls, since tiny chunks have overhead.
- Use spatial indexes and local adjacency instead of all-pairs building/space checks. Bound graph searches by sector and a compact shared interface graph.
- Require component-specific caps for bays, roof divisions, support instances, signs, lights and decorative props; record counts and omission reasons in diagnostics.
- Use compact descriptors for deferred sectors. Do not retain completed full near/lite/collision arrays for an entire large complex simultaneously.

Throttle using CPU pressure, available memory, queue depth, measured frame-time debt and downstream acknowledgement latency. Use hysteresis to prevent oscillation. Prioritise retaining usable paths and recognisable silhouettes; omit minor details first. Remain able to improve visuals when pressure subsides without regenerating physical geometry.

## Code organisation and migration

Prefer small pure planners and explicit immutable interfaces over expanding `buildings.py` into another monolith. Suggested responsibilities:

- `server/sitegen/`: evidence/membership, ownership, common plan records, interfaces, reservations, circulation, sectors and coordination. Reconcile with the pavement plan's access/pavement/parking modules.
- `server/buildgen/`: identity/programme, structural grids and levels, facade/roof assemblies, histories, profiles, validators and existing geometry adapters.
- A dedicated building/site plan cache module: canonical serialization, dependency indexes and product manifests, reusing general cache utilities.
- Existing `earthd`, worker and budget modules: admission, priority, cancellation, backpressure and telemetry.
- Existing progressive compiler and Lua modules: bounded manifests, staged import, physical readiness, revision validation and safe retirement.

Exact module names are design choices; the ownership of responsibilities is mandatory. Keep dependency direction from common records to planners to emitters. Building and site planners exchange interfaces through the coordinator rather than importing each other's orchestration functions.

Use versioned adapters for existing `Spec`, `BuildingPlan` and site catalogues. Add explicit client capability negotiation for new manifests; reject incompatible combinations clearly or use a documented compatible path. Include new code, profiles and material assets in source identity, packaging and cache signatures. Preserve residential roofs, doors, driveways, landscaping, specialised infrastructure, fuel interactions and existing road readiness.

## Milestones and acceptance gates

| Milestone | Implementation | Exit gate |
| --- | --- | --- |
| 0. Baseline | Audit selection/fallbacks, evidence coverage, current timing/memory and client import/collision costs. Capture reproducible fixtures and routes. | Explain current uniformity with measured selection and visual evidence; separate cold/warm cases and historical measurements. |
| 1. Shared records | Add complex membership, ownership, interfaces, canonical frames and backward adapters. | Existing one-owner inputs still work; mixed-use membership, overlapping levels and cross-tile shared resources emit once. |
| 2. Resource infrastructure | Add bounded admission, cancellation, dependency cache and sector manifests through existing scheduling. | Slow-worker, stale-result, queue-saturation, cache-corruption and memory-pressure tests remain bounded and preserve existing physical state. |
| 3. Architectural core | Add programme, identity, grids, floor zones, facade runs and compatible assemblies. Deliver workshop, strip shops, supermarket and three office-era directions. | Equivalent envelopes produce recognisably different compositions; collision/LOD/topology agree; baseline scenes stay within regression budgets. |
| 4. Detail and history | Add roof assemblies, material/trim assets, construction details, alterations and exposure-based wear. | Multiple seeds and footprint forms remain coherent; variation is more than recolouring; near detail stays within import/render limits. |
| 5. Shared commercial sites | Integrate multiple buildings, common courts, plazas, shared parking, outdoor malls, mixed retail/office/workshop areas and fuel-site interfaces. | Connected routes and exclusive surface ownership across tile boundaries, reverse load order and partial residency. |
| 6. Multi-level systems | Add parking decks/ramps, enclosed-mall passages/atria, supported podiums, bridges and terraces. | Level-aware reachability, support, vehicle envelope, safe collision activation and in-game traversal pass before broad activation. |
| 7. Calibration and rollout | Calibrate regional/era profiles, performance tiers, sparse-data fallbacks and dense-scene behaviour. Package a private integrated playtest. | Required automated, visual and gameplay gates pass; unresolved engine/data limitations are explicit; feature flags provide rollback. |

Validate the scheduling infrastructure early with synthetic oversized complexes; do not wait until all architecture families exist. Introduce complex features behind independent capability flags. Preserve the validated everyday architecture slice while advanced topology matures.

## Validation and measurable completion

Extend relevant existing suites rather than duplicating assertions about implementation details: building inference/topology/plan/facade/commercial/site/access/chunks/progressive tests, worker/codefiles/cache/budget tests, and Lua building staging/progress/governor tests. Add focused complex membership, ownership, structure, multi-level circulation and resource-lifecycle suites.

Required semantic and geometry fixtures:

- Old one-owner site, multi-building estate, nested precinct, shared car park, standalone plaza/lot and supermarket/fuel complex.
- Retail under offices over parking; two unrelated uses sharing XY at different levels; multi-tenant building belonging to multiple associations.
- Workshop court, historic shopping parade, dated office, contemporary office, enclosed mall, outdoor mall, parking decks and supported bridge.
- Narrow/deep/concave/holed footprints; attached walls; corner sites; disconnected parts; slopes; rough/missing terrain; conflicting heights and uses.
- Unknown era/material, sparse source data, ambiguous POIs, incomplete membership/exclusions and absent surveyed access.

Verify deterministic results under seed reuse, ring rotation/winding, member ordering, tile order, worker count, restart, cache reuse and rebase. Test global-frame edge cases. Validate finite nondegenerate meshes, exclusive resource ownership, openings/voids, support continuity, route connectivity, clearance, surface seams and collision agreement.

Lifecycle and load tests must include teleport during generation, rapid turn-away/return, obsolete revisions arriving late, worker death, disconnected source fetch, slow disk, full cache, memory pressure, duplicate requests, unload of one shared member, and a vehicle occupying a deck during attempted retirement. Test supported AI/multiplayer vehicles as well as the player.

Build a visual review tool that shows evidence, selected programme/identity, facade roles, supports, levels, routes and omitted-feature reasons beside generated views. Compare silhouettes without textures and final materials in BeamNG. Review front, rear, oblique, aerial and driving views. Prototype previews cannot establish in-game material or performance acceptance.

Performance reporting must separate evidence I/O, planning, terrain sampling, meshing, serialization, delivery, import, deferred engine cost, collision rebuild, draw calls, physics triangles, memory and cache churn. Report median/p95/p99 and worst observed operations, throughput and queue age. Measure equal workloads before/after; report accepted coverage as well as cost so suppressing features cannot masquerade as an optimisation.

Use at least a small-machine profile and a representative desktop, with fixed vehicle/traffic/graphics settings. Run cold approach, warm revisit, dense urban driving, large-complex traversal, sustained highway approach and cold teleport scenarios. Include at least three repeat runs per measured route and a sustained memory/streaming soak; record hardware, settings, route, revisions and cache state.

Proposed release gates:

- Unchanged simple-scene worker generation p95 no worse than 10% above a fresh baseline, with equivalent feature coverage.
- Architecture main-thread contribution p95 at most 1 ms/frame while driving inside the existing shared governor; report p99 and synchronous outliers separately.
- Total driving frame-time p95 and p99 no worse than 10% above the comparable baseline, and no new repeatable architecture-attributable stall above 50 ms. These are initial acceptance thresholds, not a claim that smaller stalls are imperceptible.
- Zero introduced route discontinuities, missing occupied-deck collision, duplicate shared surfaces or stale-result activations in the required fixtures/routes.
- Aggregate incremental residency and queues remain within configured limits; no sustained monotonic growth across repeated visit/unload cycles.
- Essential readiness keeps ahead of the tested driving envelope; optional detail may lag without pausing gameplay. Report readiness latency and the speeds/conditions actually validated.

If an engine operation cannot meet a gate, document its measured cost, isolate its cause and implement a supported mitigation before declaring that feature gameplay-ready. Never promise universally hitch-free execution on arbitrary hardware or unseen data. The deliverable is bounded behaviour and demonstrated performance on declared profiles.

## Required deliverables

Deliver the integrated implementation, compatible data migration, versioned grammar/profile catalogues, reusable visual assets, deterministic fixtures, focused tests, reproducible benchmark commands, before/after review sheets and a private playtest package using the project's established workflow.

Update the implementation documentation with achieved capabilities, current limits, resource defaults, measured performance and exact reproduction steps. Distinguish automated checks, offline visual review and real BeamNG driving validation. Do not reuse historical passing-test counts as evidence for the new system.

The first implementation task is to establish the baseline and shared ownership/plan contracts, followed immediately by resource admission and a six-building architectural comparison scene. Continue toward shared complexes and multi-level systems through the gates above. Success is recognisable, coherent architecture and usable shared places generated within gameplay budgets; catalogue size alone is not a completion criterion.
