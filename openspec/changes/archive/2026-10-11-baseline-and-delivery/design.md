## Context
Initial commit `4aae81d` contains local DSP, CLI, Gradio UI and Linux/NSIS Windows
packaging with Python 3.12.10, but no CI/tests/tags. Preserve its DSP and packaging;
migrate the UI as explicitly requested while retaining its observable contracts.

## Decisions
- Keep Python DSP/NSIS packaging; Node compiles Angular/Tailwind and runs tooling.
  FastAPI serves assets and local endpoints; one DSP worker supports progress polling.
  Recreate the captured Gradio layout, labels/defaults, waveform/transport and jobs.
- Use frontend/backend/scripts/config/cicd/docs folders. Runtime config/library
  defaults remain at the project or installed app root for compatibility.
- Use the conventionalcommits parser for `!`, with only docs mapped to no release.
  Other semantic-release defaults remain; first eligible version is 1.0.0.
- Plan versions with read-only analysis of reachable stable tags and the same
  analyzer. Official semantic-release publishes; its prepare guard rejects planner
  mismatch, stale source SHA, changed checksums or advanced main before tagging.
- Build 0.0.0 previews for non-docs PRs and stable versions only when due on main.
  Validate on Linux and execute the installed embedded runtime on Windows.
- Run an always-reporting aggregate gate and grant release credentials only after
  tests/build/install smoke checks pass. Serialize main runs.
- Verify docs using narrow paths and both sides of renames. Docs-only pushes never
  flush pending code releases. Lightweight policy/spec/tool tests still run.
- Pin dependencies with uv.lock and export hashed requirements from that single source.
  Check Python with Ruff/ty/pytest and frontend with ESLint/Vitest/strict build/Playwright.
- Generate native agent workflows and add root policy. Explicit full-lifecycle
  user authorization overrides generated planning-only guidance. Reject unfinished
  active changes except labeled docs-only proposal exceptions.

## Risks and boundaries
WRITE cannot enforce merge settings; owner setup is documented. Installer remains
unsigned. Static DLL checks need Windows execution. Confirmed upstream tooling
audit findings must be documented, not hidden by obsolete downgrades. Failure
after tagging may need release-asset repair. Source launchers now use locked uv;
supported runtime targets Python 3.12, aligned with the embedded build.

## Validation
Test config/catalog portability, deterministic recipes, mix/remix/export, mastering,
title/docs/rename policy, semver defaults and asset guards. Run synthetic demo and
producer tests, paired baseline screenshots and real browser flows. Build and run
the installer/compiled UI with the same browser tests on Windows.
Strictly validate delta/canonical specs, complete tasks, sync and archive in this PR.
