# Proposal

## Why

CI currently duplicates standard PR-title/version tooling, repeats frontend builds
and spreads checks across unnecessarily separate jobs. The first main release
also failed because the changelog preset is incompatible with its writer.

## What Changes

- Use released action version tags, maintained semantic PR-title validation and
  changed-path filtering; remove the custom Python policy implementation.
- Run one Python job and one Angular job in parallel, then combined integration
  and specs, then a single Windows build/installation job, then main-only release.
- Compile Angular once and reuse its artifact. Install dependencies only once per
  isolated job, with dependency caches.
- Remove custom release planning. Let official semantic-release select versions,
  prepare the versioned installer from the checked payload, and generate notes.
- Reject unpublished version tags before release so successful releases cover the
  complete range since the preceding published release. Test changelog generation.
- Document the limited remaining app-specific packaging and OpenSpec scripts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `delivery-workflow`: Simplify validation ordering, action/tool reuse and release
  preparation while retaining truthful docs skips and checked publication.

## Impact

GitHub workflow, release tooling dependencies/lock, Windows packaging helpers,
policy tests, development/agent instructions and delivery specs. No changes to
the app's audio engine, API, UI or data contracts. Changes extend the open cleanup PR.
