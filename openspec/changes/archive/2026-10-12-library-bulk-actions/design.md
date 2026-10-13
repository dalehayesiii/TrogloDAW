# Design

## Context

See proposal.md for motivation. Library has a single preview selection, logical folder metadata and queued single-song operations. Catalog writes are atomic and locked. Existing recipe assets and original-family caches remain independent of catalog deletion.

## Goals / Non-Goals

**Goals:** Visible scoped selection, one queued bulk request, exact-ID validation, recoverable partial deletion and preserved playback/lineage.

**Non-Goals:** Physical library relocation, folder renaming/deletion, multi-song FX or generation, cache garbage collection and catalog schema changes.

## Decisions

- Keep checkboxes separate from the preview button so bulk selection does not trigger audio fetches. Clear selection on search/folder changes; reconcile after refresh. A cross-filter basket was considered but risks deleting hidden songs.
- Move all assignments and optional folder creation under one catalog lock, after validating the complete request. Repeated per-song requests could create partial moves or redundant folder updates.
- Delete sequentially with per-song outcomes and cancellation between songs. Stage only unshared managed audio to temporary sibling names before removing the catalog entry, restoring staged paths on failure. After the catalog commits, cleanup failure is reported as a retained-file warning. No folder/cache tree is recursively deleted.
- Use the established centered modal for explicit delete confirmation and move destinations. Capture a selection snapshot for confirmation; disable duplicate submission while busy. Failed/unprocessed songs remain selected and notices follow existing Library error policy.

## Risks / Trade-offs

- Files locked by another process → preserve the affected entry and staged files, identify it for retry.
- Interrupted process during staging → temporary sibling files can remain; documented recovery uses their original filename suffix. This is not a distributed transaction or trash/recycle-bin feature.
- Catalog changed while a request queues → validate IDs/folders again at execution and never resolve ambiguous prefixes.

## Migration Plan

No data/configuration migration. Existing catalogs and single-song operations remain compatible.
