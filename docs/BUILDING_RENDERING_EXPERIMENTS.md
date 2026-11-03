# Reusable components and rendering experiments

Reusable window surrounds, closed sills and pipe profiles are integrated into
the editable generator. Distant facade baking and reduced shadow detail are
implemented as an isolated A/B laboratory, with no change to normal streaming,
the current playtest package or its launcher.

## Reusable construction components

`server/buildgen/components.py` stores geometry independently of position,
orientation and paint. Templates are stamped into the existing mesh batches;
they add no game objects or material instances. Separate cap/reveal vertices
preserve hard normals and UV seams. Pipe ends stay capped, sills retain their
undersides/end returns, and sun hoods keep their original projection.

The caches are bounded to 256 surrounds, 256 sills, 32 pipe profiles and 512
orientation/UV transforms per worker. Their topology has fixed small sizes.
Window dimensions normalize subtraction roundoff at 1e-12 metres to avoid
separate cache entries for mathematically identical sizes. This is far below
the resolution of the exported float32 positions.

The benchmark compares current code against an in-memory version with only the
component emitters restored. Concurrent trim-frame caching, facade planning
and block paint-grid changes therefore remain in both sides. Results and every
timing sample are in `build/component-rendering/components-benchmark.json`.
Both fresh component caches and warm caches are measured. These are geometry
timings, not FPS measurements or full streaming latency.

Across all 64 regional houses and 192 block variants, 512 near/lite comparisons
retain identical triangles, materials and vertex colours. Maximum measured
position difference is about 5.1e-13 metres; UV differences are also below 1e-10.
Source snapshots and the isolated facade patch are in `build/component-rendering`.

## Distant facade baking

`server/buildgen/facade_bake.py` bakes actual resolved facade surfaces and stock
textures. It samples base colour, normal, roughness, metalness, ambient occlusion
and night emission. Source normal maps are reoriented into each card's tangent
frame. Source mips, edge padding and complete output mip chains are included.
Identical resulting facade images share an atlas entry.

Only opaque, outward-facing surfaces within 4 cm of a footprint wall can be
flattened. Continuous wall coverage is checked geometrically before replacement;
pixel coverage alone is insufficient. Roofs, footprint holes, undersides,
projecting/sideways faces and other unselected triangles retain their original
attributes. Missing textures, open surfaces, specialized envelopes and excessive
resolution requirements keep the original mesh. The office fixture exceeds the
512-pixel face budget and is deliberately retained.

The final diagnostic package contains these results:

| Fixture | Original lite triangles | Baked triangles | Material primitives before / after |
|---|---:|---:|---:|
| House | 110 | 46 | 4 / 3 |
| Regional block | 406 | 10 | 5 / 2 |
| Courtyard house | 182 | 48 | 4 / 3 |
| Office retained by budget | 664 | 664 | 7 / 7 |

**This is not ready for synchronous high-speed streaming.** The 16 unique
facades use six uncompressed 1024-square diagnostic maps, about 32 MiB including
mips. Cold baking took roughly 0.28–1.01 seconds per accepted building on this
machine, before atlas publication. That is much more work than ordinary geometry
generation. The smaller meshes do not establish a net memory or frame-time win.

Before production integration, use supported GPU texture compression, budget
resident texture bytes, reuse facade bands/components across buildings, and
bake during background/cache preparation. A missing baked asset must fall back
immediately to existing lite geometry. Never overwrite a live shape or atlas;
use immutable content identities. Materials must be loaded before publishing
their referencing shapes, and their lifetime must follow resident shape users.
Night appearance, mip transitions and grazing-angle quality require native-game
acceptance. The prototype has no automatic runtime activation.

## Reduced shadow detail

The laboratory preserves the complete visible near mesh. Small flat surround
strips, sills up to 12 cm deep and pipe profiles up to 4 cm radius receive
equivalent private materials with `castShadows=false`. Four recess closures
around each pane remain shadow casters, avoiding light leaks. Roofs, primary
walls, arches, canopies, larger projections and all unclassified geometry retain
their shadow casting.

| Fixture | Original candidate triangles | Retained shadow triangles | Reduction | Extra visible material primitives |
|---|---:|---:|---:|---:|
| House | 1,912 | 916 | 52.1% | 1 |
| Regional block | 4,546 | 2,494 | 45.1% | 1 |
| Courtyard house | 2,836 | 1,120 | 60.5% | 1 |
| Office without classified micro-components | 2,270 | 2,270 | 0% | 0 |

These are potential shadow-submission counts, not measured GPU savings. Object
culling/preparation still occurs and the extra visible material primitive has a
cost. Close views and low sun may reveal missing tiny shadows. Keep full shadows
near the camera unless native testing establishes an acceptable transition and
distance. The experiment does not disable all building shadows or rely on an
unverified shadow-only TSStatic flag.

The installed game's editor exposes `Material.castShadows` in
`lua/ge/extensions/editor/materialEditor.lua`. The official
[TSStatic documentation](https://docs.beamng.com/modding/levels/level_classes/tsstatic/)
describes shape/LOD and material-remapping controls, while the
[material format](https://documentation.beamng.com/modding/file_formats/materials/)
documents texture bindings and material targets. These support the probe's
integration approach; they do not establish its performance or visual result.

## Native comparison package

`build/component-rendering/lab-final/building_render_lab.zip` is an isolated
diagnostic mod, not a replacement Earth build. Its SHA-256 sidecar and
`verification.json` accompany it. Twenty CDAE shapes, sixteen private materials,
six complete-mip atlas maps and all local texture paths have been verified.
Source game textures are read from the local installation during export.

Install the ZIP using the normal BeamNG mod workflow, load a flat map and use
the GE Lua console:

```lua
extensions.load('beamngEarth_renderLab')
extensions.beamngEarth_renderLab.setMode('lite')
extensions.beamngEarth_renderLab.setMode('baked')
extensions.beamngEarth_renderLab.setMode('near')
extensions.beamngEarth_renderLab.setMode('shadow_detail')
dump(extensions.beamngEarth_renderLab.inspect())
extensions.unload('beamngEarth_renderLab')
```

Four fixtures appear ahead of the vehicle at fixed positions. Hold the camera
and sun fixed when switching. `shadow_geometry` shows only retained caster
geometry as a diagnostic; it is not a shadow-only rendering mode. Probe objects
do not collide, do not save into the level and are deleted on unload. Private
source-material clones keep the probe's day/night changes isolated from the map.

Compare near/lite/baked at normal and grazing angles, above courtyard openings,
at dawn and night, and from both driving and free cameras. Measure GPU frame
time, shadow pass time, material submissions, import stalls and texture memory.
Native-game appearance/performance validation has not been performed.

## Reproduce and verify

```powershell
python -B tools/benchmark_building_components.py
python -B tools/building_render_lab.py --game 'D:/SteamLibrary/steamapps/common/BeamNG.drive' --out build/component-rendering/lab-final
```

The benchmark uses the original facade snapshot retained under
`build/component-rendering/original`. The exporter requires the installed game's
stock textures. It writes only into its output directory and does not install or
enable the mod.

108 Python tests pass across components, baking, facades, regional blocks and
polish, roofs, city buildings, churches, progressive generation and chunk
transport. Twelve Lua checks cover probe modes, lifecycle, collision isolation,
private material lighting and cleanup. Those are offline checks, alongside the
512 geometry comparisons, and do not substitute for renderer acceptance.
