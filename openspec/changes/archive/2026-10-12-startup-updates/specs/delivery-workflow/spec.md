# Spec Delta

## ADDED Requirements

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
