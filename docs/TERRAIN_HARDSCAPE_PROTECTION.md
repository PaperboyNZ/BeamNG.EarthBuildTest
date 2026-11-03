# Terrain corrections beside curbs and sidewalks

The local parking terrain smoother now reserves source roads and their possible
sidewalks before applying optional cut/fill. Corrections are exactly zero inside
those reservations, for both raising and lowering terrain. Road grading still
runs last. Existing lawn and garden overlays sample the accepted terrain; they
do not modify the heightmap.

Reservations use the same measured road/sidewalk width provider as road grading.
They include the tallest regional curb profile, the sloping back skin, median
bands and a conservative allowance for the source offsets' 2x miter limit.
Both sides are protected even where only one sidewalk is currently enabled.
The protected envelope includes junction returns and crossing flares without
generating sidewalk meshes during terrain planning.

A further guard of `sqrt(2) * max(1 m, 2 m, 8 m)` protects the vertices used to
interpolate near physics terrain, near visual terrain and remote-vehicle
collision islands. Outside that envelope the existing cut/fill strength returns
smoothly over 4 m. This deliberately leaves a wider unsmoothed strip beside a
street; clear parking interiors retain their bounded 35 cm smoothing.

Each reservation is built for a complete feature-local patch, including source
roads in neighbouring map cells. It does not depend on query batches, anchor or
load order. Restoring parking footprints from the revisit cache still loads the
road inventory before allowing smoothing. Failed or incomplete inventories omit
optional smoothing and are never cached as an unprotected patch.

Planning is limited to 64 protection cells and 65,536 source points per patch.
Unsupported widths or exhausted budgets also omit optional smoothing. Protected
geometry storage participates in the existing 64 MiB patch cache limit. The
source fingerprint changes automatically, invalidating generated terrain products
on server restart while retaining downloaded source data.

Validation: 187 tests pass across parking/surfaces, road grading, sidewalk layout
and collision, driveway geometry, landscaping, shared terrain sampling, plan
cache and source identity. Nine added regression tests cover positive/negative
cut/fill, wide one-sided sidewalks through bends with every regional profile,
neighbouring cells, cached footprints, missing inventory and retries, batch/order/
anchor invariance, final junction grades and coarse collision interpolation.

Run from this source root with the project's existing Python environment:

```powershell
New-Item -ItemType Directory -Force build/terrain-curb-protection/tmp | Out-Null
$env:TEMP = (Resolve-Path build/terrain-curb-protection/tmp).Path
$env:TMP = $env:TEMP
& ../BeamNG.Earth-pr2-latest-dev-20261102/.venv/Scripts/python.exe -B tools/run_tests.py test_parking_surfaces test_grading test_sidewalk_collision test_sidewalk_layout test_buildgen_landscaping test_sitegen_surfaces test_plancache test_surface test_buildgen_driveways test_codefiles --par 3 --timeout 90 --logs build/terrain-curb-protection/final
```

The active combined playtest and the previous PR2 package receive the same three
source/test changes. Restart the Earth server and BeamNG through the existing
launcher to use them. Native-game visual/driving acceptance remains pending.
