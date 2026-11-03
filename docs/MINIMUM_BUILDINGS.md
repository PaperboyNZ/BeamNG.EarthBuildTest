# Minimum building generation

Under **Graphics**, select **Advanced**, then **Minimum** for Building generation
quality. Sidewalks & Property Grounds sits alongside it. Both quality controls
stay visible but are disabled while Simple is selected; their saved values are kept.
New settings use Simple generation and Minimum for Advanced; saved
choices are preserved. Switching replaces complete products;
existing buildings remain visible until their replacements are ready.

Minimum is a separate compact compiler, below Very Low. It retains the advanced
source identity, all 64 regional themes, seeded material/colour choices, observed
heights and storeys, footprint holes, regional roof silhouettes, main supports,
grounded entrances and garage access. Specialist churches, bridges, ships and
parking decks retain their established safe geometry. Explicit mapped sites stay
supported. No buildings are removed to meet a performance budget.

Ordinary facades use material zones and inexpensive textured windows. Ground
floor windows reserve real entrance and garage intervals. Upper floors use five
small shared window/glass textures, so a tall facade does not require a mesh or
layout object for every window. Regional window proportions and spacing remain
recognizable, but the complete detailed aperture layout is not retained. Small
trim, recesses, projecting window bays, rainwater fittings, optional rooftop
equipment and inferred site decoration are omitted. Removed bays have neither
collision nor occupancy boxes. Commercial entrances retain stock door props.

The normal updated wall and roof materials, normal maps, seeded weathering and
detail UVs remain. Shared window masks use simple materials; they do not generate
per-building textures. Their opacity masks are independent of weathering's packed
vertex alpha. Glass facades retain the selected per-building tint.

There is one final visual pass, with no intermediate shell, detailed-opening
graph or duplicate near/coarse representation. Meshes still split losslessly at
20,000 vertices; frame-budgeted imports and physical handover remain in place.
Common rectangular roofs use scalar clipping against the same analytical planes
as the full solver. Irregular wings, courtyards and intersecting roof forms keep
the full solver. Plane, coverage and height equivalence are tested.

Minimum also reaches distant building workers. Worker context, cache keys,
session filenames and memoization distinguish it from other levels. Entering or
leaving Minimum queues distant replacements without dropping existing coverage.
Schema-30 candidate plans pin their physical recipe when accepted. A visual
ceiling change cannot remove their projected collision or occupancy. Lowering a
standard accepted building to Minimum retains its closed bay silhouettes;
compact accepted buildings retain their compatible speed representation until
anchored refinements are implemented. Optional site policies still have separate
cache identities in this compatibility stage. Every quality mode now owns its
performance policy; there is no independent adaptive toggle. Minimum never
automatically upgrades behind the user's selected ceiling.

## Validation and performance

The recorded 3 November 2026 comparison used an AMD Ryzen 7 5700X3D, Python
3.14.7 and one serial worker. Each run wrote fresh output files; warm results are
medians of five repetitions at 120 buildings and three at 1,200, with Simple
followed by Minimum. These measurements predate the final upstream integration.

| Buildings / tiles | Simple warm | Minimum warm | Near triangles, Simple / Minimum | Visual files, Simple / Minimum |
| --- | --- | --- | --- | --- |
| 120 / 12 | 0.557 s | 0.511 s | 45,820 / 9,801 | 10.99 / 1.36 MB |
| 1,200 / 112 | 5.657 s | 6.188 s | 459,180 / 98,708 | 109.99 / 13.70 MB |

First execution was slower for Minimum: 1.477 versus 0.680 seconds at 120
buildings, and 6.983 versus 5.888 seconds at 1,200. Material primitives increased
from 82 to 127 and from 722 to 1,148 respectively. Lower triangle and file counts
do not establish faster GPU rendering or cold startup. Simple's visual file size
includes its near and coarse LODs; the triangle column compares near meshes only.

The paired synthetic scenes contain 120 and 1,200 buildings across actual geotile
boundaries. Both modes receive identical source footprints, tags, identities,
roads and flat terrain. Timings include source ingestion, planning, access,
collision, native shape encoding and file publication. They exclude downloads,
road/terrain meshing, queue waits, native game import/rendering and GPU work.
Warm repetitions and first executions are recorded separately; these are not
in-game FPS measurements. Native visual and driving acceptance remain pending.

The implementation, shared texture assets and regression fixtures are included
in this branch. See [the upstream review guide](ADVANCED_BUILDINGS_REVIEW.md)
for scope, validation and remaining acceptance work.
