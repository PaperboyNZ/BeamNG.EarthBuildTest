# Vegetation and physical surface exclusions

## Server filtering

Implemented 1 November 2026 in `server/vegetation.py`, cache **VERSION 21**.
The vegetation cell cache path includes this version, so version-20 placements
with trees in sidewalk/tree-pit exceptions are not reused. Eight-value vegetation
rows and group IDs are unchanged.

Previously, inferred street trees could be moved into a sidewalk/tree pit,
footway lines were deliberately excluded from road masks, mapped plaza/parking
polygons masked scattered bushes/rocks only, and forest-edge bushes bypassed the
paved-area mask. These exceptions have been removed for the user's requirement
that trees, bushes and rocks stay off pavement and access surfaces.

The server now masks complete road corridors, including their drawn sidewalk
widths. It respects the wider of existing class defaults, drawn/measured widths
and retained source width observations. Mapped footways, paths, steps, cycleways,
bridleways and pedestrian lines also reserve corridors; their missing-width
fallback is one metre per side. This is a conservative procedural clearance,
not a regional standard or a claim that a missing source width was surveyed.

Source canopy crowns over roads may move beyond the complete road/sidewalk
corridor plus their full footprint. They cannot be relocated onto inferred tree
pits. Every candidate is checked again after relocation, random position jitter,
species/group selection, size variation, ordinary scatter and forest-edge scatter.

Existing retained source fields supply mapped hardscape:

- Land-use pedestrian/plaza areas use their class/subtype evidence.
- Infrastructure parking uses the same paved-lot classification as the existing
  terrain painter; explicitly grass/unpaved lots are not blanket paving.
- Existing substation yards remain free of natural trees/bushes/rocks.
- Polygon features with an explicitly observed paved/cobble surface use the
  existing road-surface vocabulary, covering supported observations without
  inventing infrastructure classes, map layers or inferred facility extents.

The current cell and its eight existing neighbours contribute polygons, matching
the existing road/building neighbour-mask extent. Green land-use classes, grass,
gardens and polygon holes are not treated as paving. A hole permits decoration
only when the entire finite footprint fits clear of the paved perimeter. There
is no special exception for an unobserved tree pit. Terrain-surface definitions
and parking/source catalogue acceptance are unchanged.

Mapped polygon interiors use the existing native `mask_polys`. Its `grow_m`
parameter only enlarges the search box; it does not geometrically buffer the
polygon. Therefore polygon boundaries also use native segment/corridor masks,
with a conservative grid-diagonal allowance. This covers thin/subpixel paving
that contains no raster pixel centre and retains holes with a safe edge margin.

After all candidates are assembled, one summed-area mask grid checks every
object's complete planar footprint. Axis-aligned squares conservatively contain
the footprint circles; radius and scale therefore matter at road shoulders as
well as inside polygons. The row-compatible minimum radius is:

| Group | Radius before scale |
| --- | --- |
| Trees, including palms/junipers and regional tree groups | `0.12 * height + 1` |
| Shrubs and desert shrubs | `max(0.12 * height + 1, 0.6 * height)` |
| Rocks and desert rocks | `0.6 * height` |

The server retains a larger declared `Items.radius`, multiplies by scale, and adds
0.25 m for placement/rounding clearance. This formula is exposed as
`vegetation.footprint_radius(items)` for parity checks; client asset bounds may
enlarge the radius further. Web-Mercator distances account for local latitude.
Nonfinite/invalid dimensions and footprints leaving the observed raster window
are omitted rather than assumed clear. Work is one grid prefix sum plus vector
queries over the existing CHM/candidate arrays, without radius-dependent repeated
grid dilation or per-object polygon scans.

The server can only mask available source evidence. Existing unavailable
neighbour/source failures remain logged; absence of a mapped polygon is not proof
that real pavement is absent. Generated building paths, driveways, garage aprons,
fuel pads and other accepted runtime surfaces require the separately integrated
road-manifest/client exclusion path, since vegetation cells are source-based and
can be generated before those surfaces. This server change does not claim that
source-only masks establish their geometry or elevations.

Grass/garden areas remain eligible for the existing natural decoration rules;
the server does not change density or invent plants where source canopy/land
cover supplies none. Bounded authored landscape detail is a separate renderer.

### Current mapped surface export

`sitegen.mapped_surfaces.collect(frame, bounds, surface)` returns bounded
`(kind, shapely.Polygon)` records in the road content's current XY frame. The
root producer supplies these to `hardscape.collect(mapped_polygons=...)` so
already loaded natural props can be excluded when the actual surface arrives.
It reads only the existing `surface.lots` cached service and `surface.extra_pads`
runway delegate, using the current frame to project source coordinates. It does
not read map-data files directly, request new facility sources or duplicate the
separate fuel-pad path.

Selection matches existing painting predicates: paved parking becomes `parking`,
pedestrian/plaza paving becomes `pavement`, substation yards become `hardscape`,
and current open paved runway pads become `road`. All four are established client
hard-surface kinds. Plain grass/garden classes and explicitly unpaved parking are
not blanket-masked. A plaza class alone does not establish painted paving; the
existing painter also requires the pedestrian subtype.

The current parking and plaza terrain/photo painters fill source holes even
where a raised plaza skin retains a hole. Therefore this helper conservatively
fills those mapped source holes too: they display paved ground rather than a
confirmed green bed. This documents the current renderer limitation without
changing its appearance. The generic hardscape record format still preserves
holes for genuinely unpaved/landscaped voids; accepted grass/garden patches remain
eligible for their bounded authored bushes/rocks.

Parsing caps are 64 cached feature tables, 10,000 feature rows, 2,048 output
polygons, 131,072 projected source vertices and 4,096 vertices per ring. Outputs
are clipped to the supplied content bounds. Overflow, a failed service or invalid
relevant geometry produces one conservative whole-bounds `hardscape` exclusion;
an ordinary empty cached result stays empty. The helper does not repair source
geometry or turn missing cached geometry into an inferred parcel.

Ten focused `test_sitegen_mapped_surfaces` tests pass, covering complete parking
bodies, current-frame/rebased projection, runway pads, exact clipping, source
array preservation, actual painted-hole behavior, grass/garden eligibility,
non-paved parking, service failures and bounded parsing. Logs are in
`build/vegetation-surface-exclusions/tests-mapped-final/`.

### Server verification

Original runtime copied before editing to
`build/vegetation-surface-exclusions/original/vegetation.py`, SHA-256
`35fcb1638558d5a6c57fe712d10f9c29e1dce93902aee87af379c6f43a499d71`.

```powershell
New-Item -ItemType Directory -Force build/vegetation-surface-exclusions/tmp | Out-Null
$env:TEMP = (Resolve-Path build/vegetation-surface-exclusions/tmp).Path
$env:TMP = $env:TEMP
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/run_tests.py test_vegetation_surfaces test_vegetation.VegetationTest test_vegetation.RegionalTest test_vegetation.DilateTest test_vegetation.RockSinkTest test_vegetation.FlatTileTest test_vegetation.DemFailedTest --par 3 --timeout 120 --logs build/vegetation-surface-exclusions/tests-final
```

**29 tests passed:** nine new hardscape/green-space tests and twenty existing
vegetation tests. Tests cover all three object kinds, scaled shoulder clearance,
full sidewalk/footway widths, plaza/parking/observed paving, grass/garden eligibility,
source holes, subpixel surfaces, post-jitter positions, finite radius parity,
source-canopy filtering, deterministic generation, native masks and unchanged
row/tile behavior. Existing tests now assert full-footprint sidewalk clearance
instead of requiring an inferred tree-pit placement.

The first sandboxed attempt at the unfiltered `test_vegetation` module hit an unrelated
`FlatHelloTest.test_older_mod_gets_rows` stalled during Windows asyncio loop setup,
inside `socket._fallback_socketpair`/`accept`, before reaching vegetation behavior.
The captured stack is in `build/vegetation-surface-exclusions/tests-initial/`.
The exact full `test_vegetation` and `test_vegetation_surfaces` rerun outside that
sandbox subsequently passed all 29 tests, including both hello tests. Successful
logs are in `build/architecture-next/vegetation-local-runtime/`. No generator
workaround was introduced for the sandbox socket failure.
No in-game appearance, streaming or performance acceptance
is claimed from these source-level tests.

## Generated surface producer and planted detail

`sitegen.hardscape.collect` exports `vegetationExclusions` version 1 in both anchor
and geographic road manifests. Each polygon has complete rings, a hard-surface
kind and a finite vertical interval. Coordinates use the road content ENU frame;
building-local solids receive the tile offset once. Geographic placement and
later rebases are the client's responsibility. Missing ground is explicitly
`unknown_height: true`, so the mask remains horizontally local and vertically
conservative without rotating sentinel heights into distant XY coordinates.

Inputs include accepted building paths, steps, parking and paved margins; exact
garage aprons even without pedestrian access; legacy driveways; drawn road ribbon
edges and fixed deck heights; sidewalks including their sloped back skin and
corners; and actual fuel-pad polygons. `sitegen.mapped_surfaces` supplies cached
mapped paving and current runway pads through existing terrain-surface services.
Source holes are retained where the displayed surface retains them. No inferred
parcel box stands in for a known physical surface.

Draped surfaces share one deduplicated terrain-sampling pass. Output is clipped
to the owning tile and bounded by 8,192 polygons / 131,072 vertices. Overflow
conservatively excludes natural props across that tile instead of truncating
protection; it does not truncate physical geometry. This rare fallback can also
suppress plants in green space and is not a claim of measured normal-case cost.

Accepted `lawn_margin` and `garden_bed` patches are absent from paving masks. Both
now receive bounded near-detail bushes and rocks, with deterministic selection
and complete geometry kept inside the accepted soft patch. Existing profile and
global detail budgets still apply; utility profiles may remain unplanted. These
small mesh decorations add no collision shapes or per-frame simulation. Ordinary
natural trees/bushes/rocks remain allowed where their complete footprint clears
physical paving, including sufficiently large real garden holes.

Producer tests exercise coordinate offsets, garage-only access, road/sidewalk
widths and heights, sloping sidewalk backs, unknown ground, clipping/overflow,
source holes, anchor/geotile JSON retention, green-patch geometry containment,
unchanged collision and both bush/rock materials across seeds. A matching updated
server and mod are needed for generated-surface runtime filtering; an older mod
ignores the optional metadata.

## Client delivery, removal and rebase

The client consumes `vegetationExclusions = {v = 1, polygons = ...}` from each
road-content manifest. Polygon records carry `rings` (outer XY followed by soft
holes), `min_z`, `max_z`, `kind` and optional `unknown_height=true`. Accepted hard
kinds are pavement, driveway, parking, footpath, road, fuel and hardscape. Explicit
grass/garden/lawn/planting records are not exclusions. The server remains
responsible for producing valid physical polygons rather than parcel boxes.

`trees.setSurfaceExclusions(owner, payload, placement, fallbackBox)` installs a
road owner's detached mask. Geotile rings are mapped through the same current
placement as road rows. Known height bounds are transformed at both endpoints and
all vertices, with conservative XY padding for height shear. Unknown-height
sentinels are **not** projected as physical coordinates: their XY maps at local
z=0 and their vertical check remains unconstrained. This prevents kilometre-wide
exclusion shadows after a distant-anchor rebase.

Masks apply to natural groups in both cached vegetation tiles and mixed
`onRows`/`onGeoRows` street-tree rows. Deciduous, conifer, shrub, rock and the
regional natural groups participate. Doors, benches, signs, lamps, guardrails and
other street equipment remain exempt. Whole plants that fit inside real garden
holes survive; an object's envelope crossing onto adjacent paving is suppressed.
The separately fitted planted meshes described above keep their own soft-cover
reservations.

The effective horizontal envelope is the maximum of the server-style group
footprint proxy and a conservative stock-group height envelope, multiplied by
`max(1, abs(rowScale))`, plus a 0.25 m placement/rounding margin. The renderer
otherwise ignores row scale and sizes the selected asset from height, so a
subunit row scale cannot shrink its exclusion envelope. The selected asset's
actual scaled catalogue height, including the renderer's minimum scale clamp,
participates in this check. Broadleaf/tropical crown, conifer, bush and wide low
rock envelopes have separate configurable coefficients in
`trees.SURFACE_ASSET_BOUNDS`. These are engineering bounds, **not surveyed
per-model mesh measurements**; asset-width calibration and game captures remain
required. Vertical overlap considers the plant's height, preserving low growth
beneath genuinely elevated paving while excluding a tree that reaches into it.

A 64 m spatial index holds polygon references and affected vegetation-tile
references. A new/replaced/removed mask invalidates only intersecting tile buckets.
The existing row, item, shape and time budgets then remove already-spawned natural
items or admit newly clear ones. Source cached rows are retained, so restoring
vegetation after an owner retires remains deterministic. This adds no per-frame
scan over all scene vegetation. Solid-item removal requests the normal throttled
collision refresh.

The client accepts up to 8,192 polygons and 131,072 vertices per owner, bounds
index references, and limits each footprint query to 8,192 examined vertices.
Malformed envelopes, exceeded input/index limits and overfull local queries fail
conservatively in the affected road area instead of silently allowing natural
objects onto paving. That conservative fallback can temporarily suppress soft
planting too; it is a diagnosed capacity/data fallback, not proof that the area is
paved. Initial validation/index construction is synchronous and can still be
expensive at the maximum envelope size. Actual game frame-time acceptance remains
open.

Road-content masks are reinstalled at geotile placement/rebase. Retained road
owners keep their masks when vegetation clears during a disconnect, preventing a
subsequent vegetation reload from bypassing unchanged road content. Retiring
owners keep masks until the physical deletion queue drains and their recorded
pooled slots have no live references. Installing the same key cancels its stale
pending release; clear/reset also retire pending owners. This closes the transient
where a tree could respawn while the old pavement mesh was still visible.

## Off-engine client verification

Original client runtime files are preserved under
`build/vegetation-surfaces/original`. No Lua executable was on PATH. A project-local
Lupa 2.8 wheel supplies embedded LuaJIT 2.1 under `build/lua-runtime`; no system
installation was used. The small artifact runner is
`build/vegetation-surfaces/run_lua.py` and starts an isolated Lua runtime for each
existing test file.

```powershell
$python = '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe'
& $python -m pip install --target build/lua-runtime lupa
& $python build/vegetation-surfaces/run_lua.py --deterministic-clock mod/tests/test_surface_exclusions.lua mod/tests/test_trees.lua mod/tests/test_roads.lua mod/tests/test_roadgeo.lua mod/tests/test_building_progress.lua mod/tests/test_building_staging.lua mod/tests/test_rebase.lua mod/tests/test_collisionfoci.lua
```

Result: **411 checks passed across eight modules**, including 45 new exclusion
checks. Coverage includes vegetation-first/mask-first arrival, whole-object edge
intersection, garden holes, mixed street-tree/bench rows, elevated paving,
malformed/overfull inputs, bounded affected-tile invalidation, unknown-height
shear, actual road/vegetation geotile rebasing, retained-owner reload, delayed
physical deletion, pooled references, same-key replacement and level reset.
The final log is `build/vegetation-surfaces/tests/final.log`.

The runner's deterministic clock supplies a positive 0.001 ms `hptimer` tick.
Without it, the existing roads suite reports 97 passes and one failure at
`then the pending rebuild runs`: Windows `os.clock` can report zero elapsed time
for the immediate strictly-positive reload gate. The identical failure was
reproduced against **both pre-edit runtime backups** using
`run_lua.py --baseline mod/tests/test_roads.lua`. No product timing workaround was
added. The new exclusion, trees and roadgeo suites also passed with the ordinary
clock. These are stubbed engine tests, not an in-game vegetation/collision or
performance claim.
