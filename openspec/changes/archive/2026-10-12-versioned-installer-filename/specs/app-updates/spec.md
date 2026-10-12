# Spec Delta

## MODIFIED Requirements

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
