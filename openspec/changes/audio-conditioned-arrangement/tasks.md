# Tasks

## 1. Content-aware arrangement

- [ ] 1.1 Implement audible/diverse region selection and bounded budgets; verify synthetic silence/contrasting-region/short-source tests and document heuristics.
- [ ] 1.2 Implement individual transformations, shared rhythmic motifs and full-duration arrangement with recorded gains; verify every-source contribution, seed reproducibility, bounds and cancellation tests.

## 2. Actual conditioning and compatibility

- [ ] 2.1 Add real cover conditioning, capability fallback and explicit postmix mode; verify request fixtures, offline Base runs and waveform deltas at zero/partial/full adherence, including memory/60/120-second measurements.
- [ ] 2.2 Repair pinned partial-cover switch narrowly without modifying model files; verify CFG regression fixtures and independent style mapping, document the checkpoint compatibility behavior.
- [ ] 2.3 Preserve portable v1/v2 rerender and selective ingredient reuse; verify conditioned output is not double-mixed and postmix reconstructs gains after relocation.

## 3. Applicable interface

- [ ] 3.1 Add collapsed Input Audio mode/adherence controls with draft persistence; verify real-backend browser navigation/reload/no-clips/postmix/fallback tests and light/dark screenshot evidence.
- [ ] 3.2 Update README/workflow/model documentation with actual semantics and quality limits; inspect links and examples against final implementation.

## 4. Integration and delivery

- [ ] 4.1 Run documented Python/frontend/CLI/spec checks and Windows installed-app coverage on the final tree; verify all complete successfully.
- [ ] 4.2 Sync canonical specs and verify no delta remains unapplied, with strict spec validation.

## Workflow follow-up

- Archive completed artifacts before opening the implementation PR.
- Open and attach the conventional-title PR, monitor the five required checks on its latest head, and leave it open for parent review and authorized squash merge.
