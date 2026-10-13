## ADDED Requirements

### Requirement: Managed WAV song import
Library SHALL import one valid finite WAV with a title and optional existing logical folder as a playable prior song. Import SHALL preserve the external source, retain an exact managed original and record honest provenance/conversion without invented prompts/stems. Writes SHALL be registered atomically after validation; failures/cancellation SHALL leave no broken entry or overwritten song. Import SHALL support audio up to twenty minutes.

#### Scenario: Import and relocate
- **WHEN** a valid WAV is imported with a title/folder and the complete library is subsequently moved or restarted
- **THEN** the imported song plays, retains its folder/provenance and is selectable as a prior/backing song

#### Scenario: Invalid or failed import
- **WHEN** WAV decoding, validation, storage or catalog commit fails
- **THEN** no broken song is registered, owned partial files are cleaned and the original source remains

#### Scenario: Missing creation metadata
- **WHEN** creation ingredients are requested from an imported WAV
- **THEN** only honestly available metadata is offered and absent lyrics/styles/model ingredients remain unavailable
