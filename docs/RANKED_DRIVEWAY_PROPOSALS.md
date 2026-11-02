# Ranked local driveway route proposals

Implemented 1 November 2026 as a bounded M3 continuation on the existing eligible
building/garage-opening path. This changes actual driveway selection; it does not
add another site catalogue, change garage circulation or activate large complexes.

The old resolver chose its nearest geometrically compatible street mouth before
checking the full driveway outline, terrain and grade. If that route failed, it
did not try another mouth. The resolver now freezes and ranks at most **four**
complete local route proposals per eligible garage. Measured compatible sidewalk
interfaces rank before direct road/verge alternatives. Each straight source
frontage can propose its aligned mouth and two gentle lateral alternatives, up
to 20% of the setback and at most 1.5 m. These are procedural route alternatives,
not claims of mapped entrances or rights of access.

`sitegen.portals.StreetPortal` and `RouteProposal` contain detached tuple values;
source arrays cannot change an accepted proposal. Coordinates are normalized at
1 nm for deterministic local arithmetic, far below the 1 mm seam target. They are
frame-local planning values, not persistent canonical identities. Candidate
selection retains only the best four proposals while scanning the bounded nearby
inventory. Different source crossing references are not deduplicated simply
because their endpoints coincide.

`portals.simplified_lines` removes only redundant collinear nodes at a 1e-6 m
tolerance before both door frontage selection and driveway segment indexing.
It retains per-line metadata, endpoints, meaningful bends and supplied height
changes, returning detached read-only arrays. Empty/one-point entries retain the
old ignored-input behavior. This is planning normalization, not road smoothing;
the renderer still receives original source geometry.

At most 64 nearby sidewalk segments and 64 nearby road segments are admitted per
building after redundant-node removal. An oversized inventory is declined as a
whole with a diagnostic before proposals are used; no input-order-dependent
first-64 subset is accepted. Source order, reversed polyline direction, dense
collinear road nodes and translated frames are regression-tested.

All proposed physical strips and optional pedestrian branches are constructed
before commit. Their terrain points join **one callback for the whole resolver**,
reusing the existing shared terrain sampler. There are nine full-width stations
(left, centre, right), plus at most ten optional branch samples: at most
`4 * (9 * 3 + 10) = 148` requested points per eligible building before exact
sample reuse. Alternatives do more work than the previous single choice; a
worker/frame-time performance gate has not been established by this change.

Candidates retain the **18 m length / 15% grade** limits and existing fill limits.
Complete strip footprints must avoid source buildings (holes preserved), other
accepted access solids, road carriageways and unsupported walking crossings.
Known property boundaries and exclusions constrain the full outline; explicitly
unknown exclusions do not count as free space. An unsupported legacy obstacle
inventory suppresses optional fitting rather than aborting other building
geometry. Motorways/motorway links cannot acquire inferred entrances. Narrow
walks, protected pedestrian ramps, folded/curved mouths and overlapping footpath
runs remain conservative exclusions.

The resolver tries candidates in rank order after terrain fitting. A rejected
nearest footprint or grading profile can yield a connected second option. Only
the selected full route commits its immutable access solids, optional walking
link and curb cut. Candidate diagnostics record `selected` or a rejection reason;
the aggregate audit records one final outcome per eligible building, including
when earlier candidates failed. Both existing and new mouth intervals include
their flare when checking neighboring reservations during commit, so disjoint
internal strips cannot silently flatten the refuge between their crossings.

Replanning uses detached views of prior cuts; it does not remove physical pieces
before replacement. A successful replacement retires only that component's cuts
and access record. If every candidate fails while a previous accepted route is
still present on the input `AccessPlan`, that route, its cuts, metadata and green
patches remain installed, with `driveway_replan_retained_previous`. This local
atomicity is not the separate M2 engine resource/occupancy lifecycle.

Two disconnected components of one source can share source ID and seed. Their
local replan keys therefore also include component geometry, normalized against
the common source-component origin; deterministic priority includes that same
geometric tie-break. These initial keys keep components' cuts/records separate
across input reversal and whole-scene translation. Accepted plans retain their
installed local owner token in the existing diagnostics tuple; entrance refits
carry it forward, so partial-member replanning replaces only that component.
Fresh components reserve existing walk/drive owner tokens before allocation. A
collision allocates a distinct frame-local component suffix rather than claiming
the installed sibling's cuts or records, including on unsuccessful replanning.
These are local replan tokens, not canonical persistent IDs or cross-job resource
ownership. Reconstructing a component without its installed token cannot infer
authority to retire a previous component's physical route.

Surviving lawn/garden patches remain clear of the selected physical route and
pedestrian link. Their bounded bushes/rocks and the hardscape exclusion producer
are retained; optional detail does not cause a physical route rebuild.

## Verification and measured limits

The owned runtime originals were copied before work to
`build/architecture-foundations/original/`: `driveways.py`, `access.py`,
`sitework.py` and `landscaping.py`. The original driveway source SHA-256 is
`9cf3cb2fd1abb4452883aa9ab91ef69d752992a70f5eb2966feddc5eeefb68ca`.
`access.py` now carries installed local driveway tokens through entrance refits;
`sitework.py` and `landscaping.py` were not changed in this slice. Root integration
adds the road-normalization hook in `buildings.doors`; no building plan schema
field was added. Audit metadata now identifies both segment checks and ranked
full-route checks rather than describing all rejections as sidewalk-segment tests.

```powershell
New-Item -ItemType Directory -Force build/architecture-foundations/tmp | Out-Null
$env:TEMP = (Resolve-Path build/architecture-foundations/tmp).Path
$env:TMP = $env:TEMP
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/run_tests.py test_buildgen_driveways test_sitegen_portals test_generation_baseline test_buildgen_access test_buildgen_landscaping test_buildgen_garages test_sitegen_surfaces test_sitegen_hardscape --par 3 --timeout 120 --logs build/architecture-foundations/tests-access-final
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/driveway_proposals_preview.py --out build/architecture-foundations/driveway-proposals.png
```

The focused selection/telemetry run passes **33 tests**: twenty-one driveway,
four portal and eight existing baseline tests. Regressions cover nearest rejected
by grading/footprint/source hole then second valid, unknown terrain/no early cut,
controlled roads, unknown inventories, invalid legacy geometry, over-budget
inventory/order, repeated success, failed replan retention, same-source component
ownership (including partial-member replacement and fresh siblings beside
installed routes), both neighboring flares, reversed source direction, dense roads,
translation, detached worker round trips and green preservation. The integrated
access/landscape/garage/hardscape run is recorded separately in the test logs.
The final focused logs are in
`build/architecture-foundations/tests-access-owner-final/`.

The reviewed sheet `build/architecture-foundations/driveway-proposals.png` plots
actual runtime surfaces for clear, obstacle, grading and missing-terrain cases.
Its JSON report loads the preserved original driveway resolver and compares
all nine baseline access cases. Every baseline retains triangle counts, triangle
indices and crossing counts. Maximum coordinate changes are approximately
`2.7e-15 m` for connected/obstructed and `3.6e-15 m` without a footpath; the other
six cases have zero coordinate delta. These outputs are geometrically equivalent
within floating-point precision, but are not claimed byte-identical.

The two new localized obstacle/grading fixtures gain accepted second routes;
their triangle counts intentionally increase. The normal connected fixture uses
195 provider sample points across entrance/driveway work versus 144 previously.
A thirty-case warm synthetic clear-frontage run measured about 5.47/6.19 ms
p50/p95 for the preserved resolver versus 8.18/11.56 ms for ranked planning, with
the same current surrounding source. These measurements document added bounded
work, not a speedup, calibrated worker limit or in-game performance acceptance.

**Remaining M3 gate:** this slice does not independently validate a crossing-only
mouth plus a short receiving area after a farther internal route fails. It never
emits or labels such a result `crossing_only`; failures remain untested for that
purpose. Mapped vehicle-port adapters, a building/site/station proposal coordinator,
complete design/check-vehicle sweeps, curved frontage and game tyre/contact/seam
acceptance also remain open. Successful existing complete driveway strips do not
establish those broader gates.
