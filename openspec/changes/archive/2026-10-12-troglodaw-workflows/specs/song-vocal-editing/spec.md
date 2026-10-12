# Spec Delta

## Purpose

Define cached vocal extraction, uncertain singer-group editing and recoverable FX song versions that preserve the original song timeline.

## ADDED Requirements

### Requirement: Library song editing
Vocal FX SHALL accept generated library songs and FX derivatives, start cached stem lookup automatically, and run missing extraction/analysis in background jobs while the UI remains usable. Standalone voice uploads SHALL remain outside this workflow.

#### Scenario: Open an unedited song
- **WHEN** Edit Vocal FX is selected in Library
- **THEN** Vocal FX opens with that song selected and extraction/analysis starts without a second upload

### Requirement: Candidate vocal groups and correction
The app SHALL expose stable candidate singer/speaker group IDs, previews/solo and correction/grouping controls. Source separation and diarization SHALL not be represented as guaranteed separation of overlapping singers. Uncertain/overlapping results SHALL remain visibly grouped with their limitations explained.

#### Scenario: Simultaneous singers
- **WHEN** extraction contains overlapping singers that cannot reliably be separated
- **THEN** they remain an uncertain shared group instead of being confidently assigned to separate people

### Requirement: Independent group effects
Each group SHALL independently support pitch, time stretch, gain, low/high-cut EQ, compression, chorus, robotization, delay, reverb, trim and normalization, including meaningful detailed parameters. Controls SHALL appear progressively for the selected group.

#### Scenario: Edit one singer group
- **WHEN** gain is changed for one group
- **THEN** only that group's vocal contribution changes and unselected groups retain their settings/audio

### Requirement: Fixed timeline remix
FX SHALL retain source offsets, sample rate, sample count and final duration, compensate relevant latency, constrain duration-changing trim/stretch to fixed slots and handle tails intentionally. Edited voices SHALL remix with retained accompaniment and untouched groups without doubling original mixed vocals.

#### Scenario: Identity effects
- **WHEN** all effects are bypassed
- **THEN** accompaniment plus vocal groups reconstruct the original timeline within documented numeric/encoding tolerance

#### Scenario: Stretch and delay
- **WHEN** stretch or delay is applied to a vocal group
- **THEN** processing stays inside fixed timeline slots/tail policy and the exported song has the original sample count

### Requirement: Source-preserving FX versions
First save SHALL create a new identifiable FX derivative retaining source lineage. Later saves SHALL offer Update this FX version or Save a new FX version, updating only the selected derivative on the update path. The original song SHALL remain separate.

#### Scenario: Update a derivative
- **WHEN** an existing FX version is edited and Update this FX version is selected
- **THEN** its metadata/assets update safely, the original is preserved and reopen uses the family's unprocessed source stems

### Requirement: Versioned portable caches
Source stems, group analysis, edited stems, effect recipes and alignment metadata SHALL be stored with the song family using portable references. Reopens SHALL reuse source caches rather than repeatedly bake effects. Source content and relevant model/processing-version changes SHALL invalidate caches.

#### Scenario: Reopen and invalidate
- **WHEN** an unchanged song family reopens
- **THEN** its cached source extraction/analysis is reused
- **WHEN** the source hash or relevant processing version differs
- **THEN** stale results are invalidated and rebuilt before editing
