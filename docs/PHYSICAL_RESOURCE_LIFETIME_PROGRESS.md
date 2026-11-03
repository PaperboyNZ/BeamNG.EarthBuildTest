# Physical resource lifetime — source continuation, 2 November 2026

This work is in editable source after the schema 22 r5 checkpoint. The root
launcher still selects r5; none of the changes below is claimed as packaged or
native accepted. At this checkpoint fourteen original rows were implemented toward the
approximately 28-row target. This includes M2's sector/lifetime implementation
row; its native contact, memory and larger-site acceptance gates remain open.

`server/sector.py` emits a bounded version 1 manifest for an existing global
zoom-17 content sector. It declares the complete shape digest inventory, separate
physical and visual revisions, the visual product's physical dependency and the
existing `closed-v1` geometry capability. `hello.sectorManifest` is negotiated
only for matching versions with road geotiles. The client validates the complete
manifest before it can retire an accepted tile. Missing manifests require legacy
compatibility; unsupported geometry capabilities are rejected. Accepted-plan
visual upgrades regenerate their manifest while retaining the physical revision.

The producer namespace identifies an existing geotile aggregate, not an individual
building or shared site. It does not relabel tile XY as canonical source identity.
Complete site membership, canonical site frames and shared cross-tile emission
remain M1 work. No new playable topology is enabled by this negotiation.

Client source now implements:

- Collision file retention until deletion, a collision rebuild request and the
  next update, following the existing terrain collision convention. A deletion
  after a request needs another rebuild. This is not a newly discovered engine
  acknowledgement API; native timing and contact acceptance remain open.
- Session-qualified pooled-file references. A restarted server's slot number
  cannot overwrite the lifetime/debt record for the same number in an older
  resident session. Reconnect reports include debt and pending resources.
- Occupied collision retention for the active vehicle, other live vehicles,
  parked vehicles and the active walking actor. Inactive walker objects and
  explicitly floating remote actors follow existing collision-island exclusions.
  Actor IDs deduplicate native wrappers; invalid/oversized inventories retain
  physical resources conservatively instead of silently truncating actors.
- Separate activation and retirement tests: standing on a deck permits late deck
  activation but pins retirement. Vertical separation, polygon holes and resource
  frame transforms remain relevant. Teleport holds exempt only the active actor
  from activation, preserving other actors' checks.
- At most one pending content revision per resident tile, with one matching skin
  and exact-variant message. Superseded unused files release; identical pending
  retransmissions do not release their own files. Skin and exact metadata carry
  the originating content hash. Obsolete messages cancel on rebase/session change.
- Stable collider inventories through legacy ghosting and transformed occupancy
  through actual geographic rebases. Normal retirement, orphan timeouts and
  collision-distance retirement retain occupied resources. Explicit mod off/unload
  and level teardown retain their existing teardown semantics.

## Subsequent source transaction implementation

`physicalhandover.lua` now stages a complete replacement beside its accepted
geotile. Each candidate is hidden with `collisionType = None`, using the field
documented by [BeamNG's TSStatic reference](https://docs.beamng.com/modding/levels/level_classes/tsstatic/)
and the installed editor's commit/lock code. Ordinary imports, far coverage,
collision urgency and deletion still share the existing governor and single
import frame limit. Missing coverage outranks optional replacement preparation.

All candidate content and a required matching skin must import before transfer.
Actors must clear both accepted and candidate geometry. The existing teleport
hold can exempt only its frozen active car during controlled handover, allowing
the placement/readiness workflow to finish; other actors still pin the transfer,
and ordinary retirement continues to retain the active car's support. The controlled collision
rebuild enables the candidate and disables the accepted collision set in one
request. Accepted visuals and files stay until the following update. Readiness
queries distinguish that pending frame from an acknowledged collision epoch.
Only then do the primary tile, visuals, props and ownership commit together.
These are source semantics; actual engine contact/timing still needs native proof.

Missing/import-failed shapes, partial field failures and rebuild exceptions retain
the accepted tile. Inert superseded candidates cancel; the latest desired revision
coalesces while a collision request is in flight. Rebase/session transitions either
discard inert work or finish the active transfer after a fresh rebuild, requesting
one existing-protocol road resync. Retirement and subsequent residency renewal
retain their ordering across these transitions.

Metadata owners now retain pooled files independently of scene instances and
physics debt. Two tiles can share a file; removing one, or temporarily unloading
the other's distant collider, cannot recycle it. Admission claims incoming files
before releasing superseded metadata. Actual path sessions qualify ownership,
including delayed messages from older server sessions. Both hello and pose report
road source folders alongside far-field folders. Unpooled files, parked resources,
live instances and pending physics all keep their source folder claimed.

At most two physical candidates stage globally. Existing deletion debt blocks
additional staging, with at most one later descriptor per accepted tile. A test
holds deletion unavailable through 30 superseding revisions: native import count
stays fixed, the latest descriptor survives, and work resumes after cleanup.
These count limits are not measured RSS/VRAM budgets. Oversized-sector admission
and small-machine/desktop memory calibration remain required.

Standalone skin and exact-precision updates now use the same transaction manager.
They import only changed resources, inherit the parent's collision policy and
retain unchanged structures and props. Visual-only changes avoid collision
rebuilds. Occupancy tests select the changed accepted surfaces rather than pinning
an unrelated sidewalk update because a vehicle occupies an unchanged deck.
Skin and precision requests merge by resource while an earlier transfer finishes;
full retransmissions can explicitly cancel or reverse a pending precision choice.
Rebases cancel obsolete requests without changing accepted body identities.
Completed progressive groups transfer their visibility tracking to replacement
instances, preventing later visibility updates from reviving retired nodes.

Failure tests retain accepted resources after skin imports or collision rebuilds
fail, including mixed skin/precision transfers. Cleanup backpressure leaves one
latest descriptor per tile. Metadata/file owners balance through cancellation,
retirement and reset. Shared site/station references, canonical runtime ownership
and native residency, contact and memory gates remain open. Large playable sites
are not enabled on the basis of the deterministic engine model.

Verification uses real production encoders for product upgrades and deterministic
engine stubs for client lifetime. The final transaction run records **112 Python
tests and 1,724 Lua assertions passing**, including 610 assertions in the asynchronous
whole-content transaction suite and 279 resource-patch assertions. Six focused
protocol tests also pass against a synthetic
localhost server, including source-folder adoption/release and negotiation.
All seven modified runtime Lua modules compile under LuaJIT. The 42 focused contract
tests overlap these runs. No FPS, tyre-contact or actual engine acknowledgement
claim follows from the stubs. Sources and log hashes are retained in
`build/world-architecture-programme/m2-transaction-checkpoint-patches/manifest.json`.
The earlier whole-content-only checkpoint remains at `m2-transaction-checkpoint-r3`.
The earlier 815-assertion source slice and 33-test protocol run (one standalone
LuaJIT-dependent skip) remain in `m2-resource-checkpoint` as historical evidence.

The previous isolated native process has ended. Its log stops at the existing
third-party DLL warning, with no recorded cause for the exit; the latest process
check found its PID absent and no BeamNG process. The earlier question asking
permission to press OK remains unanswered. The prepared roof/architecture fixtures
can be reviewed after relaunch and that approval; no warning has been accepted.
