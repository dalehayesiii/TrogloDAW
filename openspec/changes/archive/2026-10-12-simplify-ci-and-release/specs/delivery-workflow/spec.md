# Spec Delta

## MODIFIED Requirements

### Requirement: Conventional PR and documentation policy
PRs SHALL use a maintained Conventional Commit title action as the first gate.
Maintained changed-path filtering SHALL check old/new rename paths; docs PRs SHALL
touch only approved documentation and SHALL not declare breaking changes. Squash
titles SHALL supply main commit subjects. Truthful docs-only changes SHALL skip
app checks/builds and all version/tag/release actions. Spec and release-tool
validation SHALL still report a required gate.

#### Scenario: False docs claim
- **WHEN** a docs PR modifies Python, dependencies or workflow code
- **THEN** the title/docs check fails and GitHub's required statuses block merging

#### Scenario: Docs-only merge
- **WHEN** a valid docs-only PR is squash merged to main
- **THEN** no app build, version bump, tag or release occurs

### Requirement: Standard quality and installer gate
After the title gate, Python and Angular SHALL run in parallel, followed by
integration/spec validation, then one Windows build/installed-EXE job. Checks SHALL
cover Ruff/ty/pytest, ESLint/Vitest, strict Angular compilation and Playwright.
Bundle validation SHALL fail on incompatible or missing dependencies/DLLs/ffmpeg.
Jobs SHALL use native GitHub dependencies, with owners requiring individual
statuses for merging; no aggregate check job SHALL be used.

#### Scenario: Embedded runtime failure
- **WHEN** the installer builds but installed runtime cannot run its CLI, producer or UI
- **THEN** the required build check fails and no main release may publish

#### Scenario: Reuse checked frontend
- **WHEN** integration tests and packaging need compiled frontend assets
- **THEN** they use the Angular job's artifact without rebuilding its source

### Requirement: Default semantic versioning with docs exception
Official semantic-release SHALL select versions with its defaults: feat minor,
fix/perf patch, breaking code changes major, docs always no bump, and other
nonbreaking types no bump. First eligible release SHALL start at 1.0.0; stable
tags SHALL follow vX.Y.Z on main. Nonbreaking maintenance SHALL still undergo
code checks and a preview build on main, but SHALL not publish a release.

#### Scenario: Breaking feature
- **WHEN** feat! merges after version 1.2.3
- **THEN** the next eligible version is 2.0.0

#### Scenario: Nonbreaking maintenance
- **WHEN** only chore/refactor/test commits remain unreleased
- **THEN** no version is due and main does not create a tag or release

### Requirement: Publish tested version and artifact only
Official semantic-release SHALL run only on main after the build and its prerequisite jobs succeed.
Its prepare hook SHALL version the installer from the checked payload and test
that installed artifact before creating the tag. Publication SHALL include the
installer, checksum and source/version manifest. Mismatched version/SHA/checksum
or an advanced main SHALL abort before tagging. Only the publisher SHALL receive
release writes; a separate custom version planner SHALL NOT be used.

#### Scenario: Asset mismatch
- **WHEN** an installer manifest differs from semantic-release's version or source
- **THEN** publication fails before creating its release tag

### Requirement: Owner-enforced merge configuration
The repo SHALL document owner configuration for squash-title commits, mandatory
up-to-date title/Python/Angular/integration/Windows build status checks, no
direct/force main pushes and no bypass. Contributors without admin access SHALL
report these requirements without claiming enforcement.

#### Scenario: WRITE-only contributor
- **WHEN** implementation is delivered by an account lacking repository admin
- **THEN** owner setup is clearly documented and the PR remains reviewable

## ADDED Requirements

### Requirement: Published-release changelog range
Release notes SHALL use semantic-release's full commit range since the preceding
published stable tag, include all Conventional Commit types, and provide a compare
link. A reachable stable version tag without a published GitHub release SHALL
block subsequent release until repaired, so a failed publication cannot silently
advance the changelog baseline.

#### Scenario: Unreleased maintenance between releases
- **WHEN** docs, chores, fixes and features accumulate after the previous release
- **THEN** the next successful release notes include those conventional changes
  and a comparison from that previous tag to the new tag

#### Scenario: Interrupted publication
- **WHEN** a previous run pushed its version tag but failed to publish its release
- **THEN** the next publisher stops for recovery instead of omitting those changes

### Requirement: Released actions and isolated environments
Actions SHALL use explicit released version tags, with Dependabot tracking action
updates. Each isolated job SHALL install its needed locked dependencies at most
once, use caches where supported, and pass built artifacts between jobs. Remaining
custom scripts SHALL implement documented app-specific contracts rather than
duplicate generic title validation or version calculation.

#### Scenario: Readable action dependency
- **WHEN** a contributor reads a workflow action reference
- **THEN** its released version is visible without resolving an opaque commit SHA
