# Church generator implementation plan

Prepared 1 November 2026. Proposed work governed by the [shared specialized building plan](SPECIALIZED_BUILDING_IMPLEMENTATION_PLANS.md).

See [current church implementation](CHURCH_IMPLEMENTATION_STATUS.md) for the
bounded three-family slice and outstanding reference/game acceptance.

Churches should range from modest timber chapels and plain meeting halls to masonry parish churches and complex mapped cathedrals. Recognition should come from coherent proportions, roof structure, openings and entrance composition. A steeple pasted onto a generic box is insufficient, and a steeple is not appropriate for every church.

## Current behavior and gaps

`buildgen/compiler.py::specialised` retains classes `church`, `chapel`, `cathedral` and matching name keywords on the legacy path. In `buildings.py::_legacy_plan`, churches can receive a tall single storey, a gabled roof and a steeple for buildings below 2,500 m². Roof eligibility still uses footprint fill and width heuristics. `_steeple` supplies the repeated tower/spire treatment; ordinary wall and roof kernels supply much of the rest.

Keep church recognition and existing supported silhouettes during migration. Replace automatic size-driven steeples with evidence-aware components. Distinguish current use from architectural fabric so a converted church may retain its mapped architecture without receiving an invented active-worship identity. Generic religious tags must not automatically receive church-specific symbols.

## Proposed architectural families

Family IDs below belong to a proposed catalogue, not the current runtime presets.

| Family | Composition and variability | Eligibility and fallback | Phase |
| --- | --- | --- | --- |
| `church_plain_chapel` | Simple pitched body, modest entry emphasis, restrained paired or individual windows; timber, brick or render vocabulary | Confirmed church/chapel; conservative default when subtype is unknown | 1 |
| `church_parish_hall` | Longer nave-like hall, larger entrance composition, fitted vertical window bays and coherent plinth/eaves | Confirmed use and fitting proportions; no assumed tower | 1 |
| `church_modern_hall` | Broad entry, grouped glazing, plain metal/render/brick envelope and compatible mapped roof | Modern fabric evidence or validated weak prior; keep arbitrary wings and crosses out | 1 |
| `church_aisled` | Taller central body, lower side aisles, separate roof/wall roles and clerestory bands where supported | Mapped parts or supported height/roof evidence; otherwise one preserved shell | 2 |
| `church_cruciform` | Nave and transept composition with resolved roof junctions; mapped chancel/apse retained | Actual cross-shaped outline or source parts; never add a transept footprint for variety | 2 |
| `church_towered` | Mapped front, side or detached tower; belfry openings and roof/spire chosen independently | Tower extent/height or curated reference; otherwise keep tower absent | 2 |
| `church_classical_front` | Ordered piers, entrance surround, pediment where supported, restrained cornice | Style evidence or validated compatible prior; projecting portico needs mapped/curated extent | 2 |
| `church_complex_landmark` | Several source volumes with individually resolved roofs and shared material/axis relationships | Detailed parts/reference evidence; retain conservative part shells for unsupported geometry | 3 |

Material vocabularies include timber weatherboard, plain brick, dressed or rubble stone, rendered masonry and contemporary panel construction. Choose whole-building compatible combinations; do not mix Gothic window tracery, classical columns and modern metal trim through independent random draws. Roof materials/colors remain subordinate to mapped evidence.

Regional packs adjust compatible material, roof and opening probabilities, not religious identity. Begin reference coverage in NZ/Australia, Britain/Ireland, continental Europe and North America, with neutral defaults elsewhere until local examples are reviewed. These are sampling groups rather than claims that each region has one church style.

## Fitting and detail rules

Resolve axes from mapped roof direction and parts first, then footprint geometry. Do not rotate a building to face east or the nearest road. Identify public frontage from mapped entrances/access; uncertainty should permit a modest fitted entry rather than a dominant invented ceremonial front.

Fit a bounded bay grid to each available wall interval after reserving corners, entries, party walls and source openings. Support plain rectangular, round-headed and pointed openings through reusable profiles. Preserve minimum pier widths and head clearance; adjust bay count rather than stretch windows. Use recessed surrounds and shallow glazing for closed shells, with restrained stained-glass variation only in compatible treatments. Detailed tracery is a near-view asset, not hundreds of unique geometry objects.

Align buttresses, when supported by the family/reference, with structural bays and fit their entire projection envelope. Reserve them before paths and landscaping. Add believable plinths, sills, lintels, bargeboards, ridges, fascia, gutter/downpipe runs and entrance steps from shared detail components. Keep tower louvers and window proportions distinct from ordinary office windows.

Preserve mapped total height across body and roof. A spire/tower may not silently increase a source building's height; separate mapped parts retain their own datums. Shared roof components must handle intersecting volumes and drainage relationships. If an apse, dome or ornate roof is unsupported, record the fallback and preserve its outline; do not treat all curved church parts as ordinary gables.

Choose subtle material age coherently across connected surfaces. Concentrate weathering around runoff, bases and exposed edges without changing the implied building type. Near detail may simplify at distance, while major tower/roof silhouettes and large entrance/window patterns remain.

## Site and access

Reuse grounded entrance, stair, path, pavement and landscaping reservations. A church without site evidence still receives building detail and a verified short entrance connection where it fits. Full forecourts, car parks, gates, walls and planting require mapped/surveyed extent. Preserve mapped churchyard paths and grave/burial exclusions; never sprinkle graves or monuments as generic decoration.

Landscaping should support the setting: restrained planting near entrances, coherent lawn or paved edges where justified, and no industrial loading apron by default. Treat detached halls and towers as linked source buildings only with actual relationship evidence. Do not merge nearby properties because their names contain the same word.

Historic England's guidance describes aisles, transepts, chapels, vestries and porches as established church forms and emphasizes compatible scale and materials. Here that supports coherent treatment of existing mapped parts, not permission to invent extensions. [New facilities in places of worship](https://historicengland.org.uk/advice/caring-for-heritage/places-of-worship/making-changes/principles/new-facilities/).

## Implementation tickets and acceptance

1. **Evidence and adapter.** Add `buildgen/churches.py` selection and part roles; carry source use separately from fabric. Add fixtures for keyword false positives, converted churches, generic religious buildings and unknown tower evidence. Preserve legacy routing outside supported cases.
2. **First architectural slice.** Implement the first three families, fitted openings and material vocabularies using current flat/gabled/supported hipped geometry. Give the same plain rectangular fixture three plausible compositions without altering its outline or supplied height. Verify that every church no longer gets the same steeple.
3. **Mapped composition.** Add aisles, transepts and towers through shared part/roof contracts. Each supported shape needs a valid roof/height fixture, a concave or courtyard case and a diagnosed fallback. Add classical and complex forms after their components pass.
4. **Setting and polish.** Integrate verified paths, entrance landings, churchyard exclusions and LOD materials. Review realistic sizes, eye-level proportions and nearby residential/commercial compatibility.

Extend `test_buildings`, roof/topology/access/chunk suites and add `test_buildgen_churches`. Test complete projection envelopes, no openings on shared walls, no windows through entrance surrounds, source-height conservation, no filled courtyard or grave exclusions, and unchanged decisions under seed replay/rebase/chunk splitting.

The review matrix includes a small timber chapel, brick hall, stone parish church without a tower, mapped tower church, cruciform church, aisled church, modern broad hall, urban attached chapel, converted church, sloping entrance and complex cathedral parts. Use explicit source/curated evidence for reference-specific detail.

First ticket completion requires the three phase-1 families to be distinguishable in unlabelled street and roof views, valid grounded entries on supported terrain, and baseline collision/streaming parity. Towered and complex landmarks remain separate milestones; fully modelled interiors, bells and congregation simulation are outside this plan.
