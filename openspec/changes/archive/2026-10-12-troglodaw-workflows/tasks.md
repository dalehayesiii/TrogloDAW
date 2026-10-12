# Tasks

## 1. Verified model/runtime setup

- [x] 1.1 Pin optional inference dependencies and upstream assets; verify locked Windows installation and document exact redistribution/runtime requirements.
- [x] 1.2 Implement explicit resumable verified model/runtime installation, selected cache roots, supported model selection and cancellation; test invalid hashes, interrupted setup, access/space failures and offline verified reuse.
- [x] 1.3 Implement storage preferences and recoverable library/model root reuse/relocation; test paths with spaces, restart persistence, destination conflicts and interruption without data loss.
- [x] 1.4 Implement default-checked manifest-aware model uninstall with opt-out; verify owned-file removal, shared/custom-folder safety and upgrade retention in installer tests.
- [x] 1.5 Validate real lyrics/style inference on the RTX 3070 with desktop active, document memory/timings and meaningful control mappings, and verify no networking after setup.

## 2. Song generation and provenance

- [x] 2.1 Implement all-source sample slicing/transformation/placement and separate generated assets; test source contribution, fixed seeds, portable recipes and arrangement rerender.
- [x] 2.2 Implement lyrics/text generation, automatic title/duration, independent outputs and requested/effective controls; test N=1/N>1, unchanged lyrics/zero-variety prompts and per-output failure retention.
- [x] 2.3 Implement prior-song preset decisions and selective ingredient reuse; test accepted/declined decisions, no repeated unchanged-source prompts and preservation of unselected fields.
- [x] 2.4 Document generation contracts/limits and expose recipe asset inspection; verify saved originals/effective styles, sources, seeds, model identity and placements after reload/relocation.

## 3. Song editing and organization

- [x] 3.1 Implement actual vocal extraction and conservative pretrained candidate groups with correction/preview; test overlap ambiguity, stable IDs and document representative listening evidence.
- [x] 3.2 Implement fixed-timeline group FX and source-stem caches; test identity reconstruction, all effects, stretch/trim/tails, repeated edits and content/model cache invalidation.
- [x] 3.3 Implement atomic new/update FX versions and persistent folders/rename/search; test original preservation, lineage, portable assets and restart metadata.

## 4. Three task-focused browser workflows

- [x] 4.1 Replace browser tabs/forms with Generation, Library and Vocal FX, progressive detail controls, draft persistence and direct song actions; verify strict Angular compilation, frontend tests and real-backend browser tasks.
- [x] 4.2 Implement multi-upload/clip preview/remove/replace and microphone keep/discard/retakes with accessible guidance; verify mixed collections, capture release and permission/device/empty-format failures.
- [x] 4.3 Implement selective reference, preset and FX-save dialogs plus compact initial model/storage setup; verify keyboard/tap flows, clear state/errors and no extra primary tab or advanced generation controls.
- [x] 4.4 Capture representative desktop/narrow screenshots of three workflows/dialogs and validate first-use tasks without config editing or developer docs.

## 5. Integrated delivery validation

- [x] 5.1 Run all documented Python/frontend/spec/release checks, synthetic CLI/producer smoke and real-backend Playwright; repair regressions and record validation evidence.
- [x] 5.2 Verify packaged Windows launch/setup/inference/uninstall behavior and existing catalog/recipe compatibility; document runtime and hardware limits accurately.
- [x] 5.3 Validate completed change strictly and sync canonical specs, verifying every delta requirement/scenario matches the delivered behavior.

## Workflow follow-up

- Archive only after every tracked task is complete; verify canonical specs and completed archive with npm run specs:check.
- Commit specs and archive together, push a feature branch, open the WRK-4 PR, attach it to this chat and monitor all five required jobs on the latest revision.
- Once current with main and all required jobs pass, squash merge with the exact validated Conventional Commit PR title; continue WRK-5, WRK-6 and WRK-10 in order.
- Investigate WRK-7 after the four PRs and post measured findings to its Linear issue without pushing spike changes.
