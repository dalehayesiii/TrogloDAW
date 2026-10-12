# Tasks

## 1. Validate and repair generation
- [x] 1.1 Inspect the reported recipe and pinned sampler; run same-seed two-minute SDE/ODE comparisons in an isolated D: library.
- [x] 1.2 Preserve independent shift/guidance while selecting ODE throughout the slider range; verify boundary regression tests.
- [x] 1.3 Verify sequential two-output calls, separate seeds/assets and completed-output preservation in backend tests.
- [x] 1.4 Document affected settings and regeneration recovery without changing existing audio; verify documented mapping against source.

## 2. Integration and specification delivery
- [x] 2.1 Run required Python/frontend/backend integration checks and strict OpenSpec validation.
- [x] 2.2 Sync canonical song-generation requirement and verify exact delta content.

## Workflow follow-up
- Archive completed artifacts before opening the PR, then monitor all required checks and squash merge when current.
