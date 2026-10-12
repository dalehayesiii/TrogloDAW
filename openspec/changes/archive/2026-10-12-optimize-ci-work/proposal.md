# Proposal

## Why

CI installs the Angular workspace in jobs that never compile it and runs the browser suite three times. Reduce repeated work while retaining one full installed-app gate and focused validation of the final release installer.

## What Changes

- Run full Playwright E2E only in the Windows build job; integration retains synthetic CLI/producer, OpenSpec and release-tool checks.
- Validate final installer installation, version, service startup, static UI and uninstall in semantic-release preparation without repeating browser/audio workflows.
- Install only root npm tools outside Angular, preserving required development dependencies and lockfile installation.
- Produce a separate main-only release payload artifact; avoid compressing already compressed Windows artifacts again.
- Remove the redundant Python lock check after locked sync.
- Treat PNG/SVG assets under docs/ as documentation so the concurrent documentation cleanup gets the intended docs-only skips; frontend/runtime assets remain code.
- Document the resulting gates and complete this OpenSpec lifecycle in the implementation PR.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `delivery-workflow`: Full browser coverage belongs to Windows build; release uses focused final-installer validation and jobs install/transfer only needed tooling and assets.

## Impact

GitHub CI, installer validation/release configuration, delivery instructions and delivery-workflow specification. Application behavior, dependency versions and semantic-release version calculation remain unchanged.
