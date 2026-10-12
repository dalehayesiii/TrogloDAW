# Proposal

## Why

The UI's themed three-workflow layout is coherent, but preview ownership, control feedback and empty/error states can mislead normal use. Frontend changes also lack a reusable, conditionally applied usability review.

## What Changes

- Keep Library previews tied to the latest selection, with loading and recovery feedback.
- Make audio mute, playback failures and local-link copying explicit; enlarge small audio actions and contain long titles.
- Distinguish saved song/last-rendered Vocal FX audio from a preview of current settings.
- Explain empty pickers and unmatched searches, and validate generation counts next to the field before submission.
- Install a pinned MIT audit playbook and measurement script, with frontend-scoped guidance, provenance and a practical audit record.
- Order shutdown after ordinary browser tests through an explicit test dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `frontend-service`: reliable previews, audio feedback, actionable empty states and generation count validation.
- `song-vocal-editing`: disclose previews that do not represent the current effects.
- `delivery-workflow`: conditional frontend usability review with reusable local skill and behavior regressions.

## Impact

Angular components/templates/styles, real-service Playwright regression tests, agent guidance, vendored audit resources and documentation. No runtime dependency, backend API, audio engine, catalog or packaging changes. Accessibility compliance and visual redesign are outside this audit's requested scope.
