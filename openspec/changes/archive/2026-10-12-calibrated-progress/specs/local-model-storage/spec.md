## ADDED Requirements

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
