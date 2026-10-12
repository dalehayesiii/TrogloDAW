# Proposal

## Why

WRK-4 replaces scattered music tasks with Generation, Library, and Vocal FX. The published baseline provides procedural beats and single-voice effects, but cannot deliver lyrics-conditioned music inference, sample-based arrangement, or singer-aware song editing.

## What Changes

- Replace the browser's four legacy workflows with three task-focused tabs, preserving drafts and existing CLI contracts.
- Add local, hardware-validated model inference, lyrics/style conditioning, five meaningful advanced controls, sequential multi-output requests, and inspectable source-sample transformation/placement recipes.
- Add multiple uploads, accepted microphone takes with retakes, prior-song input presets, and selective reuse of creation ingredients.
- Add persistent song folders and direct library-to-workflow actions without changing song IDs or portable asset references.
- Add cached vocal extraction and candidate singer grouping, explicit ambiguity/correction, fixed-timebase group effects, and source-preserving FX version saves.
- Add recoverable in-app library/model storage selection and explicit, verified initial model installation in a selectable known location. Track installed model ownership for the uninstaller's default-checked removal option while preserving unrelated files and user libraries.
- Keep the baseline visual vocabulary in this PR; WRK-5 owns branding and themes, WRK-6 calibrated estimates, WRK-10 startup updates, and WRK-7 eager-stem investigation.

## Capabilities

### New Capabilities

- `song-generation`: Local model inference, source sample arrangements, preserved lyrics, controls, provenance, batches and references.
- `song-vocal-editing`: Cached separation, candidate groups and fixed-timeline FX derivatives.
- `local-model-storage`: Explicit model acquisition, verification, offline runtime and recoverable storage preferences.

### Modified Capabilities

- `frontend-service`: Three primary workflows replace the initial visual/control contract; responsive worker and same-origin API remain.
- `user-interfaces`: Browser workflow navigation and task-focused controls change; retained CLI is compatible.
- `local-library`: Song organization and recoverable root relocation extend portable persistence.

## Impact

Python/FastAPI orchestration, Angular forms and media controls, recipes/catalog metadata, model/runtime dependencies, Windows payload/setup, synthetic unit/integration tests, screenshots and current product documentation. No cloud audio processing or personal test audio. Existing catalogs remain readable; new recipe types extend rather than replace legacy recipe support.
