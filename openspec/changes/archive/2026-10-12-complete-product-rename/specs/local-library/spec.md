## MODIFIED Requirements

### Requirement: Local configuration precedence
The app SHALL resolve runtime settings from environment variables, then config.local.json, then config.json, then defaults. TROGLODAW_CONFIG_DIR SHALL select the config folder. It SHALL accept UTF-16 installer configs and default to localhost and a library next to the source app. Current CLI/environment identifiers SHALL use the TrogloDAW namespace without old-name aliases.

#### Scenario: Machine override
- **WHEN** port is configured in both files and TROGLODAW_PORT is set
- **THEN** TROGLODAW_PORT wins, with the local file taking precedence if the variable is absent
