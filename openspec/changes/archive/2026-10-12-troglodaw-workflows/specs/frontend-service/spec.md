# Spec Delta

## MODIFIED Requirements

### Requirement: Preserve initial visual and control contracts
The frontend SHALL expose exactly Generation, Library and Vocal FX as primary tabs. It SHALL retain the baseline visual vocabulary until the separate theme change. Generation SHALL use concise requested inputs and collapsed More Options; detailed clip, reference, FX and storage/model controls SHALL use progressive disclosure. Drafts and selections SHALL survive navigation.

#### Scenario: Defaults on first load
- **WHEN** a user opens Generation
- **THEN** Number of Generations is one, More Options is collapsed and only the requested generation controls are available

#### Scenario: Visual evidence
- **WHEN** the workflow change is reviewed
- **THEN** screenshots at representative desktop/narrow viewports cover all three tabs, expanded settings, results, references and error states

### Requirement: Browser functional parity
The browser SHALL provide uploads/recordings, local library organization/playback,
selective recipe reuse, source-sample generation, song Vocal FX, downloads, refresh
and quit through Python. Existing catalogs and playable legacy songs SHALL remain
accessible. Existing DSP and CLI operations SHALL remain compatible while new
song inference/editing extends their behavior.

#### Scenario: Recipe loading
- **WHEN** saved creation ingredients are selectively imported
- **THEN** only chosen available fields populate Generation, preserving other draft values

#### Scenario: No voice selected
- **WHEN** lyrics/styles are supplied without audio
- **THEN** model inference creates a song without requiring a vocal upload

## ADDED Requirements

### Requirement: Task-focused accessible workflows
Each primary tab SHALL have a clear current task/selection and primary action. Empty, loading and error states SHALL explain next steps. Help SHALL work with keyboard/tap as well as hover. Infrequent setup SHALL use a compact settings dialog/drawer without an extra primary tab or normal-form diagnostics.

#### Scenario: First-use task
- **WHEN** a user records/uploads clips, generates, organizes/reuses a song, edits a vocal group or chooses storage
- **THEN** they can complete the flow through labeled controls without developer documentation or manual config editing
