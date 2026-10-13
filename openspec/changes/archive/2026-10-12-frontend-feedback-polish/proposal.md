# Proposal

## Why

Review of the UI identified an unclear club-shaped local-link control, right-aligned success feedback and a folder button touching its input. These details add confusion despite otherwise working interactions.

## What Changes

- Remove the local-link copy control, retaining the audio download action.
- Center success toasts horizontally at the bottom of the page and inside foreground dialogs.
- Separate Create folder from its field by a deliberate 12px gap.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `frontend-service`: remove local-link copying from the player contract, center success feedback and clarify folder action spacing.

## Impact

Angular player/template/styles, real-service layout regressions and the existing audit record. This refinement is delivered in the existing audit PR; no new dependency or backend contract changes.
