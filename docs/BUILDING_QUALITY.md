# Building quality ladder and performance audit

3 November 2026: **Minimum** now sits below the six levels described here. See [MINIMUM_BUILDINGS.md](MINIMUM_BUILDINGS.md) for its compact geometry and separate physical policy.


The six detailed levels were introduced on 2 November 2026; Minimum was added
on 3 November. Ultra retains the full roof, weathering, parking and shared-ground
pipeline. See [the current upstream review guide](ADVANCED_BUILDINGS_REVIEW.md)
for the integrated scope and validation limits.

## Quality contract

The six settings combine visual ceilings with optional site policies. They do not change source footprints,
heights, floor counts, seeds, regional selection, roof forms, courtyards, mapped
materials or essential entrance/garage support. Optional paths, inferred commercial
sites and decorative planting differ at the lowest settings; their collision and
exclusion plans rebuild together through the existing atomic handover. Major
supports, deep openings, projected bays, landmark silhouettes, window positions,
colour families and inexpensive shared surface textures remain recognisable.
No building is dropped to meet a quality budget.

| Setting | Added work and fidelity | Expensive work omitted |
| --- | --- | --- |
| Very Low | Complete lightweight buildings, resolved roofs, regional paint, window grid, broad structural facade bands, essential site surfaces and major roof equipment | Small commercial trim planning, minor facade components, shallow recesses, closed trim returns, rainwater assembly and roof microdetail |
| Low | Additional regional/commercial facade components and panel rhythms as shallow faces | Close surround geometry, shallow recesses, sills, fine site trim and rainwater assembly |
| Medium | Recesses and closed simple returns on the first two storeys; structural/deep openings remain three-dimensional at every height; simple upper apertures stay overlays | Upper shallow aperture depth, full surround/sill components, fine site trim, rainwater assembly and rooftop microdetail |
| High | Full upper facade depth, closed component returns, surrounds, sills, corners and fine access/site detail | Gutters/downpipes, complex roof flashing and small rooftop clutter/equipment detail |
| Very High | Closed simplified gutter and downpipe silhouettes on eligible low roofs | Full gutter channels, falls, elbows, collars/brackets, complex flashing, small rooftop clutter and equipment inset panels |
| Ultra | Existing complete generation: full rainwater assembly, flashing, rooftop clutter and equipment details | Nothing removed from the previous current method |

Each row adds capabilities to the one above. A church, tall tower or simple shed
need not gain geometry at every setting: absent/inapplicable features stay absent.
Window density is not randomly thinned and architectural inference never changes
with the quality setting. Source-constrained roofs are not replaced by boxes.
The transient initial shell still uses the existing cheap complex-roof proxy;
that proxy is never a final quality level.

Shared material normals, colour aging, roof stain control and detail UVs remain
at every level. They use shared materials and participate in the visual identity.
This change does not claim shader/GPU savings from disabling material effects.
Very Low omits inferred front paths and decorative native planting; Low restores
those and keeps the cheaper site policy. Medium and above restore inferred
commercial frontage planning. Explicit mapped sites remain supported throughout.
See [the lean pipeline measurements](LEAN_BUILDINGS_20261102.md) for current costs.

## Adaptive performance at every level

`buildingQuality` selects the ceiling. `buildingAdaptive` is a separate boolean,
enabled by default for all six levels. New settings default to Simple generation with Minimum quality for Advanced; saved quality
choices and explicit overall graphics presets retain their intended values. The existing overall graphics presets map
Low/Medium/High/Ultra/Extreme to building Low/Medium/High/Very High/Ultra. Very Low
is available independently. Existing saved Light becomes Low, Adaptive becomes
Ultra with adaptation, and Full becomes Ultra without adaptation.

| Ceiling | Refinement reach cap | Fast travel enter / leave | Recovery after pressure | Facade group cap / cost units |
| --- | ---: | ---: | ---: | ---: |
| Very Low | 150 m | 16 / 8 m/s | 6 s | Tile batch / 60,000 import vertices |
| Low | 200 m | 18 / 9 m/s | 5 s | Tile batch / 40,000 import vertices |
| Medium | 250 m | 20 / 10 m/s | 4 s | 8 / 6,144 |
| High | 350 m | 22 / 12 m/s | 3 s | 6 / 4,096 |
| Very High | 500 m | 24 / 13 m/s | 3 s | 4 / 3,072 |
| Ultra | 640 m | 26 / 14 m/s | 2 s | 2 / 2,048 |

The effective reach is the smaller of the profile cap and the user's refinement
distance. Existing camera FOV/resolution projection and enter/keep hysteresis
apply, using representative features of 0.30/0.25/0.20/0.16/0.14/0.12 m as the
ceiling rises. This is demand estimation, not per-feature screen-space culling.

New work falls back to Low (Very Low stays Very Low) during fast travel, missing
physical tile coverage, terrain pressure, or a worker taking over five seconds.
It recovers after the quiet interval. A detached camera's demand is independent
of an unrelated fast car, while coverage/worker pressure still applies. Optional
upgrades alone do not perpetually restart recovery. Already completed detail is
retained under automatic pressure. Explicitly lowering the selected ceiling
requests replacement visuals; raising it requests refinement of nearby tiles.

Even at Very Low, smaller work groups, coverage priority, bounded chunks and the
existing client frame governor apply. All tiers share the existing import limit,
cost estimates, urgent collision priority, engine debt handling and atomic group
replacement. No competing frame scheduler or fixed FPS target was introduced.
Profile budgets are initial measured-policy choices, not a hardware guarantee.

## Pipeline audit and policy

The benchmark records fixture planning, immutable-plan freezing, shells,
near/reduced geometry, collision and encoding separately. The publication audit
uses the production progressive publisher and actual CDAE writer. Full runtime
profiling now exposes additional named building stage timers; essential mode
does not collect their timings. Nested inclusive times overlap and must not be
summed as if they were exclusive costs.

| Pipeline step / implementation | Cost finding and policy |
| --- | --- |
| Input acquisition, context/evidence, topology, road clipping (`ingest`, `topology`, `context`, `road_conflicts`) | Network/cache/real-data latency is not measured by the synthetic audit. Correctness and stable identity remain mandatory at every ceiling. Source-hashed caches retain their existing invalidation rules. |
| Regional/use/material/height inference (`compiler`, `inference`, `presets`, `environments`, regional catalogues) | Measured within fixture planning, before geometry. Resolve once; do not reroll or simplify semantics on quality changes. |
| Roof form, outline and solution (`roof_outline`, `roofs`, `roof_edges`, regional/commercial roofs) | Shared cached solutions preserve the silhouette across representations. Existing process and job caches remain bounded. Full profiling records roof-solution cost. |
| Facade/programme/layout planning (`facades.plan`, `programme`, residential/commercial/city grammars) | Retained in immutable accepted plans. Tiny commercial trim planning is skipped at Very Low. Opening placement remains shared across tiers. |
| Terrain grading, access and shared-site coordination (`access`, `driveways`, `automatic_sites`, `sitework`, `sitegen`) | Essential access is preserved; optional site policies have separate cache identities. Reuse physical products within a policy and safely replan across policies. New timers expose access/frontage/site coordination. |
| Stock planting (`landscaping.native_props`) | Skip inferred decorative planting at Very Low. Other tiers retain deterministic fitting/exclusion; boundary reuse and vectorized obstacle distances reduce placement cost. |
| Plan freezing (`plan.freeze_items`) | Measured separately; detached immutable records are shared by visual and physical compilation. Architectural identity is invariant; optional site policy is part of the accepted physical identity. |
| Early shells (`progressive.shell`) | Skipped at Very Low/Low; higher tiers retain fast coverage and atomic publication. Never a final substitute for valid specialised geometry. |
| Lightweight facades / coarse LOD | Low and Very Low compile and publish this final product once, with no second encode or tile-wide lite spool. Higher ceilings reuse lightweight arrays as their final coarse LOD. |
| Near facade geometry (`facades.draw`, `city.draw`, regional/residential emitters) | Dominant cost for large ordinary blocks. Medium preserves street depth while flattening shallow upper openings. High restores full detail. Repeated city pane and pier clipping sweeps now reuse local tuples, with byte-identical mesh output. |
| Window surrounds, sills, closed component returns (`components`, `details`, `facades`) | Meaningful geometry at close range; progressively introduced at Medium/High. Shared component batching is preserved. No extra per-window game objects. |
| Rainwater (`details.rainwater`) | A notable low-house CPU cost. Omitted through High, silhouette-only at Very High, original full assembly at Ultra. |
| Flashing and rooftop extras (`details.roof_caps`, `commercial_roofs`, legacy clutter) | Small high-cost details are reserved for Ultra. Major equipment/roof panels remain in lightweight form; no change to source roof forms. |
| Site surfaces and trim (`access.draw`, `sitework.draw_details`) | Essential entrance and garage surfaces remain at all levels. Fine visual restraints/rails enter at High. Optional path/site surfaces follow the physical policy. |
| Surface aging (`weathering.apply`) | Measured in each visual profile and timed in full runtime profiling. Retained as a bounded shared visual treatment rather than adding per-building materials/textures. |
| Collision and collider boxes (`buildings.collision_mesh`, `collider_boxes`) | Independently compiled and cached. Transitions within Medium–Ultra reuse physical hashes/bytes; crossing optional site policies rebuilds complete matching collision. Never omit collision to meet a visual budget. |
| Mesh assembly, splits and LOD (`build_parts`, `split_mesh`, `split_with_lod`) | Final import caps are 60k/40k/16k/12k/10k/8k vertices across the six tiers. Split oversized buildings without discarding triangles; coarse triangles are distributed once. Profile group sizes bound batches, not a single emitter's execution time. |
| UVs, normals/tangents, native encoding and writes (`buildings.write`, `cdae`) | Baseline in-memory encoder timing is separate from actual publication timing, which also includes detail UVs, file writes and metadata. Avoid duplicate encoding; retain final-file adoption. |
| Cache/refinement (`products`, `productcache`, `revisit`) | Separate quality keys, including safe Very Low/Very High storage names. Accepted plan/physical product is keyed by essential/path/full site policy. A downgraded or mixed progressive job cannot populate the requested higher-quality cache. Cache misses still use the complete safe planning path. |
| Transport/import/retirement (`progressive`, client `buildingprogress`, `roads`, governor) | Keep bounded polling, revision tokens, cancellation and shared frame admission. Old complete geometry stays visible until replacement is ready; far coverage and collision handover remain authoritative. Native-game timings remain unmeasured here. |

## Deepening-quality workflow

1. Classify a new feature as identity/physical, major visible structure, close
   detail, or microdetail. Identity/physical requirements belong to every tier.
2. Add visual-only work at the lowest tier where its visible benefit justifies
   its measured cost; keep the previous Ultra output as the regression reference.
   Provide a simpler representation when depth/silhouette is important.
3. Measure planning, emission, assembly and publication separately. Record
   vertices, triangles, material primitives, file bytes and first-final latency,
   not just one aggregate generation time. Material draw calls may plateau even
   when triangle counts fall.
4. Test all six tiers for stable bounds/identity, valid meshes, matching collision for each site policy,
   unique caches, rising/falling settings, pressure recovery, free camera and
   cancellation. Run the existing client import/handover/governor regressions.
5. Deepen from an accepted plan through `products.refine`; retain the physical
   product and replace only complete visual groups. Do not generate all six
   complete meshes in sequence: Low/VL use shell → final; higher levels use the
   existing shell → lightweight → selected-final progression. This avoids paying
   for intermediate detail that may never be shown.
6. Compare identical seeds/cameras in the contact sheet, then drive the same
   dense urban, suburb, industrial, steep access and shared-site routes in BeamNG.
   Capture cold/warm generation, queue age, imports, p50/p95/p99 frame time and
   memory. Tune profile thresholds only from that evidence.

The offline checks are complete; native visual/driving, GPU frame-time, dense
real-data and long-session memory acceptance remain open. Future improvements
should target measured residuals (including shared material draw calls and
accepted-cache misses) before adding more geometry. Do not omit essential support or change regional identities to obtain a favourable benchmark.

## Reproduction and evidence

From the selected playtest, use its `.venv/Scripts/python.exe`:

```text
tools/benchmark_building_quality.py --output ../artifacts/building-quality/tiers.json --tiers very_low low medium high very_high ultra --repeats 9
tools/audit_building_quality.py --output ../artifacts/building-quality --baseline-city ../artifacts/building-quality/original/server/buildgen/city.py
tools/run_tests.py test_buildgen_quality test_buildgen_products test_buildgen_progressive test_building_streaming test_buildgen_detail_demand
```

On a restricted Windows host, point TEMP/TMP at a writable workspace directory.
The live profiler regression harness additionally needs local process/loopback
access. Original files, baseline fingerprints, per-function profiles, timing
samples, source hashes, test logs and the comparison image are retained under
`../../artifacts/building-quality`. See `QUALITY_PATCH.json` at the package root
and `measurements.md` in that artifact folder for the final measured results.

Restart the Earth server and BeamNG through the existing **Play latest
buildings.bat** launcher to load the matching server/mod. Open Earth settings →
Graphics → Building generation quality. Source hashes invalidate obsolete
generated products; the quality preference and adaptive toggle persist normally.
