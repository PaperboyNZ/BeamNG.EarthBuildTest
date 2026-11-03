# Pavement, property access, commercial complexes and fuel stations

Execution order, resolved cross-plan conflicts and current progress are tracked in
[the integrated implementation checklist](GENERATION_IMPLEMENTATION_CHECKLIST.md).

Prepared 1 November 2026. Status: implementation specification only. No generator,
runtime, schema, catalogue or package has changed as part of this preparation.
Use the current combined `BeamNG.EarthBuildTest` source (schema 12), retaining
residential roofs, zoning, commercial facades, docks, driveways and landscaping.

## Intended result

Rounded pavement corners and usable, smooth property entrances should form one
system with driveways, commercial paving, parking, building entrances and fuel
forecourts. A credible vehicle entrance may receive a dropped curb even when a
complete driveway cannot reach the garage. Large sites should read as connected
places with circulation, customer areas and service areas, rather than unrelated
buildings surrounded by arbitrary pavement or rows of parking lines.

Scope includes detached homes, workshops, warehouses, industrial yards,
supermarkets, shopping centres, malls, retail parks, standalone mapped car parks,
and petrol/service stations of different sizes and regional identities.

## Verified starting points

| Current code | Behavior and consequence for this work |
| --- | --- |
| `server/buildgen/driveways.py` | Requires a garage opening; selects a preferred frontage before terrain validation; rejects most curved/offset crossings and footpaths below 2.4 m. Crossing emission depends on a complete accepted driveway. |
| `server/vehicle_crossings.py` | Already replaces sidewalk spans with vehicle profiles; retains a rear walking strip. Current road lip is 10 mm and flare interpolation is linear between longitudinal stations. Extra vehicle geometry is also used for collision. |
| `server/junctions.py` | Already constructs tangent corner arcs, sampled at approximately 0.75 m spacing. Improve curvature error control, not indiscriminate subdivision. |
| `server/sidewalks.py`, `native/earthfast/src/sidewalks.rs` | Batched sidewalk meshes and lean collision. Native collision simplification uses a 3 cm tolerance; crossing contact points need protection. |
| `server/buildgen/site_layout.py` | Supplied property evidence enables docks, straight service approaches and one small parking row; 12 stalls, 24 patches and 512 terrain points per site. Shared parking/pedestrian planes can reject otherwise plausible sloping sites. |
| `server/buildgen/site_data.py` | Surveyed, source-linked boundaries and ports; one building owner per site. No existing shared-complex ownership model. |
| `server/parking.py`, `server/surface.py` | Mapped parking polygons have a separate terrain-paving, marking and parking-position pipeline. Lot geometry currently extracts outer rings; blocker checks for parked vehicles include centre tests. Preserve holes and check full envelopes in the new path. |
| `server/gasstations.py` | Existing source classification, pin merging, canopy/shop detection, regional stock-asset selection, forecourt pads and mapped/inferred road connections. Extend this instead of creating another station generator. |
| `mod/beamng_earth/lua/ge/extensions/beamngEarth/gasstations.lua` | Staged station props and functional refuelling areas/POIs; region-specific preload and lighting hooks. Preserve these contracts. |

Actual prevalence of driveway rejection causes is not measured yet. Historical
benchmark and test counts in other documents are not new validation of this plan.

## Engineering basis and resulting decisions

These sources inform the proposed game geometry. Numerical gameplay defaults
must be labelled separately from sourced regional dimensions, with source,
edition and applicability recorded in the eventual profile catalogue.

* Preserve the walking through-route across driveways; place vehicle grade
  transitions outside it where space permits. NZTA's path guidance describes
  continuous path grade and crossfall and a maximum 2% crossfall for the NZ
  through-zone. This refines the earlier suggestion to simply dip an entire
  narrow footpath: first shorten/reposition the crossing, use available verge or
  private frontage, or choose another entrance. A constrained whole-path lowering
  is accepted only if its longitudinal transitions and crossfall pass the walking
  profile checks. [NZTA Paths, April 2026](https://www.nzta.govt.nz/assets/Walking-Cycling-and-Public-Transport/docs/pedestrian-network-guidance/docs/3.3-paths-apr-2026.pdf)
* Fit circulation and access to the intended vehicles and preserve understandable
  pedestrian routes, waiting space and visibility. Treat a commercial entrance
  as a route to a destination, not just a wide curb cut. [MBIE routes and parking](https://www.building.govt.nz/building-code-compliance/d-access/accessible-buildings/vehicle-circulation-parking/routes-set-down-points-parking),
  [MBIE vehicle entrances](https://www.building.govt.nz/building-code-compliance/d-access/accessible-buildings/vehicle-circulation-parking/vehicle-entrances)
* Fit parking bays together with manoeuvring and buffer space; shrinking bays to
  maximize count is not the objective. Validate an ordinary design vehicle and a
  larger check vehicle. AT's parking chapter explicitly distinguishes these and
  their tracking space. Its table is a regional reference, not a worldwide
  default or a blanket specification for private malls. [AT Parking v2](https://at.govt.nz/media/1991687/engineering-design-code-parking-version-2.pdf)
* Keep customer parking/walkways clear of loading courts; reserve space for
  delivery movements. Prefer through routes or turning space that permits a
  forward exit, with explicit reversing areas where required. [HSE loading areas](https://www.hse.gov.uk/workplacetransport/loading.htm),
  [HSE reversing](https://www.hse.gov.uk/workplacetransport/information/reversing.htm)
* Preserve gutter/swale continuity and avoid creating pavement dams. Model
  coherent falls and drainage destinations where evidence exists; missing
  underground drainage is not permission to invent an outlet. [TCDC crossings](https://www.tcdc.govt.nz/Our-Services/Transport-Roads-and-Road-Safety/Vehicle-Crossing)
* Markings describe a real circulation decision: bay boundaries, arrows,
  crossings, loading areas and keep-clear areas. Choose colours, symbols and
  controls from regional profiles, not one universal paint scheme. [NZTA TCD manual](https://www.nzta.govt.nz/resources/traffic-control-devices-manual),
  [NZTA parking control](https://www.nzta.govt.nz/assets/resources/traffic-control-devices-manual/part-13-parking-control/docs/13-parking-control.pdf)

Reference verification limits: the NZTA Paths and TCDC points above were available
in indexed source text; direct fetches returned 403. AT's current index identifies
July 2025 vehicle-crossing details, tracking envelopes and Practice Note 07. The
practice-note fetch failed and the tracking PDF exceeded the tool size limit.
Retrieve and check the applicable drawings/practice notes before fixing NZ
vehicle dimensions or crossing details. Do not treat obsolete ATCoP or an unread
drawing as a verified requirement. [AT current documents and practice notes](https://at.govt.nz/about-us/manuals-guidelines/transport-design-manual)

## One site plan, multiple consumers

Add a small `server/sitegen` package for immutable shared records and pure planning
functions. Existing building, parking and station modules remain adapters and
emitters. Proposed split: `plan.py`, `evidence.py`, `access.py`, `pavement.py`,
`parking.py`, `vehicles.py`, `markings.py`, with versioned profile data alongside.
Add the package and JSON data to `codefiles.source_files`; current recursion only
covers `buildgen`. Avoid an import cycle between buildings, roads and sitegen.

| Record | Required information |
| --- | --- |
| SiteEvidence | Stable site/source IDs, boundary including holes, observed paved areas, building/lot/station membership, exclusions, source strength and revision; distinguish mapped extent from surveyed ownership. |
| SitePlan | Site ID, member building IDs, stable generation frame, selected recipe/profile, access ports, circulation, pedestrian links, pavement cells, marks, reservations and diagnostics. |
| AccessPort | Stable road/run reference and side, source-frame station interval, mouth width, approach direction, endpoint heights, supported vehicle class, evidence and status. |
| SurfaceCell | Boundary/holes or bounded triangulation, material, height function, shared boundary samples, visual and collision ownership, drainage intent. |
| CirculationEdge | End nodes, directionality, width, design vehicle, accepted swept envelope, grade profile and connected destinations. This is a generation graph, not new live traffic AI. |
| Marking | Semantic role, regional style, parent surface, geometry and visibility tier; no paint outside the accepted parent pavement. |

Entrance status is explicit: `connected`, `crossing_only`, `pedestrian_only`, or
`rejected`. Keep entrance rejection separate from an internal driveway failure.
Evidence strength is rule support, not a calibrated probability.

Prefer supplied site relations, mapped lots/access roads and explicit complex
membership. Where only a footprint exists, allow bounded frontage paving and a
short credible entrance corridor. Do not infer a large asphalt parcel from
commercial zoning alone. Zoning informs a compatible recipe, not proof of use.

Multi-building complexes need a site-level owner independent of any one building.
Migrate the existing `owner_id` format through a backward-compatible adapter to
`member_ids`; preserve current catalogues. Support standalone lots with no
building and fuel stations attached to larger complexes. A station remains the
owner of its pumps/refuelling, while the complex owns shared circulation.
Keep nearby unrelated sites separate; proximity alone is insufficient membership.

Plan a whole site in a stable source frame with sufficient neighboring evidence,
then partition its output into existing spatial chunks. Every component receives
a stable ID and one emitting owner. Site selection, crossing position and parking
row phase must survive tile order changes and rebasing. A tile-local list index
is not a persistent curb identifier; project onto the final canonical curb path.

## Planning order

1. Collect evidence, ownership and exclusions; retain mapped road/access topology.
2. Resolve building roles and actual door, garage, service and dock interfaces.
3. Rank entrance candidates and reserve provisional vehicle/pedestrian corridors.
4. Construct bounded alternatives for circulation, courts and walking routes.
5. Fit whole parking rows and useful residual pavement around those reservations.
6. Batch terrain/road-profile samples, resolve shared levels, grade transitions and
   candidate vehicle envelopes; retry ranked alternatives within the same budget.
7. Commit feasible components atomically. If internal connection fails, recheck
   whether an independent crossing and short receiving area remain usable.
8. Generate curb modifications, surface meshes/masks, paint, parking positions,
   fences, landscaping and optional props from the same accepted plan.

This requires moving final fence/landscape and parking-clearance decisions after
access resolution. The current `buildings.doors` sequence resolves driveway work
before commercial site work; a coordinator must collect proposals first so later
site generation cannot contradict a previously emitted entrance.

## Driveways and curb crossings

Try at most four ranked entrance/path candidates per ordinary property. Rank
mapped vehicle ports first, then garage/carport/service-court alignment, then
clear road-facing hardstanding. A pedestrian path is supporting evidence only:
vehicle width, a receiving area and obstruction clearance must all pass.

Use straight, offset and gentle tangent curves; support curved frontage. Choose
by feasibility and alignment, not nearest-road distance alone. Exclude medians,
controlled-access road edges without mapped access, incompatible grade-separated
roads, buildings, water/exclusions and protected pedestrian crossing space.
Retain current 18 m/15% residential limits initially; change only when failure
reports and profile checks justify an extension. Never solve low coverage by
randomly adding mouths or raising every probability.

The front edge meets the generated road/gutter contact surface with a zero-lip
target, not a raw terrain height. Use shared boundary vertices, tangent vertical
transitions and smooth lateral flares. A crossing-only entrance must join a
short, tested receiving area behind the footpath without a rear curb/step.
Missing or unsuitable terrain at that receiving area suppresses the crossing;
failure farther inside the property does not.

Keep existing pedestrian ramps protected. Merge mouths only where their combined
geometry and circulation are compatible; do not flatten an intervening refuge.
Feed even crossing-only reservations into curbside parking, props and vegetation
exclusions. Today parking clearance largely depends on completed drive records.

## Smooth corners and continuous paved surfaces

Use curvature/error-based tessellation of actual tangent arcs and approach
curves. For a circular arc, choose segment angle from
`2 * acos(1 - error / radius)`, with guarded small/zero-radius handling and a hard
segment cap. Start at 2 cm visual chord error; do not add vertices to a straight
chord and call it smoothing. Include the outer pavement edge in the error check.

Preserve intersections, tangent points, crossing boundaries, grade breaks and
tile clipping points. Recompute offsets/normals from the curve; reject folded or
self-intersecting strips. Sample smooth longitudinal flare easing explicitly;
four endpoint sections alone cannot represent its curvature.

Use connected piecewise planes/strips for large sites instead of one plane per
entire car park. Shared constraints give identical heights along seams; short
vertical curves join differing longitudinal grades. Bound terrain residuals and
avoid floating pavement or buried driving surfaces. Check edge and interior
samples with bounded refinement; fail/defer unsupported rough terrain. Retain
the no-excavation/no-retaining-wall scope initially.

Provide separate asphalt carriageway/aisle, concrete footpath, forecourt/apron,
loading hardstand, island and gravel roles. Surface evidence takes priority over
inferred material. Use coherent texture scale, aligned concrete joints and
restrained wear; fine cracks/paint/joints are visual, not collision bumps.
Material identity should agree with tyre-contact behavior. Check that broad
terrain masks, raised surfaces and vegetation suppression agree at seams/LODs.

Keep broad terrain-following areas on the existing surface-mask pipeline where
possible. Use explicit meshes for controlled grades, curbs, islands and joins.
Assign one physical contact owner per patch and avoid overlapping terrain/mesh
surfaces that produce wheel jitter. Preserve the drivable network when dropping
optional visual detail under budget pressure.

## Commercial and industrial layout families

| Family | Layout intent |
| --- | --- |
| Supermarket | Clear customer entrance/forecourt, connected parking blocks, trolley bays outside travel paths, rear/side delivery court and suitable loading access. |
| Neighbourhood shopping centre / strip retail | Shared frontage walk, several tenancies/entrances, common parking and access; no duplicate driveway per tenancy. |
| Enclosed mall | Multiple evidenced entrance groups, pedestrian arrival plazas, parking sectors, circulation spine/ring where feasible, drop-off and separate service edges. Preserve actual complex footprint/roof composition. |
| Retail park / big-box complex | Several anchor buildings sharing roads and parking, pedestrian links between anchors and a separate service network where space permits. |
| Mixed urban commercial block | Compact shared/service access, paved pedestrian frontage and small courts; no forced suburban parking apron. |
| Warehouse / logistics / industrial estate | Heavy-vehicle manoeuvring courts, service lanes, staff parking and protected staff paths; practical concrete/asphalt treatment. |
| Standalone large car park | Evidence-bounded parking sectors with connected aisles, end turns, islands and walking routes, even without an owning building. |

Choose use from mapped categories, names/relations where reliable, current
building evidence and compatible surroundings. Area alone cannot establish a
mall, supermarket or industrial process. Expand commercial presets and facade
roles alongside site planning: customer-facing glazing/canopies, anchor entrance
features, secondary entrances, and restrained service walls should face their
corresponding routes. Do not create doorways that lead into loading conflicts.

Fit circulation first. Initial parking layouts: 90-degree two-way rows, then
60-degree one-way rows, with peripheral parallel bays where they fit. Orient
using mapped aisles, access and buildings; try a bounded set of alternatives.
Require a complete route from each accepted stall to an entrance/exit and a
pedestrian connection. Check full bay/vehicle envelopes, holes and turning ends,
not just bay centres. Existing mapped pavement may remain without invented
parking if no usable circulation can be established.

Reserve entry throats/queue space before the first bay. Select vehicle envelopes
by role: passenger car, van, rigid delivery truck, articulated truck. Use bounded
low-speed kinematic/precomputed sweeps, including overhang and trailer offtracking;
a centreline buffer alone is inadequate for articulated vehicles. Check canopy
headroom plus approach/departure/breakover at grade changes. Provide forward exits
where feasible; loading reversal belongs in a dedicated court. Reduce the chosen
vehicle class only if the site's actual role supports it, otherwise omit the
unsupported heavy-vehicle facility with a diagnostic.

Paint follows the accepted circulation graph: complete stall divisions/end lines,
direction arrows, loading/keep-clear hatching, pedestrian connections and selected
entry/exit controls. Use regional road side and marking conventions. Paint is
render-only, clipped to surface cells, projected to their heights and batched by
material. Do not use signs/arrows to imply a route that fails geometry checks.
Accessible bays require their complete access aisle and step-free connection,
with dimensions from a verified regional profile; they are not ordinary stalls
with a symbol. Bus/taxi/drop-off areas need matching evidence or a supported
facility recipe rather than appearing on every supermarket.

## Fuel station variety and identity

Separate three choices: observed station/brand, site layout family, and visual
identity. Keep current confirmation, closure and convenience-store safeguards;
commercial zoning or a shop brand alone must not create pumps. Mapped canopies,
lanes and shops constrain the layout before regional style is selected.

| Layout family | Fit and purpose |
| --- | --- |
| Compact urban | Small island count, tight but usable approach, integrated kiosk/shop, low signage where appropriate. |
| Neighbourhood / suburban | Several pump islands, separate shop-side short-stay bays and a clear walking connection. |
| Supermarket-linked | Forecourt associated with the retail complex, access from its circulation rather than duplicate cuts to the public road. |
| Rural / small-town | Sparse islands, modest kiosk or unattended equipment where supported, restrained paved footprint. |
| Highway service area | Larger forecourt and convenience/food buildings; mapped service-road access rather than a cut through a motorway edge. |
| Truck / industrial | Separate larger vehicle lanes, adequate canopy clearance, turning/queuing and refuelling envelopes. Customer car parking stays out of truck circulation. |

Provide modular canopy forms, fascia proportions/palettes, columns, island noses,
pump arrangements, kiosk/shop facades, sign types, paving, joints and lighting.
Scale by adding correctly spaced modules rather than stretching stock pumps and
canopies beyond plausible proportions. Preserve mapped canopy footprint/height
when credible. Keep pump positions, hose-side stopping zones and refuelling
triggers aligned with final pavement heights; never lose gameplay refuelling for
a visual variant. Supported energy types remain explicit, not inferred from colour.

Plan initial reference packs for NZ/Australia, North America, UK/Ireland,
continental Europe and Japan, followed by separately researched Latin American,
Gulf, South/Southeast Asian and African country contexts. These are coverage
workstreams, not assertions that each region has one uniform style. Country,
traffic side, climate, urban density, zone and observed site size select compatible
features. Evidence overrides regional defaults. Keep a neutral fallback for
unreviewed localities; do not silently activate an unvalidated broad-region pack.

For each pilot pack, author at least three coherent identities and small/medium/
large compatible variants. Use persistent semantic seeds so rebuilding does not
rebrand a station. Mapped names/brands remain attached to their source; inferred
identities use consistent fictional branding rather than assigning an unrelated
real operator. Review actual station imagery/locators before fixing visual motifs.
Current research establishes reference leads, not a completed visual survey:
[Z truck-stop/service-station formats](https://www.z.co.nz/for-businesses/z-business-fuel-card/our-network/truck-stops),
[Aral shop and food formats](https://www.aral.de/de/global/retail/einkaufen-und-verpflegen.html),
[ENEOS Japan network](https://www.hd.eneos.co.jp/english/business/energy/),
[Love's location/amenity finder](https://www.loves.com/en/location-and-fuel-price-search).

Observed fuel/service facilities and commercial zones inform size and supporting
uses; do not force a truck stop into a small parcel. Fuel forecourts share curb,
surface and reservation plans with complexes, including tanker/service space
where supported. Drainage intent may distinguish fuel areas but does not invent
underground equipment. Car washes, EV areas and other extras need evidence or an
explicit compatible recipe with space; they are not mandatory decorations.

Extend the existing region-specific asset manifest/preload and staged spawn path.
Reuse materials and modular meshes; cap lights and decorative props. Identity
changes must not duplicate stations, drop legitimate neighboring buildings or
reset refuelling availability while adjacent tiles load/unload.

## Work and performance budgets

All values below are proposed engineering budgets, not measured performance.
Retain existing simple-case budgets where possible; record budget exhaustion.

| Work item | Initial bound / approach |
| --- | --- |
| Residential entrance search | 4 candidates, terrain points deduplicated in one tile access batch; retry within fixed candidates. |
| Complex alternative layouts | 4 orientations/topologies; bounded sweep checks per accepted route. No global optimizer. |
| Corner refinement | 2 cm target visual chord error; max 32 segments per analytic corner, diagnostic if error target cannot be met. |
| Simple site planning | Retain 512 terrain points / 24 base patches as the initial compatibility tier. |
| Large site planning | Up to 8 sectors of 512 unique samples and 24 base patches each; reuse shared samples. Oversized sites require explicit deferred partitioning, never silent truncation across a road. |
| Parking | Keep the existing 500 parked-position limit per tile initially; painting/layout capacity is distinct from spawning cars. |
| Triangulation | Hard per-chunk bounds below engine index limits; prioritize continuous access/collision over details, then split into existing staged chunks. |
| Runtime | No new per-frame planning or per-stall scene objects. Reuse worker, cache, tile-mesh and collision staging. Functional pump triggers remain bounded interactive objects. |

Measure preprocessing, candidate checks, terrain requests/latency, generation
median/p95, vertices/triangles, output bytes, cache size, draw calls, physics
triangles and collision rebuild time separately. Compare equal scenes and report
cost per accepted crossing/site as coverage changes. Initial regression gate:
unchanged simple-scene generation and collision p95 should stay within 10% of a
fresh baseline; exceeding it requires profiling and adjustment. Large-complex
budgets need empirical calibration, including the aggregate per-tile worker load.
A per-site limit alone cannot protect a dense tile. Preserve existing main-thread
staging budgets and verify streaming stalls on a dense in-game route.

## Implementation sequence and acceptance

| Step | Work | Required evidence before advancing |
| --- | --- | --- |
| 1. Baseline and diagnostics | Instrument driveway failure/eligibility, existing lot/site/fuel ownership and performance. Capture representative local/synthetic cases. | Counts distinguish candidates, complete drives, crossing-only opportunities and rejection causes; repeatable baseline reports. |
| 2. Shared records and ownership | Add sitegen records/adapters, complex membership, standalone lots, deterministic IDs, serialization and cache inputs. | Existing schema-12 behavior preserved through adapters; no double paving, duplicate marks or lost station IDs. |
| 3. Access and crossings | Ranked alternatives, independent entrances, narrow/curved frontage profiles, shared reservations, revised pass ordering. | Complete drives increase on targeted fixtures; valid entrance-only cases work; blocked/narrow pedestrian cases stay excluded. |
| 4. Pavement geometry | Adaptive corners, shared grading boundaries, contact ownership, drainage intent and lean collision. | No seam steps/folded strips; error and triangle budgets met; car traversal tests pass. |
| 5. Commercial complexes | Multi-building recipes, circulation/sweeps, parking sectors, customer/service separation and matching facade roles. | Supermarket, mall, retail park and industrial estate work across multiple tiles with usable routes and full stall envelopes. |
| 6. Markings and surface identity | Regional profiles, arrows, bays, walking/loading markings, material transitions and LOD. | Paint matches feasible routes, ground height and region; no double lines or z-fighting; no collision on paint. |
| 7. Fuel station expansion | Modular layouts and pilot identities, shared access/paving, regional manifests, triggers and lighting. | Size/region/zone matrix visibly differs; all accepted pumps refuel; no false stations, duplicate props or blocked lanes. |
| 8. Integrated validation/package | Regression suites, benchmark reports, visual sheets and real driving/streaming. | Private playtest package and honest measured report; publication remains separate from this preparation. |

Core existing suites to extend: `test_buildgen_driveways`, `test_buildgen_access`,
`test_buildgen_sites`, `test_buildgen_commercial`, `test_buildgen_landscaping`,
`test_sidewalk_collision`, `test_roadcorners`, `test_parking`, `test_gasstations`,
`test_surface`, `test_plancache`, `test_revisit`, `test_codefiles` and worker/staging
checks. Add focused shared-site, curved-access, sweep and regional-identity suites.
Use `tools/run_tests.py` with the established local Python environment; record
missing offline map data and existing Windows cache-lock limitations separately.

Required scene matrix: straight/curved/cul-de-sac residential frontage; no garage;
missing internal path; narrow footpath; steep/rough/missing terrain; obstructions;
crosswalk and neighboring mouths; no curb; corner property; supermarket; mall with
several entrances; multi-building retail park; industrial court; concave lot with
holes; shared supermarket fuel site; compact urban station; rural station; truck
stop; left/right traffic; translated/rebased and reversed tile loading order.

Acceptance checks include shared boundary equality (1 mm computational target),
no unplanned driving lip above 5 mm in collision fixtures, full-width obstruction
tests, vertical-clearance/grade-transition checks, coherent drainage direction,
accessible-route validation where authored, and deterministic output. Validate
representative passenger cars and delivery vehicles in BeamNG, including low
clearance and oblique entries. Test native collision and terrain interaction;
offline mesh equality alone cannot establish a smooth driving experience.

Preparation delivers this specification and source references. The first coding
task is Step 1 followed by the shared records/adapters, not immediate widespread
retuning of eligibility, terrain limits or parking capacity.
