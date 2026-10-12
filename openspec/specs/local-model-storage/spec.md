# local-model-storage Specification

## Purpose

Define explicit, verified offline model setup and persistent user-selected locations for inference assets and caches.

## Requirements

### Requirement: Selected model destination
Settings SHALL show and persist a separate model-storage folder. Before every new model download, users SHALL see/change its destination, role, compatible hardware and known size. All required weights, encoders, decoders, tokenizers, support assets and provider caches SHALL follow that folder without silently creating large home-drive caches.

#### Scenario: Choose a different drive
- **WHEN** model setup is initiated with a selected folder on another drive
- **THEN** downloads, partial assets and inference caches remain under that folder and the choice survives restarts

### Requirement: Verified explicit acquisition
Model downloads SHALL be explicit, version-pinned and verified before activation. Setup SHALL validate destination write access/free storage, expose progress and failure/cancel state, and recover partial downloads where supported. Optional-model failure SHALL preserve the working model. Runtime generation SHALL work offline after verified setup.

#### Scenario: Interrupted installation
- **WHEN** a download fails or is canceled
- **THEN** the app reports its state, preserves verified working assets and offers recoverable setup without selecting incomplete weights

### Requirement: Initial model installation
Initial setup SHALL install the recommended model into a known default folder, allowing a different supported model and/or destination. The recommendation SHALL use actual Windows RTX 3070 inference tests. Setup SHALL identify required downloads, exact versions and known sizes; model weights SHALL not need to be bundled with the app installer. Ready state SHALL require verified complete assets.

#### Scenario: Fresh installation
- **WHEN** the app opens without verified model assets
- **THEN** compact initial setup offers the recommended model/default folder and alternatives before an explicit download

#### Scenario: Completed setup offline
- **WHEN** setup verifies all required assets and the network is disabled
- **THEN** local first generation works from the selected assets without another download

### Requirement: Model removal and retention
Uninstall SHALL offer removal of installed model assets checked by default, with opt-out retention. Removal SHALL use an ownership manifest, preserve unrelated files/user libraries and handle custom/shared folders safely. Upgrades SHALL preserve verified assets and storage preferences.

#### Scenario: Custom model folder
- **WHEN** uninstall runs with model removal selected
- **THEN** only this installation's recorded model assets are removed without recursively deleting unrelated directory contents

#### Scenario: Keep models
- **WHEN** model removal is unchecked
- **THEN** uninstall retains model assets for later reuse

### Requirement: Compatible model reuse
Settings SHALL allow installing/selecting supported compatible models and reusing verified local assets. Changing model location SHALL offer existing-folder reuse or recoverable relocation, retain model/version references and avoid unnecessary duplicate downloads. Model setup SHALL remain outside the default song form.

#### Scenario: Reuse an existing installation
- **WHEN** a folder containing verified compatible assets is selected
- **THEN** the app activates those assets without redownloading them and retains the previous assets if verification fails

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
