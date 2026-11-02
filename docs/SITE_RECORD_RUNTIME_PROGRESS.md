# Runtime site-record migration

The source continuation after the r5 playtest uses building plan schema 23.
`buildings.tile_buildings()` now calls `site_data.project_record()` for the same
eligible, unpartitioned catalogue owners as before. The unchanged catalogue and
projection validators run first. Their exact projected geometry is then wrapped
by the immutable `LegacySiteAdapter`, which contains the versioned `SiteEvidence`
and `SitePlan` records. The existing fitter reads boundary, exclusions and measured
ports from those records; frozen worker plans and the typed product cache retain
them. Near, middle and collision emitters consume the resulting accepted solids.

This is a live compatibility migration, not shared-site production. Shared sites,
multi-level ownership and station resources remain unsupported by this adapter.
It rejects resource declarations and interfaces that are not observed legacy
service, parking or pedestrian ports. `surface_validation` remains `unresolved`:
the declarative record does not itself establish physical clearance. The existing
fitter still checks each emitted surface against its complete obstacle inventory,
terrain, reservations and connection constraints.

The exact original ENU origin, including ellipsoidal height, and tile offsets are
retained as `legacy_projected_xy`. These coordinates are not relabelled canonical
ENU. Catalogue owner identifiers remain explicit join keys under a catalogue
namespace; they are not inferred mapped-building identities. Legacy identifiers
outside the record text contract retain the validated old input with a warning,
preserving existing physical output. Infrastructure cuts still remove whole-site
ownership when the source owner footprint changes. Multipart sources still require
a separate common owner and do not acquire a site through this route.

Focused tests compare accepted solids/facades and exact near/middle/collision mesh
arrays with the legacy path; exercise record-controlled interface removal;
reject unsupported statuses/resources; preserve records across frozen plans,
pickle and typed codec round trips; check infrastructure cuts and original-frame
projection; and retain the legacy validator's unknown-inventory rejection.

The continuation now also includes an explicit canonical mapped-ground-court
pilot in `sitegen.shared_courts`. A site owns its common surface and carries
multiple declared building/lot consumers. Source holes remain open; measured
ellipsoidal height intervals and complete exclusions are required. Terrain,
accepted physical surfaces, building obstacles and landscaping are checked before
the whole site is accepted. One fitted plane serves every resource of that site.
The production geotile writer emits the closed surface in the existing colliding
deck container, with canonical provenance, consumer identities and exact masks.
Accepted-plan/physical products retain it across visual refinements.

This pilot only supports associations wholly within one existing closed sector,
with all declared building members resolved there. It does not implement external
sector references, station interfaces, crossings, mixed levels or shared route
search. Failed supported fits fail the proposed tile rather than silently removing
an accepted physical resource. Unknown/unsupported capabilities are diagnosed.
The optional `BNE_SHARED_SITE_RECORDS` catalogue is unset in the r6 launchers;
see [pilot constraints](SHARED_COURT_PILOT.md).

The M1 shared fitting/emission checklist row remains open for broader shared-site
integration. Cross-sector references/residency, proposal collection, station
identity and native contact acceptance remain unfinished. The matching source is
bundled in the schema 23 r6 playtest; the older r5 checkpoint remains intact.
