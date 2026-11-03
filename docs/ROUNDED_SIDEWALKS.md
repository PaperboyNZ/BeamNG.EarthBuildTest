# Rounded island, driveway and sidewalk corners

The independent **Sidewalks & Property Grounds** setting controls these outlines.
The requested rounding is in plan view: cut back the square ninety-degree
corners on islands, driveway gaps and exposed sidewalk ends. The small curb
chamfer is separate profile detail.

## Outline recipe

Minimum keeps the original outline. Every higher tier directly compiles the
same four-span circular arcs at exposed run ends, inset into the original
footprint. The radius is at most 0.6 m, 45% of width and 15% of length, and stays
inside the endpoint's first segment. Both corners of each exposed end are
rounded. The middle of a narrow end remains nondegenerate. Continuous joins
and tile cuts (`caps=False`) keep their exact sections.

Driveway gaps naturally receive arcs at both exposed sidewalk ends. Existing
continuous lowered vehicle crossings retain their accepted access profiles.
Paving UVs and ramps are mapped back to the original source station frame.

Closed island convex corners are rounded before tile clipping, in the narrow
`roads.build_tile` island call. Exact redundant straight-edge samples are removed
before fitting fixed arcs. The radius includes the entire native curb band's
sloped rear toe, preventing inner profile folds. A straight midpoint is the
closed sweep's start so its endpoint normals agree. No arc expands into a road.

Visual and lean collision meshes use this compiled outline. Ground-quality
changes therefore require the existing complete physical transaction and
occupied handover. Building presentation changes cannot alter the selected
grounds outline. The old v1 promise that all collision remains square has been
superseded by the user's clarified request: no invisible square corner should
remain where visible geometry has been cut back.

## Cheap lower quality detail and bounded work

Very Low and Low use the existing compiled native single-bevel chamfer. It adds
**zero profile triangles, zero Python smoothing passes and zero extra sweeps**.
Medium uses four profile spans; High, Very High and Ultra use six. Curved detail
reuses native endpoint vertices. Higher-tier terrain physics forks reuse the
original native sweep rather than generating it twice. No new materials or
material primitive groups are added.

There is no detailed outline planner followed by decimation. Coarse modes
directly emit the fixed arc template and call the existing native sweep.

| Grounds tier | Maximum native/ramp stations per run | Maximum island corners | Profile spans |
| --- | ---: | ---: | ---: |
| Very Low | 64 | 12 | native bevel, 1 |
| Low | 128 | 24 | native bevel, 1 |
| Medium | 256 | 32 | 4 |
| High and above | 512 | 64 | 6 |

At most eight cap stations are added to a run. Native ramp-refinement bounds
are checked before generation and after the tiny arc compile. An unsafe,
too-tight or over-budget outline uses the **whole original piece**, with its
complete endpoints; geometry is never truncated. Ring output also fits its
tier's point cap. This fallback can retain angular corners on exceptional pieces.

The implementation is `server/sidewalk_outline.py`, `server/sidewalk_rounding.py`,
and the small Builder/vehicle integration. Recipes are
`plan-corners-v2-coarse4` and `tiered-nose-v3-native-4-6`; both belong in road cache
identity. Settings, worker/protocol wiring and transaction policy are owned by
the adaptive-quality implementation.

## Evidence and activation

`artifacts/rounded-outlines-20261103/` contains the authoritative v2 evidence:

- `tests.log`: 117 focused tests pass, including actual serialized road-writer
  output, independent grounds/building controls, matching higher-tier collision,
  closed-ring joins, clipped corner safety, UVs, recipe-cache invalidation and whole-piece fallback.
- `minimum-baseline-check.json`: all 42 original Minimum visual and collision
  fixture digests match the pinned baseline.
- `benchmark.json`: fresh-process cold generation, warm median, encoding time,
  emitted vertices/triangles, actual CDAE bytes/primitives and collision hashes
  for all seven tiers. All higher tiers share one collision CDAE hash in this
  representative fixture; Minimum deliberately retains its original footprint.
- `plan-view-preview.png`: actual compiled outlines viewed from above, not an
  in-game capture. `v1-source/` preserves the superseded vertical-detail pass.

The 24-run, roughly 1.5 km fixture measured Low at about 36 ms warm generation
versus 33 ms at Minimum on this shared host. Low emits 12,104 visual triangles
and 733,148 bytes versus High's 20,304 triangles and 1,047,356 bytes. Both use
four material primitives and one mesh part. Timings are offline observations,
not an FPS guarantee; engine import, GPU work and driving remain unmeasured.

The candidate is not activated. The selected playtest, pinned baseline, launcher
and running game remain unchanged. Native acceptance is user-owned.
