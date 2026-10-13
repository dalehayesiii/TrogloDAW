# Tasks

## 1. Queued catalog operations

- [x] 1.1 Implement exact-ID bulk moves and recoverable per-song deletion; verify validation, partial failures, cancellation and lineage with synthetic backend tests.
- [x] 1.2 Document logical folders, deletion outcomes and staged-file recovery in the Library guide; verify examples against the implementation.

## 2. Library interaction

- [x] 2.1 Add independent visible-list selection and centered bulk dialogs; verify filtered selection, navigation, playback, cancellation, new/existing folders and partial-failure retry through real-service Playwright tests.
- [x] 2.2 Review compiled desktop/narrow layouts in both themes, capture before/after screenshots and record concrete usability findings in the PR.

## 3. Integration and delivery

- [x] 3.1 Run documented Python, Angular, tooling, browser and strict OpenSpec checks; verify all required checks pass.
- [x] 3.2 Sync canonical specifications and verify strict checks; confirm the completed change is ready for archival.

## Workflow follow-up

- Archive the completed change, verify canonical specs match the deltas and run specs:check with no unfinished active change.

- Archive the completed change, verify canonical specs match the deltas and run specs:check with no unfinished active change.

- Push the feature branch, open the implementation PR and monitor required Actions.
- When current with main and all required checks pass, squash merge with the validated title and monitor the release workflow.
