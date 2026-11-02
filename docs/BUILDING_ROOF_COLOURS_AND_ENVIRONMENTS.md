# Roof imagery and building environments

Private source checkpoint, 1 November 2026; building plan schema 9. The v2
planner now uses accepted aerial roof measurements before mapped `roof_color`,
then falls back to the material palette. Raw mapped evidence remains available
for inspection. The implementation adds 12 environment-specific recipes (48
total) and 22 environment states. The regional catalogue was subsequently expanded
to 64 themes, now active through the [regional runtime](REGIONAL_THEME_RUNTIME.md).

## Roof measurement and cost

`tools/sample_roof_colours.py` reads already-cached raw imagery and building
footprints. It makes no network requests and never runs during mesh streaming.
It erodes each footprint, excludes courtyards and checks at most 4,096 interior
pixel centres. It rejects insufficient resolution/interior pixels, very dark or
near-white pixels, green contamination and excessive colour variation. Accepted
RGB is the median after trimming luminance extremes. This is a conservative
heuristic, not roof segmentation or calibrated reflectance: green roofing,
small roofs, shadows and stale/misaligned imagery can force fallback.

Minimum evidence is 24 usable pixels at no worse than 2 m/pixel. The current
pipeline's coarse global imagery cannot establish individual house colours.
[EOX documents its global imagery resolution](https://cloudless.eox.at/documentation/introduction).
The mapped alternative is an optional attribute in the
[Overture building schema](https://docs.overturemaps.org/schema/reference/buildings/building/).

The local cache experiment found 9,382 mapped roof colours among 3,844,327 unique
buildings (0.244%). Of 761 imagery-covered comparison candidates, 228 passed the
quality gates. Only 164 also had a mapped colour; 163 of those were in Japan.
Median sampled-versus-mapped CIELAB D65 delta-E76 was 11.89; 39.6% were below 10.
Ignoring brightness, 74.4% had chroma-plane distance below 10. These are
agreement statistics, not accuracy scores; the convenience sample is strongly
regional and dominated by neutral mapped colours. There is enough variation to
justify image-first evidence, but no basis to claim globally superior accuracy.

Warm sampling of 228 distinct accepted roofs took 191–202 ms per batch
(approximately 0.85 ms/roof), excluding source selection and projection. Cached
tile read/decode median was 5.9 ms, p95 7.8 ms; OS cache state was uncontrolled.
A one-pixel mask displacement changed accepted outputs by median delta-E76
0.93, p95 6.62. Network latency was not measured.

The prepared private catalogue contains 20,278 accepted records from a bounded
50,000-building scan, completed in 80.46 s. It is partial coverage, not the whole
cache. Source-ID plus canonical footprint digest prevents reuse on changed
geometry; raw image-byte digests preserve provenance. Startup loads the 7.9 MB
JSON once per process (about 156 ms here); 250 pre-keyed dictionary lookups took
0.043 ms. The latter excludes footprint hashing and context resolution.

This path covers ordinary v2 buildings. Elevated building parts do not inherit a
parent's roof sample, and specialised legacy structure recipes remain separate.
RGB currently tints the existing roof texture; texture multiplication and game
lighting mean the rendered result is not a calibrated photographic match.

## Sources and environment semantics

The executable source registry retains all 68 earlier research sources, their
access/licence notes and implementation status. Existing Overture observed land
use remains active. Two explicit adapters are implemented:

| Source | Current implementation | Meaning and safeguards |
| --- | --- | --- |
| Christchurch District Plan, layer 78 | Download/local import; 55 raw zone codes; private pilot has 6,654 polygons | Statutory permission, weak evidence of present use. Requires `LegalStatus=Operative` and an empty `RemovedByPlanChangeIdentifier`; retired polygons can still say Operative. |
| NYC MapPLUTO | Local GeoJSON import; LandUse 01–11 | Observed parcel land use. Mixed use remains mixed; vacant and parking land do not become houses. No NYC polygon dataset is bundled. |

The Christchurch snapshot was retrieved for the public city envelope
172.45,-43.65,172.75,-43.43. Intersecting source polygons are retained whole.
Eleven invalid self-touching polygons were repaired only after confirming a
relative area change below 1e-8; the raw source snapshot is retained privately.
Unknown codes fail import. Proposed/superseded zones cannot influence buildings.
Source IDs, raw codes, release, original attributes and lineage remain attached.
See the [official Christchurch layer](https://gis.ccc.govt.nz/server/rest/services/OpenData/DistrictPlan/FeatureServer/78)
and [NYC PLUTO data dictionary](https://s-media.nyc.gov/agencies/dcp/assets/files/pdf/data-tools/bytes/pluto_datadictionary.pdf).

A zone must overlap at least 60% of a footprint before assigning an environment.
Conflicting environments remain unresolved. Zoning never enlarges measured
footprints/heights or establishes occupancy by itself. Explicit building classes
retain their specialised recipe; zone weights select only among compatible
generic forms. Regional material priors fill missing low-rise residential/mixed
evidence and never replace mapped materials. Ratios are authored defaults, not
measured regional prevalence.

| Environment | Compatible generated form |
| --- | --- |
| Low-density residential | Suburban low-rise shell; inferred detached garages where frontage and setback permit |
| Medium-density residential | Compact house or walk-up, constrained by existing dimensions/floors |
| High-density residential | Walk-up, perimeter/block shell; no invented tower height |
| Rural residential / rural | Rural low-rise shell; explicit agricultural classes keep their farm recipes |
| Commercial frontage / centre / mixed centre | Frontage shell, commercial block or mixed-use mid-rise |
| Large-format commercial | Hall shell and broad service facade |
| Light / heavy industrial | Distinct industrial shell defaults; no invented industrial plant |
| Education / health | Civic campus shell unless the mapped class provides a more specific recipe |
| Transport / open space / parking / vacant / unknown | Conservative existing mapped-class fallback; no inferred dwelling from permission alone |

The 12 additions are parameterised facade/function recipes, not 12 bespoke asset
sets. Existing courtyard, row-house, outbuilding, agricultural, worship,
transport and specialised recipes remain available.

## Regional mapping roadmap

The current [64-theme regional catalogue](REGIONAL_ARCHITECTURAL_THEMES.md)
supersedes the original 11-pack list. It includes geographic scopes, multiple
architectural directions per pack, detail goals, research anchors and material gaps.
The original IDs and runtime material priors remain compatible.

Global regional selection now uses a bundled offline polygon map. An explicit local regional overlay takes precedence. All 64 profiles are active, with image-informed parameterized geometry and supported materials. The original NZ/NYC zoning adapters still provide local environment/use context; they are no longer required for global regional theme selection. Geographic boundaries are approximate and source building evidence remains authoritative.

## Preparing and enabling evidence

Run from the source/package root with the installed Python environment:

```powershell
python tools/sample_roof_colours.py --cache "$env:USERPROFILE/.cache/beamng-earth" --out runtime_data/building-roof-colours.json
python tools/prepare_building_zones.py --source christchurch --download --bbox 172.45 -43.65 172.75 -43.43 --out runtime_data/christchurch-building-zones.geojson --raw-out runtime_data/christchurch-source.geojson
python tools/compile_building_zones.py runtime_data/christchurch-building-zones.geojson runtime_data/christchurch-building-zones.npz
python server/earthd.py --building-generator v2 --building-roof-colours runtime_data/building-roof-colours.json --building-zones runtime_data/christchurch-building-zones.npz --building-paths auto
```

Use `--max-buildings 50000` to bound a roof preparation run. Omit it for all
cached overlapping building cells. To refresh new areas, first let the normal
application populate its map/imagery cache, stop the server, rerun preparation,
then restart. Sampling never downloads missing tiles or updates itself in the
background. New prepared output replaces the previous scan rather than merging
it. For NYC use `--source nyc_pluto --input local-export.geojson --release RELEASE
--out normalized.geojson`, then compile it. Current runtime accepts one zoning
catalogue; a combined normalized collection must be prepared to cover multiple
jurisdictions simultaneously.

The environment equivalents are `BNE_BUILDING_ROOF_COLOURS`,
`BNE_BUILDING_ZONES` and `BNE_BUILDING_PATHS`. External content digests enter
generated cache identities. Catalogues are pinned per process: restart after
changing them; no cache deletion is required.

Packed zoning retains exact WKB coordinates and validated metadata, with no
pickle or simplification. The private 47.7 MB GeoJSON becomes a 12.2 MB NPZ;
measured loading drops from 2.08 s to 0.44 s per process. Spatial queries use an
STRtree, array projection and prepared containment. Each context frame caches
at most 64 projected boundaries / 65,536 coordinate pairs; partial overlaps
still use exact intersections. A city-wide 250-footprint synthetic check dropped
from 4.26 s to 0.395 s (about 1.58 ms/query). These timings exclude building mesh
generation and game frame time.

## Attribution and validation

Christchurch data: Christchurch City Council, District Plan zones, snapshot
1 November 2026; filtered/normalized and geometry repaired as described above.
The council publishes its general geospatial data under
[CC BY 4.0 unless otherwise specified](https://ccc.govt.nz/environment/land/geospatial-services).
No endorsement is implied. The private roof catalogue records attribution to
IGN BD ORTHO (Licence Ouverte 2.0), MassGIS 2025 aerial imagery and USDA NAIP
(public domain); it contains derived RGB evidence, not source image tiles.
The separate comparison study also used GSI imagery; see
[GSI tile sources](https://maps.gsi.go.jp/development/ichiran.html).

Regression checks cover image-first precedence, rejected/stale samples, holes,
bounded sampling, external-evidence cache invalidation, source-code semantics,
packed zone equivalence, cache bounds and regional/material safeguards. The
latest full change set has 275 passing focused tests across 17 suites. Two
real-data roadgeo checks lack offline transport blocks, and the separate revisit
suite hits an existing Windows sidecar cleanup file lock. Neither game visual
acceptance nor driving FPS has been measured.
