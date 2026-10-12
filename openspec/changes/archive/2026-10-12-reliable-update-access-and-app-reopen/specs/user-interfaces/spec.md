# Spec Delta

## ADDED Requirements

### Requirement: One running browser app per configuration
The launcher SHALL maintain one running service per configuration root, reopening its verified local URL on later desktop launches even when it uses a nondefault port. Concurrent launch attempts SHALL not create duplicate services. Closing a browser tab SHALL leave background work running; Quit SHALL stop the service. Crashed services and stale launch state SHALL permit a fresh launch, without treating unrelated listeners as this app.

#### Scenario: Close and reopen
- **WHEN** the user closes the tab and launches the desktop shortcut again
- **THEN** the existing service is reused and its browser UI reopens without another background service

#### Scenario: Default port occupied
- **WHEN** another application owns the default port
- **THEN** TrogloDAW chooses an available local port and subsequent launches reuse that instance

#### Scenario: Concurrent launches
- **WHEN** two launches start together for the same configuration
- **THEN** one starts the service and the other waits for verified readiness without starting another service

#### Scenario: Restart after exit
- **WHEN** Quit finishes or the service crashes leaving stale launch metadata
- **THEN** the next launch can start a fresh service
