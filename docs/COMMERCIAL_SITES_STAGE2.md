# Property-fitted commercial sites

1 November 2026. Schema 11 adds procedural loading courts, raised docks,
straight service access, parking and pedestrian connections to the warehouse,
supermarket and trade-unit recipes. It shares the residential access solids,
terrain frame, worker serialization, collision and visual LOD pipeline.
Residential roof sampling, zoning and driveways remain integrated.

## What generates

There are no reusable site layouts. Facade lengths, source property boundaries,
declared obstacles and measured boundary access points determine what fits.
Stable semantic seeds vary bay spacing and setback within geometric limits.
The same property inputs produce the same result after rebuilding or changing
tile origin. Partial stalls and scaled doorways are never used to fill gaps.

* Pedestrian access is reserved first, from the actual primary landing or stair
  toe to a supplied footpath interface. Its endpoint levels are preserved.
* Raised docks require an explicit loading-floor offset. Up to six closed
  service shutters, concrete platforms, rubber bumpers and edge markings share
  a fitted loading court. Warehouse courts reserve 32 m depth; supermarkets
  reserve 28 m. These are model clearance defaults, not certified swept paths.
* Where no dock court fits, an existing ground-level shutter can receive one
  straight service approach suitable for light service vehicles. This includes
  trade units. The route avoids staff thresholds and the primary walking route.
* A frontage parking row contains up to twelve complete spaces, about 2.5–2.8 m
  wide and 5.2 m deep, with a 6 m aisle, a separate frontage walk and a connection
  to the primary pedestrian route. Actual free space determines count and side.
  Parking is omitted if the walking connection cannot be built.
* Vehicle approaches join measured property-boundary cross-sections. They do
  not cut a new road, move kerbs or invent permission for a crossing. Strongly
  misaligned approaches are omitted rather than routed through obstacles.

Paving planes use a small, fixed-size least-squares fit constrained to boundary
levels. Parking and its walking connections share a plane, preventing steps at
their junction. Raised platforms retain their measured loading-floor offset.
Missing terrain, excessive grade, conflicting interface levels or more than
15 cm of required fill rejects the affected component. This stage does not
excavate terrain, create retaining walls, design drainage networks or simulate
vehicle turning. It does not label ordinary parking spaces as accessible bays.
Small terrain features between samples cannot be verified by this model.

Accepted site paving replaces overlapping decorative gravel strips. A valid
measured footpath connection replaces the earlier inferred short path while
retaining the entrance landing/stairs. An omitted component leaves existing
access in place. All doors remain closed facade panels.

## Supply property evidence

The current map feed provides building footprints, not dependable cadastral
boundaries or surveyed service/footpath levels. Site generation is therefore
opt-in through `--building-sites PATH` (environment: `BNE_BUILDING_SITES`). Without
a catalogue, normal commercial buildings and residential generation continue.
The supplied synthetic example is a format demonstration and is **not enabled
by the launcher**; it does not match a live building ID.

Use a GeoJSON FeatureCollection with one Polygon feature per property:

| Field | Meaning |
| --- | --- |
| `geometry` | Property Polygon in WGS84 `[longitude, latitude]`; closed rings; holes allowed |
| `properties.site_id` | Unique stable property identity |
| `properties.owner_id` | Exact source building ID used by the map feed, not its address or generated component ID |
| `properties.source`, `release` | Nonempty source attribution and pinned release identifiers |
| `properties.obstacles_complete` | Must be `true`; confirms the exclusion inventory is complete |
| `properties.exclusions` | Array of GeoJSON Polygons for neighbouring buildings, other roads/paths, protected areas and other permanent obstacles inside the property |
| `properties.ports` | At most eight `{ "kind": "service" | "parking" | "pedestrian", "coordinates": [[lon, lat, h], [lon, lat, h]] }` records |
| `properties.dock_rise` | Optional measured loading-floor height above the resolved building base, 0.8–1.5 m |

Port endpoints define an existing usable boundary cross-section, including its
width and crossfall. Heights are **ellipsoidal elevations in metres**, matching
the terrain/geodesy pipeline, not unspecified local/orthometric levels. Both
endpoints must lie within 0.1 m of the property boundary, and width must be
1.2–12 m. Supply these from compatible evidence; do not infer them from a
building outline. Other buildings and existing infrastructure must be listed
as exclusions so tile load order cannot change the result.

Properties cannot overlap or share an owner. Multipart buildings, parent
buildings rendered as parts, and footprints cut by infrastructure do not acquire
duplicated site work. Shared multi-building estates need a later ownership
model. Polygon complexity is capped at 128 coordinates, exclusions at 32,
catalogues at 10,000 sites / 16 MiB. The loader rejects invalid evidence.

From the extracted source/package folder:

```powershell
python tools/validate_building_sites.py C:/data/building-sites.geojson
run_server.bat -- --building-generator v2 --building-sites C:/data/building-sites.geojson
```

For the combined playtest, append `--building-sites "C:\data\building-sites.geojson"`
to the `call run_server.bat` line in `test_v2.bat`; retain its existing residential
roof-colour, zoning and path options. Restart the server after changing evidence.
Catalogue content hashes participate in context and generated-cache identity;
raw downloaded map caches do not need deletion.

An example is in `docs/examples/building-sites.synthetic.geojson`. Reproduce
the synthetic previews and planner benchmark with:

```powershell
python tools/site_preview.py --out build/sites.png
```

## Cost and checks

Planning runs during generation, with no new per-frame simulation, network
fetches, route search, optimization solver or exhaustive layout search.
At most four dock candidates and eight ground-level service candidates receive
fit checks. Each parking orientation tries at most twelve spaces. One batched
terrain request per eligible property is capped at 512 points, approximately
3 m apart. At most 24 base pavement/platform patches and twelve dock bumpers
are emitted. Sites with building footprints over 128 vertices are skipped.
Properties absent from the catalogue avoid projection and site-fitting work.

The 90-case synthetic planner benchmark measured 7.7 ms median and 10.2 ms p95
on this workstation, with at most 369 terrain samples. This measures site
planning with synthetic terrain, excluding DEM fetches, mesh generation and
game rendering. The benchmark JSON records the fixtures and actual values.

266 focused tests pass across 18 suites, including 16 site tests: irregular
boundaries, exclusions, levels, rough/missing terrain, trade service access,
nonoverlapping pavement, exact surface joins, repeated rendering, source-owner
ingestion, infrastructure cuts, cache invalidation, serialization and finite
nondegenerate visual/collision meshes. Existing residential suites pass.
The previews use approximate materials; actual BeamNG visuals, driving,
streaming and collision transitions still require playtesting.

## Engineering basis

The separation of pedestrians and loading operations follows the principles in
[HSE loading-area guidance](https://www.hse.gov.uk/workplacetransport/loading.htm).
Preserving existing footpath interfaces follows the considerations described in
[TCDC vehicle-crossing guidance](https://www.tcdc.govt.nz/Our-Services/Transport-Roads-and-Road-Safety/Vehicle-Crossing)
and [MBIE vehicle-entrance guidance](https://www.building.govt.nz/building-code-compliance/d-access/accessible-buildings/vehicle-circulation-parking/vehicle-entrances).
These inform conservative game geometry; the defaults do not assert compliance
with every jurisdiction, vehicle class or accessibility standard.
