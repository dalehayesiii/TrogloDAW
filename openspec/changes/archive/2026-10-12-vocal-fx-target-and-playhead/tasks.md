## Implementation
- [x] Add All vocals targeting, full-vocal solo and mixed-field feedback while retaining group overrides.
- [x] Add shared-player marker driven by actual media playback/seek events.
- [x] Align frontend/API postmix defaults and preserve explicit draft/recipe choices.
- [x] Add meaningful synthetic audio and real-service UI regressions and workflow documentation.

- [x] Match new postmix gestures to vocals/song with bounded gains, relative volume and portable replay provenance.

## Validation
- [x] Run documented checks, review both themes at desktop/narrow sizes and integrate current main.
- [x] Validate specs, complete tasks, sync canonical specs and archive before final PR.

After archival, deliver through a PR and monitor all five required checks on the latest revision.

Validation: 191 Python tests, 14 frontend unit tests, 5 release-tool tests and all 29 Edge real-service browser tests passed; the changed FX screenshot regression also passed after addition. Ruff, ty, ESLint, formatting, strict Angular build, synthetic CLI/producer and strict specs passed. Desktop/narrow screenshots in both themes were inspected for playheads and mixed FX controls. Based on current main c17a4f9; live GPU generation/loudness perception was not rebenchmarked, and separator bleed remains an explicit limitation.
