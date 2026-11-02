# Generic regional rectangular blocks

Implemented on 1 November 2026 from the approved
[192 textual proposals](REGIONAL_BLOCK_PROPOSALS.md). All three A/B/C variants
for all 64 themes are available through a stable source-building seed. This
module does not read the unfinished regional house-style profiles.

## Runtime behaviour

`buildgen/regional_blocks.py` owns the generic block grammar. The compiled
`catalog/regional_blocks.json` is reproducible with
`python tools/compile_regional_blocks.py`. It uses the written proposal palette,
bay ranges, group sizes and reveal depths, with ten shared geometry families.
The 192 designs have individual identities and parameters; they are procedural
interpretations, not 192 bespoke models or a claim to implement optional
courtyards, roof changes or projecting balconies.

Eligibility is deliberately separate from designed programmes: flat-roof generic
blocks with 1–48 storeys, a footprint at least 250 square metres or a facade at
least 18 metres, and a roughly rectangular outline. Small road-clipping bevels
are accepted without changing the source polygon. Narrow strips, courtyards,
complex shapes, elevated structures, houses, industrial buildings, garages and
specialists retain their existing paths. Dedicated `ci_` commercial designs,
accepted office compositions, explicit sites and independently designed city
programmes are excluded. No commercial catalogue, site or access recipe changed.

Selection is deterministic and all three proposals have equal selection domains.
This is visual variety, not a claim about real-world prevalence or building age.
The selected design is retained in facade diagnostics as `regional_block:<id>`.
Suitability ranges in the proposal text are adapted to the existing floor count;
no storeys, roof height, footprint or entrance positions are changed.

## Restrained window placement

- Typical room openings start around 1.35–1.75 metres wide and 1.55–1.75 metres
  high before material-family and storey-fit adjustments. Narrow masonry and
  solid-wall designs use smaller openings. Wide panes are subdivided.
- Shared floor datums and vertical stacks retain construction logic. Groups
  have modestly unequal bay widths and inter-group gaps, not independent random
  window offsets. The top row is slightly quieter, and coherent solid stacks
  break repetition.
- Service faces omit some complete stacks. Existing doors and garage openings
  reserve their real intervals and remain clear of windows and facade details.
- The six-storey 36 by 24 metre reference set has approximately 12–23% wall
  glazing. This is a synthetic measurement, not an enforced regional statistic.
- Per-building caps are 256 generated opening groups and 96 detail components,
  with 24 details per elevation. Wide/tall buildings coarsen room groups before
  exceeding the opening budget. Above 48 storeys the existing route remains.

## Architecture and representations

Each family composes a base, main wall and crown; some also have broad material
sections. Frames, piers, lintels, post/header rhythms, spandrel bands, entrance
surrounds, screens and closed lower window panels supply the detail. Real reveals
are used near the camera. Mapped facade material or colour overrides the inferred
wall palette. Facade relief stays shallow and the primary collision shell is
unchanged. The flat roof and its measured height remain; no speculative new roof
volumes are introduced.

Near and lite meshes share aperture layout, wall zones and major details. Far
skyline colour follows the selected body material. The legacy generic rooftop
clutter/cornice is replaced by this family's bounded crown treatment; designed
commercial rooftop treatment is unaffected.

The block route defers to any separately accepted `spec.city` architecture. This
allows concurrent city-building work to own its explicitly designed properties
without being restyled by the generic fallback.

## Verification and playtest

`tools/regional_block_preview.py` exercises all 192 variants and produces actual
near/lite/collision fingerprints, eight regional contact sheets and a compact
overview. The images use approximate material colours, not BeamNG screenshots.
The block tests check every design, finite geometry, unchanged collision,
proportions, unequal spacing, aligned stacks, opening/detail budgets, mapped
material precedence, door clearance, translation and pickle stability, and
commercial/specialist exclusions.

Before accepting in-game appearance, restart the Earth server and BeamNG with
the new checkpoint, visit several generic apartment/mixed-use blocks, and drive
past them through near/lite transitions. Check restrained window scale, entrance
clearance and shadows. Revisit an existing prepared commercial site and verify
its architecture and access remain the same. Native driving, rendering and FPS
acceptance remain pending; offline CPU timing is not game performance.
