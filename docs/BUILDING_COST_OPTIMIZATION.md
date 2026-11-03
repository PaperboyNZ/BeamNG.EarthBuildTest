# Building generation cost improvements

Follow-on component caching and opt-in facade/shadow experiments are documented
in [Building rendering experiments](BUILDING_RENDERING_EXPERIMENTS.md). The
byte-identical comparisons below describe the earlier wall-sweep/encoder changes.

Two changes are implemented in the editable source: an aperture interval sweep
in `server/buildgen/facades.py` and less repeated sorting/scanning in
`server/cdae.py`. They preserve geometry and encoded shape bytes. This work
complements the separate streaming, visibility, speed-aware refinement and
settings work. The packaged playtest and launchers are unchanged.

## Measured generation improvements

Synthetic near-plus-lite compilation, milliseconds, nine alternating paired
runs after one warmup, measured on 1 November 2026:

| Fixture | Before | After | Reduction |
|---|---:|---:|---:|
| House | 10.03 | 9.96 | Within timing noise |
| Regional block, 6 floors | 12.50 | 12.42 | Within timing noise |
| Regional block, 48 floors | 33.02 | 32.39 | 1.9% |
| Fallback apartment, 49 floors | 131.16 | 122.01 | 7.0% |
| Concrete office, 16 floors | 9.84 | 8.22 | 16.5% |
| Glass tower, 80 floors | 19.35 | 15.05 | 22.2% |
| Church | 5.53 | 5.57 | Within timing noise |

Planning, downloads, disk writes, cold caches, game import and rendering are
excluded. These numbers do not measure frame rate or total streaming latency.
The fallback apartment remains expensive; its representation needs the separate
renderer-complexity work identified in the streaming review.

The old wall cutter checked every opening against every horizontal wall band.
For large layouts the new cutter locates each opening's active band interval
once, then maintains the active openings as it moves upward. Small layouts keep
the inexpensive direct path. Empty opening lists take a fast path, particularly
useful for city rows above entrances. Band boundaries, epsilon comparisons,
rectangle order and overlapping-opening behavior are preserved exactly.

The encoder now uses one stable material sort for both triangles and material
indices. Primitive counts use one histogram instead of rescanning every triangle
for each material. Full near-plus-lite encoding improved approximately 1–4% on
these fixtures. Its output bytes are unchanged.

## Exact vertex sharing experiment

The offline experiment compares the complete encoded vertex record: position,
UVs, optional second UVs, colour, normal and tangent including handedness. Only
byte-identical records can share an index. It verifies every expanded triangle
corner against the original; shading seams and texture seams remain distinct.

| Near mesh | Original vertices | Unique records | Attribute payload saved as share of shape size | Python analysis time |
|---|---:|---:|---:|---:|
| House | 2,866 | 2,578 | 9.1% | 0.58 ms |
| Regional block, 6 floors | 9,094 | 7,921 | 11.5% | 1.77 ms |
| Regional block, 48 floors | 22,174 | 18,824 | 13.5% | 4.75 ms |
| Fallback apartment, 49 floors | 107,426 | 99,588 | 6.5% | 25.78 ms |
| Concrete office, 16 floors | 4,558 | 4,146 | 8.1% | 0.89 ms |
| Glass tower, 80 floors | 5,574 | 4,918 | 10.5% | 1.04 ms |
| Church | 728 | 660 | 8.3% | 0.18 ms |

This is a measured storage opportunity, not an enabled renderer change. Payload
estimates exclude small metadata-size changes. Triangle counts, material
primitives and pixel shading work remain unchanged. Fewer vertex records could
reduce upload/storage and vertex processing; native-game measurements must
establish the actual effect. The Python pass can cost more than the production
encoding improvements save, so it is intentionally excluded from publication.

The next experiment should hash packed records in the existing native encoder
path, after normals and tangents are finalized, and preserve first-use order.
Alternatively, compact cached shapes during idle work and use the compact version
on the next load. Do not rewrite a shape currently referenced by a live TSStatic:
publish under a new content identity. Measure complete worker time, peak memory,
import time and GPU vertex time before enabling it.

## Further opportunities

1. **Cache construction components by their actual visible parameters.** Window
   surrounds, sills, downpipe sections and gutter profiles repeat. Cache their
   local positions, UVs, indices and normals keyed by dimensions, profile,
   handedness and texture layout. Stamp transformed copies into the existing
   batched mesh and apply the resolved colour separately. This could remove
   repeated trigonometry and tiny array allocations while retaining architectural
   variety. Bound the cache by bytes and measure hit rates; nearly unique
   dimensions must not fill it indefinitely. Mirrored transforms require correct
   winding and tangent handedness.

2. **Bake only the distant facade interior.** Retain the actual roof, recesses,
   courtyards, arcades and silhouette as geometry. Represent repeated windows,
   trim colour and shallow relief with opaque facade cards drawn from the same
   resolved architectural plan. Share atlas entries by facade signature, bake
   during idle/cache work, and add mip gutters. A small set of atlas materials
   could reduce distant material submissions as well as geometry. Validate at
   grazing angles and night; large recesses and visible openings require geometry.
   This also introduces texture memory and bake costs that must be budgeted.

3. **Use projected detail size to decide representation.** With focal length
   measured in pixels, a feature of size `s` at distance `d` projects to roughly
   `s * focal_pixels / d` pixels. Use that estimate, plus travel speed and
   hysteresis, to keep an outline-changing spire or canopy while replacing
   subpixel pipe clamps or trim relief with their simpler representation.
   Bounds should come from authored component dimensions already known during
   planning. Integrate with the other chat's scheduler rather than adding an
   independent visibility controller. Camera FOV, resolution and fly/free-camera
   movement must participate.

4. **Give shadows their own complexity budget.** The client uses dynamic
   TSStatics, and the existing road comments identify repeated shadow-cascade
   rendering as a cost. Detailed building meshes therefore warrant a GPU capture.
   A roof-and-wall shadow representation could preserve the major building
   shadow while avoiding repeated window-return and gutter triangles in shadow
   passes. First prove that the engine supports a shadow-only representation or
   independent shadow LOD for these generated shapes. Keep arches, canopies and
   other large openings in that representation. Low sun and nearby receiver
   surfaces are the visual acceptance cases; disabling building shadows globally
   would not meet the quality requirement.

Prioritize native exact vertex sharing and component-template reuse first: both
can preserve the existing visible design. Facade baking and shadow proxies have
larger potential rendering benefits but need native-engine visual/performance
probes. No FPS saving is assigned to these proposals yet.

## Verification and reproduction

- 105 tests pass across wall sweep, facades, city, churches, regional blocks,
  CDAE golden files, chunk transport and progressive generation.
- The new differential tests cover 300 randomized opening layouts, overlapping
  and duplicate openings, tiny intervals, reversed bounds and large elevations.
- All 64 regional house styles and 192 regional block variants match their
  pre-change near/lite mesh arrays and encoded bytes: 512 comparisons. Seven
  additional benchmark fixtures match too.
- The initial file-writing tests encountered the sandbox's inaccessible default
  temporary directory. Re-running with `TEMP` and `TMP` inside the workspace
  passed; no code workaround was introduced.
- Source hashes, original files and patches are in `build/geometry-costs`.
  Source-based cache identity already covers both changed production files.

From the editable source, using its configured Python environment:

```powershell
python -B tools/benchmark_building_costs.py --all-regions
```

The benchmark needs `build/geometry-costs/original/cdae.py` for the historical
encoder comparison. Results, individual timing samples and exact source hashes
are in `build/geometry-costs/benchmark.json`. The vertex-sharing analysis writes
no game assets. Native-game acceptance and packaging remain separate work.
