# app-updates Specification

## Purpose

Provide optional stable-release discovery and explicit verified local Windows upgrades while keeping personal audio and generation offline.

## Requirements

### Requirement: Quiet stable release discovery
Installed releases SHALL check published stable releases asynchronously on startup without delaying local workflows. Users SHALL be able to disable startup checks and check manually in Settings. Comparison SHALL use the installed semantic version and ignore drafts, prereleases and older versions. Offline, authorization and rate-limit failures SHALL remain recoverable without blocking audio work. Source/development and unsupported-platform upgrade behavior SHALL be explicit.

#### Scenario: New stable release
- **WHEN** a newer stable release is available
- **THEN** the interface identifies its version and offers explicit download/update actions without installing automatically

#### Scenario: Inspect current version
- **WHEN** the installed app is running before or after an upgrade
- **THEN** its footer and Settings report the packaged current version, with source/development builds clearly labeled

#### Scenario: Offline or limited access
- **WHEN** release access fails or the app is offline/rate limited
- **THEN** local workflows remain usable and Settings exposes a quiet check status with retry/access guidance

### Requirement: Private release access
Private releases SHALL support optional credentials without requiring bundled secrets or a separately installed GitHub CLI. Existing accessible CLI credentials MAY be reused; user-supplied Windows credentials SHALL use the OS credential store. Tokens SHALL NOT enter config, browser persistence, logs, update plans or cross-host asset redirects. Only release metadata/artifacts SHALL use this network path, never personal audio.

#### Scenario: Authenticated asset redirect
- **WHEN** an authenticated release download redirects to another approved HTTPS asset host
- **THEN** authorization headers are removed before following that redirect

#### Scenario: Save private access
- **WHEN** a Windows user explicitly saves a release-access token
- **THEN** the token is stored in the OS credential store, cleared from the input and never returned by status APIs

### Requirement: Verified cancelable downloads
Update download SHALL be explicit and report actual bytes/status with cancellation and retry. Before readiness, the canonical installer SHALL match the same release's checksum and source/version manifest, with coherent version, filename and asset size. Invalid, incomplete, canceled or mismatched artifacts SHALL NOT be launched. Downloads SHALL stay in controlled app storage following the selected model/cache drive.

#### Scenario: Tampered or interrupted artifact
- **WHEN** the installer checksum, source/version metadata or transfer size is invalid, or download is interrupted
- **THEN** the running app and user data remain usable and no installer starts

#### Scenario: Cancel transfer
- **WHEN** the user cancels an update download
- **THEN** the download stops, readiness is cleared and retry remains available

### Requirement: Idle Windows upgrade handoff
Installation SHALL require explicit user action and verified readiness. It SHALL reject active processing, uploads, storage selection and reported live recordings across app tabs, reserving handoff against new work. A hidden helper outside the installation folder SHALL wait for service exit, reverify the installer and apply it to the existing app location. Failed helper launch SHALL leave the service running; installation failure SHALL retain recovery status/artifacts and user data.

#### Scenario: Busy app
- **WHEN** installation is requested during processing or a live recording
- **THEN** installation is rejected without stopping that work

#### Scenario: Complete upgrade
- **WHEN** a verified idle upgrade completes
- **THEN** the installed version is checked before restart and the configured library/model locations, assets, preferences and portable recipes remain

#### Scenario: Handoff fails
- **WHEN** the helper cannot start or acknowledge its plan
- **THEN** the app stays open with a recoverable error rather than claiming installation succeeded
