# Building presets and zone influence

Latest update: the catalogue now contains 48 recipes and 22 environments, with
Christchurch and NYC source adapters. The private playtest includes Christchurch
polygons. See [current regional mapping and evidence workflow](BUILDING_ROOF_COLOURS_AND_ENVIRONMENTS.md).
The 36-preset discussion below describes the earlier checkpoint.

Local implementation checkpoint, 1 November 2026. Enable with `--building-generator v2`.
Legacy remains the default. This extends the 816b344e source snapshot; it is not a
published release or a completed global reconstruction system.

## What runs

The planner selects one of 36 immutable recipes from
`server/buildgen/catalog/presets.json`. Selection uses resolved function, explicit
class/subtype, occupied area, courtyard topology and storeys. Nearby original
building observations and observed land-use overlap resolve missing function and
dimensions. Climate selects a modest presentation response. Stable source IDs
seed choices. The result carries reasons, alternatives and catalogue version in
`spec.inference.selection`, and survives worker serialization in schema 6 plans.

Recipes cover detached houses, bungalows, cabins, terraces, apartments, courtyard
housing, shopfronts, retail halls, offices, hotels, mixed use, workshops, warehouses,
manufacturing shells, barns, schools, healthcare, civic buildings, transport,
garages, sheds and utilities. Generic and unknown shells are explicit fallbacks.
Footprint, holes and mapped heights remain authoritative. Specific functions need
class evidence; an industrial zone does not invent tanks or chimneys.

Recipes control window width/bay spacing, storefront composition, service shutters,
garage eligibility and shading. Windowless warehouses, barns and sheds now receive
grounded pedestrian entries when a frontage is available. Commercial entries share
the same door/window reservations. Domestic driveways and fences no longer attach
to workshops and schools. Service shutters are closed visual surfaces, not loading
docks or traversable garage interiors. Their thresholds use frontage ground samples.

Window sills now have thickness, sloping tops, undersides and end caps. Warm-climate
house windows can receive small sun hoods beneath rectangular pitched eaves when
opening clearance permits. Details simplify at distance; collision retains the
existing occupied shell and resolved access geometry.

## Zone semantics and importing data

The existing map pipeline supplies **observed land use**. The new additional
overlay is `server/buildgen/catalog/zones.json`, a pinned RFC 7946 GeoJSON feature
collection. It ships empty: no worldwide statutory-zone coverage is claimed.

Each feature requires `source_id`, `release`, `lineage`, `raw_code`, `meaning`,
`status` and a list of normalized `uses`. Meanings are `observed`, `statutory`,
`planned`, `modelled`; statuses are `effective`, `proposed`, `superseded`.
Normalized uses are residential, commercial, industrial, agricultural, civic,
religious, transport, ancillary, mixed and unknown. Missing/unmapped codes fail
import instead of silently becoming residential.

Use `tools/import_building_zones.py --help`. A local crosswalk has the form
`{"LOCAL_CODE": ["residential"], "AMBIGUOUS_CODE": ["commercial", "industrial"]}`.
For example, after preparing a licensed WGS84 polygon release and local crosswalk:

```powershell
python tools/import_building_zones.py zones.geojson crosswalk.json --field ZONE_CODE --source local-plan --release release-id --lineage local-survey --meaning statutory --status effective
```

This replaces the one pinned catalogue; combine releases deliberately beforehand.
Do not put private datasets into a public package. Restart the server after import.
The catalogue participates in development/package source hashes, context manifests
and PyInstaller data collection. No download occurs in the planner. A spatial index
selects zone polygons, then overlap is measured in the context's local metric frame.
Courtyard holes remain excluded. Dateline-spanning zone polygons must be split.

At least 60% footprint overlap is required for use support. Observed use has the
strongest zone weight; modelled use is weaker. Statutory permissions provide only
weak support and cannot establish use alone. Proposed, superseded and planned
layers do not alter existing-use reconstruction. Correlated/duplicate layers do
not accumulate votes. Mapped use wins, with a diagnostic for a statutory mismatch.
Ambiguous classes retain divided support; weights are not calibrated probabilities.
The importer does not interpret legal development envelopes or claim compliance.

## Joined hip roofs

Orthogonal nonrectangular footprints now use maximal occupied rectangular wings
and a continuous upper union of their hip planes. This produces joined ridges and
valleys with eaves at exterior and courtyard walls, removing the giant upper-wall
wedges from supported L/T/H/U and courtyard shapes. Analytical plane UVs, mapped
roof-top heights, collision and skyline remain shared. Translation-normalized
solver caching avoids repeating the same wing calculation at different positions.

The solver is bounded to 10 unique coordinates per axis and eight maximal wings.
Nonorthogonal shapes, larger arrangements and invalid partitions retain the
diagnosed clipped-envelope fallback. Gabled cross-wing roofs remain unfinished.
This is not a general straight-skeleton or drainage-design solver. No extra solver
dependency was added. Main-thread import/rebuild staging was not changed.

## Research mapping and limitations

The private research folder now includes `building_templates_expanded.json`
(original 68 proposals plus 26 additional edge-case requirements) and
`preset_implementation_map.json` (all 68 original forms mapped to a partial runtime
recipe or marked dedicated geometry pending). The original workbook is unchanged.
The 36 executable recipes share geometry components; they are not 36 fully authored
architectural models. Named historic/regional style packs, party-wall suppression,
open-sided shelters, tanks/silos, greenhouse structures, split-level foundations,
site layouts and parcel-aware service access remain dedicated work.

Generate synthetic review sheets with:

```powershell
python tools/building_preview.py --preset-fixtures --out ../artifacts/buildings-zone-presets.png
python tools/building_preview.py --roof-fixtures --hipped-roofs --roof-grid --out ../artifacts/buildings-wing-roofs.png
```

These show approximate material colours or UV checkers, not BeamNG textures and
lighting. The associated JSON includes preset explanations and roof diagnostics.
Real geographic fidelity, material appearance, driving performance and Windows
executable packaging still require game acceptance. The existing Python launcher
is the supported local test route; no executable was rebuilt.
