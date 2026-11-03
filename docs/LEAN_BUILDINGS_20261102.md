# Lean building generation, 2 November 2026

Very Low targets near-Simple generation while preserving footprints, seeds,
regional families, colours, roof forms, opening layouts and essential entrance/
garage support. Low is the default for new settings; explicit saved values survive.

## Measured scene

120 fixed-seed buildings across 12 real tile boundaries: 40 houses, 30 apartments,
20 offices/towers, 15 shops, 10 warehouses and 5 churches. One serial worker,
warm-up plus three measured alternating-order runs, Ryzen 7 5700X3D. Timings
include planning, access, site work, planting, freeze, all progressive passes,
collision and real CDAE encoding/publication. Source acquisition, whole-world
terrain/road generation, engine imports, shaders and frame time are excluded.

| Mode | Median seconds | Shape writes |
| --- | ---: | ---: |
| simple | 0.567 | 24 |
| very_low | 0.825 | 24 |
| low | 1.520 | 24 |
| medium | 4.982 | 267 |
| high | 5.983 | 318 |
| very_high | 6.142 | 326 |
| ultra | 6.500 | 363 |

Very Low is 1.45 times Simple. Before this change, Very Low took 3.517 seconds
and wrote 177 shapes in the same scene (one measured baseline sample). The
ladder increases in cost but is not linear: Low to Medium is its largest jump.
The user accepted that spacing for this update. Higher-tier timing differences
are small enough that they should not be presented as reliable percentage gains.

## Work removed and reused

- Very Low/Low build final tile batches directly: no throwaway shell, intermediate
  facade pass or disk spool. Vertex caps still bound each engine import.
- Very Low uses texture-backed commercial facades while retaining residential
  opening placement and structural identity. It omits inferred paths/planting.
- Low restores facade components, front paths and planting. Medium adds full
  inferred commercial sites; higher levels progressively add close detail.
- All full-site tiers reuse footprint polygons, frontage subtraction and tile
  clipping, vectorize equivalent cell coverage/intersection tests, and fit each
  parking plane once. Plant placement reuses boundaries and vectorizes distances.
- Publication computes pivot/relief from encoded bytes, avoiding a second file
  read per progressive shape. File encoding and warm-read guarantees remain.

Essential/path/full site policies have distinct physical product identities.
Cross-policy refinement falls back to a full safe build; existing resident
geometry remains until its complete replacement is ready. Medium through Ultra
retain byte-identical visual and collision output against the previous source in
this scene. Every Advanced tier retains the same recorded architectural identity.

## Validation and limits

The candidate passed 156 test executions across 12 affected modules, including
64 regional identity/layout checks, site policy cache separation, cancellation,
access, landscaping and CDAE regressions. The default-setting regression also
covers saved Ultra preservation. Native driving and frame-time acceptance is
recorded separately; these offline numbers are not FPS or whole-terrain timings.

The larger 60k/40k low-tier imports reduce overhead but can increase the duration
of a single engine import. The existing client governor remains authoritative;
native frame-time testing is necessary before claiming smoother streaming.
