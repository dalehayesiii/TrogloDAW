# Proposal

## Why

Library currently requires organizing or deleting each song individually. Users need to select songs from a folder or search result and perform the same action once.

## What Changes

- Add independent selection checkboxes, Select all shown, Clear selection and a visible selected count to Library.
- Add bulk move to an existing or newly created logical Library folder, including Unfiled.
- Confirm bulk deletion with the exact selected count and song names; preserve failed selections for retry and report partial outcomes.
- Clear selection when search/folder scope changes and reconcile it after refresh, preventing hidden or stale songs from being acted on.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `local-library`: bulk organization and deletion preserving IDs, recipes, assets and per-item outcomes.
- `frontend-service`: truthful scoped multi-selection and recoverable bulk-action feedback.

## Impact

Angular Library UI, local queued service operations and synthetic backend/browser coverage. No dependencies, catalog schema migration, physical storage relocation or remote services.
