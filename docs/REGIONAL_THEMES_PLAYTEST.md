# Regional architecture playtest — 64 active themes

Playtest: `BeamNG.Earth-v2-regional-themes-balanced-20261101`, building schema 16. Native BeamNG visual and performance acceptance remains pending.

Close the previous Earth server and restart BeamNG when changing builds. Run
`Play latest buildings.bat` from the workspace, or `test_v2.bat` in this package.
Select **Freeroam → BeamNG.Earth**. The normal launcher synchronizes the matching
mod. Portable ZIP users may need the usual dependencies on first launch. Confirm the package matches this source checkpoint before using these instructions.

All 64 themes now select automatically using bundled country, province and local
polygons. A local zone overlay can override a theme; global coverage no longer
requires a hand-imported zoning file. Ordinary buildings gain regional roof
forms, facade/roof materials and tints, window proportions, trim, and bounded
shutters, sash bars, lintels, bands, screens and window canopies where compatible. Fourteen facade grammars add grouped and recessed openings, material zones and bounded structural accents. Compatible windows can use arched or segmental apertures, capped at 32 per building. Five optional pitched-roof profiles add gambrel, mansard, saltbox, shed and broad-eave forms on eligible rectangular footprints.

Mapped materials, roof shapes, colours, heights, storeys and footprints keep
priority. A region is a visual default, not a claim that every building there has
one historic style. Specialized churches, terminals and parking structures keep
their dedicated geometry. Unknown or ambiguous geographic matches stay neutral.

The primary agent personally audited all 64 themes and refined trim joins, wall
piers, gable cladding, aperture proportions and regional details. Ordinary window
spacing now scales with opening size and available wall area; the 64 comparison
houses have 26% fewer windows. Dedicated shopfront and office layouts retain their
own rules.

Suggested checks:

- Compare ordinary buildings in Christchurch, Tokyo, London, Cairo, Vancouver,
  Delhi, Singapore and Mexico City using the in-game map. The full 64-location
  reference list is in `docs/REGIONAL_THEME_RUNTIME.md`.
- Compare the larger facade compositions, roof profiles, material zones and arched or grouped openings. Check that mapped colours, materials and roof evidence remain intact.
- Look for regional roof and window differences, wall colours, clear entrances,
  shutters that do not cover doors and stable appearance when revisiting.
- Check detail/LOD transitions while driving. Pay particular attention to cold
  loading, coastal settlements and provincial/country boundaries.
- Existing commercial frontage paving, stock planting, roof imagery and the
  Christchurch zoning pilot remain included.

The three Terra research agents inspected online photographs for all 64 profiles.
Sources and interpretation limits are linked in `docs/REGIONAL_THEME_RUNTIME.md`.
This is parameterized regional architecture: traditional curved roofs, domes,
stilt structures, new earth/thatch/bamboo assets and exact local replicas are not
implemented by this update. The offline comparison sheets are actual generated
meshes with approximate colours, not BeamNG screenshots.

Validation includes all 64 routing examples, an independent city/island/border
set, near/lite/collision meshes, mapped-evidence priority, detail budgets, stable
source identity and the integrated building suites. Package checks are recorded in the workspace artifacts verification report. Native game appearance, driving and streaming performance checks remain pending. Offline generated sheets are diagnostic fixtures, not evidence of those checks.

Generated cache identity changes automatically with the source and regional
datasets. Keep downloaded map/imagery caches; manual deletion is unnecessary.
