## ADDED Requirements

### Requirement: Simple initial setup and Settings folder workflow
Initial setup and Settings SHALL share clearly labeled model/library folder controls. On Windows an explicit Choose folder action SHALL open a native directory picker, display the selected location and leave it unchanged on cancellation. Unsupported source platforms SHALL offer an explicit manual-path fallback. Existing managed data SHALL trigger clear Move existing data, Use folder without moving and Cancel choices when selecting another folder.

#### Scenario: Change a detected default location
- **WHEN** a different model/library folder is selected while data exists in the default/current folder
- **THEN** the user chooses whether to move that data before the app changes its location, using the same workflow during initial setup or later Settings

#### Scenario: Install after folder selection
- **WHEN** a model folder is selected
- **THEN** one distinct Install or verify action uses that destination and preserves elapsed time, actual-byte download time remaining and separate verification/runtime readiness status
