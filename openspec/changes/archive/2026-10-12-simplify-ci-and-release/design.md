# Design

## Context

See proposal.md. NSIS currently runs on Linux and installation tests separately on
Windows. The existing Bash staging script can support Git Bash by selecting the
Windows venv paths and extracting embedded Python with its standard zipfile CLI.
The checked app payload is independent of installer metadata/version.

## Goals / Non-Goals

**Goals:** Five clear stages, maintained tools for generic checks, no duplicate
frontend compilation, official version calculation and tested release notes.

**Non-Goals:** App behavior changes, abandoning installed-EXE testing, bypassing
branch protection, or inventing version/tag history.

## Decisions

- amannn/action-semantic-pull-request validates titles; dorny/paths-filter detects
  documentation paths including renames. Small workflow glue combines these
  outputs for the repository's docs-only exception. Remove check_policy.py/tests.
- Python runs on Linux; Windows packaging tests exercise the actual embedded
  runtime. Angular runs format/lint/Vitest/compile and uploads the compiled UI.
  The subsequent integration job restores it and runs real-backend Playwright,
  CLI/producer tests, release-note tests, OpenSpec validation and archive checks.
- One Windows build job stages wheels/assets, runs NSIS and tests the installed
  app. The build's payload archive is passed to the main-only publisher.
- Use semantic-release's official exec prepare plugin to repackage the checked
  payload with nextRelease.version and test that installer before tagging. This
  repackaging changes version metadata; it does not recompile Angular or resolve
  dependencies. This avoids a custom version planner or privileged dry-run job.
- Keep official semantic-release CLI and pinned plugins from npm lock. Correct
  preset/writer compatibility and expose every Conventional Commit type in notes.
  A GitHub API preflight rejects version tags lacking a published release; normal
  semantic-release then uses the last successful tagged release as its baseline.
- Use native GitHub job dependencies and require individual statuses through
  branch protection. No aggregate job is needed. Docs may skip the code jobs and
  build; integration still validates specs/tooling. Dependabot maintains explicit
  released action tags, following the user's requested policy.
- Preserve app-specific bundle validation, config/icon helpers, synthetic producer
  smoke tests, source/version checksum manifest and pre-tag artifact guard. Keep
  check_specs.py only for the project's full-lifecycle rule, which the OpenSpec
  CLI's structural validation does not enforce. Document each in docs/ci.md.

## Risks / Trade-offs

- Moving NSIS to Windows can reveal shell/path differences; validate the script
  locally and require a successful clean GitHub Windows build and installed test.
- semantic-release tags before publishing. An interrupted publish requires owner
  recovery of that tag/release; preflight fails safely rather than hiding commits.
- The main publisher cannot be exercised by merging without user authorization;
  test its prepare/release-note contracts locally and in PR integration checks.

## Migration Plan

Extend PR #2 and leave it open. The owner replaces the old aggregate requirement
with the five individual check names and allows the maintained third-party actions.
Main release only happens when the user merges; revert workflow changes if needed.
