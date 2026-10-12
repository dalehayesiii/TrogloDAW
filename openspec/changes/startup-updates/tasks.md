# Tasks

## 1. Discovery and private access

- [x] 1.1 Implement asynchronous stable-release checks, startup preference, explicit source identity and bounded errors; test current/newer/draft/prerelease/offline/rate-limit cases without external network.
- [x] 1.2 Add optional OS-stored private access and safe authenticated redirects; test credential redaction/persistence boundaries and cross-host authorization removal, and document access requirements.

## 2. Download and installation

- [x] 2.1 Download canonical artifacts into controlled selected-drive storage with actual progress/cancel/retry and coherent checksum/source/version/size validation; test tamper, interruption and cancellation.
- [x] 2.2 Gate installation against processing/uploads/pickers/recording leases and reserve admission during handoff; verify busy/race/failure behavior through the real API.
- [ ] 2.3 Package the hidden acknowledged helper, embedded version identity and final runtime version smoke; test real native handoff, failed launch/install and data retention with paths containing spaces.

## 3. Interface and integration

- [x] 3.0 Separate first-run onboarding from Settings using shared embedded controls; persist setup history, verify retained-folder reuse, center dialogs, correct job spacing and independent Download/Installation status, and test background continuation/readiness/restart behavior.
- [x] 3.4 Replace persistent success messages with accessible eight-second/dismissible notifications visible within dialogs, without expiring errors or replaying old completions.

- [x] 3.1 Add available-version notices and Settings check/access/download/install controls with accessible status/recovery; verify real-backend browser flows and light/dark evidence, and update user guides.
- [ ] 3.2 Run documented Python/frontend/integration/native checks and validate a real authenticated release download without exposing credentials.
- [x] 3.3 Sync all four canonical capabilities, verify every delta and validate all specs.

## Workflow follow-up

- Archive the completed change before opening the dedicated implementation PR.
- Monitor latest required checks, squash merge when current/green, verify the publisher and perform the final investigation-only WRK-7 afterward.
