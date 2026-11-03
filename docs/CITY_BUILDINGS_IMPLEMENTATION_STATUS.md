# City buildings first implementation slice

Implemented 1 November 2026 in the active source snapshot, building-plan schema
18. The regional generic-block continuation advanced the source to schema 17
while this work was starting; city serialization follows it without replacing
that work. Existing extracted playtest packages and the launcher are unchanged.

This completes the bounded city-plan foundation and an initial visual slice of
C2 in [the implementation plan](CITY_BUILDINGS_IMPLEMENTATION_PLAN.md). It does
not complete the shared-site, new material-asset, part-assembly or game-review
milestones.

## Working behavior

`buildgen/city.py` selects five material-compatible compositions: curtain office,
panel office, masonry office, contemporary hotel and masonry hotel. Initial
eligibility is an ordinary flat-roof office with 13–120 resolved floors or an
actual `hotel` with 5–120 resolved floors, in both cases with body height over
15 metres. Motels/hostels, low offices, pitched roofs, specialist structures and
unsupported source shapes retain their existing paths. Source class, material,
height, roof and holes remain authoritative; no era or hidden structural system
is inferred from a regional name.

The frozen `CityArchitecture` record reuses the existing `programme` floor datums,
merged elevation runs, source-edge mappings and semantic seed channels. It stores
one fitted descriptor per run rather than one Opening per window. The existing
access solver still owns the actual door/threshold and all ground geometry.

Facades have aligned bays, separate solid and glazed surfaces, consistent floor
divisions and a restrained roof termination below the source height. Near detail
adds bounded lower-storey reveals and compatible screen strips. Lite geometry
uses full-height pier masks and repeated glazing rows, preserving aperture
positions with fewer quads. These masks and reveal details are visual only.
Existing stock materials are reused; dedicated physically calibrated city glass,
metal and spandrel assets remain C3 work.

Admission limits are 64 elevation runs, 48 detailed columns per run, 2,048 panes
per building and 96 optional near components. Oversized admitted buildings switch
all their runs to complete textured floor bands: every source storey and envelope
remains, with a diagnosed reduction in facade detail. An unsupported run count
retains the existing renderer. These are local composition bounds, not a new
global scheduler. Existing v2 chunk splitting and staged publication are retained.

## Regional descriptions and isolation

`tools/compile_city_regions.py` produces
`server/buildgen/catalog/city_regions.json` from the allowed descriptive fields
of `environments.json` and the authored [64 city briefs](CITY_REGIONAL_DESIGN_BRIEFS.md).
Every existing geographic ID is represented. Records retain full source text,
abbreviated geographic scope, city/public-space interpretation, source digest,
qualitative cues and `text_based_proposal` status. Antarctic station context has
an explicit neutral result rather than an inferred urban identity.

The compiler annotates a small declared vocabulary of recess, screen, horizontal,
masonry and shelter cues from the city brief text. It reads no compiled regional
styles or numeric facade/roof weights. Runtime currently uses compatible recess,
screen and horizontal cues; the broader public-space and shelter directions
remain recorded for the later shared-site integration. The 64 descriptions do
not imply 64 uniquely implemented architectural systems or verified local styles.

City facade/roof colour fallback bypasses the existing regional style parameter
path. Source colours and accepted roof-colour evidence still take priority.
Geographic identity continues through the current location/overlay resolver;
no separate map, network lookup or AI inference is introduced. Unrelated regional
buildings, their opening/roof variants and the newer generic blocks remain controls.

## Pavement and landscape integration

Existing entrances, thresholds, automatic commercial frontages, site paths,
parking, bed curbs, native-asset planting and vegetation exclusions remain with
their current planners. City identity changes only the colour preference of
already accepted commercial paving; path widths, cover choices, plant placement
seeds, physical solids and reservations stay with the existing system. This is
not yet a hotel drop-off or city-plaza layout implementation.

Street/sidewalk clipping now rebuilds city runs from the clipped footprint.
Surviving party-wall labels are mapped by their actual original wall segments,
not by stale edge indices. New road-facing cuts do not inherit unrelated labels.
The entrance selector avoids city party walls. This preserves the recent road
clearance work across near, lite and collision geometry.

## Verification and review

**508 tests pass across 38 modules**, combining the integrated run and the final
affected-module rerun after the city clipping fix. Twelve city tests cover all
64 region records, descriptive compiler isolation, runtime style bypass, five
families, specialist exclusions, frozen worker round trips, translated frames,
physical/access parity, party walls, courtyard holes, finite nondegenerate meshes,
120-storey stress, lossless chunking, reduced LOD apertures and street clipping.

The broader run includes ordinary regional styles and generic blocks, roofs,
garages, churches, terminals, shared programme, automatic sites, pavement/access,
landscaping, hardscape exclusions, source collection and progressive loading.
Results are under `build/city-buildings/tests-integrated` and `tests-final`.
No Lua behavior was changed, and no new native-game acceptance was performed.

`tools/city_preview.py` creates a nine-building before/after geometry sheet and
JSON report. Both sheets were inspected. The unchanged low-office control has
identical near/lite/collision fingerprints. The city physical-parity test compares
actual vertex/index arrays and accepted access, rather than treating a changed
material tint in a mesh hash as a physical geometry change.

| Fixture | Near vertices before → after | Final lite vertices |
| --- | ---: | ---: |
| Curtain office | 8,450 → 7,278 | 1,886 |
| Panel office | 12,122 → 4,830 | 1,350 |
| Masonry office | 10,834 → 4,270 | 1,166 |
| Contemporary hotel | 13,190 → 4,206 | 1,130 |
| Masonry hotel | 11,166 → 3,054 | 874 |
| Rendered hotel | 9,994 → 2,366 | 718 |
| Courtyard hotel | 14,332 → 4,032 | 1,508 |
| Taller curtain office | 10,402 → 9,374 | 2,266 |

These are synthetic fixtures with explicit source materials and flat terrain.
The raster approximates material means; it does not show actual game textures,
reflections or lighting. The after report records five runs per fixture, including
the first pass. The baseline has one pass; these samples are not a controlled
before/after speedup or a game-FPS measurement. Unrelated source work continued
during the initial baseline, so retain its exact source hashes for reproduction.

From the source root:

```powershell
$env:TEMP = (Resolve-Path build/city-buildings/tmp).Path
$env:TMP = $env:TEMP
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/compile_city_regions.py
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/run_tests.py test_buildgen_city test_buildgen_road_conflicts test_buildgen_chunks test_buildgen_progressive --par 3 --timeout 120 --logs build/city-buildings/recheck
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/city_preview.py --out build/city-buildings/after.png --repeats 5
```

## Next implementation

Continue C2 with richer public-base composition and measured detail allocation,
then C3 with dedicated material roles/assets and fitted roof assemblies. Complete
C4 using the finished shared-site interfaces for lobby approaches, hotel drop-offs,
service routes and regional paving/planting. Existing local site behavior is
integrated; canonical shared ownership and occupied-resource lifetime still need
the broader programme's implementation and validation before new playable parts.

Prepare a fresh matching package after integrating those pieces; do not copy this
server change into an older packaged mod by itself. Native BeamNG material,
collision/tyre-contact, LOD/streaming and performance acceptance remain open.
