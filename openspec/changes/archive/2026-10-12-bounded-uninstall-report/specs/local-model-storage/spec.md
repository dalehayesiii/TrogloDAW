# Spec Delta

## ADDED Requirements

### Requirement: Reliable uninstall cleanup reporting
Successful ownership-aware model cleanup SHALL permit uninstall to finish regardless of the number of recorded assets or canceled-setup cache files. Installer-facing success output SHALL remain bounded and omit per-file paths. Actual cleanup errors SHALL retain failure status and preserve the existing retry-with-model-retention option.

#### Scenario: Thousands of interrupted setup files
- **WHEN** default uninstall successfully removes thousands of recorded unchanged cache files after canceled setup
- **THEN** uninstall completes, reports bounded removal/retention counts, and preserves unrelated files, shared assets and libraries

#### Scenario: Unsafe cleanup metadata
- **WHEN** cleanup encounters unsafe manifest paths or an actual removal error
- **THEN** uninstall receives failure status rather than a success summary and offers retry with model removal unchecked
