# delivery-workflow Specification

## Purpose
Define repository contribution, validation and semantic Windows release behavior added alongside the initial app baseline.

## Requirements

### Requirement: Conventional PR and documentation policy
PRs SHALL use a maintained Conventional Commit title action as the first gate.
Maintained changed-path filters SHALL check both rename paths. Docs titles SHALL
allow only approved docs, with no breaking changes. Markdown and PNG/SVG under
docs/ SHALL qualify; frontend/runtime assets SHALL remain code. Squash titles
SHALL supply main subjects. Truthful docs-only changes SHALL skip app checks/builds,
versioning, tags and releases; spec and release-tool checks SHALL still report.

#### Scenario: False docs claim
- **WHEN** a docs PR modifies Python, dependencies or workflow code
- **THEN** the title/docs check fails and GitHub's required statuses block merging

#### Scenario: Docs-only merge
- **WHEN** a valid docs-only PR is squash merged to main
- **THEN** no app build, version bump, tag or release occurs

#### Scenario: Retire documentation images
- **WHEN** a docs PR deletes PNG/SVG review assets under docs/ and updates Markdown
- **THEN** documentation-only skips apply, but a rename from such an image into executable code fails the docs gate

### Requirement: Standard quality and installer gate
After the title gate, Python and Angular SHALL run in parallel, then integration/spec checks and Windows build/installed tests. Checks SHALL cover Ruff/ty/pytest, ESLint/Vitest and strict Angular compilation. Full Playwright E2E SHALL run only in Windows build against the installed app. Bundle checks SHALL reject missing/incompatible dependencies, DLLs or ffmpeg. Native job dependencies and owner-required individual statuses SHALL gate merging without an aggregate job.

#### Scenario: Embedded runtime failure
- **WHEN** the installer builds but installed runtime cannot run its CLI, producer or UI
- **THEN** the required build check fails and no main release may publish

#### Scenario: Reuse checked frontend
- **WHEN** Windows packaging needs compiled frontend assets
- **THEN** it uses the Angular job's artifact without rebuilding its source

#### Scenario: One full browser gate
- **WHEN** a code PR or main push runs CI
- **THEN** integration checks synthetic CLI/producer flows and specs, while only Windows build runs the complete browser suite against embedded Python and the installed UI

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
Official semantic-release SHALL run only on main after build and prerequisite jobs succeed. Its prepare hook SHALL version the checked payload and verify final installation, displayed version, API startup, static UI and uninstall without repeating full E2E. Publication SHALL include installer, checksum and source/version manifest. Version/SHA/checksum mismatch or advanced main SHALL abort before tagging. Only the publisher SHALL receive release writes; no custom version planner SHALL be used.

#### Scenario: Asset mismatch
- **WHEN** an installer manifest differs from semantic-release's version or source
- **THEN** publication fails before creating its release tag

#### Scenario: Final installer startup failure
- **WHEN** the versioned release installer cannot start its bundled service or serve its compiled UI
- **THEN** prepare fails before tagging or publishing, without running the full browser/audio workflows again

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
up-to-date title/Python/Angular/integration/Windows build status checks, no
direct/force main pushes and no bypass. Contributors without admin access SHALL
report these requirements without claiming enforcement.

#### Scenario: WRITE-only contributor
- **WHEN** implementation is delivered by an account lacking repository admin
- **THEN** owner setup is clearly documented and the PR remains reviewable

### Requirement: Single Python dependency source
Python dependency declarations SHALL live in pyproject.toml and resolved versions
in uv.lock. Source setup SHALL use the locked environment. Windows builds SHALL
generate temporary hashed runtime requirements from that lock and install only
compatible Windows wheels with hash verification. No requirements.txt export SHALL
be tracked at the repository root or included in the installed app.

#### Scenario: Build without a tracked export
- **WHEN** a preview Windows installer is built from a clean checkout
- **THEN** dependency installation succeeds using a fresh temporary lock export
  and the installed app runs without a shipped requirements.txt

#### Scenario: Dependency maintenance
- **WHEN** a developer updates a Python dependency
- **THEN** pyproject.toml and uv.lock are the maintained dependency files and no
  separately maintained compatibility export is required

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
Actions SHALL use explicit released version tags and Dependabot updates. Each isolated job SHALL install needed locked dependencies at most once and use supported caches. Only Angular SHALL install frontend workspace tools; other Node jobs SHALL retain required root tools. PRs SHALL retain preview installers; only main SHALL transfer the checked release payload separately from preview assets. Custom scripts SHALL cover documented app contracts, not generic title checks or version calculation.

#### Scenario: Readable action dependency
- **WHEN** a contributor reads a workflow action reference
- **THEN** its released version is visible without resolving an opaque commit SHA

#### Scenario: Root tools remain available
- **WHEN** integration, build or release installs npm dependencies
- **THEN** its root checks remain available without installing the Angular workspace or omitting needed root development dependencies

#### Scenario: Efficient payload transfer
- **WHEN** a PR runs Windows build
- **THEN** its installer/checksum/manifest remain downloadable without creating a release payload archive
- **WHEN** main runs Windows build
- **THEN** release downloads only the checked payload artifact and Windows artifacts use no additional upload compression

### Requirement: Branded compatible distribution
Windows installation and release presentation SHALL use one canonical `TrogloDAW-Setup-<version>.exe` per release, with the supplied stable version suffixed before `.exe`; development previews SHALL use `0.0.0`. Checksums and publication validation SHALL cover that artifact and reject ambiguous installer uploads. Current upgrades SHALL preserve configured assets and preferences; migration of old product-name contracts SHALL NOT be required.

#### Scenario: Legacy download automation
- **WHEN** download automation requests a previous product-name installer filename
- **THEN** no compatibility filename is published and current consumers use the versioned TrogloDAW filename

#### Scenario: Canonical download
- **WHEN** a stable release is published
- **THEN** it contains `TrogloDAW-Setup-<version>.exe`, one matching checksum entry and a source/version manifest identifying that filename

#### Scenario: Retain configured assets
- **WHEN** a current TrogloDAW installation is upgraded
- **THEN** configured library/model locations and preferences remain and known app shortcut cleanup preserves unrelated custom entries

#### Scenario: Keep several installers
- **WHEN** a user downloads installers from two stable releases into the same folder
- **THEN** their different version suffixes identify both releases without a filename collision

#### Scenario: Development preview
- **WHEN** a default development installer is built
- **THEN** its filename is `TrogloDAW-Setup-0.0.0.exe` and its checksum and manifest agree

### Requirement: Installed release identity
Packaging SHALL embed the semantic-release-supplied stable version, checked source commit and current repository identity into the installed app before NSIS packaging. The runtime identity, installer registration and published source/version manifest SHALL agree. Development builds SHALL use explicit development identity without planning or publishing an independent release version. Final-release smoke SHALL verify installed runtime identity.

#### Scenario: Final versioned payload
- **WHEN** semantic-release versions the checked payload
- **THEN** the included app identity and installed service report the same version/source as the published installer manifest without rebuilding frontend assets

### Requirement: Reserved program storage and private access cleanup
Installed library/model selection SHALL reject app/runtime program directories that installation or uninstall removes. Uninstall SHALL check existing configured locations before destructive program cleanup and refuse unsafe legacy locations while preserving data for relocation. App-owned saved release access SHALL be scoped to an installation and removed on its completed uninstall without removing another installation's credentials.

#### Scenario: Legacy library inside program files
- **WHEN** uninstall discovers configured user storage inside its program directories
- **THEN** it stops before deletion and directs the user to move that data through Settings

#### Scenario: Remove one installation
- **WHEN** a safe uninstall completes
- **THEN** its saved release credential is removed while other installations' access and retained user assets remain

### Requirement: Installation migration guidance
Changes that break installed data/configuration or setup compatibility SHALL include a migration/recovery guide under docs and a README reference before delivery. Guides SHALL explain preservation, verification, recovery and known limitations for affected installations.

#### Scenario: Installation contract changes
- **WHEN** an update changes a persisted installation contract incompatibly
- **THEN** its PR includes actionable migration guidance linked from the README before release
