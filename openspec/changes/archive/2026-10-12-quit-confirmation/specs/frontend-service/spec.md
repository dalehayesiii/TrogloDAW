# Spec Delta

## ADDED Requirements

### Requirement: Full-page Quit confirmation
After acknowledged local shutdown, Quit SHALL replace the entire working interface with an accessible themed confirmation that TrogloDAW has stopped and the browser window can be closed. Recording and playback SHALL stop, dialogs/workflow controls SHALL disappear, and no browser-close permission SHALL be required. Failed or unacknowledged shutdown SHALL preserve the interface with a recoverable error.

#### Scenario: Successful Quit
- **WHEN** Quit receives the local shutdown acknowledgment
- **THEN** the page shows only the stopped confirmation with keyboard focus on its heading and remains readable after the service exits

#### Scenario: Shutdown request fails
- **WHEN** the shutdown request fails before acknowledgment
- **THEN** the working interface remains available with an error and Quit can be retried
