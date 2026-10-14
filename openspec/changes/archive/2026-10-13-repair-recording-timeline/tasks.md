# Tasks

## 1. Preserve the direct timeline

- [x] 1.1 Use decoded sample counts for direct source duration; verify rounding/boundary and batch/replay regressions in the recording-workflow tests.
- [x] 1.2 Align direct encoder input without modifying source samples, retain strict output completeness and record padding; verify adapter waveform and pinned-decoder shape regressions.
- [x] 1.3 Document the failure, retry path and measured frame limit; verify the guidance matches implementation without changing dated benchmark evidence.

## 2. Integrated validation

- [x] 2.1 Run documented Python/frontend/spec and synthetic integration checks, and bounded native validation if the GPU is idle; record actual observations and limits.
- [x] 2.2 Sync the canonical spec and validate it against the delta before archiving.

## Workflow follow-up

- Archive only after all tracked tasks are complete, verify specs and archive policy, commit them together and open a fix PR.
- Monitor the installed-Windows Actions checks and repair any failure until all required jobs pass. Keep the PR open pending authorization.
- Continue the separately requested phrase-safe sampling improvement after this prioritized repair is delivered.
