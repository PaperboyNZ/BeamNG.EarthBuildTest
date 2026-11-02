# Church architecture first slice

Implemented 1 November 2026 against this source snapshot. This is building-only
geometry under the existing v2 footprint path. It does not complete all acceptance
items in `CHURCH_GENERATOR_PLAN.md` or the integrated M0/game gates.

## Implemented behavior

`server/buildgen/churches.py` supplies three distinct closed-envelope compositions:

| Family | Fitted composition | Conservative material prior |
| --- | --- | --- |
| `church_plain_chapel` | Restrained rectangular paired panes, modest actual door, low plinth and flush eaves line | Timber weatherboard |
| `church_parish_hall` | Taller single bays with eight-segment round heads, recessed closed glazing, coherent plinth and frames | Brick |
| `church_modern_hall` | Wider three-part grouped glazing, restrained entry surround and plain envelope | Render |

Mapped supported facade/roof materials and colours override these priors. Family
selection changes facade composition, not source footprint, holes, occupancy,
roof type or mapped total height. Near and lite retain the same fitted aperture
positions and profiles. Near adds recess returns; lite removes that depth detail.
Collision is a simple closed source envelope with the same supported roof and
courtyard voids. Skyline geometry shares `draw_roof()` and its exact source roof
envelope with a matching vertex-count admission estimate. A suitable subset has
one bounded decorated roof spire, described below. No religious symbol, bell,
grave, aisle, transept or site surface is generated. Roofs and cornices stay inside
the source outline.

The adapter requires semantic church fabric from class/subtype/building evidence;
names and generic religion cannot establish that fabric. Current use is recorded
separately, so `building=church` with `building_use=office` retains church fabric
without an active-worship identity or decorative religious symbols. These optional
tags are direct adapter inputs; their production feed lineage is not newly claimed.

Missing subtype chooses the plain chapel as a low-confidence composition prior.
Explicit `parish_church`/`parish_hall` or `modern_church`/`modern_hall` subtype selects
the corresponding family. `_church_family` is an explicit internal curated/tool
override used by the comparison matrix; it is not a new observed source attribute.
Modern composition does not assert observed construction era. No regional packs
or dated style priors are activated.

## Varied decorated spires

The user's subsequent request retains varied spires on some churches. The runtime
supports three actual source-contained silhouettes: a square belfry with broach
shoulders and an eight-sided tip, an octagonal belfry with a taller needle, and a
short square pyramidal spire. Each has a fitted cornice; near geometry adds closed
dark belfry panels and six louver slats per face. No default religious symbol or
traversable tower interior is added.

Explicit `_church_spire` requests (`square_broach`, `octagonal_needle`,
`short_pyramidal`, `auto`, or `none`) and optional `_church_tower_footprint` take
priority. These are caller-provided curated inputs, not newly retained production
fields. Otherwise a stable 28% appearance prior attempts a spire on confirmed
current church use; converted office/residential fabric does not receive that
prior. The record labels this as procedural style, not mapped tower evidence.
Many churches remain plain after eligibility and fit checks.

At most nine deterministic positions are tried. The complete reservation,
including cornices and louvers, must lie in solid source footprint with at least
0.3 m boundary clearance, including courtyard boundaries. The reserved square has
a maximum half-width of 1.6 m. The body remains at least 3.4 m tall, above the door
head, and the tower starts at roof level; there is no new ground column or door
obstruction. Insufficient height or containment omits the spire.

The main body/eave height is lowered to reserve the spire **inside the supplied
total building height**. The supported main roof shape and its rise remain intact.
An explicit mapped roof height takes priority: omit the spire rather than
reinterpret a measured roof-height span. The 15 m review examples deliberately
have a supplied total height and unknown roof height. This is a style allocation
within a known outer envelope, not a measured tower claim.

The immutable `ChurchSpire` lives on `ChurchArchitecture.spire`. Shared
`draw_roof(..., detail=False)` draws the main roof, belfry, cornice and spire for
near/lite/collision/skyline; near passes `detail=True` for louver panels. Additional
skyline silhouette vertices are exactly 104/120/60 for broach/needle/pyramid,
reported without mesh allocation by `spire_vertex_count()`. Collider bounds use
the architecture's total height, including its spire. Mapped tower/part assemblies
remain a separate unsupported case.

## Runtime contract and bounds

Root integration adds `spec.church` and its immutable `ChurchArchitecture` to
`BuildingPlan`, with the combined schema version 14. `adapt(spec, attrs, footprint)`
returns `None` for unrelated fabric, a diagnosed `accepted=False` record for an
unsupported confirmed church, or an accepted frozen record after adapting the
mutable spec. Rejected adaptation leaves the input spec unchanged. The caller
appends the record diagnostics. `draw(mesh, spec, gmin, gmax, lite=False,
collision=False)` returns whether it emitted the complete church envelope;
accepted cases run before generic footprint geometry in visual and collision
builders. `layout(spec, gmin, gmax)` exposes the common `FacadeLayout`/`Opening`
records used by both representations.

The first slice accepts source area 20–2,500 m², at most 128 source vertices and
eight holes, one storey, body height 2.8–14 m, and total height no more than 20 m.
These are explicit procedural admission bounds, not researched regional standards.
Openings are capped at 192 per building and sixteen per fitted wall span. Source
polygons still pass the existing topology validator. Supplied shared walls use
`_party_walls=((boundary, edge), ...)`; those elevations remain opaque and the
entrance selector skips them. This is caller-provided context: the production feed
does not newly retain or automatically discover shared walls in this slice.
Unknown adjacency is not a measured party-wall map.

Supported roofs are flat, gabled and the existing supported hipped envelope.
Mapped total height and roof height give an exact body/roof split. If roof rise is
unknown, the existing pitch supplies a documented bounded style prior, capped
inside a supplied total height. Floating NaN numeric values follow production
normalization as missing; invalid/infinite values are not promoted to observations.
Mapped roof direction/orientation is currently unsupported and explicitly declines
the phase-1 adapter rather than silently changing that evidence.
Shared roof-material aliases retain their established meaning, including
`wood` → shingle and `stone` → slate; unsupported glass roofs decline. A differing
`_planning_footprint` declines as an infrastructure cut, preventing local clipping
from changing whole-source area admission or roof/spire proportions.

Cathedrals, mapped tower/part assemblies, elevated/playable volumes, multi-storey
conversions, unsupported materials/roofs or conflicting height evidence retain
diagnosed legacy fallback. Their topology and older automatic steeple behavior are
not claimed fixed by this bounded adapter. This is a reason to keep those cases
outside the phase-1 acceptance set, not an assertion that legacy fallback is
verified. A future parts slice must handle them with source-linked geometry.

Accepted church entrances use the actual selected door interval, reserve it before
windows, and use closed generated glazing rather than an extra stock door overlay.
They exclude generic residential driveway, fence, main-street shop promotion and
random brick-row stoop behavior. Existing access geometry is retained when present.
No new graded entrance route, projected porch or property landscaping is generated.
Flat synthetic door fixtures do not establish sloped-site or in-game traversal.

## Review artifacts and validation

`tools/church_preview.py` writes:

- `build/church-stage1/church-review.png`: twelve actual mesh cases, near view and
  lite inset. Left column holds source outline, height, roof, facade material,
  colour and seed constant across all three compositions. Other columns exercise
  an L-shaped source outline and a courtyard. The last row adds the three spire
  types at 15 m total height, with enlarged actual belfry detail and lite insets.
- `build/church-stage1/church-before.png`: explicitly labelled legacy recipe
  replay with the old nonrectangular flat fallback. It is not a capture from a
  historical executable. Its rectangle retains the old repeated tower silhouette
  and can exceed the supplied source height; the new accepted envelopes top out
  at the supplied 9 m for composition controls and 15 m for spire controls.
- `build/church-stage1/church-review.json`: source hashes, source geometry,
  architecture/layout records, near/lite/collision fingerprints, counts and small
  per-case compilation measurements. These timings are synthetic instrumentation,
  not a performance release gate.

Both sheets were inspected. The matched-material column visibly separates the
small paired-pane, tall round-head and broad grouped-glazing compositions. The
L-shaped outlines and courtyard voids remain visible. The family comparison holds
mapped roofs fixed; it does not claim three invented roof silhouettes on one
observed roof. The raster uses approximate material means, without game textures,
lighting, camera/LOD behavior or source-reference recognition acceptance.
The three decorated spires and belfry/louver details were also inspected; the
enlarged insets scale actual mesh triangles for visibility, without changing the
runtime geometry. Lite retains each structural silhouette and cornice.

The focused `test_buildgen_churches` suite currently has 24 tests. Its matrix
exercises three families × three footprints × three stable seeds. It checks
source total height/extent and collider bounds, all supported roof types, common-material composition
differences, near/lite/collision/source-hole coverage, ring rotation/replay/rebase,
reserved entries and opaque shared walls, current use versus fabric, keyword
false-positive geometry and preserved genuine Church Street Garage routing,
unmodified rejected inputs, production NaNs, frozen worker round
trips, no residential driveway/fence/shop, lossless triangle chunking, skyline
height/hole/count parity and a fast unrelated-feature eligibility path. Additional
checks cover three spires × three footprints, stable procedural subset selection,
source-contained decorations and door clearance, explicit roof-height priority,
low-height omission, flat-roof/curated-extent spires, shared material aliases and
whole-source versus clipped infrastructure cuts.

## Shared programme foundation

The next M4 slice now derives the immutable programme described in
`ARCHITECTURE_PROGRAMME_CONTRACT.md`. Church openings use its actual body datum
and a single grid for each merged straight elevation, including collinear source
samples. The near/lite emitter draws that complete run, retaining full windows
and round heads instead of adding artificial trim at digitization vertices.
Supplied party-wall changes stop the run and remain opaque. Emitted wall positions
and triangles are tested equal for equivalent sampled/unsampled straight walls.

Source floor labels remain separate metadata; the first datum stops at the body
below roof/spire reserves. Era, load-bearing structure and condition remain
explicitly unknown. Existing palette and spire hashes use a compatibility bridge,
preserving prior spire selection and physical envelopes. No new eligibility,
source field, mapped part assembly or playable topology is enabled.

The updated sheet is `build/architecture-foundations/churches.png`; its JSON
includes the shared programme and semantic seed channels. It was regenerated and
inspected with the same twelve composition/spire cases. Original specialist source
files are preserved under `build/architecture-foundations/original`.

```powershell
New-Item -ItemType Directory -Force build/church-stage1/tmp | Out-Null
$env:TEMP = (Resolve-Path build/church-stage1/tmp).Path
$env:TMP = $env:TEMP
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/run_tests.py test_buildgen_churches --par 1 --timeout 120 --logs build/church-stage1/tests
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/church_preview.py --out build/church-stage1/church-review.png
```

No game test, reference-photo matching, held-out recognition study, regional
dimension verification, memory calibration or driving/collision activation test
was performed. Mapped source parts/towers, steep entrance fitting and churchyard/site
exclusions remain later work. Publication is outside this task.
