# Bounded preview lifecycle: first resource-control slice

Implemented 1 November 2026. This is a partial M2 step, not a global scheduler or
physical residency implementation.

`buildgen.progressive` now uses per-job cancellation tombstones in staging. The
publisher checks before optional shell work, before each preview mesh write and
before manifest publication. Rebase, failure, distant preview retirement and
disconnect signal cancellation. The road tracker captures the originating token
in its completion callback so an obsolete callback cannot finish a replacement
preview job for the same tile.

Cancellation suppresses optional shell/intermediate publication. It preserves
all lite/detail meshes, final group mappings and collision content. Existing final
file reuse remains valid even if cancellation arrives partway through publication.
Reused preview meshes now enter the final watched destination through atomic
staging replacement, with re-encoding from the final mesh if the optional source
cannot be copied. Optional publication I/O failure disables previews while final
generation continues.
Essential road/building/fuel jobs continue; no new process pool is introduced.
Tombstones are retained for staging age cleanup, rather than removed when only an
outer awaiting future is cancelled while the process still runs.

Preview metadata is limited to 1 MiB, 256 groups, 256 parts per group and 4,096
total parts. Polling delivers at most four changed groups per call. The reader
checks the complete version/token/geotile envelope, finite coordinates, unique
groups, token-specific filenames and monotonic sequence; malformed, duplicate-key,
nonfinite and oversized JSON is ignored. Exceeding optional publication limits
does not truncate final geometry.

The current replacement group is **12 buildings**, not the four-building historic
proposal in earlier planning text. Tests cover unchanged final output under
cancellation, malformed/oversized manifests, stale completions and tracker hooks.

The [2 November source continuation](PHYSICAL_RESOURCE_LIFETIME_PROGRESS.md)
supersedes the implementation status of the list below. Aggregate admission and
the dependency cache are implemented; sector negotiation and occupied retention
now have verified source slices. Full physical handover and native acceptance
remain open. This older list records the initial preview checkpoint.

Remaining M2 work at the preview checkpoint:

- Aggregate memory/work admission, backpressure and bounded terrain/sector work.
- Versioned dependency cache quotas, coalescing and stale-producer recovery.
- Negotiated sector manifests and engine import/debt accounting.
- Resource reference lifetime and occupied collider pinning across refinement,
  rebase, partial residency and disconnect/reconnect.
- Measured slow-worker, saturated-queue and in-game traversal/streaming gates.

See [the integrated checklist](GENERATION_IMPLEMENTATION_CHECKLIST.md).
