# Building math and surface-detail audit — 2 November 2026

Current regional detail authoring: [25 architectural modifiers and spawn rates](REGIONAL_ARCHITECTURAL_MODIFIERS.md).

Current roof authoring: [roof proportions, attic windows and dormers](ROOF_PROPORTIONS_AND_ATTICS.md). Shared inference limits apply across all 64 regional profiles and five contemporary families; tall eligible roofs receive fitted attic details. Historical checkpoint statements below retain their original scope.

Profiled regional houses, all 192 block variants, city buildings and specialist
structures. Existing topology, roof planes, wall openings, terrain/access and
collision regressions informed the changes. The final whole-build test run was
skipped at the user's request; earlier focused checks passed before packaging.

Changes:

- Scalar pipe reference-frame calculations replace repeated tiny NumPy cross
  products. Existing beam reference tests preserve positions, UVs and winding.
- Roof UV frames resolve once per supporting plane. Roof treatments use a bounded
  immutable-key cache; grammar lookup avoids resolving unused decoration values.
- Complex-roof flashing reuses its polygon coverage mask.
- Known-size flat mesh streams use direct numeric conversion, preserving dtypes.
- Simple-roof 2–6 mm folded overlays defer to existing roof normal maps and the
  actual plane crease. Complex valley flashing retains geometry.
- Inset sash/transom/panel patterns keep textured faces without hidden 12 mm
  returns. Real openings, sills, shutters, sun hoods, porch supports, fascia,
  soffits, gutters and collision remain geometric.

No new tessellation/displacement shader or per-building texture atlas is enabled.
Existing siding, brick, roofing and weathering textures already provide surface
relief without geometry for each board, brick or tile.

Five warm repeats after a cold pass, on this machine:

| Fixture group | Before | After | Improvement |
|---|---:|---:|---:|
| 64 regional houses | 656 ms | 470 ms | 28.3% |
| 192 regional blocks | 3,524 ms | 3,365 ms | 4.5% |
| 12 architectural/specialist cases | 74 ms | 73 ms | 0.8% |
| 9 city cases | 86 ms | 84 ms | 1.7% |

These are synthetic CPU generation timings, not game FPS. Small differences are
within ordinary timing noise. House/block near meshes have 3.1%/0.35% fewer
triangles, including the requested facade correction. Collision position and
topology hashes match exactly in this performance comparison. The intentional
imagery-wall inset is checked separately and is not mixed into those timings.

`validation/building-math.json` contains the recorded comparison. The latest
playtest preserves all 64 expanded palettes and the legacy-compatible DDS fix.
