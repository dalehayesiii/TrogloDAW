# Proposal

## Why

Failed and canceled job cards accumulate after retries, while one failed job also creates a duplicate global banner. Users need failures to remain readable until they dismiss them or retry the originating workflow, without crowding out their work.

## What Changes

- Add manual dismissal and same-workflow retry replacement for persistent terminal job notices and ordinary errors.
- Persist presentation acknowledgments across reloads while retaining backend jobs, results and timing.
- Keep active jobs visible; group retained historical failures by workflow with expandable earlier notices.
- Show one copy of a job failure and use accessible foreground notifications in pages and dialogs.
- Document success versus error policy and primary accessibility/design guidance; test real backend failures and synthetic evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `frontend-service`: persistent scoped failure lifecycle, dismissals, retry replacement and accessible notification presentation.

## Impact

Angular notification state, job status UI, browser/unit tests and documentation. No API, engine, packaging, audio or dependency changes. Existing eight-second success messages remain.
