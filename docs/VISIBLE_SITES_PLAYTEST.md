# Visible commercial frontages playtest

This update enables bounded automatic site work on eligible ordinary commercial,
office, mixed-use and industrial frontages with `--building-paths auto` (the test
launcher's default). It does not require a hand-authored `--building-sites` file.

Look for concrete pedestrian forecourts, asphalt service/parking areas on deeper
setbacks, planted beds and concrete bed-edge curbs. Parking is emitted only when
the site fits stalls, an aisle and an accepted road connection with a matching
sidewalk crossing. New paving connects to the building's accepted entrance.
Shallow setbacks may receive only pedestrian paving; constrained or steep sites
may receive no extension. These are inferred facade-bounded frontages, not claims
about surveyed property boundaries or a replacement for every mapped car park.

Planting uses existing BeamNG stock shrub and rock assets through the Forest prop
renderer, with their native materials and LODs. The generator creates groundcover
surfaces, not custom shrub or rock models. Full asset footprints plus clearance
must fit inside accepted planted areas. Narrow beds can remain unplanted. Missing
native assets are omitted, with no primitive model fallback. Roads, pavement,
driveways and parking remain excluded from natural-object placement.

## Start and compare

1. Close the previous Earth server and restart BeamNG when switching updates.
2. Run `test_v2.bat` in this folder, or `Play latest buildings.bat` in the parent.
3. Start BeamNG.drive and choose Freeroam -> BeamNG.Earth.
4. Visit several shops/offices with visible space between the building and road,
   plus a supermarket or industrial frontage with a deeper setback.

The launcher installs the matching mod. The older architecture/landscape package
is retained separately for comparison. Prepared roof-colour data and Christchurch
zoning data remain included; stock game assets stay in the game installation.

## In-game acceptance still required

- Check planted beds use textured stock bushes/rocks, without foliage extending
  across curbs, paths or driveway openings. Unload/reload the area and revisit it.
- Drive from the road over a commercial sidewalk crossing into an accepted
  parking aisle; check seams, curb openings and vehicle clearance.
- Check pedestrians' forecourts meet entrance paths and retain level transitions.
- Revisit procedural garages and decorated church spires for regressions.
- Report location, nearby business/building, screenshots, and server/game logs if
  a plausible frontage stays empty or a generated surface/asset looks wrong.

Synthetic geometry, native-asset contract tests and isolated server startup are
separate from native-game visual, driving and performance acceptance. Large shared
complexes, full parcel reconstruction and fuel-site replacement remain future work.
