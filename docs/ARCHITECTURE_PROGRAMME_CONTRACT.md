# Shared architecture programme contract

Implemented in `server/buildgen/programme.py` for the M4 composition foundation.
These records derive from an existing resolved building spec and validated source
footprint. They do not change source selection, physical access, floor allocation,
roof fitting, tower admission or building plan schema 14. No persistent cache or
new worker queue is introduced.

## Records and provenance

`derive(spec, party_walls=())` returns a frozen `Programme` with relative floor
datums, merged elevation runs, source floor-label observations and separate facts
for function, structure, era, vocabulary and condition. The source identity and
existing appearance seed supply stable semantic identity; caller-local XY never
enters semantic seed keys. Source identifiers longer than 512 characters become a
bounded tagged SHA-256 value without changing accepted geometry.

Function and facade vocabulary retain the existing semantic/resolution provenance.
Facade material is not evidence of load-bearing structure. Structure, construction
era and condition therefore remain explicit `unknown` facts with `None` values and
`source_*_not_retained` provenance. A modern/period-looking composition is not an
observed construction date; an appearance/condition seed is not measured wear.

`FloorDatum(index, bottom, top)` refers to the already resolved body, relative to
its existing volume base. It is not a global elevation, source floor label or new
playable storey. Each interval ends at or below `spec.height`. In a church with a
spire, that wall/body height already excludes the space reserved for its roof and
spire, so no floor is allocated inside those volumes. Inconsistent pre-existing
floor height/count is clipped to the actual wall top and diagnosed; the foundation
does not stretch the body or add another storey to make labels agree.

The existing observed `num_floors`, `min_floor`, `level` and
`num_floors_underground` are retained separately in `source_levels`. Signed
minimum-floor/level labels do not shift datums or invent basements. If the existing
height resolver chose a different count from a source observation, the programme
records that distinction explicitly. `is_underground` and `has_parts` are not
promoted to observations: the existing feature-cache Boolean representation loses
the distinction between missing and observed false. Construction/heritage dates
are not newly fetched or inferred.

## Continuous elevations and fitted grids

`ElevationRun` contains one straight, oriented boundary interval. Contiguous
collinear source edges merge, including a ring-wrap join, while actual corners,
separate rings/holes and party-wall label changes stop the run. `EdgeMember`
records retain every original edge and its run-relative start/end offsets. Source
geometry is not simplified or repaired by this operation. `Programme.run(boundary,
edge)` resolves any member edge; `run.locate(along)` maps an accepted run position
back to an actual source edge/local offset. Internal member boundaries use
half-open ownership; the last member includes the run endpoint.

`fit_grid(length, bay, width, ...)` returns frozen `BayGrid` and `Bay` records:

- `mode='fill'` distributes complete bays over available wall spans;
  `mode='centered'` preserves a nominal centered pitch.
- `reserved_mode='reflow'` fits free spans around actual reservations;
  `reserved_mode='omit'` preserves one lattice and removes blocked bays.
- Width clearance (`gap`) and reservation clearance (`reservation_gap`) are
  explicit. Width equal to bay pitch is valid with zero clearance when wrapping
  already accepted whole frontage modules.
- `project_grid()` projects a grid to original edge-local coordinates while
  retaining global bay indices. It is a geometric utility, not permission to emit
  artificial window jambs at digitization vertices. Actual church, terminal and
  commercial facade emitters use a single merged-run elevation for complete
  apertures. `translate_grid()` wraps accepted module positions without refitting.

Church layouts derive once and use the shared first floor datum and merged runs
for their real near/lite wall emitter. Terminal openings consume the same programme
passed by the common facade planner, with centered run grids and actual entrance
reservations. Commercial families consume the same records through their common
facade/detail integration. Windows do not restart at collinear source samples;
party walls remain opaque and actual corners retain complete fitted margins.

## Seed migration and bounds

`seed(spec_or_programme, channel, subkey='')` provides independent deterministic
channels: `function`, `structure`, `era`, `vocabulary`, and `condition`. Subkeys are
bounded semantic text/integer tuples, not arbitrary Python objects or coordinates.
`legacy_seed(spec, channel, legacy_key)` is an explicit migration bridge using the
exact earlier appearance hash. Existing church spire presence/kind/sizing, church
palettes and terminal bay choices use that bridge so introducing shared records
does not reshuffle accepted physical assemblies or their prior looks. New detail
choices may use the separated channel hashes.

Records/helpers bound resolved floors to 120, source edges/runs to 4,096, bays per
grid to 256 and reservations to 256. Grids admit finite run lengths up to 100 km;
specialist admission limits remain much narrower. Datums use the actual finite
body envelope. A process-local LRU retains at most 128 immutable derivations; this
is a working-set optimization, not a persistent source identity or cache contract.
Unsupported optional derivations fall back through the facade composition path
with diagnostics; they do not require a new physical tile or topology. These are
engineering bounds, not researched regional dimensions or calibrated frame gates.

## Validation

Focused tests exercise clipped datums, source-label separation, explicit unknown
era/structure/condition, independent channel hashes and exact legacy bridging,
collinear merging/party-wall breaks, reservation modes and caps, complete projected
coverage, detached immutable worker round trips, long IDs and invalid inputs.
Specialist tests additionally compare emitted church wall positions/triangles and
complete terminal apertures under collinear source resampling. Existing source
height/roof/hole, spire, collision, skyline and eligibility tests still apply.

Original touched specialist files and their hashes are preserved under
`build/architecture-foundations/original/manifest.json`. Updated specialist sheets
and JSON records are `build/architecture-foundations/churches.png` and
`terminals.png`; they include actual derived datums/runs/provenance. The sheets
were visually inspected. They are synthetic mesh reviews, not game, recognition,
memory, performance or grounded-traversal acceptance.
