# City buildings and integrated public realm implementation plan

Prepared 1 November 2026 for the active `BeamNG.EarthBuildTest` source.
Implementation has started: [the first city slice](CITY_BUILDINGS_IMPLEMENTATION_STATUS.md)
adds detached city plans, five bounded facade compositions and all 64 descriptive
region records in schema 18. The milestones below retain the full intended scope;
their remaining site/material/assembly and native-game gates are still open.

Build convincing skyscrapers, offices and hotels as coordinated architecture:
building form, floor structure, facade systems, entrances, roof assemblies,
materials and their surrounding paved and planted spaces. Extend the existing
generators and their shared records rather than introducing a parallel city or
site generator.

**Regional authoring basis:** include all 64 regional identities using their
written architectural and geographic descriptions. Per the user's clarification,
do not derive this city expansion from the already defined regional styles,
compiled recipes, parameter values or material weights. The city-specific briefs
below are proposed interpretations of the text, not copies of those styles.

**Target baseline:** the current pavement, landscaping and shared-site work will
be completed before this implementation consumes it, as requested by the user.
Connected lobby approaches, hotel drop-offs, service access, plazas and planting
are therefore part of the intended city release. Reconcile the finished upstream
interfaces at the integration checkpoint; do not duplicate that work or reduce
this plan to today's narrow frontage capabilities. The current-state audit below
distinguishes inspected code from that expected completed baseline.

The [integrated checklist](GENERATION_IMPLEMENTATION_CHECKLIST.md) remains the
execution index. The [commercial brief](COMMERCIAL_GENERATION_OVERHAUL_PROMPT.md)
and [pavement plan](PAVEMENT_AND_SITE_ACCESS_PLAN.md) retain their evidence,
ownership, access and physical-lifecycle requirements.

## Current source and changes to carry forward

The original plan inspected schema 14; the regional continuation inspected for
this revision is **schema 16**. Regional runtime documentation still mentions its
schema 15 checkpoint. Inspect the version again when implementation starts.
Preserve the edited source snapshot rather than restoring an older bundle.

| Existing work | City integration requirement |
| --- | --- |
| Evidence, contextual presets, environments and zoning | Preserve observed use/material/dimensions and their provenance. Zoning can guide compatible choices but cannot establish actual occupancy. |
| Palette of 64 regions | All 64 existing themes are active. Reuse stable regional identity and geographic selection; author city behavior from the text/geographic descriptions, without inheriting the defined styles. Preserve existing ordinary-building regional behavior outside the city adapter. |
| Complex roofs and roof colours | Retain footprint holes, source roof form/direction/height, supported multi-wing solutions, material UV scales, accepted aerial colour precedence and mapped-colour fallback. Roof plant must fit those resolved surfaces. |
| Construction and access detail | Reuse grounded entrances, sills, thresholds, paths, handrails, gutters and roof-edge primitives where compatible with city construction. Avoid applying domestic trim indiscriminately to towers. |
| Commercial compositions | Extend the existing punched, ribbon and curtain office families and retain strip shops, supermarkets, logistics and trade-unit behavior. Offices above twelve floors currently fall back; hotels lack a dedicated city composition. |
| Garage traversal repair | Preserve its frozen portal/apron/deck/ramp plan, route and headroom reservations, shared visual/collision geometry, curb updates and parking exclusions. A city skin cannot close its entrance or deck voids. |
| Church and terminal adapters | Preserve specialist precedence, current fabric/use distinctions, roof behavior, accepted assemblies and diagnosed fallbacks. Converted churches used as offices retain their fabric; a hotel name containing “Terminal” remains ordinary hotel evidence. |
| Landscaping | Extend existing identity-led treatments, physical shoulders and bounded optional plants. Keep beds subordinate to accepted walking/vehicle routes and source exclusions. |
| Shared terrain and local coordination | Preserve `sitegen.surfaces` exact sample reuse, unknown-height handling and `sitework.coordinate` reservations, including garages without pedestrian access plans. |
| Hardscape export | `sitegen.hardscape.collect` exports accepted hard surfaces with holes and height ranges through road content as `vegetationExclusions`. Feed new accepted city pavement into this same path; keep lawns and planted beds soft. |
| Shared site contracts | Reuse `SiteEvidence`, `SitePlan`, memberships, interfaces, resource records, canonical frames and legacy adapters. Current record support alone does not establish fitted surfaces or runtime retention. |
| Progressive loading | Preserve twelve-building groups, reduced-LOD reuse, 20,000-vertex near import chunks, stale-token rejection, cancellation, complete-group swaps and essential final geometry. Collision has its separate existing chunk path. |

Status references: [commercial](COMMERCIAL_ARCHITECTURE_PROGRESS.md),
[garages](GARAGE_ACCESS_IMPLEMENTATION.md), [churches](CHURCH_IMPLEMENTATION_STATUS.md),
[terminals](TERMINAL_IMPLEMENTATION_STATUS.md),
[pavement and landscape](PAVEMENT_LANDSCAPE_PROGRESS.md),
[resources](GENERATION_RESOURCE_PROGRESS.md), [progressive display](PROGRESSIVE_BUILDINGS.md),
[site records](SITEGEN_RECORDS.md) and [identity](SITEGEN_IDENTITY_CONTRACT.md).
Use current code and fresh baselines to resolve documentation drift.

## The 64 regional descriptions as a city design foundation

Use [the regional catalogue](REGIONAL_ARCHITECTURAL_THEMES.md) and the descriptive
fields in [environments.json](../server/buildgen/catalog/environments.json): stable
ID, `label`, `group`, `coverage`, and the prose `style_directions` and
`detailing_goals`. Those last two fields are broad written design context; they
are not permission to import their implemented styles. Preserve the distinction
between the source's words and our new interpretation for a city building.

[City regional design briefs](CITY_REGIONAL_DESIGN_BRIEFS.md) accounts for every
one of the 64 IDs with an urban interpretation and a pavement/landscape scope.
It is the starting authoring matrix for this expansion. Entries are qualitative
proposals, not construction standards, measured prevalence or executable presets.

### Selection and precedence

Reuse `environments.resolve` and `regional_geography` to obtain regional identity
from source location or an explicit regional overlay. Geographic selection is
independent of any defined architectural style. Keep overlay priority, ambiguous
border/conflict handling and unknown-region fallback. Never select by render-tile
centre or move regional identity during rebasing. Geographic prose describes
intended scope, not new polygon boundaries: legacy phrases such as “NYC adapter
footprint only” and “Christchurch pilot only” are historical runtime annotations,
not the current geographic extent of those regional identities.

Resolve city design in this order: observed building/site constraints; supported
programme and structural family; verified local context; compatible regional
text interpretation; ordinary shared defaults. Existing accepted neighbour
material/roof evidence retains precedence over regional fallbacks. Region cannot
establish a building's use, age, height, ownership, concealed structure or a new
connection. Source roof colours and explicit surface materials still win.

Broad areas explicitly contain several localities: wet/dry, coastal/interior,
highland/lowland and dense/low-density distinctions must remain available. Select
a subvariant only with relevant location/environment evidence. A broad region
name alone does not establish climate, planting species or a building's exposure.
When the text does not support a city treatment, retain the neutral family and
record that limit rather than force visible regional decoration.

### Translate the text by building role and scale

Treat a regional interpretation as a modifier of the five architectural families,
not 64 additional whole-building templates or a mandatory family per country.
A contemporary tower can share its structural and glazing system with another
region while differing in its public base, shade, solid materials, entrance and
landscape relationship. Masonry offices and hotels can express more of the prose
through bay rhythm, depth, masonry articulation and roof termination. Podiums and
street fronts can differ from upper towers while using one coherent site plan.

| Domain | City interpretation to author from the text | Constraints |
| --- | --- | --- |
| Composition | Bay grouping, solid/glazed balance, base/upper distinction, horizontal/vertical emphasis and restrained roof termination | Fit actual floor datums and family; no copying residential window dimensions or turning vernacular roofs into skyscraper crowns. |
| Materials | Candidate cladding roles, masonry/stone/render character, frame/accent relationships and later city-specific glass/spandrel palettes | No inherited RGB values, material weights, roughness factors or roof recipes. Unsupported materials remain an identified asset need, not a renamed substitute. |
| Shade and weather protection | Recessed entries, fins, screens and attached rain/sun shelters where the prose and locality support them | New dimensions are authored and checked for the city system; accepted routes, support and headroom control projections. |
| Roof and services | Compatible parapets, edge treatment, equipment screening and supported roof-covering choices | Explicit source shape, height and roof-colour evidence wins. Reuse roof geometry kernels only for a newly justified compatible choice. |
| Pavement and arrival | Street-wall arrival versus evidenced court/plaza, covered approaches, paving character and joint direction | Shared coordinator owns surfaces, levels and connections; prose does not establish a regional curb or accessibility standard. |
| Landscape | Courtyard-edge beds, compact urban planting, sheltered arrival planting or restrained service margins | Actual residual space, local climate evidence, available plants and existing exclusions determine what fits. No default species list or automatic lush/dry garden from region alone. |

Traditional, ordinary and contemporary references in the source text provide
choices, not era labels. Design city-specific expression strengths without
copying the runtime's current expression probabilities. A neutral contemporary
choice must remain available throughout. Community-specific, ceremonial and
sacred motifs require explicit appropriate evidence; they are not generic hotel
branding. Arctic/Antarctic and small-island entries do not authorize inventing
skyscrapers, resorts or suburban parking where the source has none.

### Authoring and runtime contract

At C0 extract only the allowed descriptive fields into a versioned authoring
manifest, retaining source field paths and text digests. At C1 add a compact city
regional record keyed to each existing stable ID: source description, locality
conditions, applicable families/zones, proposed composition/material/arrival/
landscape directions, explicit exclusions, interpretation status and revision.
Use statuses such as `text_based_proposal`, `geometry_checked` and
`game_reviewed`; current activation of an ordinary regional profile does not
automatically validate its new city interpretation.

Author future numerical city parameters separately after fitting/asset review.
The city authoring path must not read `regional_profiles.json`, copy numeric
`facade`/`roof` lists from `environments.json`, or fall through to
`regional_architecture.for_spec` for its style decisions. Existing geometry
primitives can be reused without inheriting the recipe that previously called
them. No runtime language-model interpretation or network lookup is needed.

Pass the resolved city interpretation into material, facade and site consumers
once. Give each evidenced shared site one public-realm interpretation, resolved
from its canonical identity and explicit context, with member-specific building
variants. Do not derive the common paving/planting from whichever member loaded
first. At ambiguous regional transitions, retain a stable neutral shared treatment
or supported local override; never blend unrelated structural systems across a
facade. A material/accent change must not move portals or reseed planting positions.

Include the descriptive-source digest, city interpretation revision and geographic
identity in the appropriate dependency records, alongside existing source
signatures. Reuse a small common material/module library and the shared detail
budget; 64 identities must not multiply draw calls or create 64 new texture sets.
Unsupported or disabled city interpretations use the compatible neutral family
with diagnostics, while the existing non-city regional system remains intact.

## Architectural scope and evidence

Start with five compatible families, each fitted to the actual building rather
than scaled from a fixed model. Add variants through independent semantic seed
channels for composition, cladding, frame finish, glass, roof detail and condition.
Changing a material palette must not move an entrance, change floor levels or
rearrange planting.

| Family | Building composition | Relationship to the site |
| --- | --- | --- |
| Curtain-wall office or skyscraper | Coherent vertical mullions, vision glass and opaque floor spandrels, restrained solid core/end zones, distinct lobby and roof termination | Lobby walk/plaza, fitted entrance shelter, service interface separate from arrival |
| Precast or panel office | Repeated structural bays, ribbon or grouped punched glazing, panel joints, opaque floor zones | Practical paved arrival, contained planting and source-supported parking/service links |
| Masonry or stone office | Aligned piers and openings, reveals, lintel/sill vocabulary, compatible base and roof edge | Compact street frontage or evidenced forecourt; paving coordinated with thresholds |
| Contemporary hotel | Repeated room bays, grouped windows, differentiated lobby and service zones | Pedestrian arrival plus a validated drop-off where supported; preserve a clear through footpath |
| Masonry hotel | Room rhythm, coherent masonry bays, restrained entrance and cornice treatment | Compact entrance court or street edge, compatible paving and bounded planted margins |

Family names describe procedural architectural choices. Construction era becomes
an observation only after its source field is verified end to end. Hotels, motels
and hostels currently share a preset; use retained class/subtype, height and form
to prevent low motels or hostels automatically acquiring a tower-hotel programme.
Unclassified tall buildings receive a neutral compatible facade without invented
hotel operations, retail occupancy or service access.

Preserve supplied outline, holes, height, minimum height, floors, roof and mapped
parts. Derive any unknown dimensions once and record the inference. Conflicting
height/floor evidence produces a diagnostic and an explicit resolution, never
independent facade and collision heights. A taller lobby redistributes available
body height only when the resolved evidence permits it.

Massing variety follows supported parts and assemblies: towers on mapped podiums,
stepped volumes, linked wings and roof setbacks. With only a single extruded
footprint, use facade zones, recesses and roof-edge composition; do not invent
removed floor areas, a new tower footprint or a traversable podium. Supported
part assemblies belong in the release once the completed site/physical system
can preserve their ownership, clearances and lifetime.

Structural accuracy means credible visible construction: aligned floor datums,
piers, mullions, panel joints, support and attachment relationships. An inferred
facade grid is not evidence of the actual concealed load-bearing frame. Projecting
canopies or occupied terraces require complete supported geometry and clearance.

## Shared architecture and site interfaces

Agree these capabilities with the completed pavement/site implementation at C0.
Names below describe required data, not a demand to replace its final API.

| Interface | Producer and required content | Consumer |
| --- | --- | --- |
| Building programme and envelope | Building planner: stable source/part identity, use zones, floor datums, source constraints, facade roles and provisional portal intervals | City facade planner and shared site coordinator |
| Portal proposal | Building planner: lobby/public/staff/service/garage role, width, threshold constraints, outward approach, clearance volume, provenance, ranked alternatives | Existing shared access coordinator |
| Accepted interface | Site coordinator: stable interface/resource IDs, status, exact endpoints and levels, connected route and reservations, dependency revision | Final entrance, facade and canopy fitting |
| Surface and landscape plan | Site planner: accepted surfaces/holes, boundary samples, material role, contact owner, walking/vehicle corridors and residual planting regions | Existing mesh, collision, markings, vegetation and landscape emitters |
| Regional city interpretation | Stable regional ID, descriptive-source digest, locality conditions, new city interpretation/revision, family/zone applicability and expression | Building and site planners; does not expose existing regional recipe parameters |
| Architectural palette | Building or evidenced complex identity plus accepted city interpretation: compatible paving/edge/planting preferences, independent of geometry seeds | Existing surface and landscape material selection; mapped surface evidence wins |
| Resource dependency | Shared runtime: producer, consumers, revisions, readiness, cancellation and occupied retention | Building/part assembly publication and retirement |

Every accepted city entrance needs one shared threshold datum. A proposed door is
not a connected route. Preserve `connected`, `crossing_only`, `pedestrian_only`
and `rejected` distinctions from the completed access system; a crossing alone
cannot justify a hotel drop-off loop. Failed access retains a coherent closed
facade or supported pedestrian entry with a diagnosed omission.

Use the completed coordinator's bounded negotiation: at most four alternatives
and three total passes per sector, unless its final reviewed contract is stricter.
Architecture proposes feasible entry intervals; the site planner fits routes and
levels; architecture finalizes only accepted interfaces. Later facade decoration
cannot move a committed portal or invalidate a physical route. Terrain requests
share the established sampler and source frame/revision.

The building owns its facade, roof and attached entrance assembly. The shared site
owns shared paving, drop-offs, circulation and planting; garage and station
adapters retain their physical and functional responsibilities. References to a
common plaza do not duplicate its mesh. Membership extent is not proof of paved
area or legal ownership. Preserve unknown exclusions and source holes.

## Planning and emission order

1. Resolve source evidence, part membership, canonical identities and capability.
2. Resolve authoritative massing, programme, floor datums and architectural family;
   apply the compatible text-derived regional city interpretation.
3. Build continuous elevation runs and propose public/service/garage interfaces.
4. Use the completed shared coordinator to accept portals, walking routes,
   circulation, drop-offs and their levels and clearances.
5. Freeze accepted interfaces; fit facade grids and entrance assemblies around
   them. Reserve canopy supports and overhead envelopes before site decoration.
6. Fit roof assemblies and equipment inside the available roof and height span.
7. Resolve physical surface materials, parking/markings and residual planting
   through the existing site system. Export hardscape exclusions from the same
   accepted geometry, including newly accepted plazas and approach paths.
8. Freeze architecture and shared-resource references into worker-safe plans.
9. Publish topology-safe shells, lightweight composition and final detail through
   existing staged loading. Use the completed physical lifecycle for shared decks
   and routes; an ordinary opaque proxy cannot close a mapped passage.

Soft landscape variation may change within accepted beds without changing road,
threshold or collider geometry. Material-only changes invalidate visual products,
not unrelated physical resources, when the final dependency system supports it.

## Implementation milestones

### C0 Reconcile the completed baseline and capture controls

Read the finished pavement/landscape/resource status, inspect runtime integration
and record actual schemas/capabilities. Preserve touched-file originals and hashes
under `build/city-buildings/original` because this snapshot has no Git metadata.
Capture matching baseline previews, mesh fingerprints, source-field lineage and
stage timings before changing eligibility or materials.

Inventory all 64 descriptive records and the geographic resolver independently
of the compiled style catalogue. Record historical coverage annotations and
unknown/ambiguous locality cases. Review the accompanying 64-row city brief against
those texts; snapshot allowed prose fields and allocate city-specific authoring
files. Existing regional geometry, openings and roof variants remain regression
controls, not templates for the new city styles.

Use existing commercial, garage, church, terminal, roof, landscape and hardscape
fixtures as controls. Add city fixtures with explicit site/portal inputs through
the finished APIs. Verify canonical frame conversion, producer ownership, accepted
status semantics and both local/worker paths. If an interface changed during the
upstream work, write a small adapter and contract tests; do not fork its solver.

**Exit:** a concrete mapping from the interfaces above to the completed code,
reproducible baseline, current schema allocation and unchanged control behavior.

### C1 Add one compact city architecture plan

Introduce `buildgen/city.py` for eligibility/family selection and detached plan
records, with reusable elevation/grid logic in `buildgen/elevations.py` if it is
not already supplied by the completed commercial work. Reuse shared programme,
structure and interface records wherever available.

The plan carries family and provenance, floor datums, elevation runs, repeated
bay descriptors, major opaque zones, material roles, entrance references, roof
zones, detail budgets and diagnostics. Attach it to mutable `Spec` and immutable
`BuildingPlan`; update freeze/pickle validation and allocate the next schema at
implementation time. Include new catalogues/code in source signatures and package
collection. Keep schema and progressive protocol versions separate.

Carry regional ID, descriptive-source/interpretation revision, locality confidence,
applicable zones and deterministic city expression in that plan. Validate exact
64-ID coverage in the new authoring catalogue, allowing explicit neutral or
inapplicable outcomes. Keep this independent of the existing profile's dimensions,
material probabilities, grammar names and expression thresholds.

Merge compatible collinear wall edges into elevation runs while preserving
corners, holes, part boundaries and explicit shared walls. Retain mappings to
original edges for doors and obstruction checks. Fit full bays with consistent
corner closure; do not stretch a few windows across a giant wall. Allocate
optional detail across elevations so the first wall cannot consume all resources.

**Exit:** deterministic plans across seeds, ring starts/winding, replay and rebases;
source constraints and specialist precedence preserved; worker round trips detached.

### C2 Implement tall office and hotel composition with bounded detail

Extend the three office grammars into compact repeated runs; add hotel room/lobby
grammars. This replaces the twelve-floor detail restriction for eligible city
families without merely raising `MAX_OFFICE_FLOORS` or materializing every pane
as an `Opening` with reveal geometry.

Keep actual entrances and exceptional openings explicit. Compile repeated upper
floors as bounded panels/runs, with shared UV modules and coherent solid zones.
Generate close-range reveals, frames and sills only within a measured detail
budget; lighter representations retain the full intended window rhythm. Avoid
the general wall-cell splitter over a skyscraper-sized list of individual panes.
Measure both planning complexity and exported vertices on extreme fixtures.

Fit base/middle/top composition to actual floor datums, align mullions with
spandrels and return materials around corners. Party walls remain opaque when
supported by evidence; courtyard elevations use their own runs and obstruction
context. Preserve unknown adjacency rather than declaring every rear wall blind.

Apply compatible regional prose to masonry bay grouping, hotel/lobby rhythm,
shade and base treatment; keep the tower's floor/glazing system credible at its
height. Review both subdued contemporary and stronger locally influenced results.
Do not reuse a house facade or remove its twelve-floor guard to regionalize a tower.

**Exit:** each family remains recognizable with the same neutral material palette;
upper floors and secondary elevations remain composed under budget pressure;
near/lite layouts agree and ordinary closed-shell collision remains unchanged.

### C3 Introduce role-specific materials and roof assemblies

Extend `buildgen/materials.py`, the facade compiler and registered building
materials with a small shared palette for vision glass, opaque spandrels, coated
or exposed metal frames, precast, brick, stone/render, roof membrane and plant
screens. Audit existing texture channels and in-game material support before
choosing assets or factors. Preserve asset provenance and permitted reuse.

Build city-specific material-role combinations from the regional text briefs,
with new authored values and explicit asset support. Compare the same geometry
under several interpretations, then the same neutral palette across families.
This separates regional material expression from architectural composition.

The present facade emitter selects the stock OFFICE/SHOP material for glazing
instead of a separate resolved glazing role. Route tint and surface selection
through the city plan so facade colour does not indiscriminately tint glass,
frames and opaque panels together. Treat facade-wide colour evidence cautiously
when the source does not specify individual materials.

Use physical UV scale, independent glass/frame/spandrel properties and coherent
normal/roughness detail. Reserve metallic response for appropriate surfaces;
validate glass appearance in BeamNG rather than equating reflectivity with a
metallic flag. Prefer shared opaque glazing representations until transparent
variants prove their sorting, lighting and cost. Keep night-window variation
deterministic and prevent glowing solid wall/roof panels.

Fit parapet caps, supported roof screens and bounded equipment groups to actual
roof polygons, holes, equipment clearance and maximum height. Preserve aerial
roof colour intent on the roof covering. A known occupied roof or unsupported
sloped surface cannot silently become a mechanical yard. Equipment/canopies that
affect traversable space use the shared physical plan; cosmetic details cannot
introduce hidden collision or change a roof's supported source envelope.

**Exit:** recognizable surface differences by day/night and oblique view, coherent
texture scale, resolved material references, shared assets and bounded residency.

### C4 Integrate city entrances and public spaces

Consume the completed site planner for public walks, compact urban plazas, hotel
drop-offs, service approaches and supported parking/garage connections. Feed the
architectural family's palette and functional roles into existing fitting, rather
than adding preset rectangles around every tower.

Hotel arrival areas require a connected vehicle route and pedestrian approach;
fit waiting/turning clearance before decoration. Office plazas require evidenced
usable extent; dense street-edge sites may have only a widened accepted entrance
walk. Mixed-use podiums expose distinct source-supported interfaces while sharing
their site's circulation. Do not add shops merely because a tower is tall.

Create restrained landscape profiles for urban offices, hotel arrival, masonry
street fronts and service edges. Extend `landscaping.treatment` selection so the
current broad commercial-to-retail choice does not erase those identities.
Fit planting only in accepted residual regions, preserving footpath through-routes,
garage aprons, vehicle envelopes, doors, service access and canopy supports.
Use the new text-derived city briefs for regional design intent; use actual local
climate evidence and supported landscape assets for feasibility. Do not copy
the existing defined regional styles into paving or planting.

Share threshold and pavement vertices/levels, align paving joints to the approach
and building axes where feasible, and use the same surface ownership for tyre
contact, collision, render meshes and exclusions. Retain ordinary green patches
for intended planting while hardscape export protects paving from natural props.
Check consumption of exclusions as well as their export, including load order,
revisit and rebase. Never mask an entire site just to hide a local planting clash.

**Exit:** office and hotel arrival scenes have connected, unobstructed approaches;
surface seams and material roles pass the completed pavement gates; hardscape and
green areas remain consistent through loading and LOD changes.

### C5 Support evidenced assemblies and finish streaming integration

Apply the same programme, floor/grid and material system to supported mapped
tower/podium, stepped and linked-part assemblies. Use their real vertical
intervals and shared-resource references; align datums only where evidence or an
explicit inference supports it. Exposed terraces, arcades and overhead canopies
require headroom, support and route reservations through the completed lifecycle.

Retain shared-site producer/consumer rules, occupied-resource pinning and stale
revision rejection. Test partial membership residency, reversed tile order,
unload/revisit and rebase with a vehicle on retained physical surfaces. Preserve
topology-safe previews and current single-import scheduling. Unsupported part
relationships retain diagnosed source geometry without invented connectivity.

**Exit:** no duplicated plaza/deck resources, closed passages, lost occupied
routes, source-member truncation or decorative-triggered physical rebuilds.

### C6 Calibrate and package the integrated release

Run the full validation matrix below and profile the complete workload. Tune
geometry, shared materials and admission based on measurements, then prepare a
fresh matching private server/mod/assets package with manifests, runtime data,
preview/report artifacts and rollback instructions. Preserve prepared roof/zoning
catalogues and their attribution. Verify packaged CLI/import/material paths.

Update implementation status and the integrated checklist with actual completed
items and remaining game checks. Switch the playtest launcher only when the new
package is coherent and the old game/server is stopped. Publication remains a
separate task.

## Validation and performance acceptance

Build a matrix across five families, three stable seeds and rectangular, narrow,
concave and courtyard footprints. Include low/mid-rise controls and 13-, 30-,
60- and 120-storey synthetic stress cases; these are tests, not inferred defaults.
Add short edges, inconsistent dimensions, missing evidence, giant elevations,
mapped parts, raised volumes and explicit/unknown party-wall cases.

City-site cases include flush street entrances, sloped approaches, constrained
hotel drop-offs, shared plazas, separate service entries, garage podiums, source
holes/exclusions, partial members and missing terrain. Test the full accepted
vehicle/route envelopes and planting extents, not just their centres.

| Check | Required result |
| --- | --- |
| Source and inference | Supported observations survive; contradictory/unsupported data is diagnosed; inferred style is not promoted to observed era/use. |
| Structural composition | Floor levels and panel/window grids align; plausible complete bays, supported projections and closed corners; no intersecting openings or unexplained floating parts. |
| Determinism | Repeat runs, semantic seeds, order reversal, ring changes, worker serialization and frame conversion preserve the intended architecture and shared ownership. |
| Physical geometry | Ordinary facade changes preserve collision; all new physical interfaces use accepted shared levels and surfaces; source voids and garage routes stay open. |
| Pavement and landscape | Use the existing 1 mm computational seam target and no unintended collision lip over 5 mm in fixtures; reserve walking/vehicle routes; no plants on hardscape or lost intended beds. |
| Visual representations | Base/middle/top, openings, major materials and source roof silhouette remain coherent through shell/lite/near/skyline; bounds and chunk splits preserve every required surface. |
| Asset quality | Review actual BeamNG textures, scale, reflections, roughness, normals, night emission, distant aliasing and repeat patterns; synthetic colour sheets cover geometry only. |
| Runtime lifecycle | Bounded work/queues/memory, cancellation, stale results, failed imports, partial residency and occupied physical-resource retention preserve essential coverage. |

Extend relevant existing suites rather than duplicating them: commercial architecture,
facades, inference, roofs/roof colours, access/driveways/sites/landscaping, garages,
churches, terminals, specialized dispatch, sitegen contracts/identity/surfaces/
hardscape/lifecycle, chunks/progressive, source collection and affected Lua suites.
Add focused city-plan, repeated-facade and city-site integration suites.

Add an all-64 regional coverage gate with an applicable office/hotel case or an
explicit neutral/inapplicable result for every ID. Across eligible cases exercise
all five families and all expression strengths, then select a pairwise geometry/
site matrix for expensive compilation and game review. Include coastal/interior,
wet/dry, highland/lowland, ambiguous borders, explicit overlays and unknown regions.
Do not require a skyscraper fixture to be a plausible local building in every region.

Test authoring isolation: changing existing compiled style parameters must not
change a city's resolved interpretation, geometry or role palette when source
text, geography and city records are unchanged. Existing global cache signatures
may still invalidate a cached result. Changing the new city interpretation must
invalidate its actual consumers; unrelated ordinary-building output remains a
regression control. Test precedence of source materials/roof colours and separate
site/member identity under reversed load order and rebase. Compare regional near,
lite and skyline expression without exhausting the shared detail budget.

Record first-shell latency, planning/terrain/mesh compilation, near/lite/collision
vertices, draw calls/material slots, texture and mesh memory, import/collision
activation, queue age, and driving p50/p95/p99. Keep cold and warm measurements
separate; compare equal source coverage, route, settings and hardware. Existing
office composition and local landscape coordination have measured planning
overhead, so their historic timings cannot establish spare performance budget.

Retain the integrated gates: at most 5% regression in total steady-driving p95,
10% in p99, and separate 10% worker-generation/collision p95 gates; target at most
1 ms p95 architecture contribution within the shared governor and no new
repeatable synchronous architecture stall above 50 ms. These are acceptance
targets, not results. Measure on the designated small machine and desktop with
at least three repeats and a soak. Preserve existing 20,000-vertex near chunks;
also cap per-building/sector work, since chunk size alone does not bound total cost.

Calibrate numeric budgets for run descriptors, repeated modules, detail vertices,
materials and texture residency in C0/C2 before broad activation. Overflow drops
fine detail first while retaining complete mapped envelopes, facade coverage,
accepted interfaces and physical routes. Avoid per-building texture baking,
runtime web/AI calls and new per-frame geometry generation.

## Delivery sequence and completion

Implement **C0 → C1 → C2 → C3 → C4 → C5 → C6**. The first reviewable slice is tall
office/hotel composition on the finished shared foundation, with source-preserving
geometry and new material roles. The second review adds connected city arrival
spaces and planting; the third completes supported assemblies and runtime review.
All three contribute to the intended integrated release.

Deliver `build/city-buildings/` baseline/after contact sheets, facade close-ups,
street/roof views, city-site diagrams, source hashes, diagnostics and benchmark
JSON; actual game captures and measured runtime results are separate artifacts.
Include a 64-ID coverage report and annotated regional comparison sheets that
identify the descriptive source, city interpretation, applicability and any
neutral fallback. None of these sheets should be presented as reproduction of
the currently defined regional styles.
Completion means recognizable building families, coherent materials and visible
construction, integrated pavement/landscaping, passing regressions and documented
game acceptance. A preview image alone does not close the release.
