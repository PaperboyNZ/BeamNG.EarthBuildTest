# Regional architectural modifiers - schema 25

The 25 requested features are wired into the game generator, not just labelled
in a reference catalogue. The authoritative rules are in
`server/buildgen/catalog/architectural_modifiers.json`. Source identities select
stable combinations once; loading, translation and LOD changes do not reroll them.

## Starting selection rates

These are art-direction estimates, not measured regional prevalence. Each rate
is the chance to request a modifier on an eligible low-rise regional/style
recipe. Source facts, geometry, headroom, access, country/locality and rural
checks can reduce the final visible rate. Roof/wall materials compete within
their respective families, so contradictory coverings cannot stack. Existing
fallback material palettes also remain available. No feature is compulsory.

| Feature | Requested regional associations | Initial chance |
| --- | --- | --- |
| Dormers | Northern/Western/Central Europe | 45% |
| Mansard roof | France, Belgium | 18% |
| Stepped gable | Netherlands, Belgium | 15% |
| Half-timbering | Germany, Central Europe, England | 18% |
| Exterior shutters | Mediterranean Europe, France | 65% |
| Awnings | Mediterranean Europe | 35% |
| Bay windows | UK, Ireland, US, Canada, Australia, New Zealand | 28% |
| Iron balconies | Mediterranean Europe, Latin America | 35% |
| Timber balconies | Alps | 55% |
| Front porch | US, Canada | 50% |
| Veranda | Australia, New Zealand, Southern US, Caribbean, South Africa | 45% |
| Deep eaves | East Asia, Southeast Asia, Alps | 70% |
| Stilts / raised building | Southeast Asia | 18% |
| Roof parapet / roof terrace | Middle East, North Africa, South Asia | 55% |
| Large chimneys | UK, Ireland, Northern Europe | 35% |
| Terracotta roofing | Mediterranean Europe, Latin America | 65% |
| Slate roofing | Western/Northern Europe | 45% |
| Metal roofing | Scandinavia, Eastern Europe, Australia, New Zealand | 60% |
| Asphalt shingles | US, Canada | 65% |
| Thatch roofing | Rural Europe, Sub-Saharan Africa, Southeast Asia | 12% |
| Weatherboard / clapboard | US, Canada, Australia, New Zealand | 55% |
| Exposed red brick | UK, Benelux, Northern Europe | 50% |
| White stucco | Mediterranean Europe, North Africa | 65% |
| Timber exterior | Scandinavia | 65% |
| Rooftop water tanks | Mexico, South Asia, Middle East | 40% |

The existing North American/ANZ dormer recipes remain available alongside the
requested European regions, behind the same probability gate. France/Belgium
mansards, Dutch/Belgian stepped gables and English half-timbering use the bundled
country/locality polygons where known. Scotland, Wales and Northern Ireland do
not inherit the English half-timbering gate. Thatch requires observed rural
land-use/zone context; a small footprint alone is insufficient. Mexico is the
existing `latin_american_local` route. Existing 70/20/10 local/contemporary/global
house-style selection is retained; a global donor changes architecture, not the
source's geographic identity. Donor themes without a specific donor country use
their theme-level vocabulary.

## Geometry and representation

- Dormers: enlarged 2.6 m gabled and 3.3 m shed fronts, fitted to a single roof
  plane. Attic glazing is conditional on usable roof height. The shared roof
  proportion rules remain in [the roof guide](ROOF_PROPORTIONS_AND_ATTICS.md).
- Mansards: the existing fitted broken-hip solver, weighted in France/Belgium.
- Stepped gables: reserved for rectangular buildings with 4-8 m gable spans,
  at least 1.65 m roof rise and rise/half-span of 0.75-1.65. Broad or shallow
  roofs retain ordinary roof treatment; footprints and mapped roof heights
  are never distorted to force the ornament. Eligible unmapped roofs use a
  38-41 degree style prior within the common wall-height/3 m rise limits.
  Continuous solid masonry end walls, approximately 0.48 m thick, have
  three to five steps per side sized by roof rise and a central crown. Each tread has
  a 0.10 m light stone coping, with modest projecting edges. Ridge sampling
  includes the centre so the roof cannot poke above the crown; the complete
  ornament stays within the resolved roof height. Brick UVs continue at the
  wall's metric scale instead of stretching over individual triangles. The
  pitched roof ends behind the end wall, and projecting copings are included
  in collision/occupancy bounds. Half-timbering is unchanged by this revision.
- Half-timbering: cream/render fallback infill, floor rails, corner posts and
  opening-aligned piers. Braces occupy intact panels; clipping never turns them
  into disconnected diagonal sticks. Gable frames continue above the eaves.
- Shutters: broader fitted panels, subject to clear wall area and existing detail
  budgets. Awnings add sloping canopies/valances over eligible apertures.
- Bay windows: three glazed facets with angled returns, heads and sills. Small
  0.30 m projections have matching collision solids and occupancy bounds.
  Street-clipped sources retain an inset alternative.
- Iron/timber balconies: deep, closed recessed balcony bays, with metal pickets
  or heavier timber rails. These fit the original footprint; they are not
  advertised as traversable interiors. Verandas use deeper connected ground
  galleries plus covered entry platforms where validated access permits.
- Front porches: wider, terrain-sampled landings and roof/posts are admitted only
  after the existing building/road exclusion checks. The centre remains clear
  for the door. They use the same visual, collision and occupancy geometry.
- Deep eaves: wider existing polygon-fitted eaves, preserving local construction
  differences, mapped roof outlines and street-clearance limits.
- Stilts: six underfloor posts for suitable rectangular raised dwellings. Where
  height/minimum height is unknown, a selected low-rise recipe may infer a
  1.05 m lift. It falls back to grounded construction if validated stairs cannot
  fit; explicit mapped heights are not lifted. These are low raised houses,
  not invented multi-storey pile structures or flood engineering predictions.
- Roof terrace/parapet: a recessed deck and continuous low parapet inside the
  source footprint. Main mapped wall/roof height is preserved.
- Large chimneys: substantial brick shafts, caps and paired pots fitted below
  the pitched roof's resolved peak, not tiny arbitrary rooftop cubes.
- Rooftop water tanks: one closed 12-sided 1.64 m diameter service tank with lid,
  on a recessed flat-roof service area. The fitting can extend 0.65 m above the
  main roof; collision/skyline geometry and bounds include it. This does not
  change the mapped main roof height or source floor count.
- Materials: terracotta, slate, metal, asphalt shingles, weatherboard, red brick,
  white stucco and timber reuse the existing physical materials with appropriate
  fallback selection. Thatch adds original reproducible reed colour/normal
  textures and a registered nonmetallic rough material with deeper roof edges.
  Explicit mapped materials and colours retain priority.

Structural roof/porch/stilt solids persist through near, reduced, collision and
skyline tiers. Small façade overlays simplify with distance. New material indices
are appended to the existing table. Schema 25 and source/catalogue hashes
invalidate old generated caches; downloaded map caches need not be erased.

## Verification and visual review

`tools/architectural_modifier_preview.py` renders all 25 forced feature examples;
these deliberately bypass spawn selection so every implementation can be seen.
`tools/architectural_pair_preview.py` gives closer one/two-storey reviews of the
reworked stepped gables and half-timbering. The software renderer approximates
colours and lighting; material texture appearance and gameplay remain pending
native BeamNG acceptance. Regression tests exercise rates over 2,000 identities
per feature, country/rural gates, explicit-source precedence, actual geometry,
serialization, collision bounds, skyline counts and bundled thatch assets.

The stepped-gable follow-up is reviewed on identical 12 x 10 m and 6 x 11 m
fixtures with `tools/stepped_gable_preview.py` (`--server` selects an older
generator for comparison; `--inferred` reviews the actual unmapped-height recipe).
The proportion revision uses a narrow, steep silhouette instead of applying
shallow steps across broad roofs. Its stone-capped masonry references include
[Breedstraat 32, Hendrick de Keyser Monumenten](https://www.hendrickdekeyser.nl/de-huizen/breedstraat-32)
and [Torenstraat 7, Monumenten.nl](https://www.monumenten.nl/monument/35066).
