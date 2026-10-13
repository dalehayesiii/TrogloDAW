## MODIFIED Requirements

### Requirement: Visible model role identities
Initial setup and Settings SHALL identify the models configured for lyric writing, automatic song length and compatible musical blueprint planning alongside independent installation/readiness state. These identities SHALL follow the configured music model's associated planner/writer. Fixed vocal-separation and voice-grouping models SHALL be inspectable through progressive disclosure. Identifying a model SHALL not imply installation or introduce a new provider selector.

#### Scenario: Song writing tools absent
- **WHEN** song writing tools are not installed
- **THEN** Settings shows the configured lyric/length/blueprint model names and explains the existing setup requirement

#### Scenario: Configured model association changes
- **WHEN** the configured music model uses a different planner/writer association
- **THEN** model-description metadata and Settings reflect that association without downloading weights

#### Scenario: Inspect voice processing
- **WHEN** the user expands the voice-processing model disclosure
- **THEN** the fixed vocal-separation and voice-grouping model names are visible without adding provider choices
