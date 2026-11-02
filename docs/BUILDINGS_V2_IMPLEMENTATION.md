# Building generation v2 implementation status

## Progressive display and mesh budgets — 1 November 2026

V2 road geotiles now publish solid coloured shells, lightweight facades/access,
then completed detail in bounded replacement groups. The matching client swaps
complete groups within its shared import budget and adopts finished objects into
the final tile. Doors wait for their building visuals. Oversized buildings retain
reduced LODs, and shutter slats/paving joints use shared textures. Existing schema
12 commercial, residential and landscaping work is retained.
Read [loading design, budgets and measured costs](PROGRESSIVE_BUILDINGS.md).
The private combined checkpoint is `BeamNG.Earth-v2-progressive-20261101.zip`.
In-game performance and appearance acceptance remain outstanding.

## Prepared pavement and site expansion — 1 November 2026

The [pavement and site access implementation plan](PAVEMENT_AND_SITE_ACCESS_PLAN.md)
covers independent vehicle entrances, smooth curb/pavement geometry, commercial
and industrial paving, shared malls/shopping centres/retail parks, large parking
areas, and regional fuel-station layouts and identities. It records current code
integration points, civil-engineering references, work budgets and validation
gates. This is preparation only; generator behavior remains at schema 12.

## Shared residential/commercial landscaping — 1 November 2026

Schema 12 adds nine identity-led frontage treatments: fitted concrete shoulders,
grass/gravel margins, garden beds and bounded near-detail planting. Existing
driveways trim and preserve compatible landscaping; supplied commercial sites
can receive residual pedestrian-side beds without obstructing service access.
273 focused tests pass across 19 suites. Read [landscaping scope and costs](BUILDING_LANDSCAPING.md).
The current private package is `BeamNG.Earth-v2-landscaping-20261101.zip`.
Game playtesting remains outstanding; earlier sections are historical checkpoints.

## Commercial property layouts integrated — 1 November 2026

Schema 11 adds property-fitted docks, service approaches, parking and pedestrian
connections through optional source-linked `--building-sites` evidence. No fixed
site templates or parcel inference are used. The combined residential updates
remain integrated. See [site layout implementation and input format](COMMERCIAL_SITES_STAGE2.md).
266 focused tests pass across 18 suites. The current private package is
`BeamNG.Earth-v2-commercial-sites-20261101.zip`; later references below describe
historical checkpoints. Game playtesting remains outstanding.

## Commercial first stage integrated with residential updates

1 November 2026: schema 10 and 51 recipes include procedural warehouses,
supermarkets and trade units. Facade roles, terrain-checked service entries,
wide supermarket entrances and bounded module fitting share the existing access,
collision, LOD and packaging pipeline. Residential roof sampling, environments
and driveway behavior are retained. See [commercial first stage](COMMERCIAL_BUILDINGS_STAGE1.md)
for scope, performance limits and validation. The following sections describe
the earlier residential checkpoints retained by this combined implementation.

## Roof colours, environments and driveways — 1 November 2026

Schema 9 uses accepted offline aerial roof samples first, mapped `roof_color`
only as fallback, then the material palette. It adds 48 total preset recipes,
22 environment states, explicit Christchurch/NYC adapters and guarded regional
material priors. The private pilot includes 6,654 Christchurch zone polygons and
20,278 accepted roof records; worldwide statutory coverage is not implemented.
Read [roof evidence and regional mapping](BUILDING_ROOF_COLOURS_AND_ENVIRONMENTS.md).

Eligible inferred detached houses have garages again. Narrow mapped garages
receive unobstructed shutters. Nine-section driveways join garage sills to
actual street/footpath profiles; dropped crossings preserve the rear walking
strip, and optional links reach resolved front entrances/landings. See
[driveway design and measured costs](BUILDING_DRIVEWAYS.md).

275 focused tests pass across 17 suites. Additional real-data road checks lack
cached transport blocks, and the separate revisit suite has an existing Windows
sidecar cleanup lock. No game validation or rebuilt executable is claimed.
The newest private package is
`BeamNG.Earth-v2-roof-zones-driveways-20261101.zip`. Earlier sections below are
historical checkpoints; preserve their artifacts for comparisons.

## Construction-detail continuation — 1 November 2026

Schema 7 adds terrain-sampled frontage paths and visual yard margins to the shared
access plan. Lightweight-cladding corner boards, complex-roof fascia, roof caps,
valley flashing, merged/mitered gutter runs, downpipes/receivers, beveled paving
edges, joint seams and stair handrails now render nearby. Thresholds and suitable
flat garage aprons receive outward falls. The source-road path solver rejects
missing terrain, excessive grading and known obstructions. See
[engineering references and limits](BUILDING_DETAIL_ENGINEERING.md).

174 focused tests pass across ten suites: sitework, access, facades, complex roofs,
presets, context, immutable plans, building kernels, chunk transport and CDAE.
Tests include generated surface continuity, clearance, grading, finite geometry,
roof-top/footprint preservation and detail budgets. No game acceptance has run.

The new 250-distinct-L-house flat-ground benchmark includes frontage/access:
3.75 s planning, 0.54 s access (one terrain call, 28,250 points), 61 ms freezing and
4.13 s near/lite/collision compilation. Vertex counts are 1,082,412 near, 72,960
lite and 35,000 collision. Fine detail increases worker and rendering cost; these
are not driving frame times. Collinear path simplification reduced the initial
detail benchmark's 100,000 collision vertices to 35,000 without dropping terrain
samples. Existing mesh chunk budgets and frame staging remain unchanged.

Private previews: `artifacts/buildings-sitework-preview.png` and
`artifacts/buildings-detail-preview.png` in the parent project folder. The fresh
private playtest archive is `BeamNG.Earth-v2-site-details-20261101.zip`. The prior
zone-preset archive remains a comparison checkpoint.

## Local continuation — 1 November 2026

The source snapshot now extends 816b344e with schema 6 preset selection, normalized
zone overlays and an importer, 36 facade/function recipes, grounded nonresidential
entries, closed window sills, warm-climate sun hoods, and bounded orthogonal
multi-wing hip roofs. See [presets and zones](BUILDING_PRESETS_AND_ZONES.md) for the
current implementation, data contract and limitations. The sections below retain
the original checkpoint record; their schema 5 and single-envelope statements
describe that earlier version. No Git commit or PR was created in this snapshot.

Current checks: 203 tests pass across the building, topology, inference, context,
preset, facade, access, roof, chunk, source-identity and CDAE suites. Five worker
tests also pass with `BNE_REVISIT=off`; their default-cache run encounters Windows
file-lock errors while cleaning up revisit logs. Broader far-geotile real-data
checks cannot complete because the required offline Overture data is missing.
These are not passed game or geographic release gates.

A cold synthetic 250-distinct-L-house batch on this Windows Python 3.14.7 runtime
measured 3.83 s planning, 58 ms freezing and 662 ms near/lite/collision compilation.
The scene excludes frontage/access, export and engine work; it is not directly
comparable with the earlier cloud benchmarks. Preview images and JSON reports
are outside the source tree in the parent artifacts folder.

## Original checkpoint record

Working branch: `feat/building-plan-foundation`, based on `55ddc418`.
Working repository: `PaperboyNZ/BeamNG.EarthBuildTest` (`origin`).
Eventual PR target: `TecnaGamer/BeamNG.Earth`, base `dev` (`upstream`).

The PR is to remain unpublished until the feature and its release validation are complete. This is an internal implementation checkpoint, not a release-ready v2 generator. The full requirements remain in [the design](PROCEDURAL_BUILDINGS_V2.md).

## Implemented

- `buildgen.plan.BuildingPlan` snapshots resolved dimensions, appearance, terrain samples, inference and specialised metadata into an immutable compiler input. Arrays are detached and backed by immutable bytes; nested collections and worker pickle round-trips preserve immutability. Schema version 5 adds grounded entrance, stair and apron geometry beside the shared facade layout.
- The road-tile compiler freezes its inputs after entrance resolution. Full visual geometry, embedded lite geometry, collider bounds and collision geometry consume the same snapshot. Far and skyline entry points also produce frozen inputs.
- Skyline simplification derives its own outline without changing the source plan's ring, roof or entrances. The source plan remains usable by another representation afterwards.
- `buildgen.evidence` records mapped attributes separately from resolved geometry. Missing values, invalid values and observed zero values are distinguished. Height-source provenance, roof orientation/direction, feature IDs and parent/part IDs survive planning. A fallback height is not recorded as a mapped observation; part top heights remain available before conversion to thickness.
- The `.cdae` exporter carries explicit normals, secondary UVs and tangent UVs through embedded LODs, matching the primary mesh contract.
- Development cache keys and packaged source identities include nested `buildgen` source and JSON catalogue files. PyInstaller collects the new package.

The default `legacy` path preserves the existing architectural rules and geometry. Mapped colour keys now carry exact RGB values so separate workers recover the same colours. The compiler plan is expressed in the caller's local tile frame; it is not yet the persistent, globally canonical building plan specified by the final design. Independently requested near and far tiles still have different infrastructure/clearance selection paths.

## Experimental geometry and transport

Enable this checkpoint with `python start.py -- --building-generator v2`, or set `BNE_BUILDING_GENERATOR=v2`. Use the matching mod from this branch. The default remains `legacy`; changing the switch or the Shapely/GEOS runtime invalidates generated cache entries.

- `buildgen.topology.Footprint` validates and canonicalises exterior rings and holes. It rejects invalid geometry with a source-ID warning rather than filling a void. Source component identities are independent of winding, ring start, component order and tile-local coordinates. All disconnected wings share one parent owner; mapped multipart building parts expand once, with original source evidence retained.
- Roofs and elevated undersides use constrained triangulation. Exterior walls and courtyard walls retain their source boundaries in near, lite, skyline and collision geometry. Small bevel edges omitted by the existing window kernel receive plain closure strips. Roof UVs use one footprint origin across triangles. Skyline window materials and lighting mappings are retained.
- Road/tunnel clearance checks, bridge-passage clipping, occupied-area coverage, terrain sampling and water probes account for courtyards. Passage clipping may produce several disconnected pieces. Collision activation carries optional polygon rings beside each broad-phase box; a car in an open courtyard or below an elevated part no longer holds collision merely because it is inside that box.
- Ordinary gabled/hipped roofs partition two/four supporting planes over the occupied footprint, including concavities and courtyards. Source total heights remain consistent with ridge height. Rectangles retain overhangs and gain fascia/soffit geometry. Outlines above 256 vertices retain a diagnosed flat fallback. This is a clipped roof envelope, not a straight-skeleton solver or reconstructed cross-gable system. Complex outlines omit decorations whose placement assumes a rectangle. Ships, piers, bridge structures, parking decks and toll booths retain specialised compilers with a routing diagnostic.
- Near road tiles carry a versioned `buildingChunks` manifest containing every visual and collision chunk. Geotile writing, cache storage, pooled paths, exact placement variants, client loading, rebases and unloading carry the extra chunks. The server requires `hello.buildingChunks: 1` in v2 mode; older mods receive a compatibility status before generation starts. Legacy transport remains unchanged.
- Oversized individual near buildings split without losing triangles, UVs, materials or colours. Such split buildings currently retain full geometry at distance rather than duplicate an unmatched embedded LOD in every chunk. Collision meshes also split at the vertex budget. The client keeps far buildings visible until every listed near visual chunk exists.

Shapely >=2.1 with GEOS >=3.10 supplies polygon validation, clipping and constrained triangulation. This dependency is justified by the courtyard/concavity coverage and passage-splitting tests. PyInstaller collects the package, GEOS libraries and licence metadata. The local runtime used for these checks is Shapely 2.2.0 / GEOS 3.14.1.

This is still an experimental compiler using the existing game material assets. Source identities have not yet gained the design's fixed-precision global frame, longitude-wrap handling or persistent plan store. Full atomic replacement of an existing building set, spatially matched LOD chunks, dense far-tile transport and checks for every nearby vehicle remain release work. The client currently retains its player-vehicle collision policy.

## Context and inference baseline

Ordinary v2 buildings now use `buildgen.inference` and `buildgen.compiler`, independently of the legacy country boxes, tile-density rules and area-only warehouse guesses. Special landmarks and infrastructure retain their existing recipes with an explicit diagnostic.

- `buildgen.context` loads an explicit `observed-buildings-landuse-climate-v1` profile. Its owner is a fixed source-map cell with a 250 m halo; evidence is sampled within 250 m of the source building, with stronger use support inside 75 m. The profile reads buildings, land use and the bundled Köppen climate grid. It does not depend on roads, POIs, imagery or previously generated buildings.
- Context is immutable and includes content/revision/climate fingerprints. A bounded per-MapData spatial-index cache coalesces concurrent loads. Fetch failures propagate and failed entries can retry. Skyline jobs prefetch missing context and defer instead of finalising a partial plan. Changes to the bundled climate grid also invalidate development and packaged source identities. The near-world credits include land-use provenance and climate attribution when v2 buildings are shown, including when vegetation is disabled.
- Neighbour evidence excludes the target, repeated IDs, exact duplicate geometry and underground features. Land-use overlap preserves holes and unions duplicate/clipped polygons. A large/disconnected target extending beyond the context extent cannot use partial land-use coverage to classify the whole building; its plan records that limitation.
- Use decisions distinguish mapped, inferred, unknown and conflicting results. Explicit class/subtype observations constrain use. Conflicting mapped categories remain unknown; land use and a supported neighbourhood consensus can infer a broad use. Footprint size alone cannot establish residential, commercial or industrial use. Candidate scores and reasons remain in the immutable plan. Strength labels describe rule support, not calibrated probabilities or verified source quality.
- Architectural families describe facade construction (`masonry_punched`, `timber_punched`, `rendered_punched`, `concrete_punched`, `metal_utilitarian`, `glazed_frame`). Mapped materials and supported roofs take priority, followed by observations from at least three neighbours of comparable area and use, then conservative defaults. Climate only adjusts weak roof/pitch priors. These families do not claim a historical period or a national style.
- Missing heights can use the median of comparable **observed** neighbouring heights. Mapped total/roof heights remain consistent with the mesh ridge. Conflicting floor counts yield feasible spacing with a diagnostic while their original observations remain intact. Impossible mapped top/minimum ranges are skipped with a source warning. Roof direction/orientation remain recorded but their alignment is not yet implemented; affected pitched roofs carry a diagnostic.
- Source dimensions are measured in the context cell frame before resolving architecture. Near, far and skyline requests share that evidence and inference path, including mapped parts in the skyline. Part records distinguish inherited use/materials, measured height ranges, floor-derived heights and unmapped flat-roof fallback. This establishes inference agreement in the fixtures; it does not yet unify every infrastructure adjustment or independently persisted plan.

For inspection in Python, `dataclasses.asdict(spec.inference)` exposes decisions, candidate scores, supporting source IDs, context fingerprints and diagnostics. `spec.evidence` retains the original source observations. Direct geometry-only callers without a provider use an explicitly diagnosed `footprint-only-v1` profile; production v2 entry points supply the provider.

## Street-level presentation checkpoint

The first in-game playtest exposed a visual regression: uniform beige blocks and windows overlapping off-centre entrance props. A supplied residential reference informed the following general templates; it is not treated as measured evidence for individual buildings. Private location data and imagery are not included in the repository.

- `buildgen.facades` composes windows around the actual door and garage intervals, with corner margins and storey headroom. Close walls contain apertures, recessed panes, returns, frames and projecting sills. Lite geometry preserves opening positions and material membership, with shallower panes and simplified doors. The stock near door remains a separate prop.
- Plausible low detached forms can receive a single/double garage beside a separate pedestrian entrance when the frontage and setback permit it. Driveways and fence gaps align with the garage. Independently requested near/far tiles resolve entrances from source ground roads; rendered road adjustments preserve an existing pedestrian entrance. This is inferred access, not parcel-level reconstruction or verified driveway data. Garages remain closed surfaces without interiors.
- Explicit low house classes or sufficiently sparse observed surroundings support a detached morphology prior. Missing dimensions favour one storey, with bounded hipped/gabled roof variation. These are weak presentation priors; mapped dimensions, materials and roof observations still take priority, and unknown building use remains unknown.
- Fallback wall recipes now vary coherently among brick, timber and render, with other use-dependent families. Trim and garage finishes have separate bounded palettes. Existing game texture assets are reused; authored PBR recipes, surface roughness, lighting cohorts and asset verification remain unfinished.
- Roof UVs measure physical distances along the slope. Upper gable/courtyard walls continue the facade's texture run and height. Tiny numerical slivers from plane intersections are excluded under the occupied-area tolerance; square hips no longer require degenerate ridge quads.
- Following the next game screenshot, roof UVs use analytical supporting-plane frames rather than normals reconstructed from individual triangles. V now runs uphill from each eave, preserving the stock roof mapping convention. Coverings have separate repeat sizes (zinc/copper 1.2 m, tile/slate 2.4 m, shingle 3 m); these replace the oversized universal 6 m repeat and still require calibration against the actual game assets.
- `buildgen.access` samples entrance widths, potential stair runs and garage aprons in one terrain call per tile. Near generation uses the drawn terrain; source/far planning uses the supplied elevation provider. Missing samples fall back to the frontage's corner samples with a diagnostic. Moderate raised entrances receive short stairs with risers at most 20 cm; large differences or insufficient space lower the entrance in the foundation wall. Garage thresholds meet local ground through sloped aprons. Projections avoid other occupied footprints and road corridors. The facade, stock door, lite geometry, collision mesh and activation bounds share these resolved heights and surfaces. Extreme cross-slopes, complete parcel access and retaining structures remain further work.

Generate a review sheet with `.venv/bin/python tools/building_preview.py --out /tmp/buildings.png`. Use `--access-fixtures` for sloped entrance cases and `--roof-fixtures --roof-grid` for twelve complex footprints with a diagnostic UV checker. `--server /path/to/older/server` compares the same synthetic fixtures against an earlier source tree. These previews use approximate material means and simple lighting; they cannot validate the game's textures, door assets, shadows or night lighting. The expanded roof images expose a remaining visual limitation: a single clipped roof envelope can create oversized upper walls around deep recesses/courtyards. Passing coverage and UV tests does not establish believable roof design; individual-wing ridges and valleys remain necessary.

## Worker and frame scheduling

Generation retains the existing near-road worker process pool and separate distant-building pool; configured fallback paths use background thread executors. New access sampling is batched, with a spatial index for obstruction checks. No per-building executor or thread pool is created.

V2 near visuals now target 20,000 vertices per mesh. The client shares one synchronous mesh-import slot per frame across near, far and collision meshes, including material prewarming. Prewarm requests queue instead of importing from the network message callback. Collision rebuilds get a separate frame; an already-due rebuild pauses imports so continuous arrivals cannot starve activation. The governor's time allowance and urgent drivable-collision priority still apply. A stubbed test uses an unlimited allowance to ensure a dense building set still arrives over several frames, including its distant representation, and activates collision without stacking a rebuild with an import.

Engine imports and collision rebuilds themselves are indivisible synchronous calls. These limits prevent bunching; they do not establish a hard frame-time guarantee. Import timing, queue latency, dense far tiles and representative driving still need game measurement.

## Verification

Run the focused suites from the repository root:

```sh
.venv/bin/python tools/run_tests.py test_buildgen test_buildgen_access test_buildgen_roofs test_buildgen_facades test_buildgen_topology test_buildgen_chunks test_buildgen_context test_buildgen_inference test_buildings test_cdae test_codefiles test_revisit test_ships test_geotiles test_fargeo test_sign_packaging test_roads test_roadgeo test_outer_centres test_protocol test_blockworker test_pools test_budget --par 2 --timeout 120
.venv/bin/python tools/run_tests.py test_protocol_agreement --par 1 --timeout 180
```

Coverage includes immutable/deeply detached plans, source evidence, original part heights, shared near/lite/collision inputs, skyline non-mutation, compatibility of ordinary and specialised geometry, exporter shading round-trips and cache invalidation after nested source/catalogue edits. New fixtures cover exact occupied roof area, courtyard wall winding, elevated undersides, real geodetic ownership across neighbouring tiles, roads/decks inside holes, disconnected passage cuts, source-order invariance, oversized-building splitting, complete chunk files and later-chunk exact variants.

The context/inference suites add 32 checks for conflicting tags, weak/missing evidence, supported local materials, measured versus inferred heights, part inheritance, mapped colour recovery across workers, complete concurrent context loading, failure/retry, duplicate/self exclusion, land-use courtyards, revision/grid invalidation, and identical inference across near/far/skyline requests and rebased frames. They use synthetic geodetic fixtures, not a geographic accuracy evaluation.

At this checkpoint the 23 focused Python modules pass with 332 passing tests and five skips. Roof fixtures include L/T/H/U wings, narrow links, multiple/oblique courtyards, acute diagonal joins, bay fronts, bevels and sawtooth outlines. The mapping test exercises 648 combinations of footprint, rotation/scale/translation, gable/hip, covering and rise, alongside coverage, LOD top-height and exported normal/tangent checks. Access tests cover terrain batching, thresholds, stair dimensions, apron joins, obstruction/road clearance and shared collision bounds. Six climate/feature-attribution checks passed at the earlier inference checkpoint.

The five focused skips are one LuaJIT-dependent check and four real-data road/far-geotile checks whose cached data is absent. The earlier protocol integration suite passed with local loopback access; it was not rerun for these geometry/scheduling changes. Under the installed Lua 5.4 shared-library test runtime, building staging, roads, road geotiles, far geotiles, governor, scoping and collision-foci checks pass (673 assertions). A broader core stub test has one existing snap-target assertion failure: 279 pass, one fails identically on the unchanged `87abd05d` baseline. The runner supplies Lua 5.1 compatibility helpers; this is not BeamNG/LuaJIT acceptance. Game presentation, executable startup and global reconstruction accuracy remain unverified.

A local synthetic measurement of snapshot creation alone for 250 ordinary buildings took approximately 6–7 ms on this cloud machine. It excludes inference, rendering and game import and is not a release performance result.

A separate synthetic 250-courtyard scene measured approximately 70 ms warm planning and 214 ms near/lite/collision compilation in v2, compared with 25 ms and 170 ms for legacy, which omits the courtyards. V2 produced 275,776 near vertices in five chunks and 14,000 collision vertices. This exposed the old four-chunk truncation and motivated the complete near-chunk manifest. These measurements exclude disk export, network, game import and representative driving workloads.

The context baseline was also measured on a separate synthetic 250-house scene with repeated source features across nine cells: approximately 1.0 s for cold context construction plus planning, 0.53 s for warm planning, and 0.10 s for near/lite/collision compilation. Avoiding repeated centroid/intersection work reduced warm planning from approximately 0.58 s. This fixture differs from the earlier courtyard benchmark and excludes IO and game import; context cost and memory still need representative dense-city performance work before release.

The presentation checkpoint's synthetic 250-house batch measured 118 ms for planning/frontage, 46 ms for frozen facade layouts, and 767 ms for near/lite/collision compilation. It produced 184,886 visual vertices in four chunks and 8,782 collision vertices. Repeated shapes benefit from the bounded roof cache. This batch excludes source/context fetching, export and game import and is not directly comparable to the earlier scenes. Detailed facades add compilation and geometry cost; representative driving and dense-city budgets remain unverified.

A separate 250-house sloped grid with distinct translated footprints measured 71 ms planning, 98 ms frontage/access (one terrain call, 8,250 samples), 38 ms freezing and 3,357 ms near/lite/collision compilation. It produced 195,084 visual vertices in eleven chunks (largest 19,706) and 32,156 collision vertices. This cold geometry workload exercises substantially more roof-cache entries and access surfaces than the repeated-shape batch; it is not a game frame or a passed performance gate. Roof compilation/cache efficiency and access collision cost still need optimisation and representative measurements.

## Remaining work before publication

1. Complete canonical global plan/context identities, source precision/longitude-wrap handling, persistence and specialised-topology compatibility. Finish the original milestone 1 gates beyond the experimental local-frame topology now implemented.
2. Expand and calibrate the context/inference baseline: frontage/access, adjacency, multi-scale context, POI association, mixed uses, source-quality policies, architectural catalogues and geographic hold-out evaluation. Current rule-strength labels are not calibrated confidence probabilities.
3. Extend the initial opening layouts and roof envelopes into the full massing, multi-wing roof, facade, material and alignment systems; integrate specialised structures, mapped roof alignment, parcel-aware access and exact collision constraints.
4. Extend complete chunk transport to dense far tiles, implement atomic set replacement and spatially matched LOD chunks, and validate dense tiles and multi-vehicle collision in the game.
5. Add verified material recipes, detail assemblies, lighting cohorts and quality profiles. Complete the building mesh adapter's full shading payload and probe normal/tangent transforms through geotile placement.
6. Run the calibration scenes, visual comparison routes, day/night and LOD-motion tests, supported platform packaging and performance gates in BeamNG. Only then prepare the upstream PR.

No feature-complete claim or PR publication should be based on the foundation tests alone.
