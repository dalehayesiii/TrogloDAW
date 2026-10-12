# Tasks

## 1. Notification lifecycle

- [x] 1.1 Implement validated persisted acknowledgment/error ledger and workflow scoping; unit tests verify retry isolation, reload, corrupt storage and active-job protection.
- [x] 1.2 Integrate submission/polling/direct failures with one foreground notification representation; browser tests verify manual dismissal, retry, reload, dialogs and unchanged history/results.
- [x] 1.3 Add compact grouped terminal notices and keyboard-accessible dismissal; verify light/dark desktop/narrow synthetic before/after screenshots and axe.
- [x] 1.4 Document formal notification policy and primary UX/accessibility sources in docs/notifications.md with reviewable evidence links.

## 2. Integration

- [x] 2.1 Run documented source checks and isolated real-backend E2E; document required Windows installed-check coverage for PR CI.
- [x] 2.2 Validate OpenSpec delta and sync canonical specification; verify behavior matches tests and docs.

## Workflow follow-up

- Archive the completed change, validate all specs, commit/push and open the Conventional Commit PR.
- Monitor required CI jobs on the latest revision and keep the PR open for root-coordinated merging.

Validation: source Ruff/format/ty, 149 Python tests, CLI demo/producer smoke,
5 tooling tests, 12 frontend unit tests, strict Angular build, 12 real-backend
browser tests, and a final 3-test notification/setup regression pass. Canonical
spec validation passed. Packaged/native checks remain required in the PR CI
follow-up above; no local installer/registry test touched the active user app.
