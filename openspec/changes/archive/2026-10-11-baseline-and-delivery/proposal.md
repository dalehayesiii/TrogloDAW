## Why
The initial offline app has no canonical behavior specs, CI, tests or releases.
The bundle validator reports errors without failing and its version is hardcoded.

## What Changes
- Capture actual existing behavior/limitations as baseline capability specs.
- Install pinned OpenSpec integrations for Codex, Gemini, Antigravity and Grok Build.
- Add conventional PR titles, honest docs-only skipping, checks and dependency locks.
- Build/test the Windows installer before guarded main semantic-release publication.
- Add agent lifecycle policy and document owner-required merge settings.
- Complete implementation, spec synchronization and archive in this single PR.
- Migrate to Angular/Tailwind and FastAPI while preserving the observed four tabs,
  controls/defaults/look/behaviors; add paired screenshots and real functional tests.
- Organize the monorepo and adopt uv, Ruff/ty/pytest, ESLint/Vitest/Playwright.

## Capabilities
### New Capabilities
- `local-library`: config, import, portable catalog and management.
- `audio-creation`: effects and seeded synthesis.
- `mixing-production`: recipes, remix/rerender/export and offline producer.
- `user-interfaces`: browser UI and CLI.
- `delivery-workflow`: CI, Windows releases and agent/OpenSpec lifecycle.
- `frontend-service`: same-origin local API, processing jobs and UI migration parity.

### Modified Capabilities
None: this creates the first canonical spec set.

## Impact
Adds development tooling and Actions; runtime is Python with compiled Angular
assets and no Node/API key needed by end users.
NSIS versions become CI-generated and bundle errors fail builds. DSP is preserved.
Owner setup is needed because WRITE access cannot configure protection. Broader
runtime support, code signing, visual redesign and song-model architecture are deferred.
