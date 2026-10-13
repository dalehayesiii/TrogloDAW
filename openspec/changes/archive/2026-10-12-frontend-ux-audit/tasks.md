# Tasks

## 1. Reusable audit guard

- [x] 1.1 Install pinned audit resources with license/provenance, frontend-scoped routing and project guidance; validate the skill and run its measurements on the app.
- [x] 1.2 Record usability findings, dispositions and review limitations in docs/frontend-ux-audit.md; inspect desktop/narrow screenshots in both themes.

## 2. Interaction repairs

- [x] 2.1 Fix Library preview ownership/loading/retry and empty states; verify slow response, failure recovery and search/picker regressions through Playwright.
- [x] 2.2 Fix audio state/feedback, click targets and long-name wrapping; verify source changes, mute, clipboard/playback failure and long titles in Playwright.
- [x] 2.3 Expose stale FX preview provenance including edits during rendering; verify synthetic cached FX browser tests.
- [x] 2.4 Add generation count feedback/submission guard; verify invalid counts never submit jobs and valid count is retained.

## 3. Integration

- [x] 3.1 Run docs/development.md checks and strict OpenSpec validation, resolve failures and update audit evidence.
- [x] 3.2 Make service shutdown the final dependent Playwright stage; verify the full suite runs all app tests before Quit, including newly added files.

## Workflow follow-up

- Sync canonical specs and archive the completed change, then run specs:check.
- Push the feature branch, open a Conventional Commit PR and monitor all required Actions checks to success on its latest revision.
