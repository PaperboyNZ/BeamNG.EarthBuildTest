# Regional large-block design proposals

1 November 2026 · **64 themes / 192 proposals / not implemented**

## Scope

192 proposed designs: three per written regional theme. Target the remaining large rectangular generic shells, including apartment, mixed-use, hotel, office and civic-looking blocks. Prepared commercial sites and specialist buildings remain outside this proposal set. No runtime generator, regional profile or playtest package is changed.

## Design authority

Use the written style_directions and detailing_goals from environments.json, echoed in REGIONAL_ARCHITECTURAL_THEMES.md. Existing regional_profiles.json geometry and palettes are unfinished and are not inputs to this catalogue. These are new authored interpretations, not claims of surveyed local building types or three historical eras.

## Selection

Resolve locality and actual use first, then choose a compatible design and material family. A region-wide label alone must not activate a locality-specific tradition. For an unknown locality, prefer the contemporary/ordinary compatible option. Do not mix the three proposals into one building. There are no proposed prevalence weights; these need local review.

## Eligibility

Suggested review candidates: rectangular or near-rectangular generic footprints with a longest facade of at least 18 m or area of at least 250 square metres. Use these as authoring filters, not facts about occupancy. Exclude prepared commercial programmes, existing bespoke architecture, industrial halls, parking decks, bridges, terminals and sacred/specialist structures. Keep observed materials, windows, party walls, height and access authoritative.

## Envelope

The baseline changes facade composition inside the current envelope. Keep footprint, storeys, top height, road clearance, terrain base, real entrance positions and collision shell. Any new recess must leave a closed wall behind it. Frames, sills and shade details must fit the cleared surface allowance; otherwise use shallower relief or material zoning. No automatic courtyard, balcony platform, extra floor, stilts, portico or rooftop equipment.

## Scale

Floor ranges are design suitability ranges, not instructions to change floor count. Bay ranges are authored tuning starts. On wider walls repeat sections, not entire identical buildings. On tall blocks use a base/body/crown hierarchy and repeat middle-floor groups; simplify heritage trim above eight storeys. If outside the proposed range, retain the current shell until a taller/shorter adaptation is reviewed.

## Variation

Use a stable source-building seed for design, material palette, section width, entry emphasis and window group. Use the facade role for secondary choices. Keep a shared floor datum and bay lattice; do not randomise each window independently. Vary at least three structural/compositional controls before colour, but keep adjacent bays within one coherent rule set. Translation, tile reload and LOD must not reroll the design.

## Facade roles

The public face has the strongest entrance treatment. Secondary faces simplify trim and reduce glazing as appropriate. Service faces retain known access and can use larger solid zones; they do not receive invented loading doors. A mapped party wall remains blank. Existing courtyard-facing walls can use the same grammar but never trigger a new courtyard.

## Realism

Give windows real reveals, head/sill relationships and consistent mullion spacing. Align panels and piers to floor datums; reserve solid circulation and end-wall zones where compatible with observed openings. Place drainage only on solid pier zones and keep it clear of access. Weathering belongs to coherent exposure/material zones, not random dirty patches.

## Roof and crown

A flat roof can remain realistic: distinguish coping, cornice, fascia, upper spandrel and a quieter top-floor material. Default crown treatments sit below the measured top. Larger pitched roofs, plant screens, roof terraces and stepped upper volumes require supporting geometry or explicit later design approval. Do not use a regional label to invent a skyline.

## Use adaptation

Each proposal is a multi-purpose shell, not a business identity. Apartments/hotels use repeated room-scale pairs and more opaque lower panels; offices group two or three panes within the same bays; civic/education modes emphasise the actual entrance and reception bay. Known mixed-use fronts may enlarge ground glazing only on their public face. Use does not create extra doors, signs, roads, parking or landscaping.

## Geometry and LOD

Proposed first-pass budgets: at most 256 opening groups, 96 facade components, 24 components per elevation and 16 shade hoods per building. Large buildings switch to grouped apertures and material-level detail before exceeding budgets; never omit required doors. Near/lite share openings, solid zones and major composition; near adds reveals and trim. Distant silhouettes retain roof form and dominant colour blocks. These are design targets, not benchmark results.

## Review gates

Before implementation approval, review three side-by-side designs per region on identical dimensions; then test multiple seeds, narrow/wide/tall shells, front/side/service roles, mapped-material conflicts, door clearance, party walls and slopes. Verify near/lite consistency, unchanged essential collision, deterministic reload and frame-time/memory cost in BeamNG. No rendered or driving acceptance is claimed here.

## The 192 proposals

Use ranges below describe design suitability, never changes to observed floors. All numerical ranges are proposed authoring values.

## 01. US Northeast (`us_northeast`)

**Written theme:** Federal and Georgian townhouses; brick rowhouses and brownstones; timber suburbs and contemporary infill.

**Detail direction:** Stoops, aligned sash bays, cornices and restrained shopfront insertion.

### A. Brick pier block

Stable proposal ID: `us_northeast-a` · Punched masonry bays

Suggested fit: 3–12 storeys; 2.8–3.8 m bays; groups of 2–5 bays.

**Composition:** Tall paired windows sit between substantial piers; every fourth bay becomes an opaque stair strip. A clearly heavier base and narrow upper cornice give the box a vertical order.

**Base and entry:** Recess the existing entrance in a stone surround; keep shop glazing to a verified public frontage.

**Roof edge:** Two shallow cornice courses beneath a plain coping; retain the flat roof.

**Materials:** Red or umber brick; pale stone base; dark bronze frames

**Procedural variation:** Vary pier grouping, brick tone and lintel depth together; avoid random window offsets.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Joined street fronts

Stable proposal ID: `us_northeast-b` · Grouped street fronts

Suggested fit: 2–7 storeys; 3–4.2 m bays; groups of 3–5 bays.

**Composition:** Divide the long rectangle into three-to-five-bay compositions with aligned floors but alternating window pairs and restrained colour changes. Treat divisions as facade design, not invented separate properties.

**Base and entry:** One actual entrance anchors the principal section; secondary sections receive solid base panels.

**Roof edge:** Alternate narrow and broad coping bands within the existing height.

**Materials:** Brown brick, buff masonry and muted painted panels

**Procedural variation:** Change section widths and one accent section; keep cornice lines continuous across neighbours.

**Supported upgrade:** Where envelope evidence supports it: stepped crown sections or roof-form variation. Facade sections never become invented parcels, entrances or separate buildings.

**Authoring controls:** target glazing 30%–46%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Contemporary warehouse infill

Stable proposal ID: `us_northeast-c` · Large opaque frames

Suggested fit: 3–16 storeys; 3.8–5.2 m bays; groups of 2–3 bays.

**Composition:** Broad grouped windows alternate with solid framed bays. Emphasise the structural rhythm and a darker top storey without turning every wall into glass.

**Base and entry:** A double-width visual entry frame spans the actual lobby bay; service elevations use smaller openings.

**Roof edge:** Flush cap and inset dark upper panels; plant screens only within an approved roof envelope.

**Materials:** Dark brick piers; warm precast spandrels; charcoal metal

**Procedural variation:** Vary two- or three-window groups, corner solidity and spandrel colour; preserve vertical alignment.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 02. US Southeast and Gulf (`us_southeast`)

**Written theme:** Porch houses and shotgun houses; Appalachian timber homes; brick ranch and contemporary suburban stock.

**Detail direction:** Porch depth, screened openings and climate-specific eaves.

### A. Porch rhythm block

Stable proposal ID: `us_southeast-a` · Shaded horizontal groups

Suggested fit: 2–8 storeys; 3.2–4.5 m bays; groups of 2–4 bays.

**Composition:** Translate porch proportions into vertically aligned shaded window bays and deep horizontal headers. Solid end walls keep a long rectangular block from reading as endless balcony frontage.

**Base and entry:** A rain hood marks the known entrance; a genuine covered walkway requires available setback.

**Roof edge:** Broad-looking fascia under the existing roof edge; no automatic roof pitch.

**Materials:** Warm cream render; muted brick base; painted timber accents

**Procedural variation:** Vary paired bays, screen density and cream/grey/ochre accents; keep shade devices consistent by elevation.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Brick garden block

Stable proposal ID: `us_southeast-b` · Punched masonry bays

Suggested fit: 2–10 storeys; 3–4 m bays; groups of 2–5 bays.

**Composition:** Group ordinary punched windows into short brick panels, separated by wider stair bays. A low masonry base and modest banding make an everyday apartment, office or community shell.

**Base and entry:** Recessed entry with a simple rectangular canopy; retain existing ground levels.

**Roof edge:** Plain capped parapet with a thin contrasting band.

**Materials:** Russet brick; pale lintels; olive or dark metal

**Procedural variation:** Choose staggered panel lengths, lintel grouping and one muted accent; never scatter decorative columns.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Gulf shade frame

Stable proposal ID: `us_southeast-c` · Screen and solid-wall rhythm

Suggested fit: 3–16 storeys; 3.6–5 m bays; groups of 2–4 bays.

**Composition:** Large opaque frames hold smaller glazed openings and vertical shade panels. Screened bays alternate with clear bays, making sunlight control part of the composition.

**Base and entry:** A more transparent lobby bay sits beneath a solid horizontal header.

**Roof edge:** Flat coping with an opaque upper spandrel; roof equipment remains screened only where supported.

**Materials:** Pale concrete; light render; bronze or white screens

**Procedural variation:** Adjust screen spacing and frame depth by exposure; use solid corners or a single expressed stair strip.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 03. US Midwest and Great Plains (`us_midwest`)

**Written theme:** Worker cottages and brick two-flats; Prairie and Craftsman houses; farmsteads and postwar ranches.

**Detail direction:** Broad eaves, masonry bases and distinct urban/rural frontage rhythms.

### A. Brick two-flat rhythm

Stable proposal ID: `us_midwest-a` · Punched masonry bays

Suggested fit: 2–8 storeys; 3–4.2 m bays; groups of 2–5 bays.

**Composition:** Repeat paired upright windows in two- or three-bay groups, separated by broad brick piers. Keep the ground storey visually sturdy and the cornice restrained.

**Base and entry:** A stone-framed entrance occupies one central or off-centre bay.

**Roof edge:** Thin projecting cornice below a flat coping, with projections clearance-tested.

**Materials:** Red-brown brick; limestone-coloured sills; dark frames

**Procedural variation:** Vary brick mixes by building, pair spacing and lintel continuity; keep window heads aligned.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Prairie horizontal block

Stable proposal ID: `us_midwest-b` · Interrupted horizontal glazing

Suggested fit: 2–10 storeys; 4–5.5 m bays; groups of 2–4 bays.

**Composition:** Long sill bands connect grouped windows while solid piers interrupt them at room-scale intervals. The lower floors read broad and grounded, rather than as a glass curtain.

**Base and entry:** Low rectangular entry canopy and a darker recessed base bay.

**Roof edge:** Wide dark fascia beneath the existing roof line; any roof overhang is conditional.

**Materials:** Buff brick; sand render; dark timber-toned metal

**Procedural variation:** Change band intervals, end-wall solidity and paired versus tripled windows; retain the horizontal hierarchy.

**Supported upgrade:** Where the source supports it: inset ribbon bays or a stepped upper volume. Otherwise keep solid interruptions, deep-looking spandrels and a level crown.

**Authoring controls:** target glazing 36%–55%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Great Lakes utility frame

Stable proposal ID: `us_midwest-c` · Large opaque frames

Suggested fit: 3–18 storeys; 3.6–4.8 m bays; groups of 2–3 bays.

**Composition:** A robust grid encloses alternating opaque infill and glazing groups. An expressed circulation strip and quieter rear elevation introduce large-scale variation without changing the footprint.

**Base and entry:** A durable masonry plinth and clearly framed lobby; service doors remain at known locations.

**Roof edge:** Flush cap with a darker upper service band.

**Materials:** Warm precast; red brick infill; graphite frames

**Procedural variation:** Vary brick/precast balance, grouped bay counts and stair-strip position using one building seed.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 04. US Southwest (`us_southwest`)

**Written theme:** Pueblo Revival; Spanish Colonial Revival; desert modern and ordinary stucco suburbs.

**Detail direction:** Recessed openings, shaded courts and separately evidenced parapets.

### A. Desert deep-reveal block

Stable proposal ID: `us_southwest-a` · Deep punched wall planes

Suggested fit: 2–10 storeys; 3–4.5 m bays; groups of 2–3 bays.

**Composition:** Wide solid wall intervals surround deeply inset paired windows. Broader corner masses and a quiet upper band reinterpret the theme through an ordinary rectangular urban building.

**Base and entry:** Shade the actual entrance inside a thick rectangular surround; no invented courtyard.

**Roof edge:** Plain flat coping; a thicker apparent parapet remains within the measured height.

**Materials:** Sand, clay or chalk render; dark recessed glazing

**Procedural variation:** Vary reveal depth, aperture pairing and warm wall tone; keep wall-to-window ratio deliberately high.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Spanish Revival urban front

Stable proposal ID: `us_southwest-b` · Lower pier and upper-bay rhythm

Suggested fit: 2–7 storeys; 3.2–4.4 m bays; groups of 3–4 bays.

**Composition:** Set narrow upper windows over a regular lower arcade-like frame. Arched heads are an optional facade treatment, not open passages or a claim of historic construction.

**Base and entry:** A single shaded entry bay and restrained ceramic-colour base strip.

**Roof edge:** Simple cornice and flat cap; tile is an accent, not a fabricated tiled roof.

**Materials:** Cream render; muted terracotta accents; dark iron-toned metal

**Procedural variation:** Choose rectangular or segmental heads, three- or four-bay groups and sparse shutters.

**Supported upgrade:** Where the ground-floor envelope and access support it: a real sheltered colonnade. Otherwise the lower pier rhythm stays closed; an arch mask is not a traversable opening.

**Authoring controls:** target glazing 28%–46%; reveal depth 0.14–0.3 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Desert modern shade grid

Stable proposal ID: `us_southwest-c` · Screen and solid-wall rhythm

Suggested fit: 3–18 storeys; 3.8–5.2 m bays; groups of 2–4 bays.

**Composition:** Offset solid shade fins against grouped rectangular windows within a calm structural frame. One broad opaque end panel balances the more open principal elevation.

**Base and entry:** Deep-looking lobby recess with a horizontal shade blade inside the available clearance.

**Roof edge:** Thin straight roof edge, visually continuous with the side walls.

**Materials:** Pale mineral panels; bronze screens; charcoal glazing

**Procedural variation:** Vary fin cadence, two facade tones and solid-panel position; constrain shade depth to the envelope.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 05. US Pacific Coast (`us_pacific`)

**Written theme:** Craftsman and timber vernacular; California Spanish Revival; mid-century and contemporary coastal infill.

**Detail direction:** Porches, projecting bays, siding and local flat/pitched roof variants.

### A. Craftsman-derived urban frame

Stable proposal ID: `us_pacific-a` · Post and boarded-panel rhythm

Suggested fit: 2–7 storeys; 3.2–4.5 m bays; groups of 2–4 bays.

**Composition:** Strong posts and horizontal headers frame paired windows, with vertical cladding panels between groups. Keep the upper wall quieter than the articulated lower storeys.

**Base and entry:** A timber-toned entry frame suggests shelter without adding a porch outside the footprint.

**Roof edge:** Deep fascia treatment beneath the existing flat roof.

**Materials:** Muted green or brown siding; masonry base; dark frames

**Procedural variation:** Vary board direction by large zone, post spacing and grouped glazing; omit oversized domestic brackets.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. California courtyard-language block

Stable proposal ID: `us_pacific-b` · Shaded horizontal groups

Suggested fit: 2–9 storeys; 3.3–4.6 m bays; groups of 2–4 bays.

**Composition:** Alternate narrow window bays with wider shaded groups and opaque lower panels. The rhythm recalls courtyard-facing galleries without carving a court into a solid footprint.

**Base and entry:** Recess the known lobby; use a modest rendered surround and shaded glazing.

**Roof edge:** Warm coping and restrained upper band; no applied mission towers or false roof tiles.

**Materials:** Warm white render; clay-coloured bands; muted metal

**Procedural variation:** Vary two-to-four-bay group lengths, shutter share and cream-to-sand palettes.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Pacific modern slab

Stable proposal ID: `us_pacific-c` · Interrupted horizontal glazing

Suggested fit: 3–20 storeys; 4–5.8 m bays; groups of 2–4 bays.

**Composition:** Group horizontal glazing between deep-looking spandrels, interrupted by solid vertical circulation zones. Warm accent panels identify one entry stack rather than covering the whole box.

**Base and entry:** Transparent lobby group with a clear weather-protected threshold.

**Roof edge:** Thin metal cap and visually recessed top-storey cladding within the existing shell.

**Materials:** Light concrete; charcoal panels; limited warm wood accents

**Procedural variation:** Vary ribbon lengths, opaque corner choice and accent stack width; keep repeated floors coherent.

**Supported upgrade:** Where the source supports it: inset ribbon bays or a stepped upper volume. Otherwise keep solid interruptions, deep-looking spandrels and a level crown.

**Authoring controls:** target glazing 36%–55%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 06. Atlantic Canada and Quebec (`canada_atlantic`)

**Written theme:** Maritime timber houses; Quebec stone and brick streets; duplexes and contemporary infill.

**Detail direction:** Painted siding, dormers, exterior stairs only where evidenced.

### A. Quebec masonry block

Stable proposal ID: `canada_atlantic-a` · Punched masonry bays

Suggested fit: 3–10 storeys; 2.8–3.8 m bays; groups of 2–5 bays.

**Composition:** Upright paired windows, heavier corner piers and a measured cornice give a large block the rhythm of masonry streets. Keep small wall recesses instead of decorative glazing everywhere.

**Base and entry:** Stone-framed recessed lobby; no assumed exterior stairs.

**Roof edge:** Flat coping above a simple cornice; dormers require a supported pitched roof.

**Materials:** Grey stone or red brick; pale lintels; dark frames

**Procedural variation:** Change stone/brick balance, three-bay group widths and lintel profiles by building.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Maritime painted panel block

Stable proposal ID: `canada_atlantic-b` · Post and boarded-panel rhythm

Suggested fit: 2–6 storeys; 3–4 m bays; groups of 2–4 bays.

**Composition:** Break the rectangle into broad painted vertical sections with paired windows and narrow weatherboard texture. A common base and roof line unify the sections.

**Base and entry:** Sheltered entry surround in a contrasting but related paint tone.

**Roof edge:** Substantial clean fascia with concealed-looking drainage; retain source roof form.

**Materials:** Muted blue, ochre or red cladding; pale trim; grey base

**Procedural variation:** Vary section widths, one-to-two accent colours and board direction; avoid random per-storey colour changes.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Atlantic winter infill

Stable proposal ID: `canada_atlantic-c` · Enclosed modular fields

Suggested fit: 3–16 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Compact window groups sit inside insulated-looking opaque panels, with a distinct enclosed stair strip. Selected inset panels give depth without large exposed galleries.

**Base and entry:** Recessed wind-lobby appearance around the actual door, with no new floor-level lift.

**Roof edge:** Simple dark cap and flush upper panels.

**Materials:** Pale precast; dark brick base; warm metal accents

**Procedural variation:** Vary window grouping, panel seams and base height within the ground storey; retain substantial opaque areas.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 07. Canadian Prairies and interior (`canada_prairie`)

**Written theme:** Prairie farmhouses; railway-town brick main streets; bungalows and modern infill.

**Detail direction:** Wind lobbies, compact envelopes and shopfront/parapet variation.

### A. Railway-town brick block

Stable proposal ID: `canada_prairie-a` · Grouped street fronts

Suggested fit: 2–7 storeys; 3–4.2 m bays; groups of 3–5 bays.

**Composition:** Compose long fronts as broad brick sections with upright windows and shallow pier divisions. The shopfront-like lower scale works equally as office or civic reception glazing.

**Base and entry:** Keep a solid plinth and clearly framed existing entrance; tenancy divisions are visual only.

**Roof edge:** Several restrained coping widths under one measured roof height.

**Materials:** Buff or red brick; cream lintels; dark storefront metal

**Procedural variation:** Vary section bay counts, brick tone and lintel bands; avoid fabricated separate entrances.

**Supported upgrade:** Where envelope evidence supports it: stepped crown sections or roof-form variation. Facade sections never become invented parcels, entrances or separate buildings.

**Authoring controls:** target glazing 30%–46%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Prairie sheltered slab

Stable proposal ID: `canada_prairie-b` · Interrupted horizontal glazing

Suggested fit: 3–14 storeys; 4–5.4 m bays; groups of 2–4 bays.

**Composition:** Horizontal window groups sit between thick opaque spandrels; broad end panels and a central enclosed stair bay interrupt the long volume.

**Base and entry:** Compact sheltered lobby inside the facade plane, with a dark durable base.

**Roof edge:** Broad fascia expression below a flat roof, without an unsupported overhang.

**Materials:** Sand precast; muted brown panels; grey glazing

**Procedural variation:** Change ribbon lengths, solid-end proportion and panel texture; use one coordinated accent.

**Supported upgrade:** Where the source supports it: inset ribbon bays or a stepped upper volume. Otherwise keep solid interruptions, deep-looking spandrels and a level crown.

**Authoring controls:** target glazing 36%–55%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Interior modular civic block

Stable proposal ID: `canada_prairie-c` · Enclosed modular fields

Suggested fit: 2–12 storeys; 3.6–4.8 m bays; groups of 2–4 bays.

**Composition:** Regular panels enclose alternating single and paired windows, with one larger reception group. Panel joints remain consistent across floors and distinguish this from an all-glass office.

**Base and entry:** A strong rectangular wind-lobby frame marks the existing entry.

**Roof edge:** Clean folded-metal-looking cap with no invented rooftop machinery.

**Materials:** Warm white metal; muted earth accents; masonry base

**Procedural variation:** Vary two- and three-panel groups, accent-strip width and window density by use mode.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 08. Coastal British Columbia (`canada_pacific`)

**Written theme:** Timber coastal vernacular; Arts and Crafts; West Coast modern and mixed-use infill.

**Detail direction:** Rain-sheltered entries, wood cladding and deep glazed bays.

### A. Coastal timber gallery block

Stable proposal ID: `canada_pacific-a` · Shaded horizontal groups

Suggested fit: 2–8 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Broad window groups alternate with timber-faced opaque bays; repeated horizontal headers create a sheltered coastal rhythm. Recessed loggias are a conditional upgrade, not painted balconies.

**Base and entry:** Rain-protected entry frame with matching soffit colour.

**Roof edge:** Strong dark fascia and visible drainage positions coordinated with solid piers.

**Materials:** Warm timber-toned cladding; charcoal base; light soffits

**Procedural variation:** Change gallery-group widths, cladding direction and timber weathering tone consistently across the building.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Arts-and-Crafts masonry frame

Stable proposal ID: `canada_pacific-b` · Large opaque frames

Suggested fit: 2–9 storeys; 3.2–4.5 m bays; groups of 2–3 bays.

**Composition:** A heavy masonry base supports grouped windows in pale upper panels. Wide piers and short horizontal headers adapt domestic proportions to a larger mixed-use shell.

**Base and entry:** Modest timber-toned lobby surround; side walls receive simpler punched openings.

**Roof edge:** Restrained upper beam and flat cap; pitched roofs remain evidence-led.

**Materials:** Brown brick; pale render panels; dark timber accents

**Procedural variation:** Vary brick share, paired/triple windows and entrance offset; keep framing structurally legible.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. West Coast screened infill

Stable proposal ID: `canada_pacific-c` · Screen and solid-wall rhythm

Suggested fit: 3–18 storeys; 3.8–5.2 m bays; groups of 2–4 bays.

**Composition:** A large-scale frame alternates clear glazing groups, slatted shading and opaque panels. One solid vertical bay provides orientation and avoids a uniformly transparent box.

**Base and entry:** A generous-looking glazed entrance group beneath a narrow rain hood.

**Roof edge:** Slim continuous cap with darker top-floor infill.

**Materials:** Light concrete; dark metal; limited warm slats

**Procedural variation:** Vary slat spacing, screen coverage and accent-bay placement; avoid screening every window identically.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 09. Alaska, northern Canada and Greenland (`arctic_north_america`)

**Written theme:** Painted timber settlements; compact insulated modular housing; contemporary Arctic civic buildings.

**Detail direction:** Wind vestibules, insulated panels and surveyed foundation clearances.

### A. Painted settlement block

Stable proposal ID: `arctic_north_america-a` · Post and boarded-panel rhythm

Suggested fit: 1–5 storeys; 2.8–3.8 m bays; groups of 2–4 bays.

**Composition:** Compact paired openings punctuate large insulated-looking wall areas. Break long elevations into painted sections while keeping a continuous enclosed envelope and aligned floor levels.

**Base and entry:** Recessed wind-protected entrance surround; foundations stay at surveyed levels.

**Roof edge:** Strong simple fascia beneath the existing roof; snow hardware needs a supported roof design.

**Materials:** Muted red, blue or ochre siding; pale trim; dark base

**Procedural variation:** Vary section colour, window pair spacing and trim thickness; exclude invented community-specific motifs.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Insulated modular bar

Stable proposal ID: `arctic_north_america-b` · Enclosed modular fields

Suggested fit: 1–8 storeys; 3.2–4.5 m bays; groups of 2–4 bays.

**Composition:** Repeating panel cassettes frame compact windows, with occasional solid service modules. A contrasting circulation bay gives a long rectangular volume a clear order.

**Base and entry:** A robust framed wind-lobby appearance occupies the real entrance bay.

**Roof edge:** Folded cap and uninterrupted roof-edge insulation expression.

**Materials:** Light metal panels; dark joints; one muted colour band

**Procedural variation:** Vary two-to-four-module groups, joint spacing and accent extent; no assumed stilts or foundation clearance.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Northern civic masonry block

Stable proposal ID: `arctic_north_america-c` · Deep punched wall planes

Suggested fit: 2–10 storeys; 3.4–4.8 m bays; groups of 2–3 bays.

**Composition:** Thick-looking piers and deeply recessed grouped windows form a durable civic-scale front. Secondary elevations use smaller punched openings and larger opaque zones.

**Base and entry:** One broad sheltered entry frame supplies a focal point without a projecting portico.

**Roof edge:** Plain flat crown with a darker upper strip inside the height limit.

**Materials:** Pale mineral panels; dark stone-like base; restrained colour accents

**Procedural variation:** Vary paired window width, base tone and entry-stack emphasis; keep the envelope visually compact.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 10. Mexico and northern Mesoamerica (`latin_american_local`)

**Written theme:** Courtyard and adobe traditions; colonial masonry streets; modernist and incremental urban housing.

**Detail direction:** Recessed entries, courtyard-facing galleries and separately mapped roof terraces.

### A. Courtyard-language masonry block

Stable proposal ID: `latin_american_local-a` · Deep punched wall planes

Suggested fit: 2–8 storeys; 3–4.2 m bays; groups of 2–3 bays.

**Composition:** Thick-looking wall planes contain deeply inset window pairs and occasional broader shaded bays. A tall solid entrance surround provides hierarchy without inventing a courtyard behind it.

**Base and entry:** Recess the existing entry; use a durable darker rendered base.

**Roof edge:** Quiet flat coping, with any occupied roof terrace requiring separate evidence.

**Materials:** Warm lime-coloured render; terracotta accents; dark frames

**Procedural variation:** Vary wall warmth, paired-bay intervals and reveal depth; avoid decorative landmark features.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Colonial street rhythm

Stable proposal ID: `latin_american_local-b` · Lower pier and upper-bay rhythm

Suggested fit: 2–7 storeys; 3–4 m bays; groups of 3–4 bays.

**Composition:** A regular lower pier rhythm supports narrow upper openings and a shallow cornice. Rectangular or segmental heads create distinct variants while retaining the same grounded urban proportions.

**Base and entry:** Emphasise one doorway; arcade-like frames are closed facade composition unless circulation is actually supported.

**Roof edge:** Layered but shallow cornice beneath the existing roof edge.

**Materials:** Ochre or cream render; stone-coloured base; muted shutters

**Procedural variation:** Vary three-to-five-bay sections, shutter share and base height within the ground floor.

**Supported upgrade:** Where the ground-floor envelope and access support it: a real sheltered colonnade. Otherwise the lower pier rhythm stays closed; an arch mask is not a traversable opening.

**Authoring controls:** target glazing 28%–46%; reveal depth 0.14–0.3 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Mexican modern frame

Stable proposal ID: `latin_american_local-c` · Large opaque frames

Suggested fit: 3–18 storeys; 3.6–5 m bays; groups of 2–3 bays.

**Composition:** Broad opaque frames enclose paired glazing and rendered infill, with one full-height solid panel. The pattern reads as a composed urban building rather than random incomplete construction.

**Base and entry:** A simple deep-looking entry cutout uses the known lobby bay.

**Roof edge:** Thin flat cap and solid upper spandrel; no fabricated rooftop additions.

**Materials:** Exposed-concrete appearance; brick infill; one muted colour plane

**Procedural variation:** Change infill proportions, brick tone and accent-plane position; keep floor slabs aligned.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 11. Caribbean and Atlantic island towns (`caribbean_creole`)

**Written theme:** Creole timber houses; Spanish courtyard streets; Art Deco and reinforced-concrete urban stock.

**Detail direction:** Louvres, shaded galleries, hurricane shutters and local roof profiles.

### A. Creole shaded gallery

Stable proposal ID: `caribbean_creole-a` · Shaded horizontal groups

Suggested fit: 2–7 storeys; 3–4.3 m bays; groups of 2–4 bays.

**Composition:** Repeated shaded window groups sit behind narrow vertical posts and broad headers. Solid lower panels give gallery proportions without pretending that every bay is an accessible balcony.

**Base and entry:** A shaded entrance surround continues the post rhythm.

**Roof edge:** Broad fascia below the existing roof; roof pitch and storm hardware are conditional.

**Materials:** Pastel render or painted boards; pale trim; dark louvres

**Procedural variation:** Vary pastel family, post spacing and louvre coverage; keep local island choices coherent.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Island Deco block

Stable proposal ID: `caribbean_creole-b` · Interrupted horizontal glazing

Suggested fit: 3–12 storeys; 3.6–4.8 m bays; groups of 2–4 bays.

**Composition:** Strong horizontal spandrels meet a vertical entry strip; grouped windows and flat corner panels create an abstract Deco-derived rhythm. Use stepped surface bands, not extra storeys or towers.

**Base and entry:** A compact geometric entry frame anchors the vertical strip.

**Roof edge:** Two offset-looking colour bands below a straight flat cap.

**Materials:** Cream render; sea-grey panels; restrained coloured bands

**Procedural variation:** Vary band thickness, entry asymmetry and paired versus triple windows; avoid generic cruise-resort ornament.

**Supported upgrade:** Where the source supports it: inset ribbon bays or a stepped upper volume. Otherwise keep solid interruptions, deep-looking spandrels and a level crown.

**Authoring controls:** target glazing 36%–55%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Tropical concrete screen

Stable proposal ID: `caribbean_creole-c` · Screen and solid-wall rhythm

Suggested fit: 3–16 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** An opaque concrete-looking grid alternates glazing and ventilated-screen-like panels. Larger solid end bays and screened circulation strips prevent uniform window coverage.

**Base and entry:** Shaded lobby glazing beneath one continuous header.

**Roof edge:** Flat cap with a substantial upper spandrel.

**Materials:** Pale concrete; muted coloured infill; bronze or white shade panels

**Procedural variation:** Vary screen density and infill colour by section; actual porous screens and storm performance need later engineering.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 12. Central American isthmus (`central_america`)

**Written theme:** Highland courtyard houses; Caribbean timber settlements; tropical modern and ordinary concrete housing.

**Detail direction:** Verandas, covered circulation and highland/coastal material separation.

### A. Highland rendered block

Stable proposal ID: `central_america-a` · Punched masonry bays

Suggested fit: 2–8 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Tall paired windows, thick-looking reveals and restrained sill bands adapt the highland courtyard direction to a solid rectangular block. Broad corner piers keep the composition grounded.

**Base and entry:** One recessed masonry-framed entrance; no invented internal court.

**Roof edge:** Plain cornice under a retained flat roof; tile roofs need geometry support.

**Materials:** Warm white or ochre render; dark masonry base; timber-toned frames

**Procedural variation:** Vary paired-bay groups, render warmth and lintel depth within a highland locality preset.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Caribbean timber frontage

Stable proposal ID: `central_america-b` · Post and boarded-panel rhythm

Suggested fit: 2–6 storeys; 3.2–4.5 m bays; groups of 2–4 bays.

**Composition:** Divide a long wall into broad boarded panels with grouped windows and continuous rain headers. A strong post rhythm gives the facade scale without stretching a small house design across it.

**Base and entry:** Sheltered timber-toned entry frame, with level access retained.

**Roof edge:** Broad fascia and coordinated downpipe zones; no automatic elevated floor.

**Materials:** Muted painted boards; pale posts; dark base

**Procedural variation:** Change panel width, board direction and louvre share; restrict this family to compatible coastal/local contexts.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Isthmus tropical frame

Stable proposal ID: `central_america-c` · Screen and solid-wall rhythm

Suggested fit: 3–16 storeys; 3.6–5.2 m bays; groups of 2–4 bays.

**Composition:** Deep-looking frame bays hold smaller glazed groups, alternating solid infill and shade panels. Distinct public, side and service elevations avoid the same window grid on all faces.

**Base and entry:** A broad shaded lobby group stays on the known frontage.

**Roof edge:** Simple flat cap with a shaded upper window band.

**Materials:** Pale render; grey concrete; warm screen accents

**Procedural variation:** Vary screen cadence and frame colour; use wet/coastal and highland variants as separate selections.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 13. Andean highlands (`andean_highlands`)

**Written theme:** Adobe and stone courtyard houses; colonial urban blocks; brick and concrete self-built neighbourhoods.

**Detail direction:** Thick reveals, sheltered courts and local tile/metal roof choices.

### A. Stone-base highland block

Stable proposal ID: `andean_highlands-a` · Deep punched wall planes

Suggested fit: 2–8 storeys; 2.8–3.8 m bays; groups of 2–3 bays.

**Composition:** Heavy lower walls support compact deeply inset windows in broad upper wall planes. Repeated paired openings and solid corners give an ordinary large block a highland character.

**Base and entry:** A thick rectangular entry surround uses the existing threshold.

**Roof edge:** Restrained coping; any tile or metal roof follows source geometry.

**Materials:** Warm stone-like base; earth-coloured render; dark timber accents

**Procedural variation:** Vary base height, reveal depth and paired-bay frequency; do not label render as actual adobe.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Colonial urban rhythm

Stable proposal ID: `andean_highlands-b` · Lower pier and upper-bay rhythm

Suggested fit: 2–7 storeys; 3–4.2 m bays; groups of 3–4 bays.

**Composition:** A calm lower pier sequence supports upright window groups and narrow upper bands. Shallow arch-head options express the street-front direction without creating unsupported open colonnades.

**Base and entry:** A stronger central entry bay; secondary walls retain plain punched windows.

**Roof edge:** Simple layered cornice below the source roof line.

**Materials:** Pale lime-coloured render; muted stone; dark shutters

**Procedural variation:** Change arch-head share, shutter density and three-to-five-bay sections; avoid monumental ornament.

**Supported upgrade:** Where the ground-floor envelope and access support it: a real sheltered colonnade. Otherwise the lower pier rhythm stays closed; an arch mask is not a traversable opening.

**Authoring controls:** target glazing 28%–46%; reveal depth 0.14–0.3 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Highland brick infill frame

Stable proposal ID: `andean_highlands-c` · Large opaque frames

Suggested fit: 3–14 storeys; 3.2–4.5 m bays; groups of 2–3 bays.

**Composition:** Regular slab bands and piers enclose grouped openings with large brick infill areas. One enclosed circulation strip breaks repetition without suggesting missing walls or unfinished construction.

**Base and entry:** Durable rendered base and a clearly framed lobby bay.

**Roof edge:** Flat capped upper band; rooftop extensions remain separately evidenced.

**Materials:** Red-brown brick; grey frame bands; muted rendered panels

**Procedural variation:** Vary brick/render share, window pairing and stair-strip placement; never randomise structural alignment.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 14. Coastal and southeastern Brazil (`brazil_coastal`)

**Written theme:** Portuguese-derived townhouses; Art Deco streets; Brazilian modernism and contemporary apartments.

**Detail direction:** Shaded balconies, cobogo-inspired screens and ordinary rendered facades.

### A. Portuguese-derived urban front

Stable proposal ID: `brazil_coastal-a` · Grouped street fronts

Suggested fit: 2–8 storeys; 2.8–4 m bays; groups of 3–5 bays.

**Composition:** Long fronts become several broad upright bay groups with restrained surrounds and a shared cornice. Accent panels sit below selected windows, keeping colour ordered rather than scattered.

**Base and entry:** A slightly wider recessed entrance group with a durable darker plinth.

**Roof edge:** Continuous shallow cornice and flat cap.

**Materials:** Warm white or pastel render; ceramic-colour accents; dark frames

**Procedural variation:** Vary group width, pastel tone and ceramic-colour panel share; no automatic historic attribution.

**Supported upgrade:** Where envelope evidence supports it: stepped crown sections or roof-form variation. Facade sections never become invented parcels, entrances or separate buildings.

**Authoring controls:** target glazing 30%–46%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Brazilian shaded modern block

Stable proposal ID: `brazil_coastal-b` · Screen and solid-wall rhythm

Suggested fit: 3–20 storeys; 3.6–5.2 m bays; groups of 2–4 bays.

**Composition:** Alternate open-looking window groups with perforated-screen-inspired solid panels inside a strong frame. A clearly shaded central strip and opaque end wall supply large-scale contrast.

**Base and entry:** Broad horizontal lobby shade treatment within available clearance.

**Roof edge:** Thin roof cap over a substantial upper frame.

**Materials:** Light concrete; cream infill; terracotta or neutral screens

**Procedural variation:** Vary screen module size and clear-to-screened bay ratios; actual perforation is a later geometry option.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Coastal balcony-band block

Stable proposal ID: `brazil_coastal-c` · Shaded horizontal groups

Suggested fit: 3–18 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Continuous-looking horizontal headers are interrupted into short loggia groups by solid piers. Baseline uses recessed glazing and opaque lower panels; real balconies require supported geometry.

**Base and entry:** A darker recessed lobby group aligns with one vertical circulation bay.

**Roof edge:** Straight parapet and lighter top-storey infill.

**Materials:** Pale render; grey slab bands; muted coloured spandrels

**Procedural variation:** Vary group length, spandrel colour and solid corner treatment; preserve repeated room-scale openings.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 15. Amazon and Guianas (`amazon_guianas`)

**Written theme:** Riverine timber housing; Guianese veranda houses; contemporary lowland masonry settlements.

**Detail direction:** Ventilated eaves, rain protection and raised floors only with evidence.

### A. Guianese veranda block

Stable proposal ID: `amazon_guianas-a` · Shaded horizontal groups

Suggested fit: 2–6 storeys; 3–4.4 m bays; groups of 2–4 bays.

**Composition:** Tall shaded opening pairs sit between posts, with continuous headers and louvred upper-panel accents. Solid end sections prevent the long rectangle becoming an endless veranda illustration.

**Base and entry:** Rain-sheltered entry surround at the existing ground level.

**Roof edge:** Broad fascia and clear downpipe zones; no assumed stilts or new roof form.

**Materials:** Painted timber tones; light trim; dark weather base

**Procedural variation:** Vary post grouping, louvre share and muted paint family within local settlement variants.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Riverine timber-panel bar

Stable proposal ID: `amazon_guianas-b` · Post and boarded-panel rhythm

Suggested fit: 1–5 storeys; 3.2–4.5 m bays; groups of 2–4 bays.

**Composition:** Repeated boarded modules alternate compact paired windows with opaque service panels. Large-scale panel divisions make a low rectangular building useful for accommodation, offices or community rooms.

**Base and entry:** One strong covered-looking entrance frame; floor elevation remains measured.

**Roof edge:** Simple metal-looking edge trim beneath the existing roof.

**Materials:** Natural or painted board tones; dark metal seams; masonry base

**Procedural variation:** Vary board orientation, two-module groups and colour-block lengths; avoid unsupported traditional roof silhouettes.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Lowland ventilated frame

Stable proposal ID: `amazon_guianas-c` · Screen and solid-wall rhythm

Suggested fit: 3–12 storeys; 3.6–5 m bays; groups of 2–4 bays.

**Composition:** Large structural-looking bays contain grouped glazing and narrow ventilated-screen-like zones. Heavier rain headers and shaded vertical strips give depth to the ordinary masonry shell.

**Base and entry:** Sheltered lobby group and a less glazed service side.

**Roof edge:** Flat cap with a clearly defined upper rain band.

**Materials:** Light blockwork render; grey concrete; warm shade panels

**Procedural variation:** Vary screen density, frame width and opaque bay position; porous ventilation is an implementation option, not a claim.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 16. Southern Cone plains and Patagonia (`southern_cone`)

**Written theme:** Patio and chorizo houses; Italianate urban fronts; modernist blocks and Patagonian timber/metal homes.

**Detail direction:** Courtyard sequences, rhythmic cornices and cold/warm locality variants.

### A. Italianate urban block

Stable proposal ID: `southern_cone-a` · Punched masonry bays

Suggested fit: 3–10 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Upright paired windows align above a substantial base, with shallow horizontal bands and a restrained cornice. Broad end piers keep a large rectangle from becoming a row of identical narrow houses.

**Base and entry:** A taller-looking rectangular entrance surround fits within the ground storey.

**Roof edge:** Layered cornice entirely below a flat coping.

**Materials:** Pale stone-coloured render; warm brick base; dark metal

**Procedural variation:** Vary bay grouping, lintel articulation and wall tone; applied columns and decorative crowns stay sparse.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Patio rhythm modern block

Stable proposal ID: `southern_cone-b` · Interrupted horizontal glazing

Suggested fit: 3–16 storeys; 3.8–5.2 m bays; groups of 2–4 bays.

**Composition:** Horizontal grouped openings are interrupted by wide solid bays that suggest internal organisation. The patio theme informs shaded recesses; no courtyard is cut into an unsupported footprint.

**Base and entry:** Off-centre recessed lobby and a solid street-level base.

**Roof edge:** Straight thin cap with a darker top-storey band.

**Materials:** Cream render; exposed-concrete appearance; muted brick infill

**Procedural variation:** Vary ribbon length, opaque breaks and brick share; preserve one coherent floor grid.

**Supported upgrade:** Where the source supports it: inset ribbon bays or a stepped upper volume. Otherwise keep solid interruptions, deep-looking spandrels and a level crown.

**Authoring controls:** target glazing 36%–55%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Patagonian clad bar

Stable proposal ID: `southern_cone-c` · Enclosed modular fields

Suggested fit: 2–8 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Compact grouped windows sit in alternating vertical metal and timber-toned sections. Continuous enclosed corners and pronounced joints produce a sheltered utilitarian block rather than a tropical gallery.

**Base and entry:** Framed wind-sheltered entry at the actual threshold.

**Roof edge:** Strong folded-metal-looking fascia; roof pitch remains sourced.

**Materials:** Muted painted metal; timber-toned panels; dark base

**Procedural variation:** Vary section widths, subdued colour and joint rhythm; select only for compatible cold/local contexts.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 17. Chilean Pacific settlements (`chile_pacific`)

**Written theme:** Hillside port houses; Chilote timber and shingle traditions; contemporary seismic-frame housing.

**Detail direction:** Stepped fronts within measured envelopes and timber/metal cladding.

### A. Port-town colour block

Stable proposal ID: `chile_pacific-a` · Grouped street fronts

Suggested fit: 2–8 storeys; 3–4.2 m bays; groups of 3–5 bays.

**Composition:** Divide the long elevation into broad coloured fronts with aligned windows and narrow separating piers. Keep floor levels common; hillside stepping only follows an existing measured envelope.

**Base and entry:** A contrasting entrance section uses the real frontage and terrain connection.

**Roof edge:** Several fascia treatments remain under one source roof line.

**Materials:** Muted ochre, blue or red cladding; pale trim; dark base

**Procedural variation:** Vary front widths, colour relationships and paired-window cadence; avoid random elevation offsets.

**Supported upgrade:** Where envelope evidence supports it: stepped crown sections or roof-form variation. Facade sections never become invented parcels, entrances or separate buildings.

**Authoring controls:** target glazing 30%–46%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Chilote shingle-panel block

Stable proposal ID: `chile_pacific-b` · Post and boarded-panel rhythm

Suggested fit: 2–6 storeys; 3–4 m bays; groups of 2–4 bays.

**Composition:** Large shingle-textured panels alternate with paired upright windows and solid corners. A strong horizontal weather line separates the base from quieter upper floors.

**Base and entry:** A sheltered timber-toned entry recess.

**Roof edge:** Broad plain fascia; shingle wall texture does not imply a new roof shape.

**Materials:** Weathered timber or muted painted shingles; dark trim; stone-like base

**Procedural variation:** Vary panel width, shingle tone and upper-window grouping; keep this locality-specific option distinct from general Chilean stock.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Pacific concrete infill frame

Stable proposal ID: `chile_pacific-c` · Large opaque frames

Suggested fit: 3–18 storeys; 3.6–5 m bays; groups of 2–3 bays.

**Composition:** Clear slab and pier rhythms enclose alternating window groups and solid infill. A larger enclosed stair strip gives the rectangular shell an urban scale without claiming structural or seismic certification.

**Base and entry:** Simple recessed lobby beneath a robust header.

**Roof edge:** Flush cap with a darker top-floor infill zone.

**Materials:** Pale concrete; warm rendered infill; charcoal frames

**Procedural variation:** Change two-to-three-window groups, panel tone and end-wall solidity; keep all frame lines continuous.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 18. Britain, Ireland and Atlantic islands (`eu_atlantic`)

**Written theme:** Georgian and Victorian terraces; stone cottages; postwar estates and contemporary infill.

**Detail direction:** Sash-bay rhythm, brick/stone reveals and local slate/tile distinctions.

### A. Brick civic street block

Stable proposal ID: `eu_atlantic-a` · Punched masonry bays

Suggested fit: 3–10 storeys; 2.8–3.8 m bays; groups of 2–5 bays.

**Composition:** Upright sash-proportioned windows form three-to-five-bay groups between wider brick piers. A sturdy base and restrained cornice bring street scale to a long rectangular shell.

**Base and entry:** Recess the existing door within a stone-coloured surround; stoops require real level differences.

**Roof edge:** Shallow cornice and plain coping; no invented slate roof.

**Materials:** Brown or red brick; pale stone trim; dark frames

**Procedural variation:** Vary paired bays, lintel continuity and brick tone; reserve larger glazing for known public frontage.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Stone-panel urban infill

Stable proposal ID: `eu_atlantic-b` · Deep punched wall planes

Suggested fit: 2–10 storeys; 3.2–4.5 m bays; groups of 2–3 bays.

**Composition:** Deep-looking punched window groups alternate with broad solid panels. Large corner masses and an off-centre circulation strip give a contemporary interpretation of stone-building proportions.

**Base and entry:** One broad recessed entrance frame and a durable base course.

**Roof edge:** Flush stone-coloured coping with a dark upper reveal.

**Materials:** Grey or buff stone-like panels; warm render; bronze frames

**Procedural variation:** Vary solid-panel widths, window pairing and stone/render balance by locality.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Postwar renewal slab

Stable proposal ID: `eu_atlantic-c` · Enclosed modular fields

Suggested fit: 4–20 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Regular room-scale windows sit within larger three-bay panel groups, separated by solid stair strips. Horizontal spandrels are interrupted often enough to avoid an endless window sheet.

**Base and entry:** A clearly glazed lobby group occupies the actual entry position.

**Roof edge:** Simple dark cap; top-storey panels receive a quieter tone.

**Materials:** Warm precast; muted brick infill; charcoal accents

**Procedural variation:** Vary panel grouping, infill family and circulation-strip emphasis; retain measured storeys and footprint.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 19. Iberian Mediterranean and interior (`eu_mediterranean`)

**Written theme:** Patio houses; whitewashed and tiled urban fronts; modern apartment and suburban stock.

**Detail direction:** Shutters, balconies, shaded courts and ceramic accents.

### A. Whitewashed shaded block

Stable proposal ID: `eu_mediterranean-a` · Deep punched wall planes

Suggested fit: 2–9 storeys; 3–4.2 m bays; groups of 2–3 bays.

**Composition:** Compact upright window pairs sit in thick-looking white wall planes, with larger shaded openings on the principal elevation. Solid corners and sparse ceramic-colour panels break repetition.

**Base and entry:** A deeply framed existing entrance; courtyard references remain facade-only.

**Roof edge:** Plain coping with a restrained coloured edge band.

**Materials:** Chalk or sand render; stone-coloured base; muted shutters

**Procedural variation:** Vary shutter share, reveal depth and warm/cool white; use local palettes rather than a universal whitewash.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Iberian tiled street rhythm

Stable proposal ID: `eu_mediterranean-b` · Grouped street fronts

Suggested fit: 2–8 storeys; 2.8–4 m bays; groups of 3–5 bays.

**Composition:** Divide the block into broad upright sections, placing tile-like accents in spandrels rather than covering every surface. Window heads remain aligned beneath a common shallow cornice.

**Base and entry:** One principal entrance section with a durable masonry base.

**Roof edge:** Thin cornice and flat cap; tiled roof forms stay source-led.

**Materials:** Pale render; restrained blue, green or ochre tile-colour panels; dark frames

**Procedural variation:** Vary section width, ceramic-colour coverage and shutter pattern coherently within each section.

**Supported upgrade:** Where envelope evidence supports it: stepped crown sections or roof-form variation. Facade sections never become invented parcels, entrances or separate buildings.

**Authoring controls:** target glazing 30%–46%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Mediterranean loggia frame

Stable proposal ID: `eu_mediterranean-c` · Shaded horizontal groups

Suggested fit: 3–18 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Short groups of shaded glazing alternate with solid piers and opaque lower panels. Recessed loggia geometry is optional; baseline keeps windows within the existing shell.

**Base and entry:** A shaded lobby group, with service faces using smaller punched openings.

**Roof edge:** Continuous flat cap and a quiet upper spandrel.

**Materials:** Light render; pale concrete bands; dark metal screens

**Procedural variation:** Vary two-to-four-bay loggia groups, screen share and corner solidity; never add unsupported balcony slabs.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 20. Nordic countries and North Atlantic (`nordic_cold`)

**Written theme:** Painted timber towns; Nordic classicism; functionalist housing and contemporary timber.

**Detail direction:** Weather-protected entries, restrained trim and locality-specific roof systems.

### A. Painted timber urban block

Stable proposal ID: `nordic_cold-a` · Post and boarded-panel rhythm

Suggested fit: 2–7 storeys; 3–4.2 m bays; groups of 2–4 bays.

**Composition:** Paired upright windows sit in large boarded sections, with restrained posts and consistent floor bands. The composition scales timber-town rhythms to a larger enclosed block.

**Base and entry:** Weather-protected recessed entrance with a contrasting simple frame.

**Roof edge:** Broad but plain fascia beneath the existing roof.

**Materials:** Muted red, ochre or grey boards; pale trim; dark base

**Procedural variation:** Vary section width, board orientation and one paint family; no generic carved decoration.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Nordic classical masonry

Stable proposal ID: `nordic_cold-b` · Punched masonry bays

Suggested fit: 3–10 storeys; 2.8–3.8 m bays; groups of 2–5 bays.

**Composition:** Calm vertical window pairs and broad piers establish a symmetrical or gently offset facade. A heavier base and thin upper cornice provide hierarchy without ornate historical copying.

**Base and entry:** One strong rectangular entry surround; preserve the actual door offset.

**Roof edge:** Restrained cornice under a straight coping.

**Materials:** Warm pale render; grey stone-like base; muted metal

**Procedural variation:** Vary bay grouping, base height and warm neutral palette; keep trim sparse.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Functionalist insulated slab

Stable proposal ID: `nordic_cold-c` · Enclosed modular fields

Suggested fit: 3–20 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Grouped windows alternate with generous opaque panels and enclosed circulation strips. Horizontal bands are expressed through panel joints rather than large decorative projections.

**Base and entry:** Compact sheltered lobby group within a durable ground-storey base.

**Roof edge:** Flush cap and a darker upper panel zone.

**Materials:** Pale concrete; subdued brick or timber-toned panels; dark frames

**Procedural variation:** Vary panel widths, paired/triple glazing and limited timber accents; keep all corners enclosed.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 21. France and regional traditions (`france_regional`)

**Written theme:** Haussmannian streets; half-timber and stone regional houses; modernist estates and contemporary infill.

**Detail direction:** Mansard details only with roof support, shutters and rhythmic stone bays.

### A. Stone boulevard block

Stable proposal ID: `france_regional-a` · Punched masonry bays

Suggested fit: 4–10 storeys; 2.8–3.8 m bays; groups of 2–5 bays.

**Composition:** Upright windows follow a regular street-wall rhythm, with a stronger lower storey, mid-height string course and restrained cornice. Decorative balcony rails are optional surface details, not new platforms.

**Base and entry:** A broad framed existing entrance under the main bay hierarchy.

**Roof edge:** Flat coping with a deeper-looking cornice; mansards require a supported roof.

**Materials:** Warm limestone-coloured panels; grey base; dark frames

**Procedural variation:** Vary window pairing, band placement and corner piers without adding storeys.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Regional masonry infill

Stable proposal ID: `france_regional-b` · Grouped street fronts

Suggested fit: 2–8 storeys; 3–4.2 m bays; groups of 3–5 bays.

**Composition:** Compose the rectangle as broad masonry sections with varied shutter groups and restrained upper framing. Timber accents occupy selected panels rather than imposing half-timber patterns everywhere.

**Base and entry:** A recessed entrance in one wider section; simpler rear openings.

**Roof edge:** Shallow fascia or cornice chosen with the wall family.

**Materials:** Local stone tones or warm render; muted shutters; timber-colour accents

**Procedural variation:** Vary section width, stone/render balance and shutter share through an explicit locality option.

**Supported upgrade:** Where envelope evidence supports it: stepped crown sections or roof-form variation. Facade sections never become invented parcels, entrances or separate buildings.

**Authoring controls:** target glazing 30%–46%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. French modern residential frame

Stable proposal ID: `france_regional-c` · Large opaque frames

Suggested fit: 3–20 storeys; 3.6–5 m bays; groups of 2–3 bays.

**Composition:** Strong horizontal floor bands meet broad vertical piers, grouping windows into short sets. Opaque circulation bays and dark inset upper panels bring order to the large slab.

**Base and entry:** A glazed lobby group beneath a substantial header.

**Roof edge:** Clean cap with a quieter top-storey material zone.

**Materials:** Pale concrete; cream infill; muted coloured panels

**Procedural variation:** Vary infill colour, group length and solid-end proportion; use opaque lower panels for residential or hotel modes.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 22. Low Countries (`low_countries`)

**Written theme:** Brick canal and merchant houses; Flemish terraces; modernist and contemporary brick housing.

**Detail direction:** Narrow bay rhythms, gable variations and recessed entrances.

### A. Merchant-bay brick block

Stable proposal ID: `low_countries-a` · Grouped street fronts

Suggested fit: 3–9 storeys; 2.6–3.6 m bays; groups of 3–5 bays.

**Composition:** Narrow upright window rhythms combine into wider facade sections, separated by slightly stronger piers. Each section has a distinct top-band treatment under a continuous source height.

**Base and entry:** Recess the existing entrance within one wider brick bay.

**Roof edge:** Flat coping with varied band widths; gables are conditional roof geometry.

**Materials:** Warm red or brown brick; pale sills; dark frames

**Procedural variation:** Vary three-to-five-bay section widths, brick mix and lintel grouping; no fake separate parcels.

**Supported upgrade:** Where envelope evidence supports it: stepped crown sections or roof-form variation. Facade sections never become invented parcels, entrances or separate buildings.

**Authoring controls:** target glazing 30%–46%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Flemish masonry court language

Stable proposal ID: `low_countries-b` · Punched masonry bays

Suggested fit: 2–10 storeys; 3–4 m bays; groups of 2–5 bays.

**Composition:** Deep punched window pairs alternate with broader blind panels and restrained sill courses. Corner piers and a grounded base make a compact, solid street block.

**Base and entry:** One stone-framed lobby bay; a court appears only if already present in the footprint.

**Roof edge:** Narrow cornice below a plain coping.

**Materials:** Buff or red brick; stone-coloured base; bronze frames

**Procedural variation:** Vary brick tone, pair spacing and blind-panel cadence; preserve a strong wall-to-window ratio.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Contemporary brick grid

Stable proposal ID: `low_countries-c` · Large opaque frames

Suggested fit: 3–18 storeys; 3.4–4.8 m bays; groups of 2–3 bays.

**Composition:** Broad brick frames enclose grouped glazing and flush opaque spandrels. One full-height inset-looking panel strip distinguishes the composition from the heritage-derived options.

**Base and entry:** Wide recessed lobby frame with minimal ornament.

**Roof edge:** Flush dark cap and simplified top-floor panels.

**Materials:** Dark or pale brick; precast lintels; charcoal metal

**Procedural variation:** Vary frame width, two-to-three-window groups and one accent brick zone; align all joints with the bay grid.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 23. German-speaking and central Europe (`central_europe`)

**Written theme:** Half-timber and masonry townhouses; perimeter blocks; postwar estates and contemporary housing.

**Detail direction:** Rendered panels, brick trim, regular street walls and local roof pitches.

### A. Rendered perimeter rhythm

Stable proposal ID: `central_europe-a` · Punched masonry bays

Suggested fit: 3–12 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Regular upright window pairs form broad street-wall sections, separated by shallow piers. A substantial base and restrained cornice express urban masonry without assuming a courtyard.

**Base and entry:** Existing entrance framed in darker mineral material.

**Roof edge:** Plain cornice and coping; regional roof pitches remain sourced.

**Materials:** Cream or muted ochre render; stone-like base; dark frames

**Procedural variation:** Vary section length, lintel detail and render warmth; keep floor bands continuous.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Masonry-and-timber infill block

Stable proposal ID: `central_europe-b` · Post and boarded-panel rhythm

Suggested fit: 2–7 storeys; 3.2–4.4 m bays; groups of 2–4 bays.

**Composition:** Large rectangular upper panels sit between strong vertical posts and horizontal headers. Use the theme's timber/masonry contrast at block scale, avoiding arbitrary diagonal historical bracing.

**Base and entry:** A solid masonry entrance base with a restrained timber-toned surround.

**Roof edge:** Strong horizontal fascia below the retained roof.

**Materials:** Pale render panels; dark timber-toned framing; masonry base

**Procedural variation:** Vary panel width, timber share and paired-window rhythm; reserve local heritage patterns for evidence-led variants.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Central European panel renewal

Stable proposal ID: `central_europe-c` · Enclosed modular fields

Suggested fit: 4–22 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Window pairs are grouped into larger vertical panel fields, interrupted by enclosed stairs and occasional solid end sections. Surface depth and joint organisation replace a flat repeated glass texture.

**Base and entry:** A sheltered lobby group in a robust darker base.

**Roof edge:** Flush cap with an understated upper-storey band.

**Materials:** Pale precast; muted coloured render; dark metal

**Procedural variation:** Vary field widths, colour-block positions and window grouping; avoid random painted checkerboards.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 24. Alpine settlements (`alpine`)

**Written theme:** Timber chalet traditions; stone valley houses; contemporary Alpine apartments.

**Detail direction:** Deep eaves, timber galleries and snow details only where validated.

### A. Stone-base timber gallery

Stable proposal ID: `alpine-a` · Shaded horizontal groups

Suggested fit: 2–7 storeys; 3.2–4.5 m bays; groups of 2–4 bays.

**Composition:** A heavy base supports grouped windows under broad timber-toned headers. Short gallery-proportioned groups and solid end bays scale the chalet direction to a rectangular apartment or civic shell.

**Base and entry:** Sheltered entry recess in the stone-coloured base.

**Roof edge:** Strong fascia under the existing roof; deep eaves require clearance and roof support.

**Materials:** Warm timber tones; grey stone-like base; dark metal

**Procedural variation:** Vary timber tone, group width and opaque lower panels; no decorative chalet roof added by default.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Valley masonry block

Stable proposal ID: `alpine-b` · Deep punched wall planes

Suggested fit: 2–9 storeys; 2.8–4 m bays; groups of 2–3 bays.

**Composition:** Compact upright openings sit in thick-looking wall planes, with broad corners and one wider entry stack. Restrained horizontal courses keep the long building grounded.

**Base and entry:** Deep rectangular entrance surround at the existing threshold.

**Roof edge:** Plain coping or shallow cornice within the source envelope.

**Materials:** Pale stone or mineral render; muted shutters; timber accents

**Procedural variation:** Vary stone/render balance, shutter share and reveal depth by valley/locality option.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Contemporary Alpine frame

Stable proposal ID: `alpine-c` · Large opaque frames

Suggested fit: 3–12 storeys; 3.6–5 m bays; groups of 2–3 bays.

**Composition:** Large structural-looking bays contain paired windows and broad timber-faced spandrels. One opaque vertical service strip creates a clear modern composition with restrained material contrast.

**Base and entry:** Glazed lobby group beneath a sturdy header.

**Roof edge:** Flush cap and darker upper infill; snow details remain roof-specific.

**Materials:** Light concrete; warm timber infill; dark recessed frames

**Procedural variation:** Vary timber placement, two-to-three-bay grouping and corner solidity; retain the source height.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 25. Italian peninsula and islands (`italy_regional`)

**Written theme:** Palazzo and courtyard blocks; stone/stucco vernacular; rationalist and contemporary apartment buildings.

**Detail direction:** Shutters, loggias, restrained cornices and island-specific stonework.

### A. Palazzo-proportioned urban block

Stable proposal ID: `italy_regional-a` · Punched masonry bays

Suggested fit: 3–10 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** A strong base, taller-looking lower window proportions and quieter upper bays establish a clear hierarchy. A restrained cornice caps the rectangle without copying a particular palace.

**Base and entry:** Emphasise the real entrance with a broad masonry surround.

**Roof edge:** Layered shallow cornice below a flat coping.

**Materials:** Warm stone-coloured base; ochre or cream render; dark shutters

**Procedural variation:** Vary shutter share, base texture and three-to-five-bay groups; no invented courtyard or grand stair.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Stone-and-loggia block

Stable proposal ID: `italy_regional-b` · Shaded horizontal groups

Suggested fit: 2–10 storeys; 3.2–4.5 m bays; groups of 2–4 bays.

**Composition:** Short shaded opening groups alternate with solid piers and opaque lower panels. Stone-coloured end sections balance the open-looking principal elevation and distinguish regional masonry variants.

**Base and entry:** Recessed entrance under one deeper-looking header.

**Roof edge:** Quiet flat cap with a thin stone-coloured edge.

**Materials:** Pale local stone tones; cream render; dark metal

**Procedural variation:** Vary loggia group width, stone/render balance and shutter placement; real voids require geometry support.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Rationalist infill frame

Stable proposal ID: `italy_regional-c` · Large opaque frames

Suggested fit: 3–18 storeys; 3.5–4.8 m bays; groups of 2–3 bays.

**Composition:** A disciplined grid combines grouped windows, broad spandrels and a solid circulation strip. Repeated short horizontal groups give the block proportion without excess ornament.

**Base and entry:** One clearly framed glazed lobby bay and a durable base.

**Roof edge:** Thin straight cap with a darker upper panel field.

**Materials:** Pale render; exposed-concrete appearance; muted terracotta panels

**Procedural variation:** Vary solid/clear bay ratios, frame thickness and accent-panel zone; avoid randomly varied window sizes.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 26. Adriatic and Balkan interior (`adriatic_balkans`)

**Written theme:** Adriatic stone streets; Ottoman-influenced timber/masonry houses; Yugoslav modernism and infill.

**Detail direction:** Balconies, shaded loggias and coastal/interior roof differentiation.

### A. Adriatic stone street block

Stable proposal ID: `adriatic_balkans-a` · Punched masonry bays

Suggested fit: 2–9 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Upright paired openings, deep-looking reveals and broad corner piers create a calm masonry front. A continuous base and thin cornice unify the large rectangular shell.

**Base and entry:** Stone-framed entry with no assumed external stair.

**Roof edge:** Flat coping; tile roof forms remain dependent on the source.

**Materials:** Pale stone tones; warm render; green or dark shutters

**Procedural variation:** Vary shutter share, stone/render balance and grouped bays within coastal locality selections.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Timber-masonry gallery block

Stable proposal ID: `adriatic_balkans-b` · Shaded horizontal groups

Suggested fit: 2–8 storeys; 3.2–4.5 m bays; groups of 2–4 bays.

**Composition:** Upper window groups are framed by strong posts and horizontal beams over a solid lower storey. Projecting upper bays are an optional upgrade, while the baseline stays in-plane.

**Base and entry:** A sheltered-looking entrance within the lower masonry bay.

**Roof edge:** Broad timber-toned fascia under the current roof.

**Materials:** Pale render; dark timber-toned upper bands; stone-like base

**Procedural variation:** Vary upper-panel width, glazing groups and timber share; select compatible inland/local contexts.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Modernist slab with inset groups

Stable proposal ID: `adriatic_balkans-c` · Enclosed modular fields

Suggested fit: 4–22 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Divide long elevations into larger vertical fields containing paired windows and substantial spandrels. Dark inset-looking loggia panels and a solid stair strip add depth without inventing balconies.

**Base and entry:** A distinct glazed lobby group within a durable darker base.

**Roof edge:** Simple continuous cap with quieter top-floor cladding.

**Materials:** Pale precast; muted coloured infill; dark frames

**Procedural variation:** Vary field length, inset-panel share and accent location; preserve the repeated slab rhythm.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 27. Greece and Cyprus (`aegean`)

**Written theme:** Island courtyard houses; neoclassical townhouses; polykatoikia apartment blocks.

**Detail direction:** Shutters, balcony bands and locality-specific whitewash/stone treatment.

### A. Island masonry block

Stable proposal ID: `aegean-a` · Deep punched wall planes

Suggested fit: 2–7 storeys; 2.8–4 m bays; groups of 2–3 bays.

**Composition:** Thick-looking wall planes hold compact window pairs, with broader solid corners and a shaded entrance recess. Whitewash is one locality option rather than a universal regional requirement.

**Base and entry:** Recess the existing doorway within a simple rendered frame.

**Roof edge:** Plain flat coping, with no fabricated rooftop terrace.

**Materials:** Local white or sand render; stone-coloured base; muted shutters

**Procedural variation:** Vary local stone/whitewash balance, shutter tone and reveal depth; retain ordinary urban scale.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Neoclassical urban rhythm

Stable proposal ID: `aegean-b` · Punched masonry bays

Suggested fit: 3–9 storeys; 2.8–3.8 m bays; groups of 2–5 bays.

**Composition:** Upright windows align in broad groups between shallow piers. A strong base, narrow middle band and restrained cornice create hierarchy without monumental pediments or columns.

**Base and entry:** One framed entry stack occupies the actual door position.

**Roof edge:** Modest cornice below the source roof edge.

**Materials:** Cream or ochre render; pale mineral trim; dark frames

**Procedural variation:** Vary lintel grouping, wall warmth and pier spacing; keep upper floors quieter.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Polykatoikia banded block

Stable proposal ID: `aegean-c` · Shaded horizontal groups

Suggested fit: 3–18 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Long horizontal headers break into short shaded window groups with opaque lower panels. Solid stair and end-wall bays prevent a continuous undifferentiated balcony strip.

**Base and entry:** Recessed lobby below one solid circulation stack.

**Roof edge:** Straight flat cap and a darker upper spandrel.

**Materials:** Pale concrete; cream infill; muted awning-colour panels

**Procedural variation:** Vary group lengths, shade-panel share and corner solidity; actual balcony projection requires support and clearance.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 28. Eastern Europe and Baltic (`eastern_europe`)

**Written theme:** Timber and masonry vernacular; eclectic and Art Nouveau streets; socialist-era blocks and contemporary infill.

**Detail direction:** Bay/cornice variation and explicit rural/urban distinctions.

### A. Eclectic masonry street block

Stable proposal ID: `eastern_europe-a` · Punched masonry bays

Suggested fit: 3–10 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Upright windows form wider central and narrower side groups, with restrained sill courses and a clear cornice. Ornament is limited to simple geometric surrounds, not invented Art Nouveau motifs.

**Base and entry:** Emphasise the real entrance with a stronger mineral frame.

**Roof edge:** Shallow stepped cornice under a flat coping.

**Materials:** Warm render or brick; pale lintels; dark frames

**Procedural variation:** Vary bay grouping, brick/render balance and lintel depth within a local palette.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Baltic timber-panel infill

Stable proposal ID: `eastern_europe-b` · Post and boarded-panel rhythm

Suggested fit: 2–7 storeys; 3–4.3 m bays; groups of 2–4 bays.

**Composition:** Broad cladding sections contain paired windows and solid interstitial panels. Vertical boards, strong headers and a durable lower storey adapt timber vernacular proportions to a larger enclosed block.

**Base and entry:** Weather-protected entrance frame in a contrasting muted tone.

**Roof edge:** Plain deep-looking fascia beneath the retained roof.

**Materials:** Muted painted boards; warm mineral base; dark trim

**Procedural variation:** Vary section width, board direction and colour family; use only compatible local contexts.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Panel-estate renewal block

Stable proposal ID: `eastern_europe-c` · Enclosed modular fields

Suggested fit: 4–24 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Larger vertical fields organise repeated window pairs, enclosed stair strips and substantial spandrels. A few dark recessed-looking bays introduce depth without arbitrary silhouette changes.

**Base and entry:** Sheltered lobby group anchored by a darker base zone.

**Roof edge:** Flush cap and simplified upper panels.

**Materials:** Light precast; muted warm or cool infill; charcoal frames

**Procedural variation:** Vary field widths, grouped-window cadence and accent strips; maintain floor-to-floor consistency.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 29. Russia and northern Eurasia (`russia_north`)

**Written theme:** Timber izba houses; classical and eclectic urban blocks; constructivist and panel housing.

**Detail direction:** Carved trim only with support, panel rhythms and climate-specific entries.

### A. Northern timber-panel block

Stable proposal ID: `russia_north-a` · Post and boarded-panel rhythm

Suggested fit: 2–6 storeys; 2.8–4 m bays; groups of 2–4 bays.

**Composition:** Compact paired windows sit in broad boarded panels with clear horizontal weather lines. Use simple robust trim rather than unsourced carved patterns when scaling the timber direction to a larger building.

**Base and entry:** Recessed weather-protected entrance surround.

**Roof edge:** Strong fascia below the source roof; no invented pitched profile.

**Materials:** Muted painted timber; pale restrained trim; dark base

**Procedural variation:** Vary board orientation, paint family and panel grouping; retain a visually enclosed envelope.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Classical masonry urban block

Stable proposal ID: `russia_north-b` · Punched masonry bays

Suggested fit: 3–12 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Broad piers divide upright window groups, with a substantial lower storey and restrained cornice. Slightly stronger central bays organise the large rectangle without monumental towers.

**Base and entry:** A wide framed existing entrance provides the focal point.

**Roof edge:** Layered shallow cornice within the measured height.

**Materials:** Pale stone-coloured render; warm grey base; dark frames

**Procedural variation:** Vary group widths, base material and lintel detail; keep the elevation calm and regular.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Constructivist panel composition

Stable proposal ID: `russia_north-c` · Interrupted horizontal glazing

Suggested fit: 4–24 storeys; 3.8–5.2 m bays; groups of 2–4 bays.

**Composition:** Horizontal window groups intersect one strong opaque circulation strip. Solid end planes and contrasting spandrels give the slab an asymmetric but coherent modern composition.

**Base and entry:** A glazed lobby group aligns with the circulation strip where the actual entry permits.

**Roof edge:** Thin straight cap over a darker upper panel field.

**Materials:** Light concrete; muted brick infill; charcoal accents

**Procedural variation:** Vary ribbon lengths, stair-strip width and infill share; no unsupported cantilevers or added volumes.

**Supported upgrade:** Where the source supports it: inset ribbon bays or a stepped upper volume. Otherwise keep solid interruptions, deep-looking spandrels and a level crown.

**Authoring controls:** target glazing 36%–55%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 30. West African Atlantic and Gulf of Guinea (`african_local`)

**Written theme:** Compound houses; Afro-Brazilian urban fronts; tropical modern and contemporary masonry housing.

**Detail direction:** Shaded galleries, ventilation screens and courtyard-facing openings.

### A. Compound-language shaded block

Stable proposal ID: `african_local-a` · Deep punched wall planes

Suggested fit: 2–8 storeys; 3–4.3 m bays; groups of 2–3 bays.

**Composition:** Broad solid wall intervals contain deeply shaded window groups. A stronger entrance frame and selective upper screens adapt compound proportions without inventing walls, gates or internal courts.

**Base and entry:** Recess the actual entry within a durable rendered surround.

**Roof edge:** Plain flat coping with one restrained upper band.

**Materials:** Warm earth-coloured render; darker base; muted timber accents

**Procedural variation:** Vary grouped openings, reveal depth and warm palette through city/locality choices; avoid a single pan-regional motif.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Afro-Brazilian urban rhythm

Stable proposal ID: `african_local-b` · Punched masonry bays

Suggested fit: 2–9 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Upright window pairs and broad shallow piers form rhythmic street-front sections. Simple lintels, sill bands and a restrained cornice provide architectural detail without copying unsupported historic ornament.

**Base and entry:** One stronger framed entrance within a solid base.

**Roof edge:** Shallow layered cornice below the existing roof.

**Materials:** Cream or muted pastel render; pale trim; dark shutters

**Procedural variation:** Vary section width, shutter share and trim contrast; keep decorative density modest.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Gulf of Guinea tropical frame

Stable proposal ID: `african_local-c` · Screen and solid-wall rhythm

Suggested fit: 3–18 storeys; 3.6–5 m bays; groups of 2–4 bays.

**Composition:** Large bays alternate shaded glazing, opaque spandrels and screen-like circulation panels. A solid end plane balances the more open public elevation and reduces repetitive window coverage.

**Base and entry:** Shaded lobby group beneath a continuous header.

**Roof edge:** Clean flat cap with a substantial upper shade band.

**Materials:** Pale concrete; warm rendered infill; neutral screen panels

**Procedural variation:** Vary screen cadence, frame depth and infill tone; use public, side and service elevation roles.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 31. Maghreb and northwest Africa (`maghreb`)

**Written theme:** Medina courtyard houses; Amazigh earthen and stone traditions; modern Mediterranean urban stock.

**Detail direction:** Deep reveals, shaded courts and local tile/plaster detailing.

### A. Medina-language urban block

Stable proposal ID: `maghreb-a` · Deep punched wall planes

Suggested fit: 2–9 storeys; 2.8–4 m bays; groups of 2–3 bays.

**Composition:** Thick-looking wall planes contain compact paired openings and occasional screened bays. The larger entrance surround is the main focal point; the solid footprint remains intact.

**Base and entry:** A deep rectangular entry frame; decorative arches are optional shallow treatments.

**Roof edge:** Plain coping within the existing height.

**Materials:** Sand or pale lime-coloured render; stone-like base; dark frames

**Procedural variation:** Vary reveal depth, screen share and mineral tone by locality; do not fabricate a courtyard.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Earthen-and-stone interpretation

Stable proposal ID: `maghreb-b` · Punched masonry bays

Suggested fit: 2–7 storeys; 3–4.2 m bays; groups of 2–5 bays.

**Composition:** Broad piers and horizontal masonry-colour courses frame smaller upright windows. Solid corners and a heavier base express mass through surface composition rather than invented buttresses.

**Base and entry:** Simple shaded entrance within the existing wall line.

**Roof edge:** Restrained thick-looking cap with no crenellations.

**Materials:** Warm ochre render; muted stone tones; dark timber accents

**Procedural variation:** Vary stone/render balance and window grouping; render remains render, not a claimed earth material.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Mediterranean screen frame

Stable proposal ID: `maghreb-c` · Screen and solid-wall rhythm

Suggested fit: 3–18 storeys; 3.5–4.8 m bays; groups of 2–4 bays.

**Composition:** Short glazed groups alternate with deep-looking opaque frames and screened vertical strips. Substantial spandrels keep the building shaded and visually solid.

**Base and entry:** A broad recessed lobby bay beneath a simple header.

**Roof edge:** Thin straight coping and quieter upper panels.

**Materials:** Cream render; pale concrete; bronze or neutral screens

**Procedural variation:** Vary screen density, paired/triple groups and accent-strip position; avoid ungrounded religious or ceremonial motifs.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 32. Sahel and western Sudanian belt (`sahel`)

**Written theme:** Sudano-Sahelian earthen compounds; courtyard trading towns; contemporary masonry housing.

**Detail direction:** Buttressed forms only with footprint support and shaded recessed openings.

### A. Earth-tone solid block

Stable proposal ID: `sahel-a` · Deep punched wall planes

Suggested fit: 2–7 storeys; 2.8–4 m bays; groups of 2–3 bays.

**Composition:** Thick-looking wall planes, compact window pairs and broad corners create a restrained low-glazing composition. Shadow comes from reveals, not added monumental buttresses or copied sacred forms.

**Base and entry:** A deeply framed existing entrance forms the principal interruption.

**Roof edge:** Plain flat cap; no decorative finials.

**Materials:** Warm ochre or clay render; darker base; muted frames

**Procedural variation:** Vary wall tone, reveal depth and paired-bay cadence; identify the material honestly as rendered masonry.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Trading-street shaded rhythm

Stable proposal ID: `sahel-b` · Lower pier and upper-bay rhythm

Suggested fit: 2–8 storeys; 3.2–4.5 m bays; groups of 3–4 bays.

**Composition:** Broad lower piers align with compact upper window groups and occasional screened panels. The repeated shade-frame rhythm supports offices, accommodation or civic rooms without assuming retail tenancy.

**Base and entry:** One shaded actual entry; open passageways require separate support.

**Roof edge:** Simple horizontal crown beneath the source roof.

**Materials:** Sand render; stone-coloured plinth; dark timber-toned screens

**Procedural variation:** Vary pier width, grouped bay lengths and screen share; keep solid-wall proportions high.

**Supported upgrade:** Where the ground-floor envelope and access support it: a real sheltered colonnade. Otherwise the lower pier rhythm stays closed; an arch mask is not a traversable opening.

**Authoring controls:** target glazing 28%–46%; reveal depth 0.14–0.3 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Contemporary dry-climate frame

Stable proposal ID: `sahel-c` · Screen and solid-wall rhythm

Suggested fit: 3–14 storeys; 3.6–5 m bays; groups of 2–4 bays.

**Composition:** Large frame bays contain small grouped windows and solid infill, with an opaque circulation strip. Sparse shade panels supply depth without making every surface decorative.

**Base and entry:** Deep-looking lobby recess inside the existing envelope.

**Roof edge:** Thin coping with a solid upper spandrel.

**Materials:** Pale mineral panels; warm infill; neutral shade fins

**Procedural variation:** Vary shade cadence, warm/cool panel balance and solid end-wall width; no inferred cooling equipment.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 33. Nile Valley and northeast desert (`nile_valley`)

**Written theme:** Nubian courtyard traditions; urban masonry apartment blocks; modern concrete housing.

**Detail direction:** Shading, deep reveals and separately evidenced vault/dome forms.

### A. Nile masonry shade block

Stable proposal ID: `nile_valley-a` · Deep punched wall planes

Suggested fit: 2–10 storeys; 3–4.2 m bays; groups of 2–3 bays.

**Composition:** Compact grouped openings sit within substantial wall planes, with shaded vertical strips and broad solid corners. Courtyard proportions inform the facade only; no unsupported voids are cut.

**Base and entry:** A broad rectangular entry recess in a darker base.

**Roof edge:** Plain flat coping without invented domes or vaults.

**Materials:** Sand render; warm brick accents; dark recessed frames

**Procedural variation:** Vary brick/render balance, reveal depth and pair spacing through locality options.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Urban brick apartment frame

Stable proposal ID: `nile_valley-b` · Large opaque frames

Suggested fit: 3–18 storeys; 3.2–4.6 m bays; groups of 2–3 bays.

**Composition:** Clear slab bands and piers organise paired windows and opaque infill panels. A distinct enclosed stair bay breaks the long elevation while keeping an ordinary completed-building appearance.

**Base and entry:** Durable rendered base and one framed lobby group.

**Roof edge:** Capped upper band; roof additions need source support.

**Materials:** Warm brick infill; pale concrete bands; muted render

**Procedural variation:** Vary brick tone, infill share and two-to-three-window grouping; avoid random exposed structural fragments.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. River-city shaded modern slab

Stable proposal ID: `nile_valley-c` · Shaded horizontal groups

Suggested fit: 4–20 storeys; 3.6–5 m bays; groups of 2–4 bays.

**Composition:** Short shaded opening groups alternate with solid piers, screen-like panels and opaque lower spandrels. The horizontal rhythm is broken by one stronger vertical circulation zone.

**Base and entry:** Shaded lobby aligned with the known entrance.

**Roof edge:** Thin flat cap with a deeper-looking upper header.

**Materials:** Pale render; grey slab edges; neutral screens

**Procedural variation:** Vary group length, screen ratio and solid corner treatment; actual loggias remain conditional geometry.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 34. Horn of Africa and Ethiopian highlands (`horn_africa`)

**Written theme:** Highland stone compounds; Asmara modernism; coastal and contemporary urban masonry.

**Detail direction:** Local stone/render treatment, verandas and modernist horizontal bands.

### A. Highland stone block

Stable proposal ID: `horn_africa-a` · Punched masonry bays

Suggested fit: 2–9 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Upright paired openings sit between broad masonry piers, above a heavy base. Deep-looking reveals and sparse lintel bands create detail without unsupported compound walls.

**Base and entry:** One strong shaded entrance surround.

**Roof edge:** Plain cornice beneath the existing roof edge.

**Materials:** Warm grey stone-like panels; pale render; dark timber accents

**Procedural variation:** Vary stone/render share, window pairing and trim tone using highland locality choices.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Asmara-derived modernist block

Stable proposal ID: `horn_africa-b` · Interrupted horizontal glazing

Suggested fit: 3–12 storeys; 3.8–5.2 m bays; groups of 2–4 bays.

**Composition:** Horizontal grouped glazing meets a vertical entry strip, with solid end panels and crisp shallow bands. The composition borrows the written modernist direction without reproducing a landmark.

**Base and entry:** A simple geometric canopy treatment fits the actual lobby bay.

**Roof edge:** Two shallow horizontal crown bands under a flat cap.

**Materials:** Cream render; pale grey bands; restrained dark accents

**Procedural variation:** Vary ribbon lengths, entry-strip offset and spandrel thickness; no invented towers or curved volumes.

**Supported upgrade:** Where the source supports it: inset ribbon bays or a stepped upper volume. Otherwise keep solid interruptions, deep-looking spandrels and a level crown.

**Authoring controls:** target glazing 36%–55%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Coastal screened masonry frame

Stable proposal ID: `horn_africa-c` · Screen and solid-wall rhythm

Suggested fit: 3–16 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** A substantial frame alternates paired windows, opaque infill and screened circulation strips. Shaded openings and clear elevation roles distinguish the coastal version from the highland masonry option.

**Base and entry:** Recessed shaded entry group within the wall envelope.

**Roof edge:** Straight cap with a continuous upper shade line.

**Materials:** Pale render; warm masonry base; neutral shade panels

**Procedural variation:** Vary screen cadence, wall tone and solid-end proportion; separate coastal and highland selection.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 35. Swahili coast and East African interior (`swahili_east_africa`)

**Written theme:** Swahili courtyard townhouses; inland masonry and timber housing; tropical modern urban buildings.

**Detail direction:** Carved-entry references, shaded verandas and coast/interior differentiation.

### A. Coastal townhouse rhythm

Stable proposal ID: `swahili_east_africa-a` · Punched masonry bays

Suggested fit: 2–9 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Upright paired windows and deep-looking reveals form broad street-front groups. The entrance receives a restrained timber frame; specific carved patterns require locality evidence rather than automatic ornament.

**Base and entry:** One shaded existing entry with a durable base course.

**Roof edge:** Simple cornice and flat coping.

**Materials:** Pale lime-coloured render; warm stone-like base; dark timber

**Procedural variation:** Vary timber-frame width, shutter share and masonry tone; do not invent internal courtyards.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Interior veranda block

Stable proposal ID: `swahili_east_africa-b` · Shaded horizontal groups

Suggested fit: 2–8 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Short groups of shaded windows sit between broad posts and solid side bays. Horizontal headers and opaque lower panels provide veranda proportions within the existing rectangular shell.

**Base and entry:** Sheltered lobby frame with no additional raised floor.

**Roof edge:** Strong fascia treatment below the source roof.

**Materials:** Warm brick or render; timber-toned headers; dark base

**Procedural variation:** Vary group width, brick/render balance and post spacing through interior locality options.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. East African modern screen

Stable proposal ID: `swahili_east_africa-c` · Screen and solid-wall rhythm

Suggested fit: 3–18 storeys; 3.6–5 m bays; groups of 2–4 bays.

**Composition:** Broad framed bays combine grouped glazing with screen-like infill and solid circulation strips. A quieter service elevation prevents the building reading as the same facade repeated four times.

**Base and entry:** Shaded public entrance group under a robust header.

**Roof edge:** Clean flat cap and a solid upper spandrel.

**Materials:** Light concrete; pale rendered infill; warm screen panels

**Procedural variation:** Vary screen density, panel tone and window grouping; keep all shade devices coordinated by elevation.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 36. Central African forest and plateau (`central_africa`)

**Written theme:** Forest timber compounds; veranda houses; contemporary blockwork and concrete cities.

**Detail direction:** Rain-shedding eaves, ventilated screens and timber/masonry alternatives.

### A. Timber-panel community block

Stable proposal ID: `central_africa-a` · Post and boarded-panel rhythm

Suggested fit: 1–6 storeys; 3–4.3 m bays; groups of 2–4 bays.

**Composition:** Large boarded sections contain paired windows and opaque service panels. Strong posts and horizontal rain headers give a long low block scale without copying unsupported compound or pavilion geometry.

**Base and entry:** A sheltered-looking timber entry frame on the actual frontage.

**Roof edge:** Broad fascia with clear drainage zones beneath the retained roof.

**Materials:** Muted timber or painted boards; pale trim; dark weather base

**Procedural variation:** Vary board direction, section widths and subdued colour; no presumed raised floor.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Veranda rhythm masonry block

Stable proposal ID: `central_africa-b` · Shaded horizontal groups

Suggested fit: 2–9 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Short groups of shaded openings alternate with solid piers and broad end walls. A continuous weather line unifies the front while side elevations use smaller punched openings.

**Base and entry:** Recessed entry with a deeper-looking rain header.

**Roof edge:** Strong straight fascia or coping within the source profile.

**Materials:** Warm render; grey masonry base; timber-toned shade accents

**Procedural variation:** Vary group length, opaque lower panels and accent share; actual covered circulation is conditional.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Forest-city concrete screen

Stable proposal ID: `central_africa-c` · Screen and solid-wall rhythm

Suggested fit: 3–16 storeys; 3.6–5 m bays; groups of 2–4 bays.

**Composition:** Large structural-looking bays alternate glazing groups and opaque infill, with screened vertical strips. Deep-looking headers provide a rain-sheltered character without arbitrary roof additions.

**Base and entry:** One broad shaded lobby group and a durable base.

**Roof edge:** Flat cap with a substantial upper rain band.

**Materials:** Pale blockwork render; concrete-coloured frame; neutral screens

**Procedural variation:** Vary screen modules, solid/clear ratios and infill tone; distinguish public and service faces.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 37. Southern African plateau and coasts (`southern_africa`)

**Written theme:** Cape and veranda traditions; courtyard homesteads; modernist, township and contemporary suburban stock.

**Detail direction:** Stoep/porch treatments, shade devices and separate highland/arid/coastal variants.

### A. Cape-derived masonry block

Stable proposal ID: `southern_africa-a` · Punched masonry bays

Suggested fit: 2–8 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Upright paired windows and broad piers form a calm grounded elevation. A restrained cornice and darker base carry the written Cape direction without adding signature gables to a flat-roof shell.

**Base and entry:** Sheltered framed entrance at the measured threshold.

**Roof edge:** Simple cornice and flat coping; decorative roof forms require support.

**Materials:** Warm white render; stone-like base; dark timber accents

**Procedural variation:** Vary window pairs, base texture and trim colour within compatible local variants.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Stoep rhythm urban block

Stable proposal ID: `southern_africa-b` · Shaded horizontal groups

Suggested fit: 2–10 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** A repeated shaded lower rhythm supports shorter upper opening groups and solid end bays. The stoep reference becomes post-and-header composition; no invented walkable porch or parcel extension.

**Base and entry:** Existing entry receives one stronger shade frame.

**Roof edge:** Broad fascia under the current roof.

**Materials:** Warm brick or render; dark posts; pale shade bands

**Procedural variation:** Vary brick/render share, group length and shade depth; select arid, coastal or highland material variants explicitly.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Southern modern infill frame

Stable proposal ID: `southern_africa-c` · Large opaque frames

Suggested fit: 3–18 storeys; 3.6–5 m bays; groups of 2–3 bays.

**Composition:** Broad frame bays combine paired windows and solid panels, with a contrasting stair strip. Lower-floor shade treatment and substantial spandrels avoid the all-window box.

**Base and entry:** Glazed lobby group within a durable masonry base.

**Roof edge:** Thin continuous cap with a darker upper infill zone.

**Materials:** Light concrete; warm masonry infill; charcoal metal

**Procedural variation:** Vary frame width, brick tone and opaque bay placement; shade depth follows the exposure and clearance budget.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 38. Madagascar and western Indian Ocean (`indian_ocean_africa`)

**Written theme:** Malagasy highland brick houses; coastal timber traditions; Creole veranda and contemporary concrete housing.

**Detail direction:** Steep local roof variants, timber galleries and cyclone-conscious detailing.

### A. Highland brick rhythm

Stable proposal ID: `indian_ocean_africa-a` · Punched masonry bays

Suggested fit: 2–8 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Upright paired windows align between broad brick piers over a sturdy base. Selected timber-toned headers add regional contrast without stretching a small house silhouette into a large block.

**Base and entry:** A recessed masonry-framed entry.

**Roof edge:** Shallow cornice; steep roof variants require an existing compatible roof.

**Materials:** Warm red brick; pale lintels; dark timber accents

**Procedural variation:** Vary brick tone, paired-bay grouping and timber share; use highland locality selection.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Creole veranda block

Stable proposal ID: `indian_ocean_africa-b` · Shaded horizontal groups

Suggested fit: 2–7 storeys; 3.2–4.5 m bays; groups of 2–4 bays.

**Composition:** Short shaded opening groups sit behind a clear post rhythm and continuous rain headers. Opaque end sections and lower panels keep the long volume visually grounded.

**Base and entry:** Sheltered existing entrance with a restrained coloured surround.

**Roof edge:** Broad fascia within the current roof envelope.

**Materials:** Muted painted boards or render; pale posts; dark screens

**Procedural variation:** Vary post grouping, paint family and louvre share by island; no claimed cyclone performance.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Island concrete shade grid

Stable proposal ID: `indian_ocean_africa-c` · Screen and solid-wall rhythm

Suggested fit: 3–14 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Large framed bays alternate smaller glazing groups and solid screened-looking panels. The public face receives stronger shade treatment while the service side remains more enclosed.

**Base and entry:** Shaded lobby group beneath one substantial header.

**Roof edge:** Clean flat coping and upper rain band.

**Materials:** Pale concrete; warm render; neutral metal shade panels

**Procedural variation:** Vary screen cadence, infill tone and solid corners; storm-resistant detailing requires separate validated design.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 39. Arabian Peninsula and Gulf (`arid_warm`)

**Written theme:** Courtyard and wind-tower traditions; Yemeni tower houses; contemporary villas and urban blocks.

**Detail direction:** Screened openings, shaded courts and locally evidenced tower/roof forms.

### A. Gulf screened masonry block

Stable proposal ID: `arid_warm-a` · Screen and solid-wall rhythm

Suggested fit: 3–16 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Substantial wall frames contain compact grouped windows and screened vertical strips. Broad opaque corners and restrained horizontal bands keep the shell shaded and composed.

**Base and entry:** Deep-looking rectangular entrance surround on the known frontage.

**Roof edge:** Plain flat cap; no automatically generated wind towers.

**Materials:** Pale sand render; stone-coloured base; bronze screens

**Procedural variation:** Vary screen spacing, reveal depth and pale mineral tone through local variants; avoid unsourced decorative motifs.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Highland tower-house rhythm

Stable proposal ID: `arid_warm-b` · Punched masonry bays

Suggested fit: 3–12 storeys; 2.6–3.6 m bays; groups of 2–5 bays.

**Composition:** Narrow upright windows and closely spaced masonry piers create a vertical rhythm within the measured rectangle. Simple contrasting surrounds provide detail without copying a historic tower or adding height.

**Base and entry:** One stronger rectangular entry frame in a heavy base.

**Roof edge:** Restrained upper band beneath the source roof.

**Materials:** Warm earth or stone tones; pale bands; dark frames

**Procedural variation:** Vary band spacing, window pairs and mineral palette; restrict this interpretation to compatible highland/local contexts.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Gulf contemporary shade frame

Stable proposal ID: `arid_warm-c` · Large opaque frames

Suggested fit: 4–24 storeys; 3.8–5.2 m bays; groups of 2–3 bays.

**Composition:** Broad opaque frames contain short glazed groups and deep-looking spandrels. One solid circulation strip and alternating shade-panel bays replace the anonymous curtain-wall grid.

**Base and entry:** A clearly shaded glazed lobby group within the base.

**Roof edge:** Thin straight cap with darker top-storey infill.

**Materials:** Pale mineral panels; dark glazing; muted bronze infill

**Procedural variation:** Vary frame depth, opaque bay ratio and bronze accents; no invented tower crown or rooftop volume.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 40. Levant and eastern Mediterranean (`levant`)

**Written theme:** Stone courtyard houses; arcaded urban fronts; modern apartment and suburban buildings.

**Detail direction:** Limestone-like palettes, balconies and deep window reveals.

### A. Limestone urban block

Stable proposal ID: `levant-a` · Punched masonry bays

Suggested fit: 3–12 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Upright paired windows sit between substantial piers and above a strong base course. Deep-looking reveals and restrained sill bands give the rectangular volume a solid urban character.

**Base and entry:** A broad stone-coloured surround marks the existing entrance.

**Roof edge:** Simple cornice below a flat coping.

**Materials:** Warm limestone-coloured panels; pale render; dark metal

**Procedural variation:** Vary stone/render balance, pair spacing and lintel depth through local palettes.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Arcaded-front interpretation

Stable proposal ID: `levant-b` · Lower pier and upper-bay rhythm

Suggested fit: 2–9 storeys; 3.2–4.5 m bays; groups of 3–4 bays.

**Composition:** A lower pier rhythm supports paired upper openings, with selected segmental heads as shallow facade treatments. Keep the geometry closed unless an actual arcade is supported by the building plan.

**Base and entry:** One stronger shaded entry bay.

**Roof edge:** Restrained horizontal cornice and flat cap.

**Materials:** Pale stone tones; warm render; dark timber accents

**Procedural variation:** Vary head shape, pier spacing and three-to-four-bay groups; no inferred passage or internal courtyard.

**Supported upgrade:** Where the ground-floor envelope and access support it: a real sheltered colonnade. Otherwise the lower pier rhythm stays closed; an arch mask is not a traversable opening.

**Authoring controls:** target glazing 28%–46%; reveal depth 0.14–0.3 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Shaded apartment frame

Stable proposal ID: `levant-c` · Shaded horizontal groups

Suggested fit: 3–18 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Short loggia-proportioned window groups alternate with solid piers and opaque lower panels. A distinct stair strip and quieter side walls add variety without unsupported balcony projections.

**Base and entry:** Recessed lobby at the actual entry location.

**Roof edge:** Continuous cap over a solid upper shade band.

**Materials:** Cream render; pale concrete bands; muted shutters

**Procedural variation:** Vary grouped bay length, shutter share and stone accents; real balcony geometry remains conditional.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 41. Anatolia and Caucasus (`anatolia_caucasus`)

**Written theme:** Timber Ottoman houses; Caucasian stone and balcony houses; modern apartment neighbourhoods.

**Detail direction:** Projecting upper bays, shaded galleries and regional masonry details.

### A. Timber-over-masonry block

Stable proposal ID: `anatolia_caucasus-a` · Post and boarded-panel rhythm

Suggested fit: 2–8 storeys; 3–4.3 m bays; groups of 2–4 bays.

**Composition:** A solid lower storey supports grouped upper windows framed by strong posts and headers. Upper-bay emphasis is created in-plane; actual projecting bays need supported geometry.

**Base and entry:** Sheltered masonry-framed entrance.

**Roof edge:** Strong timber-toned fascia beneath the retained roof.

**Materials:** Pale render; dark timber-toned upper panels; stone-like base

**Procedural variation:** Vary upper panel widths, paired/triple windows and timber share through local options.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Caucasian stone gallery

Stable proposal ID: `anatolia_caucasus-b` · Shaded horizontal groups

Suggested fit: 2–10 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Broad stone-coloured piers frame short groups of shaded openings and solid lower panels. The gallery rhythm alternates with substantial end sections to suit a large rectangle.

**Base and entry:** One deep-looking stone entrance surround.

**Roof edge:** Plain cornice and flat coping.

**Materials:** Warm stone tones; pale render; muted metal

**Procedural variation:** Vary stone/render balance, group length and trim tone; ornamental balcony patterns need locality evidence.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Anatolian contemporary block

Stable proposal ID: `anatolia_caucasus-c` · Large opaque frames

Suggested fit: 3–20 storeys; 3.5–5 m bays; groups of 2–3 bays.

**Composition:** Regular large frame bays enclose paired glazing and opaque spandrels. A darker circulation strip and selected shaded groups give the urban slab depth and hierarchy.

**Base and entry:** Glazed lobby group in a durable darker base.

**Roof edge:** Thin cap and quieter top-floor infill.

**Materials:** Light render; concrete-coloured bands; warm brick accents

**Procedural variation:** Vary window grouping, accent-panel location and solid corner width; avoid arbitrary floor offsets.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 42. Iranian plateau and Afghan uplands (`iran_plateau`)

**Written theme:** Courtyard and earthen traditions; Caspian timber houses; brick/concrete urban apartments.

**Detail direction:** Recessed courts, local brick patterns and evidenced windcatchers.

### A. Plateau brick-reveal block

Stable proposal ID: `iran_plateau-a` · Punched masonry bays

Suggested fit: 2–10 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Compact upright window groups sit inside broad brick surrounds with deep-looking reveals. Restrained geometric brick-colour bands organise the long front without inventing courtyards or windcatchers.

**Base and entry:** A broad shaded rectangular entrance frame.

**Roof edge:** Plain coping with one narrow upper brick band.

**Materials:** Warm buff or red brick; sand render; dark frames

**Procedural variation:** Vary brick tone, paired-bay intervals and surround depth; complex masonry patterns remain optional local detail.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Caspian timber rain-front

Stable proposal ID: `iran_plateau-b` · Post and boarded-panel rhythm

Suggested fit: 2–7 storeys; 3.2–4.5 m bays; groups of 2–4 bays.

**Composition:** Grouped windows sit beneath continuous rain headers, separated by boarded upper panels and strong posts. The wet-region interpretation stays visually distinct from the solid plateau masonry option.

**Base and entry:** Sheltered timber-toned entry surround.

**Roof edge:** Broad fascia within the existing roof envelope.

**Materials:** Muted timber panels; pale render; dark weather base

**Procedural variation:** Vary board orientation, post groups and timber share; select only for compatible Caspian/local contexts.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Modern brick shade frame

Stable proposal ID: `iran_plateau-c` · Screen and solid-wall rhythm

Suggested fit: 3–18 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Large frame bays alternate paired glazing, solid brick panels and sparse vertical screens. An enclosed circulation strip establishes a clear composition without a glass-covered shell.

**Base and entry:** Deep-looking lobby recess under a robust header.

**Roof edge:** Thin straight coping with a darker upper infill zone.

**Materials:** Pale concrete; warm brick infill; bronze shade panels

**Procedural variation:** Vary screen cadence, brick share and frame depth; keep ornament abstract and restrained.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 43. Mesopotamian plains (`mesopotamia`)

**Written theme:** Courtyard brick houses; shanashil timber-front traditions; contemporary masonry and concrete blocks.

**Detail direction:** Screened projecting bays, recessed entries and shaded passage fronts.

### A. Brick courtyard-language block

Stable proposal ID: `mesopotamia-a` · Deep punched wall planes

Suggested fit: 2–10 storeys; 2.8–4 m bays; groups of 2–3 bays.

**Composition:** Broad masonry planes contain compact window pairs and occasional wider shaded groups. A stronger entry surround and restrained horizontal courses give order without carving an internal court.

**Base and entry:** Deep rectangular entrance within the existing wall line.

**Roof edge:** Plain flat cap and a narrow brick-colour upper band.

**Materials:** Warm buff brick; sand render; dark recessed frames

**Procedural variation:** Vary brick tone, reveal depth and grouped openings; retain a high opaque-wall proportion.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Screened upper-front block

Stable proposal ID: `mesopotamia-b` · Screen and solid-wall rhythm

Suggested fit: 2–9 storeys; 3–4.3 m bays; groups of 2–4 bays.

**Composition:** Larger upper window groups are framed by timber-toned screen panels over a more solid base. This interprets the written shanashil direction in-plane; projecting upper volumes need evidence.

**Base and entry:** One recessed entry below a solid screened-looking upper bay.

**Roof edge:** Strong horizontal header beneath the flat cap.

**Materials:** Warm brick base; dark timber-toned screens; pale infill

**Procedural variation:** Vary screen coverage, panel grouping and timber tone; no automatic intricate lattice or historic attribution.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. River-plain modern frame

Stable proposal ID: `mesopotamia-c` · Large opaque frames

Suggested fit: 3–18 storeys; 3.6–5 m bays; groups of 2–3 bays.

**Composition:** Broad piers and spandrels organise short glazing groups and solid infill. One shaded vertical circulation zone and simpler service elevations break the generic all-window pattern.

**Base and entry:** Shaded lobby group in a durable darker base.

**Roof edge:** Straight coping with an opaque upper band.

**Materials:** Pale render; concrete-coloured bands; warm masonry panels

**Procedural variation:** Vary solid/clear bay ratios, warm infill tone and frame depth; avoid unsupported roof additions.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 44. Central Asian oasis towns (`central_asia_oases`)

**Written theme:** Earthen courtyard houses; brick merchant streets; Soviet-era and contemporary apartment stock.

**Detail direction:** Courtyard orientation, restrained brick patterns and local timber galleries.

### A. Oasis merchant-brick block

Stable proposal ID: `central_asia_oases-a` · Punched masonry bays

Suggested fit: 2–9 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Upright paired windows sit between substantial brick piers and narrow horizontal courses. Deep-looking surrounds supply detail without copying ceremonial tilework or monumental portals.

**Base and entry:** A shaded rectangular entrance frame on the known frontage.

**Roof edge:** Plain cornice and flat coping.

**Materials:** Buff brick; sand render; dark timber accents

**Procedural variation:** Vary brick tone, bay grouping and restrained brick-colour patterns; no invented courtyard.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Timber-gallery urban front

Stable proposal ID: `central_asia_oases-b` · Shaded horizontal groups

Suggested fit: 2–8 storeys; 3.2–4.5 m bays; groups of 2–4 bays.

**Composition:** Short shaded window groups alternate with posts and broad solid sections. Opaque lower panels and a common base translate gallery proportions to a larger multi-purpose shell.

**Base and entry:** Sheltered entry within the existing facade plane.

**Roof edge:** Strong header beneath the retained roof edge.

**Materials:** Pale render; warm timber-toned headers; masonry base

**Procedural variation:** Vary group length, timber share and screen-like infill; select locality-compatible details.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Oasis contemporary panel block

Stable proposal ID: `central_asia_oases-c` · Enclosed modular fields

Suggested fit: 4–20 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Regular window pairs are grouped into larger vertical panel fields with enclosed stair strips. Selected shaded bays and warm infill distinguish the dry-climate version from an undifferentiated panel slab.

**Base and entry:** Recessed lobby group in a durable masonry base.

**Roof edge:** Flush cap with a darker upper panel zone.

**Materials:** Pale precast; warm brick infill; muted metal

**Procedural variation:** Vary field width, brick share and shade-panel cadence; keep floor levels continuous.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 45. Central Asian steppe and mountain towns (`central_asia_steppe`)

**Written theme:** Timber and masonry townhouses; Soviet-era apartment blocks; contemporary low-rise and urban infill.

**Detail direction:** Wind-sheltered entries and permanent-building treatment of settlement edges.

### A. Sheltered masonry block

Stable proposal ID: `central_asia_steppe-a` · Deep punched wall planes

Suggested fit: 2–10 storeys; 3–4.2 m bays; groups of 2–3 bays.

**Composition:** Compact paired openings sit in broad wall planes with solid corners and a stronger circulation bay. The enclosed composition adapts permanent town-building themes without borrowing temporary dwelling forms.

**Base and entry:** Recessed wind-sheltered entry surround at the measured level.

**Roof edge:** Plain coping and a substantial upper fascia.

**Materials:** Warm brick or pale mineral render; dark base; muted frames

**Procedural variation:** Vary brick/render balance, pair spacing and reveal depth through local climate choices.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Steppe panel-estate renewal

Stable proposal ID: `central_asia_steppe-b` · Enclosed modular fields

Suggested fit: 4–24 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Window pairs repeat within larger panel fields, interrupted by enclosed stair strips and solid end walls. Contrasting spandrels give hierarchy while retaining the measured large slab.

**Base and entry:** A clearly framed sheltered lobby group.

**Roof edge:** Flush dark cap and quieter top-storey panels.

**Materials:** Pale precast; muted earth or blue-grey infill; charcoal joints

**Procedural variation:** Vary field lengths, colour-block position and panel seams; no random per-window decoration.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Mountain-town modern frame

Stable proposal ID: `central_asia_steppe-c` · Large opaque frames

Suggested fit: 3–14 storeys; 3.5–4.8 m bays; groups of 2–3 bays.

**Composition:** Broad frames hold grouped windows and opaque infill, with one strong vertical service zone. Limited timber-toned panels soften the rectangle without imposing chalet or nomadic motifs.

**Base and entry:** Compact sheltered entrance in a durable base.

**Roof edge:** Straight cap beneath the existing roof profile.

**Materials:** Light concrete; warm masonry infill; restrained timber accents

**Procedural variation:** Vary two-to-three-window groups, masonry share and accent-stack width; keep locality selection explicit.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 46. Indus, Gangetic plains and western India (`indus_gangetic`)

**Written theme:** Haveli and pol courtyard houses; brick bazaar fronts; modern concrete and mixed-use neighbourhoods.

**Detail direction:** Jali-inspired screens, shaded balconies and local timber/brick detail.

### A. Haveli-language shaded block

Stable proposal ID: `indus_gangetic-a` · Screen and solid-wall rhythm

Suggested fit: 2–10 storeys; 3–4.3 m bays; groups of 2–4 bays.

**Composition:** Broad piers contain compact grouped windows and selected screen-like panels. A shaded entrance and restrained horizontal bands translate courtyard-house proportions without inventing courts or ornate ceremonial forms.

**Base and entry:** Deep-looking rectangular entry surround.

**Roof edge:** Plain flat coping and one narrow upper band.

**Materials:** Warm render; brick or stone-coloured base; neutral screens

**Procedural variation:** Vary screen density, reveal depth and masonry tone through locality options; detailed jali geometry is a later upgrade.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Bazaar brick rhythm

Stable proposal ID: `indus_gangetic-b` · Grouped street fronts

Suggested fit: 2–9 storeys; 2.8–4 m bays; groups of 3–5 bays.

**Composition:** Divide the long front into broad brick sections with upright paired windows and a unified base. Lower bays can accept known public glazing while side elevations remain more solid.

**Base and entry:** One actual entrance anchors a wider section; no invented shop tenancy.

**Roof edge:** Shallow cornice below a flat coping.

**Materials:** Warm brick; pale lintels; muted timber accents

**Procedural variation:** Vary section width, brick shade and lintel grouping; keep the real access pattern.

**Supported upgrade:** Where envelope evidence supports it: stepped crown sections or roof-form variation. Facade sections never become invented parcels, entrances or separate buildings.

**Authoring controls:** target glazing 30%–46%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Plains modern shade frame

Stable proposal ID: `indus_gangetic-c` · Shaded horizontal groups

Suggested fit: 3–20 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Short horizontal groups of shaded glazing alternate with solid piers and opaque spandrels. A clearly enclosed stair strip prevents the whole slab becoming a balcony texture.

**Base and entry:** Shaded lobby group beneath a substantial header.

**Roof edge:** Thin cap with an opaque upper shade band.

**Materials:** Pale concrete; warm render; muted shade panels

**Procedural variation:** Vary group length, screen share and accent zones; actual balconies require geometry and clearance support.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 47. Peninsular India and Deccan (`india_peninsular`)

**Written theme:** Deccan courtyard houses; Kerala/Malabar timber and tile traditions; modernist and contemporary concrete housing.

**Detail direction:** Deep verandas, rain eaves and dry/wet locality distinction.

### A. Deccan masonry shade block

Stable proposal ID: `india_peninsular-a` · Deep punched wall planes

Suggested fit: 2–10 storeys; 3–4.2 m bays; groups of 2–3 bays.

**Composition:** Broad solid piers and deep-looking grouped windows give the rectangular shell a shaded, grounded character. Selected screened bays provide variation without fabricating a courtyard.

**Base and entry:** A thick rectangular entry surround at the existing threshold.

**Roof edge:** Plain coping and restrained upper band.

**Materials:** Warm stone-like base; pale or ochre render; dark frames

**Procedural variation:** Vary mineral tones, reveal depth and paired-bay frequency; use a dry/locality variant where appropriate.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Malabar rain-gallery block

Stable proposal ID: `india_peninsular-b` · Shaded horizontal groups

Suggested fit: 2–8 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Repeated short window groups sit beneath strong rain headers with substantial vertical posts. The baseline remains enclosed; covered galleries and deep eaves need supported geometry.

**Base and entry:** Sheltered timber-toned entrance frame.

**Roof edge:** Broad fascia below the current roof; no automatic tile roof.

**Materials:** Warm timber-toned headers; pale render; dark base

**Procedural variation:** Vary group length, timber share and louvred-panel coverage; select wet/coastal contexts explicitly.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Peninsular modern screen grid

Stable proposal ID: `india_peninsular-c` · Screen and solid-wall rhythm

Suggested fit: 3–20 storeys; 3.6–5 m bays; groups of 2–4 bays.

**Composition:** Large opaque frames alternate grouped glazing, solid panels and shaded circulation strips. Public and service elevations receive different window densities, giving the block realistic organisation.

**Base and entry:** Broad shaded lobby group within a durable base.

**Roof edge:** Clean flat cap and a substantial top header.

**Materials:** Light concrete; warm infill; neutral screen panels

**Procedural variation:** Vary screen module size, frame depth and infill colour; keep dry and wet material/detail choices separate.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 48. Bengal and northeast South Asia (`bengal_delta`)

**Written theme:** Bengal courtyard and curved-roof traditions; raised timber/bamboo houses; brick and concrete urban stock.

**Detail direction:** Monsoon eaves, shaded openings and mapped floor-height constraints.

### A. Brick rain-reveal block

Stable proposal ID: `bengal_delta-a` · Punched masonry bays

Suggested fit: 2–10 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Upright window pairs sit between broad brick piers, with pronounced-looking rain headers and a durable base. Horizontal courses organise the front without adding unsupported curved roofs.

**Base and entry:** Recessed entry beneath a stronger rain header.

**Roof edge:** Plain cornice and flat coping.

**Materials:** Warm red brick; pale lintels; dark frames

**Procedural variation:** Vary brick tone, paired-bay grouping and header depth; preserve mapped floor heights.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Timber-screen urban bar

Stable proposal ID: `bengal_delta-b` · Post and boarded-panel rhythm

Suggested fit: 2–7 storeys; 3–4.4 m bays; groups of 2–4 bays.

**Composition:** Boarded upper sections alternate grouped windows and louvred-looking opaque panels. Strong posts and rain bands reinterpret the timber direction while retaining an enclosed rectangular building.

**Base and entry:** Sheltered entry frame at the source ground level.

**Roof edge:** Broad fascia beneath the existing roof.

**Materials:** Muted timber panels; pale render; dark weather base

**Procedural variation:** Vary board orientation, louvre share and section widths; no presumed stilts or bamboo material.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Delta modern shaded frame

Stable proposal ID: `bengal_delta-c` · Screen and solid-wall rhythm

Suggested fit: 3–20 storeys; 3.5–5 m bays; groups of 2–4 bays.

**Composition:** Broad frame bays contain short glazing groups and solid brick panels, with screened circulation strips. Strong horizontal headers add rain protection character and break the generic window grid.

**Base and entry:** Shaded glazed lobby group in a robust base.

**Roof edge:** Flat cap and pronounced upper rain band.

**Materials:** Pale concrete; brick infill; neutral shade panels

**Procedural variation:** Vary brick share, screen cadence and paired/triple glazing; actual ventilation and drainage need later detailing.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 49. Himalayan foothills and valleys (`himalayan`)

**Written theme:** Newar brick and timber houses; Bhutanese timber/masonry traditions; contemporary hill-town buildings.

**Detail direction:** Timber bands, deep eaves and slope-aware fronts within source geometry.

### A. Brick-and-timber urban rhythm

Stable proposal ID: `himalayan-a` · Punched masonry bays

Suggested fit: 2–9 storeys; 2.8–3.8 m bays; groups of 2–5 bays.

**Composition:** Upright grouped openings sit between brick piers and continuous timber-toned bands. The proportions adapt the written Newar direction without copying decorative or ceremonial window patterns.

**Base and entry:** Recessed entrance within a strong simple timber-coloured frame.

**Roof edge:** Plain fascia beneath the supported roof profile.

**Materials:** Warm brick; dark timber-toned lintels; pale mineral base

**Procedural variation:** Vary brick tone, grouped bay width and band thickness; keep local detail selection explicit.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Highland timber-panel block

Stable proposal ID: `himalayan-b` · Post and boarded-panel rhythm

Suggested fit: 2–7 storeys; 3–4.2 m bays; groups of 2–4 bays.

**Composition:** Larger upper window groups sit within strong posts and horizontal headers over a solid base. Broad coloured sections provide scale without invented roof tiers or decorative motifs.

**Base and entry:** Sheltered entry on the existing terrain connection.

**Roof edge:** Strong fascia; deep eaves need source and clearance support.

**Materials:** Pale render; dark timber-toned upper panels; stone-like base

**Procedural variation:** Vary upper-panel share, window pairing and restrained paint accents by locality.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Hill-town modern frame

Stable proposal ID: `himalayan-c` · Large opaque frames

Suggested fit: 3–14 storeys; 3.4–4.8 m bays; groups of 2–3 bays.

**Composition:** Clear floor bands and piers frame paired glazing and solid infill, with one enclosed stair strip. Any terrain stepping follows actual source geometry rather than a regional assumption.

**Base and entry:** A durable recessed lobby at the measured threshold.

**Roof edge:** Thin cap and quieter upper infill.

**Materials:** Light concrete; warm brick or render; charcoal frames

**Procedural variation:** Vary masonry share, two-to-three-window groups and solid-end width; do not lift or terrace the footprint.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 50. Sri Lanka and Maldives (`sri_lanka_maldives`)

**Written theme:** Courtyard and veranda houses; tropical modernism; island masonry and contemporary urban housing.

**Detail direction:** Shaded colonnades, ventilation and tile/metal alternatives.

### A. Courtyard-language veranda block

Stable proposal ID: `sri_lanka_maldives-a` · Shaded horizontal groups

Suggested fit: 2–8 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Short shaded window groups and solid end bays create a calm veranda rhythm. Opaque lower panels provide depth without pretending to add accessible galleries or internal courtyards.

**Base and entry:** Sheltered existing entrance beneath a broad header.

**Roof edge:** Strong fascia below the source roof; tile and metal choices remain locality-led.

**Materials:** Pale render; warm timber-toned headers; dark base

**Procedural variation:** Vary post spacing, group length and timber share within island or mainland variants.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Tropical modern shade frame

Stable proposal ID: `sri_lanka_maldives-b` · Screen and solid-wall rhythm

Suggested fit: 3–16 storeys; 3.6–5 m bays; groups of 2–4 bays.

**Composition:** Broad opaque frames combine grouped glazing, screened vertical strips and solid spandrels. A quieter service face and one shaded lobby group give the rectangle an organised modern identity.

**Base and entry:** Deep-looking shaded entrance within the building envelope.

**Roof edge:** Thin cap with a substantial upper shade band.

**Materials:** Light concrete; pale infill; neutral screens

**Procedural variation:** Vary frame depth, screen density and solid corner treatment; keep wet/dry locality variants distinct.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Island masonry urban block

Stable proposal ID: `sri_lanka_maldives-c` · Deep punched wall planes

Suggested fit: 2–12 storeys; 3–4.3 m bays; groups of 2–3 bays.

**Composition:** Compact paired windows punctuate broad light wall planes, with restrained rain headers and selected screened bays. The composition remains practical for accommodation, offices or community use.

**Base and entry:** One clearly framed shaded entrance at the existing level.

**Roof edge:** Plain flat coping, with no fabricated roof terrace.

**Materials:** Pale mineral render; muted stone-coloured base; dark frames

**Procedural variation:** Vary reveal depth, screen share and neutral palette through island-specific options.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 51. Japan and Ryukyu islands (`jp_temperate`)

**Written theme:** Machiya and minka traditions; postwar compact houses; contemporary narrow urban infill.

**Detail direction:** Layered eaves, screened fronts and local tile/metal roof distinctions.

### A. Machiya-rhythm urban screen

Stable proposal ID: `jp_temperate-a` · Screen and solid-wall rhythm

Suggested fit: 2–8 storeys; 2.6–3.8 m bays; groups of 2–4 bays.

**Composition:** Narrow vertical screen groups alternate with paired windows inside broader facade sections. Horizontal weather lines unify the long rectangle without imposing traditional roof shapes on an ordinary urban shell.

**Base and entry:** A simple sheltered entry frame in one wider bay.

**Roof edge:** Thin dark cap with a restrained upper fascia.

**Materials:** Muted render; dark timber-toned slats; grey base

**Procedural variation:** Vary slat spacing, section width and timber share; no applied sacred or ceremonial motifs.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Postwar compact-bay block

Stable proposal ID: `jp_temperate-b` · Enclosed modular fields

Suggested fit: 3–16 storeys; 2.8–4 m bays; groups of 2–4 bays.

**Composition:** Compact paired windows form larger vertical fields, interrupted by opaque circulation strips. Selected dark inset-looking panels and regular seams give ordinary repeated floors a more legible organisation.

**Base and entry:** A clearly framed sheltered lobby group.

**Roof edge:** Flush cap and quieter top-floor panels.

**Materials:** Warm off-white panels; muted grey infill; dark frames

**Procedural variation:** Vary panel-group width, window pairing and one accent stack; avoid random window positions.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Contemporary layered frame

Stable proposal ID: `jp_temperate-c` · Large opaque frames

Suggested fit: 3–20 storeys; 3.4–4.8 m bays; groups of 2–3 bays.

**Composition:** Larger opaque frames contain smaller glazing groups and stepped-looking infill depths. Solid corner panels and a distinct entry stack create a contemporary composition within the existing box.

**Base and entry:** Recessed glazed lobby with a narrow rain header.

**Roof edge:** Slim cap with darker upper-storey cladding.

**Materials:** Pale mineral panels; charcoal metal; limited warm timber

**Procedural variation:** Vary frame nesting, paired/triple groups and timber accent placement; real setbacks require envelope support.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 52. Northern and inland China (`china_north`)

**Written theme:** Siheyuan courtyard houses; brick hutong fronts; danwei and contemporary apartment stock.

**Detail direction:** Courtyard gates, brick bays and cold-region enclosure.

### A. Grey-brick urban rhythm

Stable proposal ID: `china_north-a` · Punched masonry bays

Suggested fit: 2–9 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Compact upright window groups sit between broad masonry piers and a sturdy base. Restrained horizontal courses translate the hutong/brick direction without inventing gates, courts or traditional roofs.

**Base and entry:** A deep-looking rectangular entrance surround.

**Roof edge:** Plain brick-coloured coping and narrow upper band.

**Materials:** Grey or muted buff brick; pale lintels; dark timber accents

**Procedural variation:** Vary brick tone, group width and reveal depth through local variants.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Danwei-era slab reinterpretation

Stable proposal ID: `china_north-b` · Enclosed modular fields

Suggested fit: 4–20 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Repeated window pairs sit in larger panel fields with clearly enclosed stair strips. Darker spandrels and occasional solid bays break repetition while preserving the ordinary measured slab.

**Base and entry:** Sheltered lobby group in a durable masonry base.

**Roof edge:** Flush cap with quieter upper panels.

**Materials:** Pale concrete; warm brick infill; muted grey frames

**Procedural variation:** Vary field width, brick share and circulation-strip emphasis; no inferred building age is stored as fact.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Northern contemporary insulated frame

Stable proposal ID: `china_north-c` · Large opaque frames

Suggested fit: 4–24 storeys; 3.6–5 m bays; groups of 2–3 bays.

**Composition:** Broad opaque frames enclose grouped glazing and substantial insulated-looking spandrels. Solid end sections and one darker service strip keep the tall rectangle from becoming a curtain-wall texture.

**Base and entry:** Compact sheltered lobby within the existing base.

**Roof edge:** Thin cap with an inset-looking upper panel zone.

**Materials:** Pale mineral cladding; charcoal panels; muted bronze accents

**Procedural variation:** Vary paired/triple glazing, frame width and accent-strip position; keep cold-region enclosure visually coherent.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 53. Southern China, Taiwan and coastal cities (`china_south`)

**Written theme:** Jiangnan courtyard houses; Lingnan qilou and Taiwanese shophouses; modern high-density and village stock.

**Detail direction:** Arcaded fronts, rain eaves and separate hill/coast urban forms.

### A. Jiangnan masonry urban front

Stable proposal ID: `china_south-a` · Punched masonry bays

Suggested fit: 2–8 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Upright grouped windows and broad solid piers create a calm shaded front, with dark horizontal headers. Courtyard traditions inform proportions only where the footprint remains a solid rectangle.

**Base and entry:** A restrained deep-looking entry frame.

**Roof edge:** Thin dark coping beneath the retained roof profile.

**Materials:** Pale render; grey masonry base; dark timber-toned frames

**Procedural variation:** Vary render/grey-brick balance, paired-bay width and timber share; use locality-compatible settings.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Qilou street-frame block

Stable proposal ID: `china_south-b` · Lower pier and upper-bay rhythm

Suggested fit: 3–10 storeys; 3.2–4.5 m bays; groups of 3–4 bays.

**Composition:** A stronger lower pier sequence supports narrower upper window groups and continuous horizontal bands. The baseline is a closed arcade-like facade; real covered circulation needs a supported ground-floor setback.

**Base and entry:** Existing entrance fits within one wider lower bay.

**Roof edge:** Simple cornice and flat cap.

**Materials:** Cream render; pale concrete piers; muted coloured infill

**Procedural variation:** Vary pier spacing, upper bay grouping and restrained colour sections; avoid invented shop tenancy.

**Supported upgrade:** Where the ground-floor envelope and access support it: a real sheltered colonnade. Otherwise the lower pier rhythm stays closed; an arch mask is not a traversable opening.

**Authoring controls:** target glazing 28%–46%; reveal depth 0.14–0.3 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Coastal high-density shade frame

Stable proposal ID: `china_south-c` · Shaded horizontal groups

Suggested fit: 4–24 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Short shaded opening groups, solid spandrels and enclosed circulation strips divide the large slab. Selected screen-like panels create depth while service elevations remain quieter and more opaque.

**Base and entry:** Shaded glazed lobby group within a durable base.

**Roof edge:** Straight cap and a darker upper service band.

**Materials:** Pale concrete; light infill; dark screens

**Procedural variation:** Vary group length, screen share and solid corner treatment; no unsourced exterior equipment or balcony cages.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 54. Korean peninsula (`korea`)

**Written theme:** Hanok courtyard traditions; brick urban houses; modern apartment and mixed-use blocks.

**Detail direction:** Courtyard-facing eaves, timber accents and ordinary contemporary facades.

### A. Timber-accent masonry block

Stable proposal ID: `korea-a` · Post and boarded-panel rhythm

Suggested fit: 2–8 storeys; 3–4.2 m bays; groups of 2–4 bays.

**Composition:** Broad upper panels frame grouped windows beneath strong horizontal headers. Restrained timber accents reinterpret the written courtyard tradition at urban scale without attaching traditional roof tiers to the box.

**Base and entry:** Simple sheltered entrance surround at the actual threshold.

**Roof edge:** Dark plain fascia under the existing roof.

**Materials:** Pale render; warm timber-toned panels; dark masonry base

**Procedural variation:** Vary timber share, paired-window groups and panel width; courtyard-facing eaves require a real courtyard.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Brick urban infill

Stable proposal ID: `korea-b` · Punched masonry bays

Suggested fit: 3–12 storeys; 2.8–4 m bays; groups of 2–5 bays.

**Composition:** Upright paired windows sit in broader brick sections, with a solid stair strip and restrained lintel bands. The base is sturdy and the upper floors remain calm.

**Base and entry:** A wide recessed brick-framed lobby bay.

**Roof edge:** Thin cornice and flat coping.

**Materials:** Warm red or dark brick; pale sills; charcoal frames

**Procedural variation:** Vary brick tone, section width and paired/triple windows; keep detail aligned with the floor grid.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Contemporary apartment frame

Stable proposal ID: `korea-c` · Enclosed modular fields

Suggested fit: 4–24 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Larger vertical panel fields organise compact window groups, opaque lower panels and enclosed circulation zones. Dark inset-looking sections provide depth without assuming accessible balconies.

**Base and entry:** Clearly glazed lobby group beneath a substantial header.

**Roof edge:** Flush cap with a simplified darker upper zone.

**Materials:** Warm white panels; pale grey spandrels; muted accent strips

**Procedural variation:** Vary field width, accent-stack location and glazing groups; avoid random façade graphics or invented towers.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 55. Tibetan plateau and high mountain settlements (`tibetan_plateau`)

**Written theme:** Stone and rammed-earth courtyard houses; timber-trimmed highland homes; contemporary masonry town buildings.

**Detail direction:** Deep reveals, local parapets and climate-specific compact openings.

### A. Highland stone-plane block

Stable proposal ID: `tibetan_plateau-a` · Deep punched wall planes

Suggested fit: 2–8 storeys; 2.8–4 m bays; groups of 2–3 bays.

**Composition:** Broad solid wall planes hold compact deeply inset paired windows, with heavier corners and a strong base. Mass is expressed through surfaces, not invented battered walls or ceremonial forms.

**Base and entry:** Thick rectangular entry surround within the source envelope.

**Roof edge:** Plain coping with a restrained dark upper band.

**Materials:** Warm stone-like panels; pale mineral render; dark frames

**Procedural variation:** Vary stone/render balance, reveal depth and pair spacing; actual earth construction is not assumed.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Timber-trimmed urban rhythm

Stable proposal ID: `tibetan_plateau-b` · Post and boarded-panel rhythm

Suggested fit: 2–7 storeys; 2.8–4 m bays; groups of 2–4 bays.

**Composition:** Upright windows form broad groups enclosed by simple timber-toned headers and posts. Keep trim geometric and restrained while giving the large rectangle a legible regional rhythm.

**Base and entry:** Sheltered timber-coloured frame around the existing entry.

**Roof edge:** Strong plain fascia beneath the current roof.

**Materials:** Pale render; dark timber-toned surrounds; warm masonry base

**Procedural variation:** Vary surround width, group size and muted palette; no automatic religious colours or decorative symbols.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Contemporary plateau masonry

Stable proposal ID: `tibetan_plateau-c` · Enclosed modular fields

Suggested fit: 3–14 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Compact glazing groups alternate with large opaque panels and an enclosed stair strip. Consistent joints and substantial spandrels produce a durable-looking modern block with limited exposed recesses.

**Base and entry:** Compact wind-sheltered lobby appearance at the existing floor level.

**Roof edge:** Flush cap and a dark upper panel band.

**Materials:** Pale mineral panels; warm stone-coloured base; charcoal frames

**Procedural variation:** Vary panel grouping, stone share and window density by use mode; retain the measured envelope.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 56. Malay Peninsula and equatorial trading towns (`tropical_humid`)

**Written theme:** Malay timber houses; Straits shophouses; tropical modern and contemporary urban housing.

**Detail direction:** Five-foot-way-inspired frontage, ventilated screens and rain eaves.

### A. Malay timber-screen block

Stable proposal ID: `tropical_humid-a` · Post and boarded-panel rhythm

Suggested fit: 2–7 storeys; 3–4.4 m bays; groups of 2–4 bays.

**Composition:** Broad boarded sections alternate grouped windows and louvred-looking panels beneath strong rain headers. The design scales timber proportions into an enclosed urban block without assuming raised floors.

**Base and entry:** Sheltered timber-toned entry frame.

**Roof edge:** Broad fascia beneath the source roof; no automatic pavilion roof.

**Materials:** Warm timber tones; pale infill; dark weather base

**Procedural variation:** Vary board direction, louvre share and section widths through local selections.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Straits street-front rhythm

Stable proposal ID: `tropical_humid-b` · Grouped street fronts

Suggested fit: 2–9 storeys; 2.8–4 m bays; groups of 3–5 bays.

**Composition:** Divide the long front into broad upright sections with paired upper windows and a strong lower pier rhythm. A shared cornice unifies the building while retaining distinct section proportions.

**Base and entry:** One actual entrance anchors a wider lower bay; open five-foot-way geometry requires support.

**Roof edge:** Shallow cornice under a flat cap.

**Materials:** Muted pastel render; pale trim; dark shutters

**Procedural variation:** Vary section widths, shutter share and pastel family; no invented shop boundaries or passages.

**Supported upgrade:** Where envelope evidence supports it: stepped crown sections or roof-form variation. Facade sections never become invented parcels, entrances or separate buildings.

**Authoring controls:** target glazing 30%–46%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Equatorial modern shade grid

Stable proposal ID: `tropical_humid-c` · Screen and solid-wall rhythm

Suggested fit: 3–22 storeys; 3.6–5 m bays; groups of 2–4 bays.

**Composition:** Large opaque frames contain short glazed groups, screened circulation strips and substantial spandrels. Different public and service faces replace the repeated all-window box.

**Base and entry:** A broad shaded lobby group below a robust rain header.

**Roof edge:** Clean flat cap with a strong upper shade line.

**Materials:** Pale concrete; neutral infill; warm or grey screens

**Procedural variation:** Vary screen cadence, frame depth and solid-end width; real porous screens are an optional detailed geometry pass.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 57. Mainland Southeast Asia (`mainland_southeast_asia`)

**Written theme:** Timber stilt-house traditions; trading-port shophouses; tube houses and modern concrete neighbourhoods.

**Detail direction:** Narrow frontage rhythms, shaded galleries and mapped raised floors.

### A. Timber rain-front bar

Stable proposal ID: `mainland_southeast_asia-a` · Post and boarded-panel rhythm

Suggested fit: 2–7 storeys; 3–4.3 m bays; groups of 2–4 bays.

**Composition:** Strong posts and horizontal rain headers organise paired window groups and opaque upper panels. The low rectangular shell gains timber character while floor elevation and roof silhouette stay source-led.

**Base and entry:** Sheltered entrance frame on the real frontage.

**Roof edge:** Broad fascia under the existing roof.

**Materials:** Muted timber boards; pale render; dark base

**Procedural variation:** Vary board direction, group lengths and muted paint; no automatically raised stilt floor.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Trading-port vertical fronts

Stable proposal ID: `mainland_southeast_asia-b` · Grouped street fronts

Suggested fit: 2–10 storeys; 2.6–3.8 m bays; groups of 3–5 bays.

**Composition:** Broad narrow-bay sections alternate paired windows and solid vertical strips. A common floor grid and restrained cornice keep the large block coherent rather than pretending it is many separate tube houses.

**Base and entry:** One wider actual entrance section; retain service access positions.

**Roof edge:** Thin cornice with varied band widths inside the source height.

**Materials:** Cream or muted pastel render; dark shutters; mineral base

**Procedural variation:** Vary section width, shutter share and restrained colour combinations by locality.

**Supported upgrade:** Where envelope evidence supports it: stepped crown sections or roof-form variation. Facade sections never become invented parcels, entrances or separate buildings.

**Authoring controls:** target glazing 30%–46%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Contemporary shaded urban frame

Stable proposal ID: `mainland_southeast_asia-c` · Shaded horizontal groups

Suggested fit: 3–20 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Short groups of shaded glazing alternate with broad piers and opaque lower panels. One enclosed circulation strip and a quieter service side give the rectangle a practical urban organisation.

**Base and entry:** Shaded lobby group beneath a continuous rain header.

**Roof edge:** Flat cap and a solid upper shade band.

**Materials:** Light concrete; warm infill; neutral screens

**Procedural variation:** Vary group lengths, screen share and accent-stack position; real loggia voids require support.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 58. Indonesia and Timor (`indonesian_archipelago`)

**Written theme:** Javanese courtyard and pavilion traditions; Sumatran and Sulawesi timber forms; contemporary kampung masonry.

**Detail direction:** Ventilated roof edges and distinctive roof silhouettes only with evidence.

### A. Pavilion-rhythm urban frame

Stable proposal ID: `indonesian_archipelago-a` · Shaded horizontal groups

Suggested fit: 2–8 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Broad posts and horizontal headers organise short shaded opening groups and solid end sections. The pavilion direction informs proportions, without adding unsupported roof tiers or open ground floors.

**Base and entry:** Sheltered existing entrance with a stronger timber-toned frame.

**Roof edge:** Broad fascia under the source roof.

**Materials:** Pale render; warm timber-toned posts; dark base

**Procedural variation:** Vary post spacing, group length and timber share through explicit local variants.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Archipelago timber-panel block

Stable proposal ID: `indonesian_archipelago-b` · Post and boarded-panel rhythm

Suggested fit: 1–6 storeys; 3–4.3 m bays; groups of 2–4 bays.

**Composition:** Large cladding panels alternate paired windows and screened-looking upper zones. Strong horizontal weather lines scale timber-building themes to a long enclosed multi-purpose volume.

**Base and entry:** A clearly sheltered-looking entrance frame at the existing level.

**Roof edge:** Simple deep-looking fascia; distinctive local roof systems remain separately supported.

**Materials:** Warm or muted painted boards; pale infill; masonry base

**Procedural variation:** Vary board direction, panel grouping and paint family; avoid mixing unrelated island traditions.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Kampung masonry modern block

Stable proposal ID: `indonesian_archipelago-c` · Large opaque frames

Suggested fit: 3–16 storeys; 3.4–4.8 m bays; groups of 2–3 bays.

**Composition:** Regular opaque frames hold grouped glazing and solid infill panels, with shaded circulation strips. Material zoning and a quieter service elevation add realism to the ordinary rectangular shell.

**Base and entry:** Shaded lobby group within a robust rendered base.

**Roof edge:** Clean flat cap with a pronounced rain header.

**Materials:** Pale concrete; warm brick or render; dark metal

**Procedural variation:** Vary brick/render balance, paired/triple openings and screen cadence; no inferred unfinished construction.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 59. Philippine archipelago (`philippines`)

**Written theme:** Bahay kubo and bahay na bato traditions; Art Deco town fronts; contemporary concrete and mixed-use buildings.

**Detail direction:** Shaded upper galleries, vent panels and local roof/eave systems.

### A. Masonry-base timber-screen block

Stable proposal ID: `philippines-a` · Post and boarded-panel rhythm

Suggested fit: 2–8 storeys; 3–4.3 m bays; groups of 2–4 bays.

**Composition:** A solid lower storey supports larger upper window groups, screened-looking infill and strong horizontal headers. The written bahay na bato direction becomes a coherent material hierarchy without a copied house silhouette.

**Base and entry:** Sheltered entry in the masonry base.

**Roof edge:** Broad fascia beneath the current roof.

**Materials:** Warm masonry base; muted timber-toned panels; pale trim

**Procedural variation:** Vary upper-panel share, window grouping and screen density; do not claim special shell or bamboo materials.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Town-front Deco block

Stable proposal ID: `philippines-b` · Interrupted horizontal glazing

Suggested fit: 3–12 storeys; 3.6–4.8 m bays; groups of 2–4 bays.

**Composition:** Horizontal grouped windows intersect a stronger vertical entrance strip, with shallow stepped surface bands. Solid corners and restrained geometric trim give a recognisable town-front composition.

**Base and entry:** Simple geometric entry surround at the actual door bay.

**Roof edge:** Two shallow crown bands beneath a straight flat cap.

**Materials:** Cream render; muted pastel bands; charcoal frames

**Procedural variation:** Vary band thickness, entrance offset and paired/triple glazing; no fabricated tower or extra storey.

**Supported upgrade:** Where the source supports it: inset ribbon bays or a stepped upper volume. Otherwise keep solid interruptions, deep-looking spandrels and a level crown.

**Authoring controls:** target glazing 36%–55%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Contemporary tropical infill

Stable proposal ID: `philippines-c` · Screen and solid-wall rhythm

Suggested fit: 3–20 storeys; 3.5–5 m bays; groups of 2–4 bays.

**Composition:** Broad frame bays alternate grouped windows, opaque spandrels and screen-like vertical strips. Rain headers and a more solid service side provide practical variety and depth.

**Base and entry:** Shaded glazed lobby group within the existing base.

**Roof edge:** Flat cap with a substantial upper weather band.

**Materials:** Light concrete; warm rendered panels; neutral screens

**Procedural variation:** Vary screen cadence, accent-panel placement and solid corners; storm and ventilation performance are not presumed.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 60. New Zealand and temperate southern Pacific (`nz_temperate`)

**Written theme:** Timber villas and bungalows; brick/render suburban houses; contemporary infill and locally evidenced Maori civic traditions.

**Detail direction:** Weatherboards, sheltered porches and metal/tile roof distinctions.

### A. Weatherboard urban block

Stable proposal ID: `nz_temperate-a` · Post and boarded-panel rhythm

Suggested fit: 2–7 storeys; 3–4.4 m bays; groups of 2–4 bays.

**Composition:** Broad boarded sections contain paired windows under strong horizontal headers. A durable lower storey and selected timber-toned entry panels translate villa/bungalow proportions into a larger urban shell.

**Base and entry:** Sheltered entrance frame at the measured threshold.

**Roof edge:** Plain substantial fascia under the existing roof; no automatic gables.

**Materials:** Muted weatherboard colours; pale trim; dark masonry base

**Procedural variation:** Vary board direction by section, muted paint and pair spacing; civic cultural detail requires local evidence.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Brick-and-render town block

Stable proposal ID: `nz_temperate-b` · Punched masonry bays

Suggested fit: 2–10 storeys; 3–4.2 m bays; groups of 2–5 bays.

**Composition:** Upright grouped windows alternate with broad brick piers and rendered spandrels. A heavier base, simple lintels and a restrained cornice give an ordinary rectangular block street presence.

**Base and entry:** Recessed lobby in one wider masonry bay.

**Roof edge:** Thin cornice and flat metal-looking cap.

**Materials:** Warm red or buff brick; cream render; charcoal frames

**Procedural variation:** Vary brick/render balance, two-to-three-window groups and base tone; keep details consistent across floors.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. New Zealand contemporary infill

Stable proposal ID: `nz_temperate-c` · Large opaque frames

Suggested fit: 3–18 storeys; 3.6–5 m bays; groups of 2–3 bays.

**Composition:** Broad opaque frames group windows into short sets, interrupted by solid circulation bays and darker upper infill. A single warm entry stack supplies identity without covering every wall in glazing.

**Base and entry:** Clear glazed lobby group with a narrow rain header.

**Roof edge:** Slim cap and visually recessed top-storey panels within the source shell.

**Materials:** Pale mineral panels; dark metal; limited warm timber

**Procedural variation:** Vary frame width, paired/triple glazing and timber-stack position; actual setbacks remain conditional.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 61. Southeastern and temperate Australia (`au_southeast`)

**Written theme:** Victorian terraces and Federation houses; brick veneer suburbs; contemporary coastal and urban infill.

**Detail direction:** Verandas, ironwork references, local brick/render and metal/tile roofs.

### A. Terrace-derived masonry block

Stable proposal ID: `au_southeast-a` · Grouped street fronts

Suggested fit: 2–9 storeys; 2.8–4 m bays; groups of 3–5 bays.

**Composition:** Broad facade sections combine upright paired windows, substantial piers and a shared base. Restrained horizontal bands reference terrace/Federation rhythms without attaching domestic roof ornaments to the box.

**Base and entry:** One wider framed entry section; verandas need real setback space.

**Roof edge:** Shallow cornice and plain coping.

**Materials:** Warm brick or cream render; pale trim; dark metal

**Procedural variation:** Vary section widths, brick/render balance and lintel detail by locality.

**Supported upgrade:** Where envelope evidence supports it: stepped crown sections or roof-form variation. Facade sections never become invented parcels, entrances or separate buildings.

**Authoring controls:** target glazing 30%–46%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Brick suburban-scale urban block

Stable proposal ID: `au_southeast-b` · Punched masonry bays

Suggested fit: 2–10 storeys; 3.2–4.4 m bays; groups of 2–5 bays.

**Composition:** Grouped windows sit in broad brick panels separated by solid stair strips. A strong base and modest sill bands give larger accommodation, office or civic uses a grounded everyday character.

**Base and entry:** Recessed masonry-framed entrance beneath a simple header.

**Roof edge:** Thin flat cap with a darker upper band.

**Materials:** Red or buff brick; pale concrete lintels; dark frames

**Procedural variation:** Vary brick tone, paired/triple glazing and panel lengths; avoid ornamental heritage defaults.

**Supported upgrade:** Where the source supports it: deeper masonry entrance recesses or an evidenced roof/cornice profile. Keep unsupported historic ornament out of the baseline.

**Authoring controls:** target glazing 28%–42%; reveal depth 0.12–0.28 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Coastal contemporary shade frame

Stable proposal ID: `au_southeast-c` · Screen and solid-wall rhythm

Suggested fit: 3–20 storeys; 3.6–5 m bays; groups of 2–4 bays.

**Composition:** Large opaque frames contain short glazing groups, shade fins and solid spandrels. A quieter service elevation and one warm entry stack create hierarchy without a uniform glass skin.

**Base and entry:** Shaded lobby group under a narrow weather header.

**Roof edge:** Slim continuous cap with darker upper infill.

**Materials:** Pale concrete; warm timber accents; neutral metal screens

**Procedural variation:** Vary fin cadence, frame depth and timber placement; coastal detailing stays a locality choice.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 62. Northern and inland Australia (`au_tropical_arid`)

**Written theme:** Queenslander timber houses; arid-region veranda buildings; tropical modern and contemporary modular housing.

**Detail direction:** Deep shade, ventilation and separately evidenced elevated floors.

### A. Queenslander-rhythm urban block

Stable proposal ID: `au_tropical_arid-a` · Shaded horizontal groups

Suggested fit: 2–8 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Strong posts and rain headers frame short groups of shaded windows with opaque lower panels. The veranda direction becomes facade rhythm while the actual floor elevation stays unchanged.

**Base and entry:** Sheltered existing entrance with a restrained contrasting surround.

**Roof edge:** Broad fascia beneath the source roof; deep eaves remain conditional.

**Materials:** Muted painted boards; pale posts; dark base

**Procedural variation:** Vary post grouping, board colour and louvre share; do not automatically raise the building.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Inland shade-wall block

Stable proposal ID: `au_tropical_arid-b` · Deep punched wall planes

Suggested fit: 2–10 storeys; 3–4.3 m bays; groups of 2–3 bays.

**Composition:** Broad opaque wall planes contain deeply shaded paired windows and occasional screened bays. Solid corners and a strong shaded entrance create an arid variant distinct from tropical timber stock.

**Base and entry:** Deep-looking entry recess within the existing envelope.

**Roof edge:** Plain flat coping with one restrained shade band.

**Materials:** Warm pale render; earth-coloured base; bronze frames

**Procedural variation:** Vary reveal depth, screen share and warm tone; select inland/arid contexts explicitly.

**Supported upgrade:** Where envelope thickness is available: deeper aperture and entrance reveals. Do not carve courts, batter walls or project buttresses without supported geometry.

**Authoring controls:** target glazing 20%–36%; reveal depth 0.18–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Northern modular shade grid

Stable proposal ID: `au_tropical_arid-c` · Enclosed modular fields

Suggested fit: 2–14 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Repeating insulated-looking panels alternate window groups, solid service modules and screened strips. Strong weather headers supply shade without an elaborate ornamental facade.

**Base and entry:** Clearly framed sheltered lobby at the actual entry.

**Roof edge:** Folded-metal-looking cap and a continuous upper header.

**Materials:** Light metal panels; muted colour accents; neutral screens

**Procedural variation:** Vary module groups, screen cadence and accent extent; tropical and arid details use separate parameter bundles.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 63. Melanesia, Micronesia and Polynesia (`pacific_islands`)

**Written theme:** Community-specific timber/pavilion traditions; Pacific bungalow and plantation-era forms; contemporary island masonry housing.

**Detail direction:** Open shaded edges, rain protection and cyclone-aware local roof profiles.

### A. Timber pavilion-rhythm block

Stable proposal ID: `pacific_islands-a` · Post and boarded-panel rhythm

Suggested fit: 1–6 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Strong posts and horizontal rain headers organise grouped openings and opaque panels. The proportions reference community-specific timber directions without assigning a ceremonial roof or motif from a regional label.

**Base and entry:** Sheltered entrance frame at the measured floor level.

**Roof edge:** Broad plain fascia beneath the existing roof.

**Materials:** Warm timber tones or muted painted boards; pale infill; dark base

**Procedural variation:** Vary post groups, board direction and local paint family; no assumed raised floor.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Island bungalow-gallery block

Stable proposal ID: `pacific_islands-b` · Shaded horizontal groups

Suggested fit: 2–7 storeys; 3.2–4.5 m bays; groups of 2–4 bays.

**Composition:** Short shaded window groups alternate with substantial solid end sections and opaque lower panels. A durable base and consistent rain line scale bungalow/veranda proportions to a larger multi-purpose shell.

**Base and entry:** Recessed sheltered entry on the real frontage.

**Roof edge:** Strong fascia; roof shape and storm details require support.

**Materials:** Pale render; muted painted posts; dark louvres

**Procedural variation:** Vary group length, louvre share and restrained palette through island-specific choices.

**Supported upgrade:** Where usable depth and collision support exist: true recessed loggias or sheltered galleries. Otherwise use closed recessed glazing and opaque lower panels; no fake balcony platform.

**Authoring controls:** target glazing 36%–54%; reveal depth 0.16–0.35 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Contemporary island masonry frame

Stable proposal ID: `pacific_islands-c` · Screen and solid-wall rhythm

Suggested fit: 2–14 storeys; 3.4–4.8 m bays; groups of 2–4 bays.

**Composition:** Broad frame bays hold paired glazing, solid panels and screened circulation strips. Clear public and service elevation roles bring practical organisation to an ordinary rectangular urban building.

**Base and entry:** A shaded lobby group under a robust rain header.

**Roof edge:** Clean flat cap with a substantial upper weather band.

**Materials:** Light concrete; warm rendered infill; neutral shade panels

**Procedural variation:** Vary screen cadence, infill tone and solid-end width; no generic cultural symbols or assumed cyclone certification.

**Supported upgrade:** Where clearances and material support exist: actual perforated screens or shallow fins. Otherwise use solid panel rhythms and bounded reveals, without claiming functional ventilation.

**Authoring controls:** target glazing 30%–50%; reveal depth 0.15–0.32 m only where the envelope allows.

**Use modes:** apartments or accommodation, office, hotel, civic or education, known mixed use.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

## 64. Antarctic and subantarctic stations (`antarctic_stations`)

**Written theme:** Historic expedition timber huts; insulated modular stations; contemporary research and service buildings.

**Detail direction:** Panel joints, wind vestibules and surveyed raised foundations.

### A. Expedition-derived clad bar

Stable proposal ID: `antarctic_stations-a` · Post and boarded-panel rhythm

Suggested fit: 1–4 storeys; 2.8–4 m bays; groups of 2–4 bays.

**Composition:** Compact paired windows punctuate large boarded wall sections, with strong weather lines and solid corners. This is a modern interpretation for accommodation, offices or support rooms, not a replica historic hut.

**Base and entry:** Clearly framed wind-sheltered entrance at the surveyed level.

**Roof edge:** Strong simple fascia; actual roof form stays sourced.

**Materials:** Muted timber or painted boards; dark base; pale trim

**Procedural variation:** Vary board direction, compact window groups and muted colour; no invented raised foundation.

**Supported upgrade:** Where roof and access geometry support it: deeper rain eaves or a sheltered entry recess. Timber-toned cladding never implies a timber structure or a traditional roof.

**Authoring controls:** target glazing 28%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** station accommodation, research or office, community or support.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### B. Insulated station modules

Stable proposal ID: `antarctic_stations-b` · Enclosed modular fields

Suggested fit: 1–8 storeys; 3.2–4.6 m bays; groups of 2–4 bays.

**Composition:** Repeated opaque modules contain compact window groups and solid service panels. One contrasting circulation section gives the long rectangle an identifiable organisation without adding unsupported linking corridors.

**Base and entry:** Robust recessed wind-lobby appearance around the existing door.

**Roof edge:** Folded cap and continuous enclosed roof edge.

**Materials:** Light insulated-panel appearance; dark joints; restrained colour blocks

**Procedural variation:** Vary two-to-four-module groups, joint cadence and colour blocks; snow clearance and insulation performance remain unverified.

**Supported upgrade:** Where supported: enclosed entry vestibule geometry and deeper cassette joints. Do not add corridors, foundation lifts or rooftop plant from appearance alone.

**Authoring controls:** target glazing 26%–44%; reveal depth 0.1–0.24 m only where the envelope allows.

**Use modes:** station accommodation, research or office, community or support.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.

### C. Contemporary research-support frame

Stable proposal ID: `antarctic_stations-c` · Large opaque frames

Suggested fit: 2–10 storeys; 3.4–4.8 m bays; groups of 2–3 bays.

**Composition:** Broad opaque frames contain grouped observation or workspace windows and substantial solid panels. The service side remains mostly enclosed, with a clear entry stack and compact corners.

**Base and entry:** One strongly framed sheltered lobby; logistics doors remain only where known.

**Roof edge:** Flush cap and a darker upper service band.

**Materials:** Pale metal panels; graphite frames; limited high-contrast accents

**Procedural variation:** Vary window grouping, solid-panel share and entry accents; no invented plant towers, stilts or public retail.

**Supported upgrade:** Where a building-part envelope supports it: a recessed top storey or alternating inset upper bays. Otherwise achieve the hierarchy with frame depth and material zones.

**Authoring controls:** target glazing 38%–58%; reveal depth 0.14–0.32 m only where the envelope allows.

**Use modes:** station accommodation, research or office, community or support.

**Locality:** Use only the proposal's compatible locality and construction context; do not distribute all three uniformly across this broad theme.
