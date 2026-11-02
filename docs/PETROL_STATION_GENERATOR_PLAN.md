# Petrol station generator implementation plan

Prepared 1 November 2026. Proposed work governed by the [shared specialized building plan](SPECIALIZED_BUILDING_IMPLEMENTATION_PLANS.md) and the existing [pavement and site access plan](PAVEMENT_AND_SITE_ACCESS_PLAN.md). This expands that plan's fuel-station stage into implementation tickets; it does not create a separate site system.

Petrol stations should have varied, coherent canopy, pump, shop and forecourt designs fitted to their actual sites. Compact urban stations, rural outlets and highway facilities must differ in circulation and scale. Functional refuelling is a release requirement for every accepted pump, including after tile streaming and rebases.

## Current behavior and gaps

`server/gasstations.py` already classifies and merges place pins, checks fuel evidence, finds shops and canopies, chooses regional stock assets, fits pump layouts and generates forecourt/access information. `_record` samples terrain independently at prop and interaction positions. `tile_sites` coordinates station records and source-canopy suppression across neighboring tiles.

`gasstations.lua` stages props and interaction areas, retains stations while tiles reference them, refreshes POIs, prewarms regional assets and provides light points. Its current energy list is shared gasoline/diesel, not per-station evidence. These behavior and identity contracts must survive the visual upgrade. New energy types or per-station filtering require an explicit protocol extension and compatibility default, not a color-based inference.

The main gaps are coherent modular identities, layout variety within real bounds, common pavement heights for props/triggers, and shared access/parking reservations. Preserve current confirmation, closure and convenience-brand safeguards. Zoning or a familiar convenience-store name alone must not create a station.

## Proposed layout families

| Family | Layout and appearance | Required evidence and fallback | Phase |
| --- | --- | --- | --- |
| `fuel_compact_urban` | Few islands, narrow but verified circulation, compact canopy/kiosk and modest signs | Confirmed fuel site and fitting envelopes; no assumed extra parcel | 1 |
| `fuel_neighbourhood` | Several fitted islands, shop-side pedestrian connection, short-stay parking only where it fits | Confirmed station with canopy/shop context; omit unsupported parking | 1 |
| `fuel_rural_small` | Sparse islands, restrained canopy or supported uncovered pumps, modest building treatment | Confirmed use; unattended operation requires evidence | 2 |
| `fuel_supermarket_linked` | Forecourt connects to the retail site's circulation; shared branding/material logic where evidenced | Actual site relationship; no duplicate public-road crossing | 2 |
| `fuel_highway_services` | Larger mapped canopy groups and separate convenience/service areas | Mapped service-road access and site support; never cut directly into a motorway | 3 |
| `fuel_truck_facility` | Larger vehicle envelopes, supported clearance, separate lanes and appropriate equipment | Truck-fuel evidence and fitting routes; no color-based diesel/truck inference | 3 |

Family controls functional arrangement, while an identity pack controls canopy fascia, structural treatment, pump casing, shop trim, signs and lighting together. Start with a neutral fallback and pilot NZ/Australia and North American references; expand UK/Ireland, continental Europe and Japan before activating additional reviewed country contexts from the pavement plan.

For each validated pack, provide at least three coherent identities with compatible small/medium/large configurations. Vary fascia depth, column grouping, roof edge, island count, shop-front treatment, material palette and sign format within tested ranges. Never stretch a dispenser, doorway or structural column to make a site fit. Canopy lengths change through fitted bays; stock asset scaling must remain inside reviewed bounds.

Retain source names/brands in metadata. Use mapped-brand visuals only where an appropriate verified asset exists; otherwise use a neutral treatment without relabeling the source operator. Unknown operators may receive a stable fictional identity. A chosen identity applies consistently to canopy, pump and signs; independent random branding is prohibited.

## Plan and fit sequence

1. Confirm and merge station evidence using existing rules. Establish stable station/source IDs and building/canopy membership. Treat ambiguous neighboring stations independently until evidence supports merging.
2. Preserve observed canopy outlines, shop footprints, holes, roads and access. Resolve a bounded allowed region from observed paved extent or surveyed site data; lack of that evidence permits only the existing conservative local fit, not an enlarged invented forecourt.
3. Select up to four compatible arrangements. Reserve road entry/exit, circulation, complete stopping envelopes, shop paths and supported service access before accepting islands. Fit pump/column/island envelopes as a group. Fewer correctly spaced pumps are preferable to blocked lanes.
4. Resolve pavement cells and their boundary heights through shared site planning. Fit canopy columns, island bases, pump bases, shop thresholds and interaction areas to the accepted surfaces. Where a common slab cannot fit the terrain, use supported separate cells or retain a simpler valid layout; do not shear a canopy or bury pumps.
5. Commit geometry, functional triggers, canopy replacement and ownership as one accepted station plan. Generate marks, trim, lighting and optional props from the remaining reservations.

Check entry-to-pump-to-exit connectivity with complete vehicle sweeps and clearances. Pump stopping space must be usable without occupying another pump's service space or a through lane. Match interaction-area position/orientation to the usable fueling side and final pavement; do not rely on independent terrain samples to make adjacent objects agree. Keep unsupported hose simulation outside scope.

Mapped shop façades may receive coordinated entrance glazing, doors, roof-edge trim and shared commercial details. Do not replace genuine neighboring buildings because they lie near the station pin. Suppress only explicitly matched canopy/source geometry after a replacement is accepted and can be streamed correctly; a failed/missing asset must retain a conservative visible fallback.

## Construction detail and site realism

Canopies need consistent roof thickness, underside, fascia, column supports and drainage detail. Preserve credible mapped canopy height and footprint. Keep large roof cantilevers within validated component profiles. Island noses and protective bollards fit full envelopes; collision must match their visible bases. Decorative pump hoses, labels, gutters and lights use shared assets and sensible detail tiers.

Use concrete/asphalt transitions, coherent joints, island curbs, restrained wear and supported drainage features to distinguish forecourt and shop frontage. Do not invent underground tanks, fill points, tanker routes or outlets. Tanker/service areas, car washes, EV areas and food/drive-through facilities require explicit evidence or a separately validated compatible facility recipe with sufficient space; none is a default decoration.

Forecourt markings follow actual movement and regional traffic conventions. Avoid arrows that send cars through pump islands or the wrong access side. Shop walking routes and short-stay parking remain outside pump/service envelopes. Planting belongs at supported perimeter or pedestrian pockets and must respect visibility, maneuvering and pump access.

Use existing material/prewarm/staged-spawn infrastructure. Batch static canopy/shop detail where practical and keep pump interactions as bounded functional records. Proposed initial optional-decoration limits are 32 props and 4 active lights per small station, 64 props and 8 active lights per large station; calibrate these against baseline scenes. Existing essential props are not deleted to meet a decoration quota. Large supported stations are sectorized, and the per-tile aggregate workload still needs a cap.

## Implementation tickets and acceptance

1. **Station plan and parity.** Adapt existing layouts into immutable station records with canonical membership, accepted surface references and component identities. Preserve current IDs, ownership, refuelling availability, preload manifests and tile reference behavior. Extend cache/package inputs.
2. **First complete slice.** Implement compact and neighborhood families, three coherent identities in the first validated pilot pack, and shared placement heights for pavement, pumps and triggers. Preserve the existing regional fallback for unreviewed locales. Deliver actual refuelling parity before adding more families.
3. **Shared site integration.** Adopt proposed `sitegen` access ports, circulation, reservations and surfaces. Reconcile station pads with roads/parking/buildings so there is one pavement/collision owner. Support supermarket-linked sites once shared-complex ownership exists.
4. **Regional and large-site expansion.** Add rural, service-area and truck families with reference-backed dimensions and fit tests. Add optional per-station energy metadata only with a versioned server/Lua change that retains the current default for old records. Treat EV behavior as separate gameplay work.
5. **Polish and streaming.** Review lighting, trim, wear, night appearance, chunk transitions and fallback assets. Ensure plan replacement never leaves a refuelling trigger without its pump or an invisible colliding canopy.

Extend `server/tests/test_gasstations.py`, `mod/tests/test_gasstations.lua`, surface/parking/access tests and new focused station-plan tests. Cover duplicate pins, convenience-only stores, closed stations, missing places data, overlapping neighbors, missing canopy, multiple canopies, one-building sites, sloped/rough terrain, road-edge conflicts, adjacent stations, source canopy across a tile boundary and unavailable assets.

For each accepted pump, test stopping in the supported vehicle, obtaining the refuel prompt and refuelling, then repeat after rebase, neighbor-tile load/unload and station relayout. Verify POI/energy behavior, one station object set, aligned interaction areas and no orphan collision. Compare old and new accepted-station/pump counts and explain losses; appearance work must not silently reduce functional coverage.

Visual review includes compact and larger stations in each validated pack, day/night, public/shop views and overhead circulation. First release completion requires distinguishable layout/identity variants, full-envelope fit, working fuel interactions, source-building retention and measured staging/collision budgets. Synthetic previews alone do not establish the refuelling or driving gates.
