## 1. Library import

- [x] 1.1 Implement validated transactional WAV song import; test title/folder, original preservation, invalid/non-finite input, cancellation/storage failure and relocated playback/provenance.
- [x] 1.2 Add the simple Library import interaction and notification lifecycle; verify success, error/retry and selection as a prior/backing without invented ingredients.

## 2. Preserved-backing arrangement

- [x] 2.1 Implement separate workflow dispatch and server guards; test absent model, invalid collections, ignored stale model settings and retained draft/recipe discriminator.
- [x] 2.2 Use measured backing beat/energy/tonal context with source derivation and bounded mixing; test source coverage, varied placement, duration, headroom, reproducible relocated replay and cancellation/partial outputs.
- [x] 2.3 Add workflow/backing selection with disabled model-only controls and retained drafts; verify real-service imported/existing backing flows and both themes at desktop/narrow widths.
- [x] 2.4 Document mode contracts, supported lengths, measured quality/resource limitations and WRK-27 integration.

## 3. Integration

- [x] 3.1 Run all required local checks, synthetic CLI/producer and complete real-service browser tests; strictly validate the change.
- [x] 3.2 Sync canonical specs and verify imports/workflow/recipe contracts match the implementation.

## Workflow follow-up

- Archive completed artifacts before opening the implementation PR.
- Integrate the squash-merged WRK-9 dependency so the final PR contains only WRK-25 changes.
- Monitor all five required current-revision checks and squash merge only when current with main.
- Record completion, limitations and extensible workflow/recipe integration decisions on WRK-25.
