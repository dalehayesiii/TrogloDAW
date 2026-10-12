# Spec Delta

## ADDED Requirements

### Requirement: Observable update checking
Manual checks SHALL immediately show a checking state while release work is pending; background checks SHALL expose the same pending message. Ordinary status-read failures SHALL appear inline and clear after a successful read without falsely reporting that ongoing backend work failed. Expected handoff interruptions SHALL remain quiet. Completed checks SHALL report availability, current status or a recoverable error.

#### Scenario: Slow release access
- **WHEN** a manual check waits on credentials or the release service
- **THEN** the UI shows Checking immediately and disables duplicate check requests until its result

#### Scenario: Status read fails
- **WHEN** status polling fails outside an installer handoff
- **THEN** an inline status-read error appears while polling continues, and a successful read clears it

#### Scenario: Handoff listener changes
- **WHEN** polling briefly fails during the explicit installer handoff
- **THEN** the expected interruption does not replace installation progress with a status error
