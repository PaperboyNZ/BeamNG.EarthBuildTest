# Advanced building generation: upstream review

This iteration targets upstream `dev` at `52e37245`. It consolidates the building
work previously reviewed in fork PR #2, including the 3 November Minimum preset,
default settings, door, handover, sidewalk and parking/context fixes.

## Player behavior

Simple remains the default. Select Advanced under Pause > BeamNG.Earth > World
and choose a quality ceiling under Graphics. Advanced starts at Minimum for new
settings; existing saved choices and explicit graphics presets are preserved.
The UI explains that higher Advanced settings are experimental and costly.

Advanced adds 64 regional themes, deterministic architecture and materials,
roofs and facades, commercial and residential variation, access, driveways,
parking, landscaping and weathering. Optional prepared zoning, roof-colour and
site catalogues enrich the result but are not required or bundled as personal
datasets. Detailed capabilities and incomplete specialist work are recorded in
[the implementation checklist](GENERATION_IMPLEMENTATION_CHECKLIST.md).

Seven quality levels run from Minimum through Ultra. Minimum uses compact
textured facades and a single final visual pass while retaining source footprints,
holes, height envelopes, regional identity and essential access. Other levels
provide progressive detail and adaptive refinement. Existing visuals remain
until replacements are ready; generation mode, quality and physical policy have
separate cache/output identities. Native chunk limits and frame-budgeted imports
remain in place. The experimental shared admission gate was removed; this branch
uses upstream worker scheduling and existing process/cache budgets.

## Review map and dependencies

- `server/buildgen/`: immutable plans, evidence, regional inference, geometry,
  quality, progressive products, roofs, facades and access.
- `server/sitegen/`, parking, grading and vegetation: site identities, connected
  surfaces, ground fit, shared-site records and clearance.
- `server/buildings.py`, `blockworker.py`, `roads.py`, `earthd.py`: compilation,
  worker context, cache keys, runtime switching and publication.
- Lua building/road/physical-handover modules and the settings UI: staged imports,
  replacement ownership, distant coverage and persisted choices.
- Materials, shader hooks and packaging: shared building textures and runtime
  dissolve/weathering support; Shapely >=2.1,<3 is a server dependency.

This PR includes the existing opt-in runtime profiler because generation scopes
import it directly and streaming reports feed it. It stays disabled until enabled
each session. The later standalone profiler UI refresh is outside this scope.
The separate road-performance PR #676 is also excluded. A trial merge against its
`529aa44b` head conflicts in `server/blockworker.py` and `server/earthd.py`; preserve
building arguments and road telemetry when merging them together. Historical
documents describing a stacked profiler PR are superseded
by this directly-to-dev submission.

## Measurements and acceptance limits

[Minimum measurements](MINIMUM_BUILDINGS.md) report warm and first-execution
generation costs, triangle counts and material-primitive tradeoffs. They are
offline measurements from before final integration, not FPS or startup claims.

The recorded Christchurch follow-up retained context, geometry and evidence
digests while avoiding duplicate ring canonicalization. A non-intersecting parking
query stopped preparing 537 unused patches. The captured Auckland sidewalk corner
now has matching complete visual/collision coverage, and intersecting pavement
fits above the drawn terrain. [Follow-up evidence](PLAYTEST_FOLLOWUPS_20261103.md)
records those comparisons and their limits.

Native visual review, driving/collision acceptance, live quality handovers and
startup performance remain pending on the final revision. Earlier loading
timeouts are not declared resolved. Corrected sidewalk collision meshes may be
denser; their engine rebuild cost needs measurement. Global statutory zoning,
surveyed parcels and every specialist building type are not claimed complete.
