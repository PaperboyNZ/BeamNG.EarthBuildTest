# Commercial building generation first stage

1 November 2026. Enabled by `--building-generator v2`, together with the existing
residential roof-colour, environment, garage and driveway updates. Schema 10
retains their decisions and adds commercial elevation roles and diagnostics.

The catalogue now contains 51 recipes. Three dedicated recipes override compatible
broad shells when mapped class/subtype and dimensions fit:

| Recipe | Selection | Generated appearance |
| --- | --- | --- |
| `ci_logistics_hall` | Warehouse, 50 m² or more, 1–2 resolved storeys | Concentrated staff glazing/entry and a fitted run of closed service shutters |
| `ci_supermarket` | Supermarket, 150 m² or more, 1–2 resolved storeys | Wide glazed public entry with matching landing, concentrated display glazing and opaque side/rear walls |
| `ci_trade_units` | Workshop, 300 m² or more, 1–2 resolved storeys | Fitted groups of staff doors and shutters with high-level glazing where height permits |

Small workshops keep their existing recipe. Generic industrial/commercial use,
hangars and malls do not acquire these specific functions merely through area
or zoning. Existing mapped footprint, holes, height, roof form/material and
roof-colour evidence remain authoritative. Grouping is architectural subdivision,
not a claim to know real tenancies.

## Procedural fitting

`buildgen/commercial.py` derives entry location, frontage runs, group counts and
window widths from the actual eligible elevation and stable semantic seeds.
It never scales a fixed building or site layout. Different widths and seeds change
composition while preserving coherent door/window dimensions. Complete modules
fit within available spans; excess wall remains blank when the detail budget is
reached. Warehouse glazing occupies the staff zone, and supermarket glazing fits
around its actual entrance rather than deleting conflicting grid windows.

Near and distant representations share immutable openings. Service and staff
doors are closed panels, with no claimed interiors. Added staff thresholds share
visual/collision surfaces. The public supermarket doorway is mesh geometry,
avoiding a domestic stock door placed over a wider entrance. Existing primary
access and footpath integration remain shared with the residential engine.

## Terrain and obstruction checks

The commercial pass runs after primary access resolution. It uses one spatial
index and one additional terrain batch for the eligible commercial buildings.
Each optional opening samples six points across its wall contact and a short
exterior strip. Known buildings and buffered road corridors suppress obstructed
openings. Existing paths and thresholds reserve space against service/staff
entries; upper glazing is not rejected simply because a path is below it.

Missing terrain, excessive local level differences or inadequate headroom omit
service/staff doors with diagnostics. Staff threshold sample relief is limited
to 90 mm, keeping the modeled 60 mm lift within a 150 mm fill envelope. These
are conservative generation cutoffs, not construction standards. Repeated
resolution replaces the commercial thresholds rather than accumulating them.

This first stage uses the source-resolved front elevation. It does not infer
rear service roads, loading docks, truck aprons, parking layouts, new road
connections, parcel boundaries or statutory access compliance. Separate service
elevations and full site layouts remain later stages requiring suitable evidence.
Collinear footprint-edge merging and party-wall treatment across all elevations
are also broader engine work; this pass suppresses known obstructed optional
frontage openings without altering mapped topology.

## Performance

There are at most 16 inferred groups and 64 openings on the eligible frontage,
with at most 384 additional terrain points per building. An optional opening is
rejected when its local spatial query exceeds 64 obstacles. No iterative fitting,
layout optimisation, imagery downloads, hydraulic simulation or per-frame
generation was added. Existing material batching, chunk splitting and staged
game imports remain unchanged.

Run the offline review and benchmark with:

```powershell
python tools/commercial_preview.py
```

The report writes planning/access, freezing and near/lite/collision timing
percentiles for 90 varied synthetic buildings. Local measurements are a few
milliseconds per building for each main stage; consult the associated JSON for
the exact run. This excludes map acquisition and uses a cheap flat terrain
provider. It is not an in-game frame-time measurement.

## Validation and combined playtest

250 tests pass across 17 relevant suites, including 12 new commercial tests.
Checks cover fitted dimensions, composition variation, obstruction and terrain
rejection, missing frontage, bounded sampling, repeat resolution, translation,
worker serialization, finite/nondegenerate meshes, collision, chunk transport,
packaging inputs and existing residential functionality. Eighteen saved baseline
fixtures match exactly for geometry, access and inference after the changes.

The private combined source package preserves the preceding package's prepared
roof colours, Christchurch zoning pilot, source attribution and automatic
residential path settings. It includes the current server and mod source and
launchers with normal CRLF line endings. No executable was rebuilt.

Close game/server, extract the combined package into a fresh folder and run
`test_v2.bat`. Inspect large warehouse frontages, supermarket entries and trade
rows alongside houses and garage crossings. Check materials, shutters, approach
levels and LOD transitions in BeamNG. The preview sheet uses approximate colours;
actual game appearance and driving performance remain to be validated.
