# Parking garage generator implementation plan

Prepared 1 November 2026. Proposed work governed by the [shared specialized building plan](SPECIALIZED_BUILDING_IMPLEMENTATION_PLANS.md).

The first functional repair is implemented; see [garage access and traversal
status](GARAGE_ACCESS_IMPLEMENTATION.md) for accepted geometry, tests and remaining
in-game gates. The baseline gap description below is retained as planning context.

Parking garages should retain their playable decks while gaining believable structure, diverse facades, clear entrances, coherent circulation and grounded road connections. Architectural variety must be fitted around a working circulation plan. A visually open entrance leading into a column, ramp wall or unusable grade is a failed result.

## Current behavior and gaps

`buildings.py::deck_plan` selects open decks when dimensions, ground variation and a ramp fit permit them; otherwise the generator uses a closed building. `_deck_layout` searches a bounded set of long edges. `_parking_deck` emits slabs, alternating ramps, parapets and perimeter columns. `_garage_skin` supplies five brick/precast choices, repeated spandrels/piers and an inferred stair tower. `garage_drives` independently selects a nearby road-facing edge and generates a connection.

Retain the working ramp/deck implementation as a baseline. Improve its coordination: one accepted plan should determine portal position, ground-deck aisle, ramp landings, structural exclusions and road connection. Existing single-ring/sampled fit logic needs full topology and vehicle-envelope checks before broader shapes are enabled. A stair tower must fit its entire footprint, not only its center.

## Separate circulation from appearance

| Proposed circulation family | Eligibility and behavior | Phase |
| --- | --- | --- |
| `garage_edge_ramp` | Existing alternating edge-ramp arrangement, upgraded with complete fit and smooth transitions | 1 |
| `garage_straight_internal` | Straight ramp within a reserved internal strip, with clear landings and connected aisles | 2 |
| `garage_split_level` | Half-level decks and short ramps; mapped levels or supported explicit recipe | 2 |
| `garage_external_ramp` | Ramp occupies its own mapped/source-supported volume with connected deck openings | 3 |
| `garage_helical_ramp` | Bounded curved ramp with swept-envelope, overhead and grade checks; source-supported footprint | 3 |
| `garage_shell_only` | Recognizable parking facade preserving source topology when a playable interior cannot be fitted | 1 fallback |

Do not choose a circulation family merely to increase visual variety. Preserve known levels and ramps first, then try at most four compatible inferred arrangements. A closed-shell fallback must not advertise an open playable portal. Retain existing viable gameplay layouts when they pass the upgraded checks.

Apply facade vocabularies separately: exposed concrete frame, precast spandrels, brick/stone urban infill, perforated metal screen, vertical fins/louvers and contemporary mixed opaque/open treatment. Proposed phase 1 includes concrete, masonry and metal-screen systems. Fit screen density and openings to the structural grid and compatible evidence. Do not add fake floor bands unrelated to actual deck levels.

## Geometry and driving rules

Resolve floor/deck semantics first. Preserve explicit heights and floors; keep the existing split-level-count safeguard with an auditable reason when source counts cannot yield credible headroom. Define clear headroom from the highest road surface to the lowest slab, beam, sign or service obstruction, including the full ramp path. Roof parking is a deliberate accepted level, not an accidental extra floor from array indexing.

Reserve ramp wells, landings, turning envelopes, pedestrian cores and source holes before placing columns or parking. Use full polygon containment/intersection checks for every reserved envelope. Select portal, ground aisle and external access together. Attempt another bounded candidate if the nearest road-facing edge cannot connect to the internal route. Protect road/pavement clearance and preserve walking routes at the mouth.

Replace abrupt ramp start/end joints with bounded vertical transition profiles evaluated against an ordinary design vehicle and a lower/longer check vehicle. Store wheelbase, overhang, clearance and turning parameters in a versioned gameplay profile; calibrate against BeamNG test vehicles. Do not present these as universal engineering dimensions. Validate uphill/downhill traversal, ramp-side parapets and turning landings in both intended directions.

Place complete parking stalls only after the circulation graph and structural grid are accepted. Count full stall/access envelopes; remove stalls that conflict with columns, wells, cores or barriers. Markings follow accepted levels and surfaces. Keep vehicle spawn capacity separate from painted capacity and initially retain the existing per-tile parked-position limits. Do not fill every deck with parked vehicles.

Support believable slab edges, beams, columns, parapets, expansion-joint visuals, stair/core faces, entry surrounds, height signs and sparse lighting. Sign values must match the validated clearance profile; otherwise use a nonnumeric entry treatment. Static gates must not block an accepted driving route; working barriers are a later gameplay feature. Roof plant, solar canopies and external towers require mapped or curated support and clearance.

Facade and structure share the same bay grid. Use material/pier/run differences for variety, with coherent weathering around deck edges and drainage. Keep important openings legible through LOD changes. Glass or screen facades must not turn a playable opening into collision, and disappearing decorative mesh must not leave invisible physical obstacles.

## Site and fallback behavior

Integrate `garage_drives` with shared access ports and surface cells from the pavement plan. Resolve gutter, footpath, landing and ground-deck datums together. Do not flatten an entire sloped site to make one portal fit. Multi-level road access requires actual source support; an upper street nearby is not proof of an entrance.

Unknown site boundaries do not prevent facade improvements or a validated short road connection. They do prevent arbitrary external queues, car parks or ramp footprints. Expose diagnostics for insufficient headroom, missing road connection, slope failure, hole conflicts and over-budget geometry so coverage can improve without weakening fit checks.

## Implementation tickets and acceptance

1. **Capture and shared garage plan.** Record current successful and rejected decks. Introduce proposed `buildgen/garages.py` records for levels, portals, ramps, aisles, structure and skins, with existing output adapted first. Extend immutable-plan and packaging tests.
2. **First playable slice.** Coordinate edge-ramp circulation with the entry and road connection. Add transition geometry and whole-envelope checks, then concrete, masonry and screen facades over the same valid structural plan. Preserve a diagnosed shell fallback.
3. **Parking and detail.** Fit structural bays, cores, complete stall rows, directional markings and entry detail. Integrate shared pavement/access levels and regional markings. Verify parked vehicles cannot obstruct ramps or openings.
4. **Additional circulation.** Add straight/internal and split-level arrangements, then mapped external and helical ramps only when their collision, transitions and turning checks pass. Complex holes and sloping multi-entry cases require dedicated fixtures.

Extend existing `test_buildings` garage/deck tests and add `test_buildgen_garages`. Cover rectangular, narrow, L-shaped and courtyard footprints; insufficient headroom; missing and contradictory levels; sloping access; no road; blocked nearest edge with a valid alternate; upper street; oversized/chunked garage; and legacy fallback. Assert route connectivity as well as triangle validity.

In-game acceptance requires entering from the road, reaching every advertised deck, turning at landings and returning to the road in the design vehicle. Repeat critical transitions in the check vehicle, including low-speed diagonal approaches. Check parked-car exclusions, overhead collision, wheel contact, parapet collision, streaming and rebases while inside the garage.

Phase 1 is complete when the edge-ramp family remains playable and three facade systems are visibly distinct without changes to source geometry. Compare floor count, facade bands and roof level directly in captures. Working lifts, animated barriers and unrestricted underground garages are separate scope.
