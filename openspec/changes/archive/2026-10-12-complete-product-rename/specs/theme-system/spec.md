## MODIFIED Requirements

### Requirement: Consistent product identity
The app/header/browser title, Windows installer/assets/shortcut/uninstall metadata, runtime/default-root/tooling identifiers, current release-facing descriptions and maintained documentation SHALL identify TrogloDAW without compatibility aliases using the previous product name. Existing remote repository URLs SHALL remain valid and historical evidence SHALL remain truthful.

#### Scenario: Upgrade an existing installation
- **WHEN** a current TrogloDAW installation is upgraded
- **THEN** installer/launch/icon/payload/default paths retain the complete TrogloDAW identity while configured user asset locations and preferences remain usable

#### Scenario: Fresh complete identity
- **WHEN** TrogloDAW is installed and its current repository assets are inspected
- **THEN** installer/launch/icon/payload/default paths and current product names consistently use TrogloDAW without previous-name aliases
