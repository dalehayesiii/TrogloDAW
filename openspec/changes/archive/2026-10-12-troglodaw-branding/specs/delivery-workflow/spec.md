# Spec Delta

## ADDED Requirements

### Requirement: Branded compatible distribution
Windows installation and release presentation SHALL use TrogloDAW, with a canonical TrogloDAW installer and byte-identical legacy installer alias for automation compatibility. Checksums and publication validation SHALL cover the actual distributed artifacts. Existing installed roots, registry/config/environment/launcher contracts and user assets SHALL remain compatible.

#### Scenario: Legacy download automation
- **WHEN** a published release is consumed using the old installer filename
- **THEN** it resolves to the same validated installer/version/source as the canonical TrogloDAW filename

#### Scenario: Retain configured assets
- **WHEN** an existing installation is upgraded with TrogloDAW branding
- **THEN** existing library/model locations and preferences remain, and shortcuts/uninstall display identify TrogloDAW without removing unrelated custom entries
