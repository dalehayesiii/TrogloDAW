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
Update download SHALL be explicit and report bytes/status with cancellation and retry. Discovery SHALL prefer `TrogloDAW-Setup-<release-version>.exe`, accepting the historical fixed name only when that asset is absent. Readiness SHALL require matching release checksum, source/version manifest, selected filename and asset size. Invalid, incomplete, canceled or mismatched artifacts SHALL NOT launch. Downloads SHALL use controlled storage on the selected model/cache drive.

#### Scenario: Tampered or interrupted artifact
- **WHEN** the installer checksum, source/version metadata or transfer size is invalid, or download is interrupted
- **THEN** the running app and user data remain usable and no installer starts

#### Scenario: Cancel transfer
- **WHEN** the user cancels an update download
- **THEN** the download stops, readiness is cleared and retry remains available

#### Scenario: Versioned release
- **WHEN** a newer stable release publishes its exact versioned installer
- **THEN** discovery selects it and readiness requires that filename in its manifest and checksum

#### Scenario: Historical fixed-name release
- **WHEN** a newer stable release has only the historical `TrogloDAW-Setup.exe` asset
- **THEN** discovery and verified download remain supported using that exact historical filename

#### Scenario: Both names available
- **WHEN** a release contains both versioned and historical installer names
- **THEN** the exact versioned asset is selected and invalid verification does not fall back to the historical asset

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

### Requirement: Accessible release discovery
Update checks SHALL reuse available preferred or active GitHub CLI credentials, including standard Windows CLI installs missed by an older desktop PATH. Settings SHALL offer opening the latest release in the browser for manual access using that browser's login. Browser login SHALL not imply authenticated backend download access or require browser-cookie extraction. Existing private/public access and verification rules SHALL remain.

#### Scenario: CLI installed after desktop login
- **WHEN** the desktop PATH misses a GitHub CLI executable in a standard Windows install location
- **THEN** checks can discover and reuse its authenticated release access without a separately entered token

#### Scenario: Another active account
- **WHEN** neither preferred username has accessible credentials but another active CLI login does
- **THEN** update discovery can use that active CLI login

#### Scenario: Browser-only login
- **WHEN** the user has private repository access only through their browser
- **THEN** Settings can open the latest release there for manual download while verified in-app downloads retain separate authentication requirements

### Requirement: Observable update checking
Manual checks SHALL immediately show a checking state while release work is pending; background checks SHALL expose the same pending message. Ordinary status-read failures SHALL appear inline and clear after a successful read without falsely reporting that ongoing backend work failed. Expected handoff interruptions SHALL remain quiet. Completed checks SHALL report availability, current status or a recoverable error.

#### Scenario: Slow release access
- **WHEN** a manual check waits on credentials or the release service
- **THEN** the UI shows Checking immediately and disables duplicate check requests until its result

#### Scenario: Status read fails
- **WHEN** status polling fails outside an installer handoff
- **THEN** an inline status-read error appears while polling continues, and a successful read clears it

#### Scenario: Handoff listener changes
- **WHEN** polling briefly fails during the explicit installer handoff
- **THEN** the expected interruption does not replace installation progress with a status error

### Requirement: Bounded idle process handoff
An acknowledged idle Windows update SHALL wait thirty seconds for graceful old-process exit, then MAY terminate only that same validated original executable/start-time identity. It SHALL wait for exit before installation; reused PIDs or changed executable identities SHALL fail safely.

#### Scenario: Stalled idle shutdown
- **WHEN** the acknowledged idle app stops serving HTTP but its original process remains alive beyond the exit deadline
- **THEN** only that validated process is stopped, installation proceeds after exit, and the verified restarted app becomes healthy without leaving an orphaned launcher lock

#### Scenario: Original process identity changed
- **WHEN** the recorded PID now belongs to a different process or executable
- **THEN** the helper does not stop that process or launch the installer

### Requirement: Observable helper recovery and verified restart
Helper failures SHALL retain status/artifacts and serve recovery status on the original local port when available, including failures before installer launch. Successful completion SHALL require restarted application health, compiled frontend and the verified version/source identity within sixty seconds; restart failures SHALL retain local diagnostic logs.

#### Scenario: Failure before installation
- **WHEN** an acknowledged handoff fails before the installer starts and the local port is available
- **THEN** the helper serves retained failure details and recovery guidance so a browser reload does not leave an unexplained wait

#### Scenario: Restart cannot become healthy
- **WHEN** installed files verify but the restarted app exits, fails to serve or reports a different identity
- **THEN** the helper reports failure with retained diagnostics rather than claiming successful reopening

### Requirement: Recoverable missing handoff status
After forty-five seconds without a successful handoff status read, the browser SHALL show actionable unavailable-status feedback while continuing to poll. A later successful read SHALL clear that warning; the verified restarted version SHALL return the page to the app. Reloading during helper failure SHALL show retained recovery status when its listener is available.

#### Scenario: Helper status remains unavailable
- **WHEN** expected listener interruption continues beyond forty-five seconds
- **THEN** the page explains how to reopen or repair the app instead of indefinitely promising automatic return, and polling remains active
