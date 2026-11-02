# Roadside, coverage and surface-aging pass — 2 November 2026

This pass is included in `BeamNG.Earth-v2-consolidated-r3-20261102`, together with
the prior integrated streetscape work and the expansion to **16 distinct wall
colors in every one of the 64 regional themes**. China North's separate brick
palette also has 16 entries. The palette catalogue and swatch review are bundled.

## Streetlamps and decorations

The previous clearance pass treated lamp supports and their elevated, offset
lenses independently. A narrow sidewalk's pedestrian reservation could remove
the support while leaving the lens or glow behind. A broad fallback vegetation
mask could also suppress roadside furniture without a resolved access surface.

The server now places lamp assemblies together, regenerates their lenses from
the retained support, and searches nearby positions along the curb or a sampled
verge behind the sidewalk. Whole prop footprints must clear driveways, crossing
flares, walking routes, roads and building footprints. Already-valid furniture
positions are reserved. Terrain must support a relocation; large height jumps
are rejected. Wire spans follow moved supports.

Up to eight validated positions travel with each movable assembly. The client
can choose another when a neighboring tile's precise access masks arrive. It
keeps lenses, point lights and posts together and avoids overlapping assemblies.
Unknown-height coarse vegetation masks do not act as furniture bans. An assembly
with no safe position is suppressed; never blocking an entrance takes precedence
over preserving a prop count. Wired poles cannot move independently of their
compiled span: a late conflict suppresses the affected assembly and wire owner.
Traffic-control signs keep their original placement rules.

## Appearance transitions

Update, 2 November: [building revision dissolves](BUILDING_DISSOLVE.md) now extend
this earlier static-LOD change to independently generated versions.

Completed render-only building shapes previously used `TSStatic.dynamic=true`,
which bypasses the static shape manager. They now use the static path; provisional
shells, roads and collision objects retain their existing path. This makes the
completed shape's embedded detail levels eligible for the installed renderer's
instanced LOD transition path. The official [TSStatic reference](https://documentation.beamng.com/modding/levels/level_classes/tsstatic/)
documents the static-manager distinction. Installed shader inspection also found
GPU LOD alpha and opaque fizzle support.

**This is not a general revision crossfade implementation.** Separately generated
shell/lite/detail revisions still replace complete groups atomically. Native
in-game testing must establish how the current BeamNG version renders embedded
LOD transitions, and check static registration/rebasing/import cost. Smooth
revision blending remains a separate renderer experiment, requiring a supported
per-instance coverage control and bounded overlapping residency.

## Progressive coverage and caching

Groups are now spatially compact (maximum 12 buildings, approximately 64 m center
span, with an estimated work cap). All groups receive lite geometry before full
facades begin. Exact lite arrays are reused during full construction, with a
32 MiB memory cap and temporary spill files cleaned up when the job ends. This
is a job-local cache; persistent revisit caching is still at tile level.

Missing coverage takes priority over upgrades on the client, with nearby tile
demand first. A queued cheap shell survives an early-arriving detailed revision
until that group has coverage. Complex pitched footprints use a cheap capped
footprint shell; holes, minimum height and unsupported special-type safety rules
remain intact. Existing final-stage adoption, collision priority and import caps
remain active.

An isolated three-run CPU comparison, with current weathering enabled in both
modes, produced these medians (milliseconds):

| Fixture | All lite before / after | First detail before / after | Total before / after |
|---|---:|---:|---:|
| 60 houses spread along a line | 414 / 114 | 139 / 146 | 497 / 545 |
| 12 collocated regional block fixtures | 41 / 42 | 189 / 98 | 190 / 183 |

Final geometry, colors and materials matched exactly between scheduling modes.
House group count rose from 5 to 15, and block groups from 1 to 3. This benchmark
excludes map I/O, encoding, native import, rendering and FPS. It establishes
earlier CPU coverage availability for the spread-out fixture, not a universal
throughput gain. The first shell still depends on terrain/source preparation.

## Weathering and palettes

Each building gets stable seeded aging, from recently maintained to visibly
weathered. Wall and roof colors become more muted, with stronger dirt near the
base. The same height-dependent treatment applies to shell, lite and detail
geometry. Color alpha, collision and topology are unchanged.

One shared 256-pixel uncompressed RGBA DDS with a full mip chain supplies fine mottling and
vertical rain streaks to eleven existing wall/roof materials. A second UV channel
uses a six-meter surface projection rather than repeating per atlas window.
It adds eight UV bytes per visual vertex and a shared texture, with no additional
building triangles or per-building materials/textures. Glass/shop/window atlases
retain their texture treatment and receive reduced tint aging. The shared grime
texture has a common strength; building-to-building aging variety comes from
vertex tint. This is a low-cost first weathering pass, not simulated local runoff.

The expanded regional base palettes remain intact before aging. Explicit mapped
colors retain their selection precedence; the weathering pass then affects the
rendered surface. Review `regional-wall-palettes.html` for unweathered swatches.

## Checklist: next work

1. Drive the consolidated playtest in daylight and at night. Check narrow walks,
   adjacent driveways, parked cars, newly arriving tiles, floating accessories,
   weathering brightness, embedded LOD transitions, teleport and rebase behavior.
   Record native p95/p99 frame times and worst synchronous imports.
2. Continue **P1**: cache resolved plans and independent physical/visual products
   persistently, so refinements do not repeat terrain/access planning. Preserve
   collision and access revision identities.
3. Continue **P4**: keep typed arrays through native encoding and measure actual
   allocation/import costs. The existing reuse optimizations are already included.
4. Calibrate **P6** group/import budgets from those native measurements, then
   pursue **P2/P3** bounded coverage and middle-distance representations. Native
   revision dithering needs its own supported-control prototype and acceptance.

Do not enable experimental facade baking or reduced-shadow modes by default.
Automated fixture checks do not replace the native visual/performance acceptance.

The 2 November texture compatibility correction is documented in [the weathering hotfix](WEATHERING_HOTFIX.md). Native loading and performance acceptance remain pending.

The latest pass removes unsupported facade posts and synchronizes relocated prop collision: [facade and collision fix](FACADE_PROP_COLLISION_FIX.md).
