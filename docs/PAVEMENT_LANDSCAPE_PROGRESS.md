# Bounded pavement and landscape coordination

Implemented 1 November 2026 against the current source snapshot. This continues
the existing frontage/property planners with a small runtime coordination step;
it does not activate shared-complex geometry or new property catalogue inputs.

`sitegen.surfaces.SharedTerrainSampler` pins exact XY observations for one planning
pass. The root integration wraps the existing `buildings.doors` terrain provider
once, before entrance, driveway, commercial and property-site planning. Repeated
coordinates share the same observed height across those consumers. There is no
coordinate rounding, inferred height, persistent cache or datum conversion.
Missing/failed observations remain NaN; optional terrain-fitting consumers omit
unsupported geometry. The existing primary entrance fallback remains unchanged.

The cache retains at most 8,192 points. Dense input arrays continue through
callback chunks of at most 65,536 points, preserving every requested result rather
than failing the tile at a new global cutoff. Once the cache fills, later samples
still resolve, and duplicate coordinates within each chunk still share a query.
Returned arrays are detached and bytes-backed, so callers cannot make them
writeable again. A sampler belongs to one fixed source callback, frame and terrain
revision; it must not be reused after any of those change.

`sitework.coordinate(items)` runs after the existing access/site planners and
again after garage access. It snapshots local source footprints (including holes),
accepted access/parking/shoulder solids and garage aprons before committing optional
groundcover. Garages without an ordinary `AccessPlan` still contribute their apron
reservations; legacy buildings without `Footprint` contribute their validated ring.
Groundcover cannot overlap those complete planar envelopes or already admitted
groundcover. Edge contact is permitted; positive overlap above 1e-7 m² is rejected.

Optional beds retain their existing terrain/fill checks, full-quad extent checks
and 25% edge-grade limit. Final accepted cover is detached into tuple-backed frozen
solids. Known property boundaries, holes and complete exclusions are retained.
An explicitly unknown exclusion inventory is not free space. With no supplied
property, the existing narrow frontage allowance remains the only inferred extent.

All existing physical solids, parking layouts/markings, portal heights and collision
geometry remain unchanged by coordination. Conflicting decorative patches are
suppressed with an explicit `landscape_omitted_shared_reservation` diagnostic;
the coordinator does not retire a traversable route. Owners commit together after
decisions finish. Priority is deterministic from stable source/seed labels, with a
translation-normalized local geometry tie-break when source identity is absent.
Replanning the same inputs and reversing scene order retain the same results.

At most 8,192 physical/decoration reservations and sixteen cover patches per owner
are admitted. Overflow suppresses optional cover and records a budget diagnostic;
it never truncates accepted physical geometry.
Unsupported legacy obstacle polygons likewise suppress optional cover with an
unresolved diagnostic; they do not abort the existing physical build. These are
local bounded helpers,
not the M2 admission scheduler, global memory budget or occupied-resource pinning.
They do not resolve physical overlap between sites or grade-separated structures.
No `crossing_only` receiving-area result, canonical cross-tile ownership, new
parking layout or large-site feature is claimed.

## Verification and preview

Owned runtime originals were copied before editing to
`build/pavement-landscape/original/`. SHA-256:

| File | Original SHA-256 |
| --- | --- |
| `sitework.py` | `462075d702f7f25fa40949c6d713da966813c827ffe2caa91650e7e3b8def8f4` |
| `landscaping.py` | `e781d65c6e55f336972c07fcdc48f2bdf0d263995367f91b57a512156b7441ec` |
| `landscape_preview.py` | `b3846d63345cc2169587e8f93673b0f1b06977c353b1c78dd79b8a025d84d7b3` |

Run from the source root:

```powershell
New-Item -ItemType Directory -Force build/pavement-landscape/tmp | Out-Null
$env:TEMP = (Resolve-Path build/pavement-landscape/tmp).Path
$env:TMP = $env:TEMP
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/run_tests.py test_sitegen_surfaces test_buildgen_landscaping test_buildgen_sites test_buildgen_access test_buildgen_driveways test_buildgen_garages --par 3 --timeout 120 --logs build/pavement-landscape/tests-final
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/landscape_preview.py --out build/pavement-landscape/frontages.png
```

The six suites pass **66 tests**, including sixteen new sampler/coordination tests.
Coverage includes exact sample reuse, dense callback chunks, read-only detachment,
cache overflow, source holes/exclusions/unknown inventories, physical preservation,
parking/garage reservations, missing terrain, difficult grades, source-free legacy
footprints, competing-bed rebase priority, reversed load order, repeated planning,
worker pickle round trips and exact path/shoulder shared heights.

The reviewed preview is `build/pavement-landscape/frontages.png`; its JSON report
records nine existing frontage identities and an explicitly injected paving
reservation before/after optional cover fitting. That comparison removes one of
three cover patches while retaining every physical solid. It is a synthetic
coordination fixture, not a newly generated driveway or mapped entrance.

Across the nine unchanged frontage fixtures, direct terrain callbacks receive
**1,192 points instead of 1,239** (47 fewer, about 3.8%). Mesh fingerprints are equal
with sample reuse enabled/disabled. The ninety-case warm synthetic run measured
about 5.57 ms p50 / 8.28 ms p95 for access plus landscape, versus 4.10 / 5.89 ms
with both new sample reuse and final coordination disabled. Thus this safety slice
has measurable CPU overhead in a cheap flat-terrain callback fixture; the reduced
terrain work does not establish a speedup. These are small synthetic measurements,
not worker-total, steady-driving, collision or game-import acceptance, and no
performance release gate or in-game visual acceptance is claimed.

### Grass and garden decoration follow-up

At the user's request, both accepted lawn margins and garden beds now receive
small opaque bushes and rocks in near detail. A deterministic seed selects stone
for approximately 30% of placements; the existing per-profile and global plant
budgets remain in force. Complete geometry stays inside the accepted patch,
including near its ends. Paved/gravel margins do not receive this added planting.
These are low mesh details without extra physics or per-frame scene objects.
Natural trees, shrubs and rocks remain eligible on sufficiently clear green
areas under the existing vegetation rules; see
[surface exclusions](VEGETATION_SURFACE_EXCLUSIONS.md).

The refreshed `frontages.png` and JSON include these details. The latest synthetic
run measured 4.93/5.99 ms p50/p95 versus 3.93/4.41 ms with sampling reuse and final
coordination disabled. Terrain counts remain 1,192 versus 1,239; timing variability
and the measured coordination overhead still preclude a performance claim.
