# Spec Delta

## ADDED Requirements

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
