# Spec Delta

## ADDED Requirements

### Requirement: Installed release identity
Packaging SHALL embed the semantic-release-supplied stable version, checked source commit and current repository identity into the installed app before NSIS packaging. The runtime identity, installer registration and published source/version manifest SHALL agree. Development builds SHALL use explicit development identity without planning or publishing an independent release version. Final-release smoke SHALL verify installed runtime identity.

#### Scenario: Final versioned payload
- **WHEN** semantic-release versions the checked payload
- **THEN** the included app identity and installed service report the same version/source as the published installer manifest without rebuilding frontend assets
