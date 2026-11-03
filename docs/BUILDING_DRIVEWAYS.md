# Garage, driveway and footpath connections

Schema 9, 1 November 2026. This pass restores garages on eligible inferred
detached homes and resolves their ground surface against the actual generated
street/footpath profile. Narrow mapped garage outbuildings receive a centred
shutter without an overlapping pedestrian door. Garage eligibility still
requires compatible form, floors, frontage and setback.

## Continuous surfaces with bounded work

The vehicle surface starts at the garage sill, widens toward the street and
ends at the back of the footpath, or at the road edge where there is no footpath.
Nine sections form eight panels with shared endpoints. Fixed Hermite curves
provide gradual grade changes; terrain is checked at both sides and the centre
of each section. There is one additional terrain batch per tile, at most 27
points per driveway plus 10 for an optional pedestrian branch.

The crossing is built into the existing footpath mesh and collision surface.
A 1.2 m rear walking strip retains the footpath's original elevation and 1.5%
crossfall. The front portion transitions to a 10 mm game kerb lip, with short
curved grade transitions and 0.6 m side flares. Existing pedestrian ramps are
preserved, and vehicle crossings receive no tactile pedestrian pads. Adjacent
crossing mouths merge; unchanged spans use the existing native sidewalk kernel.

Where clearance and grades permit, a 1.2 m landing and side link join the front
entrance route to the driveway. An elevated deck needs an already-resolved stair
and path connection: the generator does not bridge unsupported height gaps.
Use `--building-paths off` to disable generated pedestrian paths/links, or
`--building-paths auto` (default) to enable eligible ones.

Visible paving includes longitudinal/transverse joints and a garage isolation
joint. Buried vertical faces between adjacent panels are omitted using exact
edge counting; there are no mesh booleans. Shared access plans supply building
visual/collision geometry, while the sidewalk builder supplies the crossing.
Final street connections resolve during near road generation, so independent
far-only previews do not contain the final street-resolved access additions.

## Civil reference principles and authored limits

The walking route stays continuous across the driveway rather than tilting the
whole footpath toward vehicles. This follows the design principle in
[NZTA pedestrian path guidance, April 2026](https://www.nzta.govt.nz/assets/Walking-Cycling-and-Public-Transport/docs/pedestrian-network-guidance/docs/3.3-paths-apr-2026.pdf).
The distinction between the rear walking route and vehicle ramp is also
illustrated in [NZTA chapter 14](https://www.nzta.govt.nz/assets/resources/pedestrian-planning-guide/docs/chapter-14.pdf).

The numerical limits below are conservative game-authoring choices, not a
claim of engineering approval or a universal local standard. For comparison,
[Kāpiti's residential crossing drawing](https://www.kapiticoast.govt.nz/media/z5abvvol/kcdc_rd_005-roading-standards-residential-vehicle-crossing-2021.pdf)
uses its own kerb geometry; our 10 mm lip is selected for gameplay continuity.

| Check | Current limit / response |
| --- | --- |
| Garage-to-street length | At most 18 m; no iterative route search |
| Drive grade | At most 15% sampled panel grade; gentle endpoint tangents |
| Terrain difference | Positive cover, at most 0.35 m fill; no terrain excavation |
| Optional pedestrian link | At most 8 m gap, 5% grade and 0.15 m fill |
| Footpath | At least 2.4 m wide to fit the protected strip and crossing ramp |
| Geometry/obstructions | Spatial-index checks against known buildings/roads and accepted neighbouring new driveways/branches |
| Complex cases | Missing terrain, sharp curves, existing pedestrian ramps, excessive grading and blocked routes are diagnosed and omitted |

Drainage channels, swales and culverts require information that the current map
inputs do not supply; they are not invented. See
[Thames-Coromandel's vehicle-crossing guidance](https://www.tcdc.govt.nz/Our-Services/Transport-Roads-and-Road-Safety/Vehicle-Crossing)
for why drainage continuity is a separate design requirement. Surveyed property
boundaries, utilities, street furniture, watercourses and all existing paths are
not yet integrated as exclusions. Adjacent-tile access arbitration, complex
curved/offset approaches and retaining structures remain follow-up work.

## Measured cost and checks

A synthetic batch of 250 distinct houses produced 250 driveways and 250 optional
links. Connection/path resolution took 274–282 ms (about 1.1 ms/house); crossing
visual and collision geometry took 127–145 ms (about 0.5–0.6 ms/crossing). There
was one terrain batch of 9,250 points. Each typical crossing adds 44 visual
vertices and 60 triangles. Base building planning, full building mesh compilation,
terrain-provider latency, rendering and game frame time are excluded.

Checks cover garage/footpath endpoint equality, shared panel continuity,
translated coordinates, densely sampled straight footpaths, missing/steep/
obstructed terrain, optional links, preserved pedestrian ramps, walking-strip
crossfall, finite geometry, matching collision and crossing vertex limits.
`buildings-driveway-preview.png` is a synthetic geometry preview, not a BeamNG
capture. Actual vehicle traversal, material brightness, edge shadows and near/far
transitions still need an in-game playtest.
