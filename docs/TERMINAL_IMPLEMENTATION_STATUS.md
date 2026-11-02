# Terminal classification and facade slice

Implemented 1 November 2026, using building plan schema 14.

`buildgen.terminals` activates two bounded, closed-shell treatments from explicit
retained `class`/`subtype`: `airport_terminal` selects a regional hall;
`airport_concourse` selects a linear concourse. The existing source extraction,
decoded feature columns, `ATTRIBUTE_FIELDS`, normalized evidence and worker plan
retain these fields. This establishes the field path, not the prevalence or
accuracy of those labels in real-world data. Unretained aeroway/mode tags do not
silently activate the adapter.

The shared facade compiler fits entrance reservations and glazing. Regional halls
concentrate glazing at the existing road-selected front; concourses repeat bounded
glazing groups along their long sides. Other sides use sparse high-level windows.
These are public/hall/service composition roles, not evidence of airside/landside
boundaries, boarding gates or restricted areas. No roads, aprons, jet bridges,
canopies or traversable interiors are invented.

Observed total height, floor count, minimum height, footprint holes, supported roof
and materials remain with the existing evidence/roof compiler. The legacy 13 m,
two-storey name default no longer overrides these terminal cases. The two facade
families fit at most 96 openings per building, up to six storeys, 256 source
vertices and 10,000 square metres. Large/multipart assemblies and unsupported roof
forms retain diagnosed ordinary shell fallbacks.

Name-only `Terminal Hotel` and `Concourse Coffee` cases now use their observed
ordinary building use. Explicit freight/cargo terminal labels resolve industrial
use; they do not acquire passenger glazing. Generic terminals and bus/ferry/rail
classes remain neutral mode-specific-facade fallbacks. Bridge, garage, ship, pier
and church routing remains separate. The historical `compiler.specialised`
predicate remains available for compatibility; the v2 planning entry point now
applies the terminal evidence adapter before choosing its compiler.

Tests cover both families, three shapes/seeds, courtyard roof/collision coverage,
same supplied outline/height, facade reservations, worker round trips, translated
frames, keyword and freight controls, unsupported assemblies and infrastructure
names. Run `tools/terminal_preview.py` for the public/opposite elevation review at
`build/architecture-next/terminals.png`, with mesh counts/layouts in its JSON.

This is a building-only implementation slice. Real-map reference recognition,
native texture/lighting review, playable approaches and occupied streaming remain
unverified. It does not close the full terminal plan or M4 release gate.

The shared M4 programme foundation now supplies immutable relative floor datums,
continuous elevation runs and centered glazing grids. The common facade planner
passes one derivation into terminal fitting. Complete openings span collinear
digitization samples without artificial seams or a restarted bay phase; actual
corners and source holes remain separate. Ground-floor entrance reservations omit
blocked modules while preserving alignment with upper-floor grids. The existing
terminal bay hash remains exact through the programme's legacy seed bridge.

Datums derive from the already resolved wall body, not raw level labels. The
programme explicitly records unknown era, load-bearing structure and condition;
source floor-count/level observations remain separate metadata. Existing shared
height resolution can diagnose a conflicting observed floor count; introducing
these records does not change that resolution or infer basements from labels.
Unretained Boolean flags and construction dates are not promoted to observations.

`test_buildgen_terminals` now has twelve focused tests, adding emitted complete
aperture/vertical-grid parity under collinear source resampling and safe optional
programme fallback. The updated public/opposite view sheet and JSON are
`build/architecture-foundations/terminals.png` and `.json`, including the actual
shared records and explicit era status. See `ARCHITECTURE_PROGRAMME_CONTRACT.md`
for API, bounds, provenance and seed migration. Original specialist sources and
hashes are preserved under `build/architecture-foundations/original`.
