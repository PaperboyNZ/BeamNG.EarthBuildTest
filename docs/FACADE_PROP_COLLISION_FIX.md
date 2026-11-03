# Fitted roof edges, facade trim and relocated prop collision — 2 November 2026

Included in `BeamNG.Earth-v2-consolidated-r3-20261102`.

The vertical strips on the reported weatherboard houses were facade components:
the `timber_veranda` style painted shallow accent posts directly onto the front
wall, without a projecting veranda roof, deck or actual post structure. They
were not caused by the weathering texture. This pass removes those unsupported
posts from both close and lite representations. Modest rectangular timber houses
retain narrow painted corner boards, scaled to the elevation and storey height,
joined around corners and omitted where an opening would cut them into stubs.
Existing projecting porch assemblies retain their supports. The later Alpine
and East Asian review also removes guessed posts between window gaps. Horizontal
joinery in those families now blends toward the wall colour; corner boards and
joined bands have closed 35 mm depth instead of a dark flat-strip appearance.

Corner boards continue around suitable timber buildings. The previews are
synthetic geometry reviews, not native lighting screenshots.

## Roof edges across styles

The existing ML/imagery input route now treats ordinary rectangular pitched
building footprints as roof outlines. Walls inset beneath that outline, retaining
the complete style-appropriate overhang inside the mapped roof extent. Door,
foundation, facade and collision planning use the inset wall. Ground sampling
for the new corners is batched. Road clipping operates on the roof outline and
refits the walls beneath it. Explicit wall-outline inputs keep their dimensions.
Complex and very narrow imagery outlines use conservative flush-edge fallbacks.
Building-plan schema is now 20; source identity also invalidates old mesh caches.

All 64 regional profiles and the contemporary families use shared construction
families. Timber, alpine and tropical treatments have broader eaves; compact
masonry and urban treatments have shallower edges. Eaves and gable verges have
separate dimensions, stable per-building variation and small-building limits.
Visible edge depth is typically 160–240 mm according to roof covering, with a
100 mm lower limit on small buildings. This represents the visible roof assembly,
not the sheet-metal gauge. Fascia colour follows the building's trim palette.

Standard gables and hips, gambrel, mansard, saltbox, shed and broad-eave variants
extend their original supporting planes. Ridges and slope breaks stay fixed;
the shed's plane and wall infill resolve together to retain the mapped total
height. Fascia, sloped soffits and gutters use the same surface. The old fascia
calculation could disagree with an explicitly mapped roof rise. Close and lite
meshes now both contain the fascia and underside. Existing flat-roof coping and
parapet recipes remain appropriate to their regional material treatment.

Complex outlines retain conservative flush edging around recesses and courtyard
holes; this pass does not buffer roofs across those voids. Very distant skyline
and initial placeholder meshes remain simplified. Dedicated church, terminal,
city and parking-deck kernels retain their existing roof assemblies. The supplied
chart is a reference for forms, not a claim that new dormer, butterfly or M-shaped
roof solvers have been added.

Construction references: [BRANZ's eave guidance](https://www.branz.co.nz/design-build/articles/adding-eaves)
distinguishes sloped and boxed soffits; [MBIE's sleepout guide](https://www.building.govt.nz/assets/Uploads/projects-and-consents/constructing-a-sleepout-that-does-not-require-building-consent-guide.pdf)
illustrates supported eave and gable extensions. Dimensions here are bounded
visual recipes, not structural sizing or international code-compliance claims.

Tests cover all regional styles, contemporary families, rotated roof variants,
coverage, supporting-plane agreement, mapped heights, matching fascia endpoints,
lite/close underside retention, vertex budgets and courtyard preservation.
`tools/roof_edge_preview.py` renders nine representative style/form combinations.

## Prop collision

Roadside relocation already recreated Forest items, using the same new transform
for rendering and the collidable item. The missing pieces were collision refresh
requests: removing a solid item during a partially completed tile cleanup, a
solid-to-nonsolid transition, or complete clearing could miss the refresh. A
relocation also used the normal six-second collision batching delay.

Every removal of a solid Forest item now requests a collision refresh, including
budget-limited early returns and clearing. The request reserves the next safe
import-free collision slot instead of waiting for the ordinary six-second timer.
Terrain-swap quiet periods and the existing bounded frame-room check still apply;
this is not an unsafe synchronous rebuild inside the pathway callback. New
render-only decorations stay noncolliding, and distant props keep the existing
collision-range policy.

Regression tests model cached physics separately from visible Forest objects.
They cover lamp/bin/hydrant/bench moves, restoration, old-position removal,
distance changes, partial deletion, and relocated geotile collision after a
rebase. A scheduling test verifies that a requested refresh receives its own
frame without a mesh import. Native vehicle contact still needs a playtest.

Restart BeamNG and the Earth server, then run `Play latest buildings.bat`.
The server's source identity changes with the facade generator, invalidating
old generated-building content through the existing cache keys. All 64 regional
palettes and the r2 DDS compatibility correction are included.

The final integrated regression run and server smoke were skipped at the user's
request to deliver a playable build immediately. Earlier focused checks and
offline previews are recorded; they are not full validation of this final build.
See [math and surface-detail audit](BUILDING_MATH_AUDIT.md) for optimization scope.
