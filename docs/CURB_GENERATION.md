# Curb and roadside generation update

Implemented in the editable source on 1 November 2026. Existing playtest ZIPs
and launchers have not been replaced. Restart the server with this source and
its matching mod to exercise the changes; the normal source fingerprint includes
the new Python modules and invalidates generated content.

## Property access

Automatic commercial, industrial and mixed-use frontage generation can now work
without a resolved door or AccessPlan. It selects a nearby compatible street
facade without inventing a door or parcel. A fitted service yard can receive one
3.5–7 m vehicle mouth even when a complete parking lot does not fit. It tries at
most six mouth positions. Receiving pavement, the connector and the owned curb
cut commit together. Repeated regeneration replaces that owner's cut, and a
failed replacement retains the previously accepted route.

Terrain, neighbouring structures, mapped exclusions, pedestrian ramps, other
driveways and controlled-access roads still constrain the proposal. Unknown or
obstructed ground remains unresolved rather than receiving an unusable opening.
Planting no longer consumes the entire usable depth of a small service yard.

Vehicle crossings support sidewalks from 1.5 m wide. Wide sidewalks keep their
level rear strip; narrow ones use more of the width for the transverse ramp.
The rear datum matches the regional sidewalk height. Vehicle flares use 1.2 m
smooth easing with bounded samples. They have pavement, rather than pedestrian
tactile material. Separate curb UVs prevent random painted texture bands across
the opening. Visual and collision surfaces share the same driving geometry.

## Regional treatments

All 64 existing architecture themes map to six authored roadside treatments:

| Treatment | Upstand | Country gutter default | Other cue |
| --- | ---: | ---: | --- |
| Concrete channel | 150 mm | 0.50 m | Local-street grass verge |
| Precast channel | 150 mm | 0.45 m | Local-street grass verge |
| Compact precast | 125 mm | 0.30 m | Compact concrete footway |
| Paved edge | 120 mm | 0.25 m | Paver sidewalk |
| Cold climate | 160 mm | 0.35 m | Raised concrete edge |
| Deep channel | 180 mm | 0.55 m | Wider drainage strip |

These are gameplay defaults, not assertions that every street in a country uses
one construction standard. The palette retains the native bevel cross-section;
height, gutter width and adjoining surface treatment vary. It does not add six
independent native mesh implementations. Gutter ribbons and their grate width
and position use the same country setting. Source-road locations select curb
styles before clipping, and metadata survives rebased skins.

Where a local street has enough width, a 0.6 m grass strip occupies the front
sidewalk band while at least 1.65 m stays paved. Narrow walks, medians, corners,
pedestrian ramps and vehicle crossings stay paved. Existing historic brick
overrides remain available. Native sweeps stay batched: the planted treatment
adds at most one extra sweep call per sidewalk builder.

Design references: [Auckland Transport vehicle-crossing details](https://at.govt.nz/media/pjyhjvio/tdm-vehicle-crossings-standard-engineering-details-version-2.pdf),
[TfL Streetscape Guidance](https://tfl.gov.uk/cdn/static/cms/documents/streetscape-guidance-2022-revision-2.pdf),
and [Tacoma standard plans](https://tacoma.gov/government/departments/public-works/engineering/standard-plans-and-gsi-typical-details/).
They inform the treatment families and continuity between crossings, paths and
berms; the entire palette is not presented as surveyed engineering dimensions.

## Corners and furniture

Ordinary and compound junction arcs share curvature-based sampling: up to 8 mm
chord error for supported radii, with a 97-point cap. Tangents meet adjoining
straight runs exactly. Short joined sidewalk gaps use tangent-aligned curves
and check the complete walkway width against carriageways. Roundabout bands
retain more of their source curvature. Asymmetric corner slabs now meet each
adjoining sidewalk's actual crossfall datum instead of assuming both are 2.5 m
wide. Native lean collision simplification remains active on ordinary runs and
corners.

A final spatial-index pass checks full furniture footprints against completed
driveways and their flares, rear walking strips, pedestrian ramps, corner slabs,
building paths, mapped paths/service roads, and crosswalks. Conflicting bins,
hydrants, benches, poles, lights, signs and vegetation are omitted. Removed poles
also retire attached lights and wire spans. Malformed polygon boundaries use a
conservative enclosing shape for clearance.

Precise `access` masks also travel through the existing streamed surface-owner
system. A neighbouring driveway arriving later can suppress already-visible
furniture. Owner removal and rebasing reuse that system's lifecycle; ordinary
paving alone does not ban furniture from its clear edge zone. Prop radii are
conservative authored envelopes, so actual stock-asset appearance still needs
native-game review.

## Verification

- 270 Python checks pass: 17 targeted modules plus 64 road geometry checks.
- 313 Lua assertions pass across surface exclusions, trees, roads and roadgeo.
- New cases cover all 64 theme mappings, six regional driving seams, missing-door
  service access, ownership/idempotence, rejected unsafe proposals, narrow ramps,
  planted-strip exclusions, actual junction sampling, asymmetric corner heights,
  furniture footprints, late arrivals, unloads and rebases.
- A synthetic 200-run / 20 km workload with 40 vehicle crossings and planted
  strips generated in a median 32.36 ms; 16,160 visual and 13,520 collision
  triangles. Plain runs took 2.87 ms. These are geometry-generation timings,
  not frame-rate or game-collision-rebuild measurements.
- The complete `test_roads` tracker group stalls initializing Windows asyncio's
  socketpair in this sandbox. Its 64 geometry checks pass separately.
- `test_blockworker` has a manifest mismatch and open revisit-file cleanup errors;
  the saved pre-change modules reproduce those failures.

Native BeamNG driving, appearance and streaming-performance acceptance remain
pending. Reproduce the geometry preview and timings with `tools/curb_review.py`.
Outputs and logs are in `build/curb-overhaul`: `overview.png`,
`geometry-review.json`, `validation.json`, and the test logs.
