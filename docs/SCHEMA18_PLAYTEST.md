# Schema 18 integrated performance playtest

Private testing checkpoint: `BeamNG.Earth-v2-schema18-integrated-20261101`.

This integrates the current city buildings, 64 regional themes, 192 regional
block designs, per-building preset variation, reusable component geometry,
wall/shape encoding optimizations and adaptive building streaming. Existing
street clearance, frontage paving, stock planting and collision remain enabled.
Facade texture baking and reduced-shadow laboratory modes are not activated.
The alternative architectures discussed during review are not implemented here.

## Launch

Close the previous Earth server and exit BeamNG before switching packages.
Run the parent `Play latest buildings.bat`, or this package's `test_v2.bat`.
The normal launcher installs the matching mod and starts the server. Then open
BeamNG and select the BeamNG.Earth level. Keep the server window open.

This checkpoint includes the existing Christchurch zoning and roof-colour data.
The previous dated build remains available for comparison. Automatic updates are
disabled by the playtest launcher to preserve the tested source/mod pairing.

## Performance comparison

Use the same route, vehicle, weather, time of day, resolution, graphics preset
and building draw distance for each run. Record the CPU/GPU frame-time display,
visible stalls and building coverage; average FPS alone can hide import stalls.

1. Start with Building quality **Adaptive**, refinement distance **350 m**.
   Record the actual settings: existing saved preferences can override defaults.
2. Drive a dense urban route, then repeat it to compare first approach and warm
   revisit. New source identities can make the first run colder than the old build.
3. Accelerate above 80 km/h, brake below 43 km/h, reverse direction and stop.
   Check that simpler buildings refine without missing buildings or road surfaces.
4. Repeat with **Full**. For a **Light** comparison, restart the session or enter
   an unseen area: already completed full buildings are deliberately retained.
5. Teleport to a dense area and move the free camera. Check near/far/skyline
   coverage, roofs, courtyards, night windows, collisions and frontage transitions.

Repeat the same route at least three times when comparing settings or packages.
Capture the location, quality/refinement settings, first/warm visit, frame times
and server/game logs with any issue. Do not delete the normal cache to force a
cold test; a separate cache directory can be supplied after the launcher command.

## Scope of verification

The matching verification JSON in the parent `artifacts` folder records frozen
source hashes, regression checks, archive integrity, packaged geometry parity
and isolated offline server startup/capability negotiation. Synthetic checks do
not establish native appearance, driving, occupied streaming or FPS performance.
Those are the purpose of this playtest and remain pending.
