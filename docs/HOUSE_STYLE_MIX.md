# House style and colour variety — schema 19

Current regional detail authoring: [25 architectural modifiers and spawn rates](REGIONAL_ARCHITECTURAL_MODIFIERS.md).

Current roof authoring: [roof proportions, attic windows and dormers](ROOF_PROPORTIONS_AND_ATTICS.md). Shared inference limits apply across all 64 regional profiles and five contemporary families; tall eligible roofs receive fitted attic details. Historical checkpoint statements below retain their original scope.

The regional rollout replaced Auckland's earlier generic v2 suburban houses
with the authored NZ regional profile. In Auckland, the earlier zoning-only
regional resolver had no NZ polygon; the bundled Christchurch zoning does not
cover this location. The generic recipe mixed render, brick and timber. The
active NZ profile instead prefers timber/render, different roof proportions,
regional facade trim, narrower windows and smaller paint palettes.

Roof-colour evidence is still enabled. It is prepared offline and pinned at
startup, not sampled live while driving. The existing 20,278-record catalogue
has zero source-ID/footprint matches among the 146 cached buildings within 250 m
of the supplied Marbeth Court position (-36.91410, 174.90925). The audit is in
`build/house-style-mix/auckland-roof-audit.json`. These buildings therefore cannot
receive an imagery sample from that catalogue. Mapped colour remains the next
fallback before generated palettes. Red/green roof colours were not removed
entirely from the NZ profile; its material/palette restrictions reduced variety.

## Stable mixture

For eligible ordinary houses, a source-ID hash chooses:

- 70% local regional architecture.
- 20% a shared contemporary alternate.
- 10% a uniformly selected other active regional profile from the existing
  global catalogue. The donor changes appearance, not the geographic identity.

These are independent deterministic probabilities over many buildings, not a
quota enforced within every street. Houses do not change style when neighbours
load, when the camera moves, or when a worker generates another detail level.

The contemporary pool contains only five shared families: suburban mix (the
earlier generic house composition), timber, brick, rendered, and mixed-material
infill. The suburban mix has weight three; each other family has weight one.
All regions reuse this pool. They use existing materials and fitted facade
geometry; no new textures, interiors or additional game objects are introduced.

The mixture applies to ordinary house/low-rise residential classes and compatible
unknown-use shells with a source ID, an active region, at most three storeys,
15 m source height and 500 square metres. Building parts, apartment-block classes,
city offices/hotels and specialist buildings retain their own planners. Unknown
or conflicting regional context does not fabricate a geographic identity.

## Colours and evidence

House paint and roof-colour choices have independent stable channels. Regional
and global house variants retain their authored palettes for 65% of fallback
colour selections and reuse the broader existing material palette for 35%.
Contemporary houses use the broader material palettes. This restores variety
without generating a unique material or texture for every house.

Accepted imagery roof colour still takes priority, followed by valid mapped
roof colour. Mapped facade colour, cladding, roof material, shape, height, floors
and footprint remain authoritative. Style changes can alter inferred roof forms;
they cannot overwrite an observed roof or create invented footprint extensions.
The new frozen style descriptor advances building serialization to schema 19.
Source-based cache identities include the new module and invalidate old geometry.

## Review and reproduction

`tools/house_style_preview.py` produces a 24-house identical-shell neighbourhood;
`--families` shows all five contemporary families. The files under
`build/house-style-mix` compare the earlier suburban, schema 18 regional, and
current mixed recipes. These are approximate-colour geometry renders, not game
screenshots or roof-reflectance measurements.

`test_buildgen_house_styles` checks proportions across 192,000 source identities,
all 64 global donor themes, the five contemporary emitters, colour diversity,
evidence precedence, serialization, translation and mapped collision-envelope
parity. Existing regional/detail/access suites remain part of integrated checks.
The matching packaged verification report records final regression results.

The new private playtest is `BeamNG.Earth-v2-house-variety-20261101`. Close the
old server and restart BeamNG when switching. Revisit Marbeth Court, then inspect
other regions, near/far transitions and night lighting. The previous schema 18
package remains available. Native visual and performance acceptance is pending.
