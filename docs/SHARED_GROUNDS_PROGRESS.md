# Shared grounds and curved access — 2 November 2026

This continuation connects bounded shared-site layout planning to the existing
runtime and sector collision lifecycle. It also extends ordinary residential
driveways. It retains the separate parking-surface and roof updates.

Performance is a primary constraint: region shapes are prepared/indexed before
grid clipping; whole-region triangles bypass polygon triangulation; coordinate
transforms run once per mesh batch; only exterior/hole edges receive side walls.
The three-member review fixture has 1,928 total mesh triangles instead of 7,040
individual-prism triangles (72.6% fewer), with 880 unchanged top triangles.
Three local repetitions measured 218 ms median planning and 95 ms mesh assembly.
Accepted physical products survive visual upgrades without replanning. These are
synthetic generation measurements, not native FPS or general hardware budgets.

## Ordinary residential access

Garage approaches can meet gently curved frontages (up to 25 degrees of tangent
variation across the mouth). The final ribbon uses the actual rear sidewalk
vertices and heights, including intermediate source stations. Full-width
obstruction, grade, terrain support, protected pedestrian ramps and neighbouring
mouth checks still apply. Straight/offset alternatives retain their existing
ranked order and their normal single terrain batch.

After all complete routes fail, a separate 5.5 m receiving-area proposal can
produce `driveway_crossing_only`. It must have clear supported ground, acceptable
grades and no overlap with the building's retained apron/threshold. It does not
claim a connection to the garage. Receiving alternatives use one lazy batched
terrain query only if reached. A failed replan retains an existing accepted route.

## Whole-property shared layouts

`sitegen.shared_layouts` consumes canonical `SitePlan` records with observed
interfaces through the existing `BNE_SHARED_SITE_RECORDS` catalogue. Records
without interfaces keep the original single-sector court behaviour.

Inputs require a complete source-linked association, explicit building/lot
membership, measured hardstanding boundaries and height intervals, complete
exclusions including member footprints, and measured XYZ opening edges. External
mouths belong to the site; destinations belong to declared members. Building IDs
use `beamng-earth/source-building-id`. The input supplies the observed external
connection; this module does not infer a road connection across an unrecorded
verge, wall or public sidewalk.

The planner reserves connected pedestrian routes, delivery access and customer
aisles before fitting parking and planting. It tries four bounded smooth route
shapes per destination and checks full strips, curvature and a rigid-van swept
envelope. Service support is limited to a 5.5 m van; articulated-truck turning,
loading reversal and turning-court simulation are not implemented.

Parking requires a six-metre aisle, a complete bay footprint and a connection to
an accepted walking strip. Accepted stalls drive both parking positions and
render-only paint. Inferred per-building frontage paths/sites are suppressed for
explicitly managed members. Existing essential thresholds remain obstacles.
Conflicting mapped parking rows/marks are replaced only inside accepted shared
surfaces. Residual beds are allowed only inside surveyed property, keep openings
clear and receive existing native shrubs/rocks after full-envelope terrain checks.
Mapped pavement association alone does not authorize a garden outside it.

## Continuous surfaces and streaming

All resources use one constrained smooth quadratic height solution in the source
frame. Measured opening elevations remain pinned; incompatible pins, missing
terrain, excessive grades or excessive fill reject the complete proposal.
Canonical grid triangles, with opening coordinates included as grid knots, are
the common visual/contact surface. Material and resource boundaries clip those
same planes instead of fitting independent heights. The planner reports surface
fall direction; underground outlets remain explicitly unresolved.

The complete site is fitted before partitioning into at most eight geographic
sectors. Shared geographic boundary samples give adjacent fragments the same
edge. Every clipped contact patch has one sector owner and uses existing occupied
collision retention. Each fragment carries the complete site's contact revision.
The client refuses to mix different resident revisions of the same site. Changes
wait for old neighbouring sectors to retire; this is not an atomic multi-sector
hot-swap. Restart the server after changing the pinned catalogue, and restart the
game when deliberately switching source/terrain revisions for testing.

Hard bounds: 24 interfaces/routes, 32 members, 16 source surfaces, 64 parking
bays, 16 soft beds, 4,096 probes for a shared-site planning pass and 4,096 top
triangles per accepted layout/fragment. Current terrain defaults allow at most
18 cm fill, 8% overall grade and 5% along pedestrian routes. These are capability
limits for the game, not claims of regional engineering compliance. Terrain is
not modified by this solver.

## Validation and use

Run the new suites with the existing project environment:

```powershell
python tools/run_tests.py test_driveway_curves test_sitegen_shared_layouts test_sitegen_shared_courts
python tools/shared_site_preview.py --out build/shared-grounds.png
```

The preview writes an illustrative three-member source catalogue beside its PNG
and JSON report. Its coordinates and heights are synthetic; do not activate that
fixture over the real map. Use a genuinely measured `SiteGraph` with the existing
`BNE_SHARED_SITE_RECORDS` environment variable or the new `--shared-sites FILE`
server option for runtime reconstruction. The ordinary launcher clears inherited
pilot settings, so pass the explicit option through it:

```powershell
& './Play latest buildings.bat' --shared-sites 'G:\path\measured-sites.json'
```

The CLI validates the catalogue before starting the server. It does not download
or fabricate property ownership data.

Ordinary driveway improvements are default-on. Shared sites remain evidence-led
and require that explicit catalogue: automatic global parcel discovery or
membership inference is not implemented. Native appearance, contact, occupied
seam traversal and performance acceptance remain pending; synthetic geometry,
production encoding and deterministic lifecycle tests cannot establish game FPS.
