# Spec Delta

## MODIFIED Requirements

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

### Requirement: Publish tested version and artifact only
Official semantic-release SHALL run only on main after build and prerequisite jobs succeed. Its prepare hook SHALL version the checked payload and verify final installation, displayed version, API startup, static UI and uninstall without repeating full E2E. Publication SHALL include installer, checksum and source/version manifest. Version/SHA/checksum mismatch or advanced main SHALL abort before tagging. Only the publisher SHALL receive release writes; no custom version planner SHALL be used.

#### Scenario: Asset mismatch
- **WHEN** an installer manifest differs from semantic-release's version or source
- **THEN** publication fails before creating its release tag

#### Scenario: Final installer startup failure
- **WHEN** the versioned release installer cannot start its bundled service or serve its compiled UI
- **THEN** prepare fails before tagging or publishing, without running the full browser/audio workflows again

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
