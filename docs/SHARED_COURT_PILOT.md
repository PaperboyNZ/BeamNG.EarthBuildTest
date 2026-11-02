# Explicit shared-court pilot

`sitegen.shared_courts` fits supplied, source-linked common ground pavement. It
does not infer property boundaries, courtyard holes, roads, entrances or parking.
It is bundled with the schema 23 r6 playtest and disabled in its normal launchers.
This is a bounded runtime integration pilot, not native/shared-route acceptance.

The optional `BNE_SHARED_SITE_RECORDS` environment variable names a version 1
`SiteGraph` JSON file. It accepts at most 1 MiB / 128 sites. Supported sites have
a canonical source-extent ENU frame, pinned revisions, association extent,
complete exclusions, at most 32 building/lot members and eight common resources.
Each `shared_circulation` resource has the site's producer, explicit consumers,
and one physical extent with the same identity and a measured ellipsoidal height
interval. Building references use the explicit source-ID join namespace
`beamng-earth/source-building-id`; this is not an inferred provider identity.
Height intervals are not source floor labels. Interfaces and level memberships
require the future shared solver and are unsupported here.

The complete association must lie inside one geotile, with a conservative margin;
all declared buildings must resolve within it. The site emits once there. Its
physical surface lives in that sector's colliding deck container, and all its
building consumers share that same container lifetime. There is no independent
cross-sector reference scheduler. Cross-sector sources are diagnosed and never
clipped into competing per-tile producers.

At most eight sites, 2,048 terrain points and bounded output are accepted per
tile. Each site's terrain work is at most 1,024 points on a two-metre interior
and boundary sampling grid, with at most 128 total source polygon vertices. A
single plane fits all its resources, with at most 5% slope and 15 cm sampled
fill. These are authored capability bounds, not regional design standards or
proof of native tyre contact. Terrain is not modified. Holes, full XYZ frame
transforms and closed top/bottom/boundary geometry are retained. Connected road
interfaces, flush/eased edges and advertised vehicle routes remain separate work.

The fitter also checks existing physical surfaces, full building footprints and
accepted landscaping. Generated optional roadside props are cleared using the
existing clearance mechanism. Common surfaces add bounded vegetation masks and
hole-aware occupied-resource bounds. The existing sector staging, collision
rebuild and deletion-debt protocol owns their complete physical container.

A failed supported fit, missing member or exhausted tile budget fails the proposed
content build, preserving the previously accepted state through existing M2
failure handling. A catalogue is pinned into the process generator identity;
restart the server after editing it. A changed file cannot silently rebuild new
content using stale records. File dependencies also invalidate accepted-plan reuse.

`tools/review_shared_court.py` creates an explicit two-building synthetic graph,
an offline review sheet and a production-encoded native shape. The retained
`build/world-architecture-programme/m1-shared-court-review-r2` review has one
96-vertex / 32-triangle court, one producer, two consumers, an open source hole
and 360 terrain probes. The 12 focused tests cover conservative failure, identity,
budgets, source order, full XYZ rebasing, closed geometry, seams between resources,
typed worker/cache round trips and unchanged physical files through full/lite
upgrades. These checks do not establish native appearance/contact/performance.
