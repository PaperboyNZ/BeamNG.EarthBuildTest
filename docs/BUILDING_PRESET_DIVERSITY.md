# Procedural variation within building presets

The editable source now treats a regional building preset as a vocabulary with
bounded choices per building. All choices derive from the existing source seed,
so regeneration, worker serialization, translation and near/lite rendering keep
the same design.

Regional window widths vary by up to 12%, nominal bays by -10% to +12%, window
heights by up to 8%, and sills by 8 cm. Frame and reveal depths also vary within
small ranges. Symmetric or paired room groups distribute spare wall width into
unequal piers. The layout repeats across storeys; access openings retain their
positions and clearance. Generic buildings without a regional match receive the
same bounded width, bay and room-group variation. Dedicated commercial and city
solvers retain their existing dimensioning.

Optional sash, shutter, screen, lintel and canopy detail is selected coherently
for each building, weighted by its ordinary, detailed or contemporary expression.
Structural grammar remains connected and retains its existing detail budgets.
Fallback regional wall zones now select from the regional paint palette instead
of always taking the first colour. Mapped materials and colours remain authoritative.
Observed footprints, heights, storeys, roof forms and entrances are preserved.
Existing inferred roof, pitch and cladding variation continues to apply.

The catalogue is never mutated by a building's resolved choices. Source code
already participates in generation cache identities through `codefiles.py`, so
these changes invalidate derived geometry without changing the serialized plan
schema.

## Validation — 1 November 2026

- 1,024 same-shell buildings: 16 source identities in each of 64 regional themes.
  With the same observed wall colour, footprint, height and flat roof, the old
  code produced 1–2 aperture layouts per theme; the new code produces 15–16.
  The comparison quantizes aperture coordinates to 2 cm and excludes paint and
  pane variants, so colour changes or microscopic noise cannot pass it.
- Each of the existing 192 regional block designs produces at least eight
  distinct aperture layouts within that design. Their implementation already
  had suitable per-building variation and was retained.
- Tests cover narrow and irregular footprints, garage/door clearance, preserved
  source evidence, catalogue immutability, translation, serialization and stable
  near/lite/collision geometry. All 150 tests in 14 affected/integration modules
  pass. Two initial preset tests hit Windows sandbox temporary-directory access
  errors; both pass with temporary files directed into the writable build folder.
- The actual-mesh sample sheet was inspected. Native BeamNG appearance and
  performance acceptance remain untested.

Run `tools/preset_diversity_preview.py` with the project's Python environment to
regenerate `build/preset-diversity/diversity.json` and
`build/preset-diversity/same-region-variation.png`. The optional `--baseline`
argument accepts saved copies of `regional_architecture.py` and `facades.py` for
a fixed-catalogue before/after comparison. Regression coverage is in
`server/tests/test_buildgen_preset_diversity.py`; test logs are under
`build/preset-diversity/tests-*`.

This is an editable-source update. Existing dated playtest folders, ZIPs and
launchers have not been rebuilt with it.
