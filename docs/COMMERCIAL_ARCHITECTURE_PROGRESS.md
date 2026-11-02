# Commercial architecture composition slice

Implemented 1 November 2026. This is a bounded M4 building-only slice, not M4
completion or a performance release. No new yards, roads, tenant routes, public
interiors, source wings or parcel boundaries are inferred.

## Geometry and evidence

The existing `office` preset now has three fitted opening compositions:

| Composition | Compatible resolved facade | Actual geometry |
| --- | --- | --- |
| `office_punched` | Brick, stone, render or wood | Tall individual punched openings, substantial piers, narrow floor bands and closed sills |
| `office_ribbon` | Concrete or metal | Long grouped horizontal apertures, repeated mullions, deep opaque spandrel zones and floor bands |
| `office_curtain` | Glass | Taller vertical curtain groups, repeated mullions, thin floor divisions and an opaque end zone |

These correspond to useful historic-compatible, mid-century-compatible and
contemporary-compatible compositions. They are **weak material-compatible style
priors**, not observed construction eras. `FacadeLayout.diagnostics` records the
composition, `ci_style:weak_material_compatible_prior` and `ci_era:unknown`.
Resolved facade observations remain observations of material only. Missing
material evidence remains a fallback; no source construction date is invented.

The new `ci_strip_shops` preset applies only to mapped `retail`/`shop` sources of
300–6,000 m² and one resolved storey. It fits repeated display-glazing groups,
opaque separators and a restrained wall-plane sign band along the resolved front.
It retains one actual reserved entrance. The grouping does not claim observed
tenants, additional public doors, branding or walkable interiors. Smaller or
multi-storey retail retains its previous recipe. Workshop/trade units, logistics
halls and supermarkets retain their existing compositions.

Office windows fit secondary **outer** elevations as well as the entrance face.
Shared walls and exterior obstructions suppress openings using the existing
bounded reservation/terrain fitter. Courtyard voids remain intact; this slice
leaves courtyard elevations opaque rather than inferring a courtyard programme.
Source heights, floors, roof forms, roof directions and explicit materials remain
with the existing evidence and roof solvers. Mapped high-rise offices above twelve
floors retain their established renderer with a diagnosed composition fallback.

New floor bands exist in both near and lite meshes. They remain shallow within
the existing visual envelope, are clipped around every accepted aperture, and
add no collision volume. Source geometry and the physical shell remain governed
by the existing compiler. Tests compare collision arrays across the three office
grammars, check near/lite bounds with and without bands, and retain courtyard
holes in collision. There are no new plan fields or serialized record types.

## Bounds and integration

Office work is limited to twelve floors, sixteen groups per elevation, sixty-four
openings per elevation and 256 optional openings per source building. The primary
reserved entrance survives budget exhaustion. Giant elevations keep plausible
module widths and residual blank wall; optional opening exhaustion is diagnosed.
Existing source members and outlines are never truncated. Strip groups retain the
existing sixteen-module limit. One terrain batch is shared across the work, and
repeated storeys reuse identical exterior reservations and ground samples.

`commercial.office_profile(spec)` identifies eligible office compositions.
`commercial.openings(...)` and `commercial.bands(...)` provide the fitted opening
and shallow subdivision proposals through the existing facade renderer.
`FACADE_IDS` includes the new strip recipe. `IDS` deliberately retains the original
three site adapters, preventing a facade change from enabling a new inferred site
layout. `buildings.doors` must call the commercial resolver for eligible offices
as well as existing `ci_` presets; that integration is included in this source.

The accepted terminal opener has one proposal slot in `facades.plan`, immediately
after reserved door/garage intervals and before commercial fitting. A successful
specialist proposal prevents the ordinary commercial solver from replacing it.
Accepted terminals are excluded from the office profile.

## Review artifacts and measurements

Pre-edit owned runtime/catalogue/tool files are preserved under
`build/commercial-next/original`. The equal-footprint six-building sheets are:

- `build/commercial-next/comparison-before.png` and matching JSON.
- `build/commercial-next/comparison-after.png` and matching JSON.
- `build/commercial-next/legacy-commercial-controls.png` and matching JSON.

The before/after sheets were visually inspected. The office row now shows tall
punched masonry openings, broad horizontal ribbons and vertical curtain groups,
rather than the same window grid with different wall colours. Strip frontage
spans most of its front while supermarket glazing remains concentrated near its
single wider entry. The unchanged nine-case logistics/trade/supermarket sheet has
SHA-256 `b68917b8fa01a04a056b3a05cd651b4af59526614ada54ee4a65bb8eb42c40c1`, identical
to the retained M0 control sheet.

All six comparison sources have a 30 × 20 m footprint. Offices have three floors
and 12 m supplied height; the others have one floor and 6 m supplied height.
Each process records a first pass and five warm samples. The final report contains
source hashes and complete layouts. The following warm medians are synthetic
measurements on this machine; concurrent work and the small sample prevent a
release-grade performance comparison.

| Fixture | Near vertices before → after | Plan/access ms before → after | Near/lite/collision compile ms before → after |
| --- | ---: | ---: | ---: |
| Workshop/trade | 1,010 → 1,010 | 4.16 → 4.32 | 3.00 → 3.32 |
| Strip shops | 2,126 → 770 | 4.30 → 4.44 | 6.42 → 2.41 |
| Supermarket | 950 → 950 | 4.36 → 4.80 | 3.99 → 2.79 |
| Punched office | 5,914 → 5,218 | 3.18 → 7.49 | 9.08 → 7.30 |
| Ribbon office | 5,746 → 2,578 | 3.12 → 4.96 | 7.28 → 5.51 |
| Curtain office | 3,858 → 3,434 | 2.91 → 6.65 | 6.24 → 8.26 |

Office planning now includes exterior obstruction fitting that the old office
pipeline skipped. It costs additional planning time despite fewer near vertices.
This slice does **not** establish the 10% generation gate or driving-frame gates;
the curtain case also increased lite detail and compile time. Collision vertex
counts stayed unchanged for every six-building comparison fixture. Game import,
driving, collision activation, memory and equivalent-coverage performance remain
unmeasured and must pass the integrated gates before broad release.

## Verification

```powershell
$env:TEMP = (Resolve-Path build/commercial-next/tmp).Path
$env:TMP = $env:TEMP
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/run_tests.py test_buildgen_commercial_architecture test_buildgen_commercial test_buildgen_facades test_buildgen_presets test_buildgen_inference --par 3 --timeout 120 --logs build/commercial-next/tests-final
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/commercial_preview.py --comparison --repeats 5 --out build/commercial-next/comparison-after.png
& '../BeamNG.Earth-v2-progressive-20261101/.venv/Scripts/python.exe' tools/commercial_preview.py --out build/commercial-next/legacy-commercial-controls.png
```

Result: **69 tests passed** across five modules. The eight new architecture tests
cover geometry distinction, era uncertainty, strip-route restraint, source
height/roof/footprint conservation, rectangular/concave/courtyard cases, stable
seeds, translated frames, shared-wall suppression, aggregate detail/terrain bounds,
repeated resolution, detached worker round trips and near/lite/collision behavior.

Reference-based era selection, part-level history, dedicated workshop roof
grammars, richer strip entry assemblies, signage assets, shading systems,
regional construction packs and observed/held-out visual acceptance are deferred.

The later [shared composition foundation](COMMERCIAL_FOUNDATION_PROGRESS.md)
records merged elevation runs, aligned floor grids and bounded structural trim.
Its before/after measurements supersede the first-slice geometry counts above.
