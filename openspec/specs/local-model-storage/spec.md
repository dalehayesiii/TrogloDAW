# local-model-storage Specification

## Purpose

Define explicit, verified offline model setup and persistent user-selected locations for inference assets and caches.

## Requirements

### Requirement: Selected model destination
Settings SHALL show and persist a separate model-storage folder. Initial setup and Settings SHALL offer a user-triggered native Windows directory picker rather than requiring typed paths. Before every new model download, users SHALL see/change its destination, role, compatible hardware and known size. All required weights, encoders, decoders, tokenizers, support assets and provider caches SHALL follow that folder without silently creating large home-drive caches.

#### Scenario: Choose a different drive
- **WHEN** model setup is initiated with a selected folder on another drive
- **THEN** downloads, partial assets and inference caches remain under that folder and the choice survives restarts

#### Scenario: Cancel native selection
- **WHEN** the directory picker is canceled
- **THEN** the selected location and existing data remain unchanged and model installation does not start

### Requirement: Verified explicit acquisition
Model downloads SHALL be explicit, version-pinned and verified before activation. Setup SHALL validate destination write access/free storage, expose progress and failure/cancel state, and recover partial downloads where supported. Optional-model failure SHALL preserve the working model. Runtime generation SHALL work offline after verified setup.

#### Scenario: Interrupted installation
- **WHEN** a download fails or is canceled
- **THEN** the app reports its state, preserves verified working assets and offers recoverable setup without selecting incomplete weights

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

### Requirement: Model removal and retention
Uninstall SHALL offer removal of installed model assets checked by default, with opt-out retention. Removal SHALL use an ownership manifest, preserve unrelated files/user libraries and handle custom/shared folders safely. Upgrades SHALL preserve verified assets and storage preferences.

#### Scenario: Custom model folder
- **WHEN** uninstall runs with model removal selected
- **THEN** only this installation's recorded model assets are removed without recursively deleting unrelated directory contents

#### Scenario: Keep models
- **WHEN** model removal is unchecked
- **THEN** uninstall retains model assets for later reuse

### Requirement: Compatible model reuse
Settings SHALL allow installing/selecting supported compatible models and reusing verified local assets. Location changes SHALL offer verified moves, destination reuse or cancellation when current/default data exists. Moves SHALL verify managed data before committing preferences and retain shared, changed and unrelated originals. Model/version references SHALL persist without unnecessary downloads. Installation/verification SHALL remain separate from folder selection.

#### Scenario: Reuse an existing installation
- **WHEN** a folder containing verified compatible assets is selected
- **THEN** the app activates those assets without redownloading them and retains the previous assets if verification fails

#### Scenario: Move shared models
- **WHEN** model data is moved to an empty chosen folder
- **THEN** verified independent assets and this installation's references follow the new location while shared originals, foreign references and unrelated data remain in the original folder

### Requirement: Sequential memory-aware inference
Inference SHALL use measured available GPU/system memory and compatible offload/fallback settings, preserving normal desktop/display activity. GPU-heavy stages SHALL not compete. Unsupported workloads SHALL fail clearly without silently substituting procedural generation or changing requested duration.

#### Scenario: Insufficient free GPU memory
- **WHEN** available memory is insufficient for the selected workload
- **THEN** the app uses a validated fallback or reports the limit while preserving successful outputs and user inputs

### Requirement: Observable acquisition work
Setup SHALL show the selected destination, current file/asset, known required-asset bytes, reuse/resumption and overall asset progress separately from verification, extraction, runtime installation and loading. Unknown transfer/work totals SHALL remain honest; complete asset bytes SHALL NOT imply complete model activation. Failure/cancel state SHALL preserve working assets and partial-resume capability.

#### Scenario: Resumed asset
- **WHEN** a server resumes a partial model download
- **THEN** actual downloaded/resumed bytes and the known file/asset total are visible at the selected destination, followed by verification before activation

#### Scenario: Unknown-sized runtime installation
- **WHEN** locked inference wheels are installed without a reliable aggregate transfer total
- **THEN** setup shows the installation stage and elapsed/estimating state rather than invented byte totals or a completed job

### Requirement: Owned interrupted transfer caches
New partial-download files SHALL live within this installation's selected model cache and be recorded safely for default uninstall cleanup, including changed/resumed files after interruption. Unowned legacy partials, unrelated files and mismatched existing final assets SHALL be preserved.

#### Scenario: Uninstall canceled download
- **WHEN** setup is canceled after writing a partial asset and default model removal is chosen at uninstall
- **THEN** the recorded unchanged partial may be removed while unrelated or unowned legacy files remain

### Requirement: Model download time remaining
Known model-file download remaining time SHALL update from measured transfer speed and bytes still missing across all required assets, separately from the current file and subsequent setup stages. Verification speed SHALL NOT be presented as network transfer speed.

#### Scenario: Multi-file transfer
- **WHEN** required model files are downloading
- **THEN** setup shows a live range for all remaining known file bytes alongside elapsed time, current-file progress and destination, without claiming subsequent verification or runtime installation finishes then

### Requirement: Reliable uninstall cleanup reporting
Successful ownership-aware model cleanup SHALL permit uninstall to finish regardless of the number of recorded assets or canceled-setup cache files. Installer-facing success output SHALL remain bounded and omit per-file paths. Actual cleanup errors SHALL retain failure status and preserve the existing retry-with-model-retention option.

#### Scenario: Thousands of interrupted setup files
- **WHEN** default uninstall successfully removes thousands of recorded unchanged cache files after canceled setup
- **THEN** uninstall completes, reports bounded removal/retention counts, and preserves unrelated files, shared assets and libraries

#### Scenario: Unsafe cleanup metadata
- **WHEN** cleanup encounters unsafe manifest paths or an actual removal error
- **THEN** uninstall receives failure status rather than a success summary and offers retry with model removal unchecked

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

#### Scenario: Quiet runtime installation
- **WHEN** the runtime tool downloads or installs large packages without reliable aggregate bytes
- **THEN** setup reports safe recognized package activity, current-stage elapsed time and liveness without inventing totals, then shows measured file-registration progress for safe cleanup
