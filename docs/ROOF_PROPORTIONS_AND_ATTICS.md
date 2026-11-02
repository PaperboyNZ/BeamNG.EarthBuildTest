# Roof proportions, attic windows and dormers - 2 November 2026

The active v2 generator now treats regional roof pitches as visual priors subject
to the actual roof run and the house's wall height. These are authored visual
choices, not surveyed pitch distributions or statements of attic occupancy.
Legacy generation and specialist church roof planners retain their own rules.

## Height and angle rules

- All 64 regional pitch ranges are reduced to 85% of their earlier values,
  rounded to whole degrees and limited to 36 degrees. Relative regional variety
  remains. Contemporary/fallback low-rise pitches use 20-26 degrees; the generic
  fallback is 26 degrees, tropical 22 and cold-climate 32 before proportion limits.
  The narrow stepped-gable modifier has its own 38-41 degree prior so it does
  not become a squat staircase. It remains subject to the same rise/wall limits
  and is omitted when the resolved roof is too broad or shallow.
- Standard gables, hips, joined wings and courtyard roofs use the solved roof's
  peak divided by its steepest active plane gradient as their horizontal run.
  An entire building's bounding width no longer stretches short wing slopes.
- Ordinary domestic roofs are limited to 60% of wall height and 3 m rise.
  Gambrel/mansard profiles allow 75% and 3.6 m. A 3 m one-storey body therefore
  receives at most 1.8 m ordinary or 2.25 m broken-slope inferred roof rise.
- When total height is fixed, the same ratio is solved within that total:
  roof rise <= ratio * total / (1 + ratio). Existing minimum wall/storey
  clearance constraints still apply. Inferred roofs never raise mapped tops.
- Shed roofs use their full slope run with half the nominal pitch, at most
  14 degrees. Other domestic faces are limited to 42 degrees; the short lower
  faces of gambrels and mansards may reach 60 degrees.
- Valid explicit roof heights bypass the visual caps, retaining tall measured
  roofs. Source conflicts still use the existing diagnosed fallback. Flat roofs,
  source footprints, heights and floor counts are not reclassified as attics.
- `Resolution.pitch`/`Spec.pitch` remain equivalent rise-over-half-width angles
  for compatibility. Physical face slopes come from the solved plane gradients.

The shared policy is in `server/buildgen/roof_proportions.py`; catalogue pitches,
regional/global donor styles and contemporary families all pass through it.
The `inferred_roof_proportion_limited` diagnostic identifies reduced priors.

## Attic detailing

`server/buildgen/attics.py` fits at most two attic windows to the actual gable/high
wall boundary when roof rise is at least 2.1 m and glazing plus margins fits.
The upper corners and centre must all clear the roof. Normal low roofs receive
no attic window. Residential/compatible unknown shells, at most three ordinary
storeys and 12 m walls, are eligible; plain/windowless and specialist buildings
are excluded. This does not add to the source floor count.

Regional recipes permit gabled or shed dormers through the shared modifier catalogue.
The selected architectural donor controls this choice, rather than geographic
location alone. These are conservative style options, not prevalence estimates.
A stable per-building hash requests dormers on 45% of eligible style recipes, before roof fit checks.
Contemporary families without an architectural donor do not inherit dormers.

Dormers require at least 2.2 m roof rise, a 0.50-2.2 slope, one continuous
supporting face, and adequate space for a 2.6 m gabled or 3.3 m shed front.
Ordinary cheeks are 1.70 m tall, with another 0.35 m gable or 0.15 m shed rise.
Broken slopes use 1.55 m cheeks. Glazing is 1.35 m wide on gables or 2.05 m
on shed dormers, normally 1.25 m tall (1.10 m on broken slopes). The initial
smaller dormers were enlarged after visual review. They are at most 4.2 m deep,
retain 0.16 m face/footprint clearance, remain at least 0.18 m below the existing
peak, and are separated by at least 1 m. Maximum two per building. Unsupported
faces, low roofs, narrow faces, courtyards and complex special roof variants
simply omit dormers. Gambrel/mansard dormers appear only if a single slope fits.

The cheek and cap geometry meets the original roof surface and is shared by
near, reduced, collision and skyline meshes. Skyline vertex counts include it;
near/reduced rendering adds existing window-atlas glazing and matching trim.
Source peak and occupied footprint stay unchanged. No interiors or penetrable
window openings are created. The first progressive shell can omit glazing.
Planning caches are bounded; no extra scene objects or external assets are used.

## Verification

The 4,608-case audit uses 64 regions, three widths and 24 stable identities, all
with one mapped storey and no mapped roof height. The baseline has 2,949 pitched
roofs; the final modifier-enabled generation has 2,781. Median pitched-roof
rise changes from 3.58 m to 1.80 m and maximum from 8.37 m to 2.25 m. Cases whose
roof rise reaches wall height fall from 1,930 to zero. This is a synthetic visual
acceptance fixture, not an estimate of worldwide building stock.

`tools/roof_proportion_preview.py` writes the audit JSON and geometry sheet;
`--server` compares an actual older build and `--attics` renders attic examples.
Previews use approximate materials, not BeamNG textures or lighting. Regression
tests cover all regional/contemporary priors, special roof slopes, joined and
rotated roofs, mapped dimensions, dormer face clearance and all persistent LODs.
Native gameplay appearance and performance acceptance remain pending.

See [all 25 architectural modifiers and spawn rates](REGIONAL_ARCHITECTURAL_MODIFIERS.md) for the completed regional wiring, new rooftop fittings and representation rules. The table below records profile-specific dormer shape options; the modifier catalogue controls eligibility and chance.

## Regional authoring ranges

Degrees below are nominal priors before geometry and height limits.

| Profile | Previous pitch | Revised pitch | Dormer option |
| --- | --- | --- | --- |
| us_northeast | 28-40 | 24-34 | gabled |
| us_southeast | 22-35 | 19-30 | gabled |
| us_midwest | 23-36 | 20-31 | shed |
| us_southwest | 15-23 | 13-20 | none |
| us_pacific | 26-39 | 22-33 | shed |
| canada_atlantic | 30-42 | 26-36 | gabled |
| canada_prairie | 25-38 | 21-32 | gabled |
| canada_pacific | 25-38 | 21-32 | gabled |
| arctic_north_america | 20-32 | 17-27 | none |
| latin_american_local | 15-24 | 13-20 | none |
| caribbean_creole | 16-26 | 14-22 | none |
| central_america | 20-32 | 17-27 | none |
| andean_highlands | 18-30 | 15-26 | none |
| brazil_coastal | 18-29 | 15-25 | none |
| amazon_guianas | 23-34 | 20-29 | none |
| southern_cone | 20-32 | 17-27 | none |
| chile_pacific | 22-35 | 19-30 | none |
| nz_temperate | 25-38 | 21-32 | gabled |
| au_southeast | 20-32 | 17-27 | gabled |
| au_tropical_arid | 18-30 | 15-26 | none |
| pacific_islands | 21-33 | 18-28 | none |
| antarctic_stations | 18-29 | 15-25 | none |
| eu_atlantic | 18-30 | 15-26 | gabled |
| eu_mediterranean | 21-33 | 18-28 | none |
| nordic_cold | 30-43 | 26-36 | gabled |
| france_regional | 27-39 | 23-33 | gabled |
| low_countries | 30-42 | 26-36 | gabled |
| central_europe | 18-30 | 15-26 | gabled |
| alpine | 21-33 | 18-28 | gabled |
| italy_regional | 24-36 | 20-31 | none |
| adriatic_balkans | 27-39 | 23-33 | none |
| aegean | 30-42 | 26-36 | none |
| eastern_europe | 30-43 | 26-36 | gabled |
| russia_north | 21-33 | 18-28 | none |
| african_local | 24-36 | 20-31 | none |
| maghreb | 27-39 | 23-33 | none |
| sahel | 30-42 | 26-36 | none |
| nile_valley | 18-30 | 15-26 | none |
| horn_africa | 21-33 | 18-28 | none |
| swahili_east_africa | 24-36 | 20-31 | none |
| central_africa | 27-39 | 23-33 | none |
| southern_africa | 30-42 | 26-36 | none |
| indian_ocean_africa | 30-43 | 26-36 | none |
| arid_warm | 18-30 | 15-26 | none |
| levant | 18-31 | 15-26 | none |
| anatolia_caucasus | 22-37 | 19-31 | none |
| iran_plateau | 17-28 | 14-24 | none |
| mesopotamia | 16-27 | 14-23 | none |
| central_asia_oases | 20-34 | 17-29 | none |
| central_asia_steppe | 25-42 | 21-36 | none |
| indus_gangetic | 16-29 | 14-25 | none |
| india_peninsular | 19-34 | 16-29 | none |
| bengal_delta | 17-30 | 14-26 | none |
| himalayan | 24-39 | 20-33 | none |
| sri_lanka_maldives | 22-36 | 19-31 | none |
| jp_temperate | 23-38 | 20-32 | none |
| china_north | 22-36 | 19-31 | none |
| china_south | 18-31 | 15-26 | none |
| korea | 20-35 | 17-30 | none |
| tibetan_plateau | 16-27 | 14-23 | none |
| tropical_humid | 23-38 | 20-32 | none |
| mainland_southeast_asia | 20-33 | 17-28 | none |
| indonesian_archipelago | 25-40 | 21-34 | none |
| philippines | 22-37 | 19-31 | none |
