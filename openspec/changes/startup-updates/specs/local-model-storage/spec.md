# Spec Delta

## MODIFIED Requirements

### Requirement: Initial model installation
Initial setup SHALL offer the recommended tested model/default folder and alternatives on first run only. It SHALL require explicit verified acquisition, show pinned versions/sizes and never bundle weights. Installation preferences SHALL retain setup history across upgrades; fresh reinstalls without preferences SHALL prompt again even when retained assets exist.

#### Scenario: Fresh installation
- **WHEN** the app opens without prior installation setup history
- **THEN** centered first-run setup offers the recommended model/default folder and alternatives before an explicit download

#### Scenario: Completed setup offline
- **WHEN** setup verifies all required assets and the network is disabled
- **THEN** local first generation works from the selected assets without another download

#### Scenario: Upgrade with existing setup
- **WHEN** the installed app is updated with preserved setup preferences
- **THEN** startup reuses them without reopening first-run setup, including unfinished background installation

#### Scenario: Reinstall with retained assets
- **WHEN** a fresh installation selects previously retained library/model folders
- **THEN** its explicit verification reuses compatible assets/runtime without unnecessary downloads and preserves incompatible existing files

## ADDED Requirements

### Requirement: Distinct onboarding and background continuation
First-run setup and Settings SHALL be separate flows sharing useful embedded controls. All foreground modal dialogs SHALL be centered. Closing setup SHALL leave backend installation running with clear continuation guidance. The app SHALL explain available local work and block song generation until a compatible model is ready. Job cards SHALL retain spacing from surrounding widgets.

#### Scenario: Continue exploring during installation
- **WHEN** explicit model installation starts and the user chooses Continue in background
- **THEN** setup closes, existing job progress remains visible, import/record/playback/drafts remain available and generation waits for readiness

### Requirement: Independent download and installation status
Model setup SHALL show local start time and combined download/installation remaining time on one line. Overall and current-stage progress/time scopes SHALL describe Download until its known bytes are present, then switch to Installation. Installation SHALL count actual completed verification/runtime checkpoints, with unknown stage totals indeterminate. Complete bytes SHALL NOT imply ready state.

#### Scenario: Transfer finishes before runtime setup
- **WHEN** all required model files are present but runtime setup or verification remains
- **THEN** both bars switch to Installation with completed checkpoints and actual stage work, retaining the combined top estimate or estimating state until activation
