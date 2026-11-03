# Consolidated playtest — 2 November 2026

Run `test_v2.bat` in this package, or `Play latest buildings.bat` beside it.
Close the previous Earth server and restart BeamNG before switching builds.
This frozen package includes the server and matching mod; its local environment
is prepared. The ZIP installs dependencies through the usual server launcher.

Included changes from the recent development chats:

- Style-aware pitched-roof overhangs, material-scaled edge depth, connected
  fascia/soffits and gutters, with edges retained in close and lite meshes.
- Imagery-derived rectangular roof outlines retain their mapped extent, with
  inset walls, fitted entrances and foundations underneath. Schema 20.
- Faster pipe/roof calculations and mesh conversion, bounded treatment reuse,
  and texture-based shallow details. See `BUILDING_MATH_AUDIT.md`.
- Unsupported dark facade posts replaced by fitted painted corner trim where
  appropriate; relocated solid props request a prompt, safely scheduled
  collision refresh, including partial cleanup and clearing.
- Five contemporary house families, the 70/20/10 regional/contemporary/global
  house mix, varied windows and roof colours, with mapped overrides preserved.
- All 64 regional themes, 192 regional block fixtures, and city office/hotel
  families with their entrances, landscaping and terrain integration.
- Expanded palettes: 16 wall colors for each of the 64 regional themes, plus
  China North's 16-color brick override. Open `docs/regional-wall-palettes.html`.
- Stable house-to-house weathering, muted surfaces, lower-wall aging and shared
  rain-streak/mottling detail on existing wall and roof materials.
- Building generation and component-cache improvements, complete-set LOD swaps,
  speed-aware refinement and Light/Adaptive/Full detail controls.
- Six regional streetscape treatments, fitted commercial/industrial service
  entrances, grass verges, continuous rear footpaths, gutters and eased crossings.
- Smooth bounded corner geometry, matching crossing collision, and roadside
  furniture clearance that also handles neighbouring tiles arriving later.
- Whole lamp assemblies and relocated bins, benches and hydrants; resolved
  pathways reserve space without blanket-removing roadside decoration.
- Spatial building groups, all-lite-first generation, bounded temporary reuse,
  and missing-coverage priority. Completed buildings use the static renderer's
  native LOD path; separate generation-revision swaps remain atomic.
- The world tour: 128 places across 75 countries, covering all 64 styles, with
  repeatable capture batches, retries and A/B comparison tools. Open
  `World tour.bat` for the itinerary; `World tour.bat validate --routing` checks it.

The final regression suite, package geometry comparison and server handshake were
skipped at the user's request. Packaging records source/archive identity and
includes earlier focused findings; this final build is not fully verified.
See `validation/`, `BUILD_ID.json` and the report beside the package.
BeamNG driving, visual acceptance and live tour captures remain pending.

Facade baking and reduced-shadow experiments remain opt-in lab work, disabled
in normal runtime. Future checklist items and unfinished dithering are not
advertised as implemented. See `BUILDING_RENDERING_EXPERIMENTS.md` for findings.
Existing dated packages are retained for comparison.

See [investigation and next checklist priorities](ROADSIDE_STREAMING_WEATHERING.md)
for root causes, measured CPU tradeoffs, remaining dithering work and native checks.

The 2 November texture compatibility correction is documented in [the weathering hotfix](WEATHERING_HOTFIX.md). Native loading and performance acceptance remain pending.

The latest pass fits roof edges across styles, preserves appropriate timber trim,
and synchronizes relocated prop collision: [implementation and scope](FACADE_PROP_COLLISION_FIX.md).
