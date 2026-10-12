## Purpose
Define repository contribution, validation and semantic Windows release behavior added alongside the initial app baseline.

## ADDED Requirements
### Requirement: Conventional PR and documentation policy
PRs SHALL use validated Conventional Commit titles. docs PRs SHALL touch only
approved documentation paths, checking both old/new paths for renames, and SHALL
not declare a breaking title. Main introduced commit subjects SHALL be validated.
Validated docs-only changes SHALL skip app builds and all version/tag/release actions.
Lightweight policy, spec and release-tool tests SHALL still report a gate.

#### Scenario: False docs claim
- **WHEN** a docs PR modifies Python, dependencies or workflow code
- **THEN** policy fails and the PR cannot satisfy Required checks

#### Scenario: Docs-only merge
- **WHEN** a valid docs-only PR is squash merged to main
- **THEN** no app build, version bump, tag or release occurs

### Requirement: Standard quality and installer gate
Non-docs PRs SHALL run Ruff/ty/pytest on Linux and Windows, ESLint/Vitest,
strict Angular compilation, Playwright, tooling tests, strict specs validation,
and a preview installer plus installed runtime tests. Bundle validation SHALL fail
on detected incompatibility, missing dependency/DLL, or missing Windows ffmpeg.
Required checks SHALL fail for any failed/cancelled/unexpectedly skipped prerequisite.

#### Scenario: Embedded runtime failure
- **WHEN** the installer builds but installed runtime cannot run its CLI, producer or UI
- **THEN** Required checks fails and no main release may publish

### Requirement: Default semantic versioning with docs exception
The release analyzer SHALL use semantic-release defaults with feat minor,
fix/perf patch, breaking code changes major, and docs always no bump. Other
nonbreaking types SHALL retain default no-bump behavior. First eligible release
SHALL start at 1.0.0; stable tags SHALL follow vX.Y.Z on main.

#### Scenario: Breaking feature
- **WHEN** feat! merges after version 1.2.3
- **THEN** the next eligible version is 2.0.0

#### Scenario: Nonbreaking maintenance
- **WHEN** only chore/refactor/test commits remain unreleased
- **THEN** no version is due and main skips installer/release jobs

### Requirement: Publish tested version and artifact only
Official semantic-release SHALL publish only on main after all required checks
and installer/runtime tests succeed. The build SHALL inject the planned version
into NSIS metadata and publish installer, checksum and source/version manifest.
Before tagging, the publisher SHALL reject different version/SHA/checksum or main
advancing beyond the tested commit. Only the publisher SHALL receive release writes.

#### Scenario: Asset mismatch
- **WHEN** an installer manifest differs from semantic-release's version or source
- **THEN** publication fails before creating its release tag

### Requirement: Full OpenSpec lifecycle and agent support
The repo SHALL provide pinned OpenSpec CLI/workflows for Codex, Gemini CLI,
Antigravity and Grok Build. Changes warranting specs SHALL normally include
proposal, design, tasks, implementation, canonical spec sync and archive in one PR.
Proposal-only exceptions SHALL require explicit user intent, a docs PR and the
openspec:proposal-only label. CI SHALL reject unfinished archived tasks and
unapproved active changes.

#### Scenario: Normal implementation
- **WHEN** an agent finishes a behavior or delivery change
- **THEN** its PR contains completed archived artifacts and updated canonical specs

### Requirement: Agent delivery and merge gates
Agents SHALL deliver PRs and only merge if authorized and latest required checks pass.

#### Scenario: Pending checks
- **WHEN** required checks are pending, missing, cancelled or failed
- **THEN** an agent SHALL leave the PR unmerged and repair or report the failure

### Requirement: Owner-enforced merge configuration
The repo SHALL document owner configuration for squash-title commits, mandatory
up-to-date Required checks, no direct/force main pushes and no bypass. Contributors
without admin access SHALL report these requirements without claiming enforcement.

#### Scenario: WRITE-only contributor
- **WHEN** implementation is delivered by an account lacking repository admin
- **THEN** owner setup is clearly documented and the PR remains reviewable
