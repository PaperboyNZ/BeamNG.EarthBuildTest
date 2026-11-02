# Sidewalk texture and geometry polish — 2 November 2026

This update builds on world-architecture r6 (building schema 23). Run the parent
`Play latest buildings.bat` after closing the previous Earth server and restarting
BeamNG. Previous playtests remain intact.

## Mapping and retained details

The old `sidewalk1` sheet contains five separate strips, panel joints and embedded
utility covers. Ordinary runs selected a strip, but corners, vehicle crossings
and verges used repeating XY UVs against the whole sheet. Width changes stretched
the selected strip; shared tactile/pavement vertices could also interpolate
between incompatible UV scales.

Paving now uses dedicated stock tileable materials with consistent physical size:
2 m concrete panels, approximately 20 x 10 cm herringbone bricks, and 0.5 m paving
tiles. A shared frame-space projection keeps scale and phase through different
pieces and tile origins. Material seams get independent UVs. Curb face/nose/top
UVs retain the original plain trim band. Both the legacy tile writer and current
geotile skin writer use the same regional finish for runs, corners and crossings.

Utility-cover artwork is preserved from the original atlas, together with matching
normal/roughness/AO coordinates, on sparse flush surface patches. A candidate needs
a paved furnishing strip beside the curb, at least 1.5 m of clear pedestrian width,
and 2 m setbacks from run ends and ramp flares. Driveway profiles split the eligible
runs before placement. Grass verges, corners, narrow paths and sharp/uneven support
do not receive these patches. The artwork is decoration, not surveyed utility data;
it adds no raised collision, road obstruction or free-standing prop. Patches share
one material per tile and straight sections are generated in a vectorized batch.

## Geometry sanity fixes

- Loose ends can join across sub-30 cm and coincident seams. Reversed multi-run
  chains retain their endpoints and median metadata; different levels, opposite
  sides and deliberate crossing gaps remain separate. Endpoint candidates use
  spatial bins instead of scanning every pair.
- Duplicate source vertices no longer collapse a sidewalk's outward normals.
- Raised runs preserve source curvature at 1.5 cm simplification tolerance;
  they no longer inherit the road decal's coarse 25 cm tolerance.
- Normal junctions retain sampled curved returns. A tight corner can fall back to
  a short chamfer when the larger radii do not fit. Complete corner footprints
  are checked against carriageways before cuts are committed.
- Whole sidewalk footprints, including sloped backs, are checked against indexed
  carriageway envelopes. Conflicts trim sidewalk length; the source lane widths
  stay fixed. A connection that cannot fit safely may still remain open.
- Island smoothing is constrained against complete road envelopes, including
  wide approaches. Smoothed vertices and intervening chords must fit. Island
  bands carry median metadata and do not become planted pedestrian sidewalks.
- Regional paving selection survives corners, driveways and rebased source
  metadata. Low-countries paved edges use brick; other paved-edge regions use
  stock paving tiles. Reannotation clears stale finish flags.

## Verification and playtest focus

`tools/check_sidewalks.py` runs the offline geometry, UV, export, access, streaming
and Lua road regression checks. `tools/sidewalk_uv_review.py` compares actual
generated UVs against installed stock albedo textures and measures generation.
`tools/sidewalk_sanity_review.py` audits all 64 geographic theme examples and checks
actual swept island footprints for one- and two-lane roundabouts with wide entries.
Evidence and reproducible reports are under `build/sidewalk-uv`.

The texture comparison verifies identical base triangle positions, collision and
curb UVs in five mapping fixtures; accepted utility patches add visual triangles.
The geometry polish intentionally changes unsafe/previously disconnected layouts.
Generated caches invalidate automatically through the source-code fingerprint.

Inspect Auckland/New York verges, Amsterdam brick streets, Rome paved edges,
London/Tokyo compact curbs, Oslo and Singapore. Approach skew junctions and
roundabouts, revisit tile boundaries, and drive across pedestrian and vehicle
ramps. Check cover placement, material transitions, tyre contact and streaming.

The previews are offline UV sampling, not engine screenshots. Native appearance,
tyre-contact and FPS acceptance are pending. Two cache-dependent road-geotile tests
cannot run without the missing Overture parquet data; the offline suite covers
their synthetic ownership, seam, placement and rebase counterparts separately.
