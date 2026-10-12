## MODIFIED Requirements

### Requirement: Branded compatible distribution
Windows installation and release presentation SHALL use TrogloDAW with one canonical TrogloDAW-Setup.exe and no legacy installer alias. Checksums and publication validation SHALL cover that actual distributed artifact. Current TrogloDAW upgrades SHALL preserve configured user assets and preferences; migration of old product-name contracts SHALL NOT be required.

#### Scenario: Legacy download automation
- **WHEN** download automation requests a previous product-name installer filename
- **THEN** no compatibility filename is published and current consumers use TrogloDAW-Setup.exe

#### Scenario: Canonical download
- **WHEN** a stable release is published
- **THEN** it contains the canonical TrogloDAW installer, one matching checksum entry and source/version manifest without compatibility-installer metadata

#### Scenario: Retain configured assets
- **WHEN** a current TrogloDAW installation is upgraded
- **THEN** configured library/model locations and preferences remain and known app shortcut cleanup preserves unrelated custom entries
