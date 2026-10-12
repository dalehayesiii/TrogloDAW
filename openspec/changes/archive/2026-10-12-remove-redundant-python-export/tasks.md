# Tasks

## 1. Dependency and packaging cleanup

- [x] 1.1 Remove the root export and installer copy, keep temporary hashed exports, update build/agent/development instructions and remove stale pandas cleanup; verify references and uv lock/export checks.
- [x] 1.2 Update ffmpeg recovery instructions, README tab wording and policy manifest examples; verify Ruff, ty and pytest.

## 2. Integration validation

- [x] 2.1 Run the documented local Python/frontend/tooling checks and strict change validation; verify they pass without the root export.

## Workflow follow-up

- Sync the delivery-workflow delta into canonical specs and archive this completed change in the same PR; validate all canonical specs and archive hygiene.
- Push the cleanup PR and monitor the clean-checkout installer build and actual Windows installed-app tests until Required checks passes.
