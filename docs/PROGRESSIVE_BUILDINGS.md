# Progressive building display and mesh budgets

Implemented 1 November 2026. This extends the schema 12 commercial, residential
and landscaping snapshot. Rendering protocol `buildingProgress=1` is independent
of the immutable building-plan schema. Source hashes invalidate older compiled
revisit content automatically.

## Visible stages

For a matching v2 client using road geotiles, workers publish twelve-building
replacement groups while a tile is still generating:

1. Solid walls and resolved roof geometry/colours, immediately after building
   inputs and ground heights are available, before road/access detail compilation.
2. Lightweight facades and resolved access surfaces. These meshes are reused as
   the final shapes' reduced LOD; they are not generated a second time.
3. Detailed facades, roof edges, site features and landscaping, as each group
   finishes. Finished meshes are reused by the final road-content writer.

The first stage still depends on the existing footprint, elevation and context
pipeline. It does not remove current map-data dependencies or integrate live
statutory zoning. Specialised structures without an ordinary inferred footprint
skip the solid proxy and appear when their valid geometry is available.

Workers publish complete CDAE files and an atomically replaced status manifest.
The manifest is outside BeamNG's file watcher when running in its user folder.
The server polls on poses, caches unchanged manifests and sends at most four
changed groups per job per poll. Superseded stages coalesce to the latest stage.
Warm revisit hits use their already-finished content directly.

The client shares the existing one-mesh-import-per-frame limit with road meshes.
Urgent collision work retains priority. A partial replacement stays hidden until
all its pieces are imported; the previous complete group remains visible until
that swap. Existing far geometry remains until near coverage is complete.
Already-imported final groups are adopted into the final tile without importing
duplicates. Exact anchor variants use the normal final import path.

Door props wait for their host tile's building visuals. Ordinary furniture is
unchanged. Previews are render-only: collision is still supplied by the existing
final collision pipeline, including its vehicle safety checks.

Revision tokens and stage ordering reject stale updates. Failed imports retain
the last complete group; final content can still import normally. Cancellation,
unload, rebases and server restart release transient objects/slots. Completed
token history is capped at 256 records; idle previews have a 120-second expiry.
Preview files use the session's generated-asset lifetime, so cold progressive
generation uses more temporary disk space than final-only generation. Cancelled
status manifests outside the game folder participate in the staging age sweep.

## Geometry and materials

- Near visual chunks are limited to 20,000 vertices. No building is discarded to
  meet the import budget. Collision remains separately chunked at 60,000.
- Every final generated visual chunk receives its reduced LOD. Oversized single
  buildings preserve all detailed triangles and distribute coarse triangles
  exactly once across their pieces. Shared conservative shape bounds coordinate
  the pieces' projected-size LOD selection. Detail-only pieces use a native empty
  coarse mesh instead of retaining expensive near geometry at distance.
- Existing far-building and skyline representations remain. LOD reduces geometry;
  it does not imply a proportional reduction in material draw calls.
- Garage/shutter slats and flat paving joints use two shared 256x256 opaque,
  vertex-tinted textures. They replace per-slat and per-joint geometry. Existing
  window atlases are retained. No per-building texture baking, alpha blending,
  dynamic texture synthesis or new per-frame geometry calculation was introduced.
- Reveals, sills, fascia, gutter profiles, ridge/valley folds, steps, graded surfaces
  and raised edge restraints retain geometry where depth or silhouette matters.
  Their fine detail is omitted from the reduced LOD.
- Roof solutions are shared across loading stages with a job-local cache capped
  at 2,048 entries and 8,192 source footprint vertices; it is released with the job.
  The existing smaller process LRU remains for ordinary generation.

The detail textures can be regenerated offline with
`python tools/building_detail_textures.py` (Pillow and NumPy).

## Measured fixture and validation

A synthetic 240-house scene on this workstation, with the roof-solver cache cleared
before each pipeline, measured:

| Measurement | Result |
| --- | ---: |
| Final-only geometry compilation and CDAE writing | 4.40 s |
| Progressive compilation and publication of all stages | 5.07 s |
| First shell published | 110 ms |
| First lightweight facade group published | 2.07 s |
| First detailed group published | 2.50 s |
| Final mesh chunks: final-only / progressive | 37 / 40 |
| Near / reduced-LOD vertices | 670,088 / 39,106 |
| Near / reduced-LOD triangles | 300,870 / 18,824 |
| Largest visual chunk | 19,984 vertices |
| Near / reduced-LOD material primitives | 310 / 307 |
| All-stage temporary output | 43.5 MB |

Reduced LOD uses 5.8% of near vertices and 6.3% of near triangles in this fixture.
Progressive generation adds approximately 15% to this measured compilation/write
cost. Common planning/access, road/collision writing, network delivery, game
imports and GPU rendering are excluded. These are single-run measurements, not
FPS, percentile latency or a worldwide performance guarantee.

Offline checks cover early delivery before a worker future finishes, colour and
height retention, LOD completeness and bounds, empty native LOD encoding, final
file reuse, worker cleanup, cancellation, anchor changes, pooled-slot release,
far/near handover, failed imports, final adoption and deferred door props. Existing
building, commercial/site, landscaping, driveway, road, native shape and client
protocol suites are also exercised.

In-game acceptance remains necessary: inspect cold-load stage changes, garage
textures, path joins, large-building LOD transitions, collision timing and dense
street frame times with the matching server and mod. Legacy/anchor-road mode
retains its existing non-progressive generation path.

## Subsequent source import pricing — 2 November 2026

The editable source now passes each progressive chunk's estimated synchronous
import cost to the existing frame governor. The estimate uses bytes, vertices,
material primitives and observed import duration. It changes that governor's
token requirement and capacity for the waiting unit; it does not add a scheduler
or budget. The existing shared import cap, urgent collision path, engine debt,
quiet/heavy frames, far coverage and final-group adoption remain authoritative.
Unused cost hints expire after one frame. A denied quote cannot import a later,
different candidate after supersession or cancellation.

Missing coverage remains first. Within the same coverage class, groups waiting
five seconds precede younger work in arrival order. This prevents indefinitely
deferred expensive work under continuous cheap arrivals. Estimates can be wrong;
they do not preempt an engine call or guarantee an import/frame-time bound.

Progressive timing now uses the project's elapsed wall-clock stopwatch, rather
than process CPU time. `roads.status().buildingProgress` reports current pending
groups/parts and oldest queue age, queue peak, aggregate/worst import and queue
durations, first actual group exposure latency, superseded parts, and native
imports/bytes/milliseconds discarded before exposure. A completed stage hidden
behind aggregate coverage is counted as wasted if superseded without rendering.
Normal retirement of visible geometry is not wasted work. Import and queue
p50/p95/p99 use only the latest 256 attempts, including failed attempts; lifetime
totals remain separate. No per-building history grows with world traversal.

Verification: 112 Python tests and 3,191 Lua assertions pass, including 452 existing
governor assertions and 1,015 pricing/saturation assertions. A 160-group workload
checks cheap-first coverage, latest-stage coalescing, partial cancellation,
failed multi-part replacement and exactly-once slot release. Other checks exercise
real governor debt/capacity, fair waiting, stale quotes, production roads' import
cap, hidden-versus-visible waste accounting and bounded sample rollover.
The retained checkpoint is
`build/world-architecture-programme/p6-priced-import-checkpoint/manifest.json`.
The activated schema 22 r5 predates this source work. Native import/frame, route,
memory and actual renderer-exposure measurements remain pending; engine-model
tests do not establish those acceptance gates.
