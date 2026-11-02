# Building streaming implementation — 2026-11-01

Implemented against the current schema-18 source. City authoring, regional recipes, road clearance, site/access planning, collision geometry, shape pooling and exact geotile placement remain in use. Existing playtest packages and launcher manifests were not replaced.

## Implemented

- Skyline coverage now means a successfully imported child or confirmed empty child, rather than receipt of a message. Each skyline's 16 children hand over together. Near, far and skyline visibility changes happen in the completion frame. Coverage is cached between state changes instead of rescanning children for every far object each frame.
- Cached/non-progressive building chunks use complete-set visibility. Progressive groups retain their existing complete-group handoffs. Repeated messages, cancellation, restart and missing imports do not expose partial replacements over the fallback.
- Near building revisions retain one complete previous visual set until their replacement is ready. Far/skyline revisions retain one previous complete mesh, including after an import failure. Fallbacks follow rebases and retain their pooled shape slots until actual object deletion.
- One in four eligible import frames is reserved for far coverage while near work is queued. The existing shared one-import-per-frame cap and urgent collision/rebuild priority remain enforced.
- Adaptive generation switches new work to lite facades at 22 m/s (49 mph), and permits full refinement again at 12 m/s (27 mph). Already completed full buildings are retained. Adaptive content outside the refinement radius starts lite. The existing 14-second, up-to-2-km forward road corridor continues to provide lead time.
- Accelerating can downgrade a running full job between 12-building groups. Leaving the retained view also limits optional facade work. Physical/access generation continues; obsolete completions do not allocate new game objects. Missing road/skin/exact coverage takes priority over optional refinement.
- Full and lite content have distinct persistent cache keys. A full job downgraded partway through is not stored under the full cache key. Final metadata records actual detail. Content identity now includes shape-byte hashes, rather than depending only on bounds and metadata.
- Quality-only replacements reuse physical objects when the nonvisual geometry and metadata match, including across different facade chunk counts. Required exact variants and returns to base geometry still use the existing replacement path.
- Lite and full compilation are interleaved per group, reducing the temporary lite working set and publishing the first finished full group sooner. Regional trim frames are solved once per elevation; regional block section width is computed once per building. Geometry and material choices are preserved.
- Building settings now expose **Light / Adaptive / Full** and **100–640 m refinement distance**, separately from draw distance and engine object detail. Presets use Light/200 m, Adaptive/250 m, Adaptive/350 m, Adaptive/500 m and Full/640 m respectively. Changes affect new work and refinement; existing full buildings are not downgraded merely to reduce quality.

## Verification and reproduction

Run from this checkout with its Python dependencies:

```text
python -B tools/check_building_streaming.py
python -B tools/benchmark_building_streaming.py
```

The check runner uses LuaJIT via the optional `lupa.luajit21` runtime in `build/lua-runtime`, or an installed Lupa. It uses workspace-local temporary files and deterministic offline fixtures. Real map downloads and native rendering are excluded.

Results: **102 Python tests and 708 Lua assertions passed**. These cover group completion, import budgets, starvation, failed imports, retransmission, restart, rebases, pooled slot retention/release, physical identity, exact variants, speed hysteresis, running-job downgrades, obsolete delivery suppression, settings validation and cache separation. Existing city/regional/road-clearance tests pass. Direct array comparisons cover near and lite geometry for all 64 regional themes and all 192 regional block designs.

`build/streaming-optimization/benchmark.json` records alternating before/after measurements, a warm-up and seven measured runs. It verifies full mesh arrays, native LOD arrays, materials, bounds and group mapping against the saved implementation. These are synthetic compilation measurements; they exclude planning, downloads, disk writes, engine imports and rendering. They are not in-game FPS results.

Median milliseconds from the final run:

| Fixture | Previous full | Updated full | Fast-travel lite | First full group, previous → updated |
| --- | ---: | ---: | ---: | ---: |
| 25 houses | 210 | 207 | 26 | 119 → 108 |
| 64 regional buildings | 999 | 738 | 123 | 345 → 195 |
| 24 regional blocks | 408 | 392 | 95 | 244 → 207 |

The strongest full-detail gain is the regional trim workload (26% less compilation time, first final group 44% sooner). The simpler house workload is approximately unchanged. Fast-travel compilation costs about 4–8 times less than updated full detail in these fixtures. Exact sample timings and geometry fingerprints are in the JSON artifact.

Original production sources and their SHA-256 hashes are retained in `build/streaming-optimization/original` and `baseline.json`. `source.diff`, `source-hashes.json` and `regression.log` provide review and verification artifacts.

## Remaining work

Update, 2 November: revision dissolves are now implemented in
[BUILDING_DISSOLVE.md](BUILDING_DISSOLVE.md). The following describes the earlier
complete-set-only implementation; native renderer acceptance remains pending.

**Dither/fade is not implemented or validated.** This change supplies a stable, complete-set handoff, not a blend. The repository's earlier renderer investigation found no exposed TSStatic shape-LOD crossfade, and its instance-opacity probe did not establish a working path. The procedural-building design explicitly calls for a verified fade, rather than an invented shader contract. See `V1_2_DESIGN.md` P2/P3 and `PROCEDURAL_BUILDINGS_V2.md` for the existing evidence and probe requirements.

A native test still needs to establish a shared alpha-tested material/instance path and complementary masks, then check roofs, glass, shadows, depth, pooled shapes and native LODs during a 150-mph drive, braking, reversal and rebase. No native BeamNG run was performed; the changes have not been packaged or deployed into a playtest.

Refinement currently re-enters the existing road/content builder, while the client reuses unchanged physical objects. A separately cached immutable planning layer and persistent per-group geometry cache would avoid more repeated server-side work. Full final mesh arrays also remain live until final writing; only the additional lite working set is reduced here. Oversized generic/tall-building fallbacks, rainwater/cap generation and engine import/draw-call costs remain further optimization targets. No architectural detail was removed to claim a speedup.
