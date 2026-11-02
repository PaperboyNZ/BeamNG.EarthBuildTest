# Shared architecture and access continuation

This continuation follows the integrated checklist's M1 field-lineage, M3 bounded
entrance alternatives and M4 shared composition work. It does not activate large
sites, new playable topology, regional standards or a performance release.

## Existing feed fields retained into planning

The current `overture.LAYERS['buildings']` numeric projection already fetches
`min_floor`, `num_floors_underground` and `level`. `mapgeom.Features` retains them
through its pickle-free array cache. They were absent from
`buildgen.evidence.ATTRIBUTE_FIELDS`, so ordinary building extraction and context
normalization discarded their observations. They now remain in immutable
`BuildingEvidence` through tile planning, freeze and worker pickle boundaries.
The current part projection also supplies `min_floor`; its observation belongs
to the part, not its parent's floor label.

These are source labels and counts, not geometric elevations. Signed floor/level
labels are retained independently from nonnegative underground-floor counts.
Missing values and NaNs stay unknown; invalid values stay invalid. They do not
create basement geometry, change wall height, allocate new floors or establish a
mapped access connection. Existing physical height resolution remains authoritative.

This audit verifies the configured projection, cache and planning path using
synthetic source features. It is not a new survey of live worldwide coverage.
No new source query, download, construction-date field or heritage claim is added.

Two remaining evidence gaps are explicit:

- The existing `mapgeom.bool_column` converts both missing values and false to
  `False`. Consequently cached `has_parts` and `is_underground` flags cannot yet
  support observed-negative provenance. This change does not promote them to
  `BuildingEvidence` observations. Existing geometry dispatch still uses its
  established flags; preserving nullable source presence is separate work.
- Construction dates, structural systems, architectural eras and mapped portal
  roles are not verified retained observations. Procedural composition remains
  labelled as authored choices, with era unknown.

`test_buildgen_field_lineage` exercises the actual feature-array cache, tile
building extraction, mapped-part provenance, detached worker plans, old missing
fields, signed labels and unchanged near/collision/sky geometry. Its first run
passed six tests; the accompanying context/topology/core suites passed 49 tests.
Logs: `build/architecture-foundations/lineage/`.

## Baseline and remaining acceptance

The twelve architecture and nine access fixtures were captured before the shared
composition/access edits in `build/architecture-foundations/before.json` and its
PNG. This baseline already includes the preceding church spires, commercial
composition and green-space decoration work. Original touched runtime files are
preserved under `build/architecture-foundations/original/`.

Native BeamNG visual review, representative vehicle traversal, occupied streaming,
packaged-runtime verification and measured performance gates remain separate from
source-level and synthetic mesh checks.

## Shared programme and facade integration

`buildgen.programme` derives immutable records from an already resolved building:
relative floor datums, continuous straight elevation runs, source-edge offsets,
fitted bay grids, semantic seed channels and provenance. Straight collinear source
edges share a run, including at a ring's wrap point; actual corners and explicit
party-wall changes end it. Source footprints and holes are not rewritten.

Source floor labels remain provenance alongside relative physical datums. Unknown
construction era, structure and condition stay unknown. Existing church spire and
palette choices use an explicit legacy seed bridge to preserve their previous
selection. New decisions can use separate function, structure, era, vocabulary
and condition channels without moving accepted portals when a palette changes.

The accepted church, terminal and commercial renderers consume these runs and
datums. A merged facade is emitted as one continuous elevation rather than as
small independently framed pieces at digitization vertices. Door coordinates
remain on their original source edge; consumers translate them into run space.
No new field is added to serialized `BuildingPlan`; schema 14 remains current.
Derivation from the same frozen input is reproducible across worker boundaries.

Supermarket wide entrances use one fit predicate shared by visual opening,
threshold width and ordinary-door prop suppression. An accepted door near a real
corner retains the ordinary treatment when a wide entrance cannot fit; it is
not relocated merely because the entire straight wall is long.

This is a foundation for existing bounded families. It does not allocate mixed
uses by floor, identify tenants, establish concealed structural systems, infer
podiums or assemble mapped specialist parts. Those larger programme and lifecycle
items remain open in the checklist.

Loading courts and parking frontage consume those accepted continuous facade
runs too. Regressions split the rear/front source walls while retaining the actual
door, verifying identical dock openings, parking counts, physical site solids
and connections. Near/lite/collision dock emission is also checked. This avoids
looking up a source edge that no longer owns a separate facade elevation or
shortening a parking row at a redundant source vertex.

## Commercial detail and local access

Commercial piers, roof-edge caps, ribbon spandrels and near-only transoms use the
accepted openings and shared datums. Complete components clear doors and windows;
party walls, courtyard detail and unresolved obstructed runs are suppressed.
The six-fixture before/after sheet retains identical collision fingerprints.
Added detail increases mesh/compile cost in several families; it is not a speedup.
See [commercial foundation](COMMERCIAL_FOUNDATION_PROGRESS.md) for measured counts,
timings and reviewed previews, and [programme contract](ARCHITECTURE_PROGRAMME_CONTRACT.md)
for the immutable API, bounds and fallback rules.

Local garage access ranks at most four detached street-interface proposals from
the existing entrance, samples their full strips in one terrain batch and commits
one feasible route with its curb opening. It retains the existing distance,
grade and fill limits. A failed replacement preserves the installed route.
Real corners, grade changes, pedestrian ramps, controlled roads, known property
limits and source holes remain constraints. Collinear road samples are simplified
only for planning, preserving source geometry and road metadata.

Existing green-space decoration rules continue to apply: accepted lawn/garden
patches can contain bushes and rocks, while generated hardscape and mapped paved
surfaces exclude vegetation. New driveway routes participate in the existing
physical-surface reservations before optional landscape fitting. Mapped vehicle
entrances, independently validated crossing-only receiving areas and canonical
shared-site/station runtime coordination remain open.

Installed local driveway ownership survives partial component replanning and the
entrance-access rebuild. Fresh components cannot claim an existing sibling's
token. Regressions cover moved openings, reversed initial order and fresh partial
membership, checking both curb cuts and emitted records. These local resource
tokens do not replace the separate canonical shared-site identity contract.
See [ranked driveway proposals](RANKED_DRIVEWAY_PROPOSALS.md).

## Final integrated verification

**488 distinct Python tests pass across 35 modules** in
`build/architecture-foundations/final-integrated`. This includes programme,
source lineage, actual near/lite facade equivalence, source heights/holes,
church spires, terminals, commercial entrances/detail, garages, partial driveway
replacement, sites, mapped surfaces, landscape exclusions, progressive lifecycle,
worker serialization and code packaging discovery. Client Lua sources were not
changed in this continuation; the preceding 411-check result is historical.

All twelve architecture fixtures retain identical collision fingerprints and
resolved body heights versus `before.json`. All nine access fixtures retain
crossing/drive-record counts. Direct original-resolver comparison also retains
triangle counts and indices: maximum coordinate delta is about `3.6e-15 m`,
so access bytes are not incorrectly described as identical. Existing connected
frontage terrain samples rise from 144 to 195 to evaluate alternatives. Detailed
synthetic timings and added mesh costs are in the commercial/access reports;
they do not establish a release performance pass.

The final reviewed baseline is `build/architecture-foundations/after.json` and
`after.png`. `verification.json` records per-fixture comparisons and per-module
test totals. `source-manifest.json` records all 172 measured source/tool files;
their hashes were rechecked against disk and every Python source in that manifest
passed syntax compilation. Aggregate SHA-256:
`802713cdf86ac85fc412647ca873c92bdfa2b077bdb74a6c5cd0ac3d0020ba18`.

Reproduce from this checkout:

```powershell
$python = '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe'
$env:TEMP = (Resolve-Path build/architecture-foundations/tmp).Path
$env:TMP = $env:TEMP
$modules = (Get-Content build/architecture-foundations/verification.json -Raw | ConvertFrom-Json).tests.PSObject.Properties.Name
& $python tools/run_tests.py @modules --par 4 --timeout 120 --logs build/architecture-foundations/final-integrated
& $python tools/generation_baseline.py --out build/architecture-foundations/after.json --repeats 3 --preview
& $python build/architecture-foundations/verify_final.py
```

One initial invocation named the mapped-surface module incorrectly; its import
error is retained in `invocation-errors/test_sitegen_mapped.log`. The actual
`test_sitegen_mapped_surfaces` module passed all ten tests and is included in the
488 total. No real-map downloads, packaged executable run or native game tests
were performed. Earlier missing-offline-data road checks remain unresolved.
