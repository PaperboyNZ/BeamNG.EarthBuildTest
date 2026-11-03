# Street clearance and terrain-aware landscaping

This continuation trims ground-level building bodies clear of streets and their
sidewalks. It also improves planting, bed-edge curbs and entrance transitions.

## Building clearance

Grounded footprints are clipped against the road width and then the actual road
and sidewalk geometry, including sidewalk back skins and corners. The body stays
0.35 m behind the reserved edge; parking decks receive extra allowance for their
projecting collision geometry. No building is translated or stretched. If a cut
splits a footprint, the largest usable piece is retained, including its holes;
tiny or narrow remnants are omitted.

The clipped footprint is shared by building rendering, collision and regenerated
entrances. Source identity, resolved use, material and body height are retained.
Unsupported clipped pitched roofs use the existing flat-roof fallback. Mapped
elevated parts with sufficient clearance, genuine bridge structures and tunnel
portals remain separate cases.
Ordinary road overlaps no longer invent a raised building above the carriageway.

Source-width checks also run for distant and skyline buildings. Near buildings
receive the actual road/sidewalk check before even their progressive shell is
published. Terrain-painted roads are included, although they may not have ordinary
road mesh chunks. Missing/unusable geometry is diagnosed rather than guessed.

## Grounds and planting

Existing game bushes and rocks use irregular spacing and multiple meandering rows
where beds are wide enough. Full asset envelopes remain inside soft areas and
separate from other placements. Placement samples support across the asset's whole
footprint on the actual groundcover triangles, including slopes and twisted quads.
Excessive unevenness suppresses optional planting. No bespoke shrub/rock meshes
are generated.

Joined curbs border planted beds along the paving side and ends. Curbs and planted
interiors share their fitted elevation; walking and vehicle openings remain clear.
Short entrance height differences can use a bounded pedestrian stair/landing
transition. Parking still requires its own drivable road connection; pedestrian
steps are not used as vehicle ramps.

## Test in BeamNG

Close the old server and restart BeamNG when switching updates. Use the parent
`Play latest buildings.bat` or this update's `test_v2.bat`, then open BeamNG.Earth.

- Check ground-level buildings alongside roads, sidewalk corners and junctions.
  Walls and collision should remain behind the sidewalk; inspect narrow remnants.
- Check a building near a bridge or tunnel for unwanted clipping.
- Visit sloping commercial grounds. Walk/drive across appropriate transitions and
  inspect curb ends, bed boundaries, bushes and rocks for gaps or floating bases.
- Move away and return to check distant, progressive and final building agreement.
- Recheck procedural garage access and church spires after footprint trimming.

Synthetic checks cover clipping, courtyard holes, grade separation, native asset
bounds, rotated/offset terrain, and visual/collision consistency. Native-game
appearance, driving, streaming and performance acceptance remain to be performed.
Large shared-site reconstruction and fuel-site replacement remain future work.
