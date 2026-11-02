# Terminal generator implementation plan

Prepared 1 November 2026. Proposed work governed by the [shared specialized building plan](SPECIALIZED_BUILDING_IMPLEMENTATION_PLANS.md).

See [current classification and facade implementation](TERMINAL_IMPLEMENTATION_STATUS.md)
for the completed building-only slice and its remaining acceptance gates.

Passenger terminals should read as transport buildings with arrival fronts, public halls, transport-facing edges and service areas. Small regional facilities, long concourses and large multi-part terminals should differ in composition and roof structure. Improve their buildings before attempting large invented transport sites.

## Current behavior and gaps

The specialized selector and legacy planner recognize `terminal` or `concourse` in names. When height and floor count are missing, the legacy terminal rule supplies a 13 m, two-storey building. Terminal facades are assigned office glass/window bands. There is no terminal-specific plan for elevation roles, public entrances, concourse rhythm or mapped transport interfaces.

Introduce semantic classification before decorative expansion. Normalize explicit building/transport use, source relationships and nearby mapped airport/rail/bus/ferry facilities; use names as supporting evidence. A freight terminal, a building named Terminal Hotel and an unrelated business containing the keyword must not automatically receive an airport passenger facade. Airport proximity alone is also insufficient. Keep ambiguous cases on a conservative passenger/public or existing shell path with a diagnostic; do not invent a transport mode.

Airport passenger terminals are the primary first release. Bus, ferry and rail passenger buildings are later adapters using the same elevation/roof contracts. Freight terminals remain in the commercial/industrial workstream.

## Proposed families

| Family | Building treatment | Evidence and boundary | Phase |
| --- | --- | --- | --- |
| `terminal_regional_hall` | Modest public hall, concentrated entry glazing, opaque service end, shallow or mapped pitched roof | Airport passenger evidence; conservative small-terminal fallback | 1 |
| `terminal_linear_concourse` | Repeated structural bays, alternating glazed/opaque zones, clearly terminated ends | Mapped passenger concourse or terminal parts; preserve actual narrow outline | 1 |
| `terminal_main_hall` | Large public entrance groups, taller glazed zones, distinct roof edge and service elevations | Confirmed terminal envelope; no assumed second road level | 2 |
| `terminal_multilevel` | Facade/entrance zones aligned with supplied floor/road datums | Mapped levels and access decks; do not fabricate elevated approach roads | 2 |
| `terminal_pier_or_satellite` | Linked mapped volumes with coherent joints, shared materials and gate-side rhythm | Actual parts and connecting structures; no invented finger piers | 2 |
| `terminal_longspan_hall` | Repeated monitor, folded or curved roof modules fitted to a supported envelope | Roof-form/reference evidence and validated geometry capability | 3 |
| `terminal_bus_or_ferry` | Passenger hall with supported boarding-side openings/canopies and public arrival front | Explicit mode; docks, ramps, berths and bus bays remain source-led | 3 |
| `terminal_rail_hall` | Public station hall, fitted entrances and compatible mapped platform-side structures | Rail passenger evidence; no extension across tracks from adjacency alone | 3 |

Select compatible masonry, precast, metal-panel, glazed or shaded contemporary vocabularies independently of facility size. Region/climate priors may favor compatible shading and material treatments, but no country-wide rule should make every terminal an identical glass shed. Regional halls can be largely opaque; glazing is concentrated by elevation role.

## Geometry and facade composition

Preserve mapped buildings and parts as the massing. Identify public arrival, transport, service and attached elevations before fitting bays. Airport airside/landside roles need mapped apron/access evidence; without it, resolve only supported entrances and retain neutral treatment elsewhere.

Establish one structural rhythm per coherent hall/part. Fit mullions, piers, opaque spandrels, entrance groups and roof supports to it. Reserve corners, source doors, linked walkways and service zones. Public entrances receive grouped doors, vestibule-like depth and an appropriately sized canopy where it fits. Service elevations receive restrained doors and screened opaque zones, not another continuous showroom facade. Use shared commercial facade roles and opening reservations rather than a second opening solver.

Concourse repetition should vary through part length, bay grouping, termination, material zones and roof form. Do not add a gate door or jet bridge to every bay. Gate equipment and passenger bridges need mapped or curated positions, actual clearance envelopes and a separately validated compiler. Their absence must not prevent a convincing closed concourse shell.

Use shallow reveal/interior backing behind glazing to avoid transparent views into an empty mesh. No passenger interior simulation is required. Entrance portals remain visibly closed unless a supported traversable interior exists. Large shading fins and canopies reserve full projection/column envelopes; preserve roads, service lanes and source passages beneath elevated parts.

Develop repeated long-span roofs with the commercial roof work: restrained parapet/metal baseline first, then monitor/folded/curved components. Roof bay counts respond to span and evidence; do not tile a fixed roof model to cover arbitrary concavities. Keep mapped heights and supported roof orientations; defer unsupported landmark forms instead of adding random shells.

## Site and transport interfaces

Use one shared facility site identity only when source relationships justify grouping. Existing mapped roads, aprons, tracks, platforms and piers retain ownership of their surfaces. The building planner supplies entrance/interface constraints, not a competing airport surface network.

Public connections may include a fitted pedestrian forecourt, supported drop-off bays and weather protection. Bus/taxi queues, multi-level arrival roads and service yards need access and boundary evidence; a terminal label does not create them. Separate public and service routing without inventing fences or restricted areas. Passenger walking routes must not end inside a driving lane or continue through a wall.

The FAA terminal-planning reference covers airport passenger terminal planning; use its building/apron/landside framework as an organizational reference for airport cases. It does not supply universal facade styles or justify generated infrastructure. [FAA AC 150/5360-13A](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC-150-5360-13A-Airport-Terminal-Planning.pdf).

## Implementation tickets and acceptance

1. **Classification and baseline.** Add mode/use evidence and false-positive fixtures. Capture existing terminal appearance, dimensions and dispatch before replacing keyword-only selection. Record absent airport/transport relationships explicitly.
2. **First architectural slice.** Add proposed `buildgen/terminals.py` with regional-hall and linear-concourse families, elevation roles, fitted entry/glazing groups, roof edge detail and neutral fallback. Exercise rectangular, narrow and concave footprints plus missing transport-side evidence.
3. **Large mapped assemblies.** Add main halls and multi-part coordination. Adopt the shared site/part identity contract before inferring cross-tile connections. Support mapped elevated access only with matching height, underside and collision behavior.
4. **Special roofs and interfaces.** Add evidence-backed long-span components, then validated passenger-bridge/boarding components and other transport modes. Each mode has its own valid and misclassification fixtures.

Add `test_buildgen_terminals` alongside existing facade/topology/roof/chunk/access tests. Cover terminal without height, explicit single tall storey, long concourse, courtyard terminal, multiple source wings, elevated passage, terminal crossing chunk boundaries, freight terminal, terminal-named shop, bus station and missing airport context. Verify that source height is not replaced by the legacy 13 m default when evidence exists.

Visual review must show different public and service elevations, coherent structural rhythm and recognizable building scale without airline branding. Review small regional, long linear and large mapped terminal cases at the same camera heights as neighboring ordinary buildings. Drive the accepted public approaches and beneath mapped elevated parts; verify no collision slab closes a passage.

Phase 1 is complete with two recognizable families, reliable classification/fallback and topology/collision parity. Aircraft operations, passenger simulation, full interiors and invented road/apron networks remain outside scope.
