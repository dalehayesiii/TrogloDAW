# Spec Delta

## MODIFIED Requirements

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
