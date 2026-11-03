# Generic industrial and commercial roofs

Broad industrial/commercial tags now choose among flat, shallow gabled,
mono-pitch, offset-ridge and six-facet barrel roofs. Selection is deterministic
and constrained by span, aspect, area, storeys and height. Barrel roofs are
uncommon and require a broad, elongated low-rise hall. Inferred rise is capped
at 2.8 m and a fraction of wall/total height; mapped roof shape, material,
roof height, total height and supported neighbour evidence retain priority.
Specialist classes and building parts keep their existing roof decisions.

Roof equipment uses service-plant, daylight or occasional solar compositions:
HVAC cabinets, ducts, ventilator boxes, access hatches, rooflights and solar
banks. These are visual priors, not surveyed installations. A complete item
must fit at least 1 m inside the occupied footprint, clear other equipment by
0.65 m, and sit on one roof plane. Courtyards, roof breaks and the rendered
mono-pitch overhang adjustment are respected. Regional rooftop structures
retain ownership of their roof area. Legacy random clutter is suppressed on
eligible buildings so it cannot duplicate the new equipment.

There are at most 24 placement attempts and 8 accepted components per building.
The bounded 512-entry layout cache is shared by visual tiers. Near details cost
at most 128 triangles; middle details use at most 20 triangles for large HVAC
silhouettes and rooflight/solar surfaces. Small fittings and panel trim disappear
at middle distance. No extra game objects, materials, textures or collision
detail are introduced. Primary roof geometry remains shared across near,
middle, collision and skyline. Existing source fingerprints invalidate caches;
the serialized plan schema is unchanged.

Validation: `server/tests/test_buildgen_commercial_roofs.py` covers mapped-data
priority, population variety, transformed barrel coverage and compiled shading,
LOD shell agreement, occupied-area/setback/spacing checks, roof support,
determinism through frozen plans, and geometry/cache budgets. The broader roof,
facade, commercial, inference, skyline, product-cache and streaming checks pass.

Run `python tools/commercial_roof_preview.py --out <folder>` to regenerate the
synthetic contact sheet and paired CPU/triangle report. The benchmark compares
the previous flat fallback and legacy clutter path with the new path over 40
industrial fixtures, five warm measured runs, alternating order. It is not an
in-game performance test. The reviewed sample added about 111 near triangles
and 39 middle triangles per building, with roughly 1.2 ms / 0.5 ms additional
CPU generation time respectively. Planning timings are single passes and should
not be interpreted as a speedup. Native lighting, frame times and driving
acceptance remain pending.

The local PR #2 playtest records the installed files and original backups in
`COMMERCIAL_ROOFS_PATCH.json`. Restart the Earth server and BeamNG using the
existing **Play latest buildings.bat** launcher to load the update.
