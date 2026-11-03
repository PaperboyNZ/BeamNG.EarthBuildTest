# Architecture and landscaping playtest — 1 November 2026

Build: `BeamNG.Earth-v2-architecture-landscape-20261101` (building schema 14).
This private test update contains the current server and matching game mod.

## Start playing

1. Close the previous Earth server and BeamNG.drive before switching builds.
2. Double-click `test_v2.bat` in this update's folder, or the workspace's
   `Play latest buildings.bat`. Leave the server window open.
3. Start BeamNG.drive and select **Freeroam → BeamNG.Earth**.

The launcher synchronizes this update's mod into the configured BeamNG user
folder. A newly extracted ZIP installs its Python dependencies on first launch.
The prepared local test folder already has its own Python environment.
Normal play downloads map data as needed. Keep your existing map cache: generated
content is keyed by source changes, so manually deleting downloads is unnecessary.

## What to test

- Parking garages: enter from the road, drive up and down each accessible deck,
  and exit. Try a normal car first, then a longer vehicle. Watch for curb lips,
  tyre catches, steep transitions, blocked ramps and missing collision.
- Churches: check chapel, parish and modern compositions, plus square broach,
  octagonal needle and short pyramidal spires on eligible buildings. Not every
  church gets a spire; supplied roof/height limits still apply.
- Commercial buildings: inspect trade units, shop fronts, supermarkets and the
  three office treatments. Look for aligned windows, intact entrances and trim
  that does not cross doorways. Check terminal public and service elevations.
- Pavement and planting: roads, sidewalks, driveways, parking and other paving
  should remain clear of trees, bushes and rocks. Accepted lawn/garden patches
  should retain planting and rocks. Drive away and revisit to check streaming.
- Watch near/far detail changes and cold-area loading. Check that a vehicle does
  not lose its supporting surface while detail changes or nearby tiles retire.

Use familiar saved places or the in-game map. Feature availability depends on
mapped evidence; there is no artificial showcase added to real locations.
Property-wide parking/loading layouts still require a surveyed site catalogue.
The included synthetic catalogue is a validation fixture and is not enabled.
Prepared roof colours and the Christchurch zoning pilot are retained, with their
original attribution in `runtime_data/SOURCES.txt`.

## Report a problem or compare

Note the location, vehicle, what happened and whether it followed a teleport or
revisit. The in-game report shortcut is **Ctrl+Shift+E**. Include this build name
with screenshots and the server console output.

For the existing legacy-generator comparison, close the game/server and launch
`test_legacy.bat`. Previous update folders are also preserved; run their launchers
to return to their matching mod/server. Restart the game when switching builds.

## Validation and limits

The source checkpoint passed 488 Python tests across 35 modules. Twelve building
fixtures retain their collision fingerprints and body heights; nine access
fixtures retain crossing counts. Packaging checks exact archive/extracted file
hashes, retained runtime data, dependency imports, synthetic geometry and server
startup. The prepared package's verification report is stored beside the ZIP.

Native BeamNG visual appearance, tyre contact, occupied streaming and release
performance are the purpose of this playtest and have not been signed off.
Added facade detail and route alternatives have measured generation overhead.
No new fuel-site replacement or large shared-site assembly is activated here.
