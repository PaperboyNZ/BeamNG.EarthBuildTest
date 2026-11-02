# Specialized building implementation plans

Execution order, resolved cross-plan conflicts and current progress are tracked in
[the integrated implementation checklist](GENERATION_IMPLEMENTATION_CHECKLIST.md).
Current garage implementation and outstanding driving checks are recorded in
[the garage access repair](GARAGE_ACCESS_IMPLEMENTATION.md).

Prepared 1 November 2026. Proposed implementation work for the current `BeamNG.EarthBuildTest` source. This package changes documentation only.

Churches, terminals, parking garages and petrol stations should gain recognizable architectural variety, convincing construction detail and usable connections to their surroundings. Preserve their existing specialized behavior while moving their decisions into shared, deterministic plans. A small chapel must not look like a scaled cathedral; a regional terminal must not look like a small glass office; a garage entrance must connect to its ramps; every accepted petrol pump must remain usable.

## Plans and delivery order

| Plan | First useful release | Later capabilities |
| --- | --- | --- |
| [Churches](CHURCH_GENERATOR_PLAN.md) | Plain chapels, parish churches and modern halls with fitted openings, coherent materials and grounded entrances | Mapped aisles, transepts, towers, apses and richer landmark roofs |
| [Terminals](TERMINAL_GENERATOR_PLAN.md) | Regional airport halls and linear concourses with distinct public, transport and service elevations | Mapped multi-level terminals, complex roof systems and evidence-backed passenger interfaces |
| [Parking garages](PARKING_GARAGE_GENERATOR_PLAN.md) | Existing drivable decks retained, with coordinated portals, smooth ramps, structural rhythm and several facade systems | Split levels, mapped external ramps, additional circulation types and larger complexes |
| [Petrol stations](PETROL_STATION_GENERATOR_PLAN.md) | Existing refuelling retained, with fitted modular canopies, coherent identities and shared pavement heights | Larger service areas, truck facilities, richer regional packs and evidenced ancillary uses |

Implement the shared contract and baseline first. Churches provide the simplest first architectural slice. Garage portal/ramp integration and petrol surface/trigger integration have priority over their decorative expansion because they directly affect driving. Terminal building-only improvements can proceed before full site planning; complex terminal roads wait for shared site support.

## Existing foundation and ownership

The inspected source uses `buildgen.plan.SCHEMA_VERSION = 12`. Ordinary v2 buildings already have evidence-led selection, topology-preserving footprints, facade openings, grounded access, roof work, commercial details, site layouts and landscaping. Specialized building routing still uses `buildgen/compiler.py::specialised`; churches, terminals and qualifying parking garages retain legacy recipes. Petrol stations run through `server/gasstations.py` and their Lua consumer, outside that selector.

The following documents define shared work. Read their current versions before implementation; schema numbers and module availability must be reconciled at that point.

* [Commercial first stage](COMMERCIAL_BUILDINGS_STAGE1.md) supplies elevation roles and fitted opening groups.
* [Commercial sites](COMMERCIAL_SITES_STAGE2.md) supplies optional surveyed site/access evidence and bounded terrain fitting.
* [Landscaping](BUILDING_LANDSCAPING.md) supplies reservations, edge treatments and restrained planting.
* [Pavement and site access](PAVEMENT_AND_SITE_ACCESS_PLAN.md) proposes shared `sitegen` ownership, surface cells, circulation, regional markings and fuel-site integration. `server/sitegen` does not exist at this checkpoint.
* [Commercial and industrial plan](../../building_generation_research/COMMERCIAL_INDUSTRIAL_PRESET_PLAN.md) supplies the larger function/style split and repeated-roof direction. Its original catalogue/schema counts are historical checkpoints.

Do not implement four independent road connectors, parking solvers or terrain graders. Use current adapters for building-only releases; add site features through the proposed shared site contracts when available. Commercial passenger terminals and freight terminals must have separate ownership rules. Share repeated roof components with commercial halls; keep specialist selection and evidence gates separate.

## Shared generation contract

Separate facility use, architectural form, material/style vocabulary, condition and site layout. Mapped evidence wins; calibrated regional priors choose compatible generic treatments when observations are sparse. Geography alone does not establish a church's denomination, a terminal's transport mode, a garage's internal layout or a station's operator.

Preserve source outlines, holes, parts, heights, roof direction and explicit colors/materials. Record unsupported observations instead of silently replacing them with random alternatives. Inferred detail may vary bay spacing, entry emphasis, cladding, trim and palette without requiring a surveyed parcel. New wings, towers, apron facilities, graves, forecourts and site boundaries require corresponding evidence. Decorative projections need a valid envelope and clearance; never cover a mapped passage or adjacent building.

Add proposed `buildgen/specialized.py` contracts and type-specific pure planners: `churches.py`, `terminals.py`, `garages.py`. Extend `gasstations.py` with a versioned station plan/adapter rather than a competing station entry point. Names are implementation proposals, not existing APIs. Suggested shared records are:

| Record | Required purpose |
| --- | --- |
| SpecializedSelection | Facility type, family, vocabulary, evidence lineage, confidence and reasons for fallback |
| PartRole | Source part identity and role, roof/body datum, parent relation and preserved voids |
| ElevationZone | Public/service/transport/party-wall role, compatible bay grid and opening reservations |
| ComponentPlacement | Stable identity, transform, bounds, material group, detail tier and collision behavior |
| TraversalPlan | Accepted portals, driving/walking routes, clearances, shared surface references and unresolved connections |

Freeze accepted records into the existing immutable compilation boundary. Extend freezing, serialization, worker round trips, cache revisions and near/lite/collision consumers together. Bump the schema from the version present at implementation time. Do not add executable catalogue rows before their loader, constraints and compiler capability exist.

Replace the boolean dispatch progressively with capability checks. For each type, select the new adapter only when its declared geometry capabilities fit the evidence. Keep the specialized legacy route for unsupported cases, with a reason; a failed adapter must not silently become an ordinary office or house. If a legacy fallback itself cannot represent a source hole or elevated passage, preserve that topology through a conservative shell or existing infrastructure representation and report the limitation. Never accept legacy output solely because it exists.

Use source/site identity plus separate semantic seeds for form, facade rhythm, palette, roof details and condition. A detail-density or LOD change must not move entrances or change brands. Derive grouped materials coherently across mapped parts while allowing supported extensions or recladding to differ. Weathering follows exposure, joints, drainage and material; avoid unrelated random stains on every panel.

## Geometry and gameplay acceptance

Resolve surfaces and routes before placing objects. Full envelopes of columns, doors, stairs, islands, parapets and vehicles must fit their allowed regions; centre-point tests are insufficient. Preserve pedestrian paths, drainage corridors and existing transport surfaces. Derive visual and collision geometry from the same accepted placements and surface heights.

Treat explicit mapped geometry separately from inferred layouts. Where an inferred driving route fails fit, do not display arrows, open portals or functional triggers that promise that route. Preserve credible existing working behavior until its replacement passes equivalent checks. Regional dimension profiles need provenance and applicability; proposed gameplay tolerances are not statements of building-code compliance.

No requirement here adds full church/terminal interiors, working lifts, passenger simulation, aircraft operations or dynamic fuel delivery. Garage decks remain playable; fuel interactions remain functional. Thin visual detail uses simplified collision only where it physically blocks the player. LOD may reduce ornament, but must preserve traversable space, major silhouettes and recognizable openings.

## Performance and caching

Initial work limits are proposed engineering budgets to validate, not measured results:

| Work | Starting bound and fallback |
| --- | --- |
| Inferred layout search | At most 4 candidate arrangements per work region; no global optimization or repeated random retries |
| Optional part-role inference | At most 32 source parts per work region; larger explicit assemblies are partitioned or retain their existing representation |
| Repeated roof inference | At most 32 bays per simple volume, following the commercial plan; simpler compatible roof if unsupported |
| Simple site terrain | Reuse the existing 512-point / 24-patch tier, deduplicated across consumers |
| Large sites | Use the pavement plan's proposed maximum of 8 sectors with shared boundary samples; exceeding it requires deferred partitioning or declining optional detail |
| Optional collision queries | At most 64 obstacle records per local candidate; an overfull query rejects or partitions that candidate rather than ignoring obstacles |
| Mesh output | Retain the existing 20,000-vertex near-chunk target and staged import; split geometry rather than drop mapped parts |

Budgets apply to aggregate work as well as individual regions. Cache plans by source/context revision, catalogue/assets, profile version and terrain revision; cache negative fit results too. Canonical site identities and cross-tile ownership are implementation dependencies, not capabilities supplied by the present local-frame `BuildingPlan`. Until those land, keep cross-tile inferred site expansion disabled where consistency cannot be established.

Reuse batched static meshes/materials and existing worker/staging paths. No per-frame procedural planning, per-window scene objects or per-building remote imagery requests. Profile candidate counts, terrain cost, CPU median/p95, memory, vertices, material groups, output size, collision rebuilds and streaming stalls. Compare both equal-detail scenes and increased-coverage scenes.

Retain the pavement plan's provisional 10% p95 simple-scene generation/collision regression gate and the wider building proposal's 5% steady-driving p95 frame-time gate on fixed hardware/route/settings. These are distinct metrics. Calibrate special-scene absolute budgets from fresh measurements; no performance claim follows from documentation or synthetic rendering alone.

## Shared implementation tickets

1. **Capture and classify.** Preserve fixed-camera baseline captures and deterministic fixtures for all four types. Record actual dispatch, dimensions, source evidence, functional behavior and rejected routes. Include mislabeled and missing-data cases.
2. **Introduce contracts without changing appearance.** Adapt existing special recipes and station output into the shared records. Verify deterministic serialization, collision parity, package inclusion and cache invalidation. Keep public behavior compatible.
3. **Deliver one vertical slice per type.** Follow each plan's first ticket. Compare old/new views at street, overhead and distant scales, plus actual driving/refuelling where applicable.
4. **Expand families and site integration.** Add families only when their fitting rules, missing-evidence fallback and test fixtures exist. Reuse shared access, roof and surface work.
5. **Validate and package.** Extend existing building, roof, facade, access, site, landscaping, topology, chunk, codefiles, gas-station and Lua staging suites as appropriate. Add focused specialist suites. Record in-game checks separately from synthetic/test results, and produce a private integrated playtest package with matching server/mod assets.

For every family, review at least three different footprints and three stable appearance seeds, including one constrained or missing-evidence case. Add at least one observed reference fixture per family and a held-out location per validated regional pack. Compare a neighborhood/complex contact sheet to expose repeated compositions. Catalogue size alone is not a variety acceptance criterion.

The first release is complete only when the relevant family is visually recognizable without labels, source geometry remains intact, documented playable routes work, cache/rebase/streaming behavior is stable and the measured budgets pass. Keep deferred families explicitly listed in each release report.
