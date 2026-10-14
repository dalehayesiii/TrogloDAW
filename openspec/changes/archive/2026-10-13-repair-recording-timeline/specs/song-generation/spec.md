## ADDED Requirements

### Requirement: Direct recording frame alignment
Direct generation SHALL derive timeline length from decoded source samples rather than rounded catalog values. It SHALL preserve source samples through encoder frame alignment using only trailing silence, remove only excess generated tail and reject genuinely incomplete output. Saved provenance SHALL record alignment without changing original audio or historical replay.

#### Scenario: Non-frame-aligned upload
- **WHEN** an intact upload's ending lies between supported decoder frames
- **THEN** the encoder receives the complete ending plus bounded silence to the next frame, and the saved result follows the exact source timeline without a false incomplete-timeline failure

#### Scenario: Rounded catalog duration
- **WHEN** a catalog's millisecond duration differs from its actual decoded sample count
- **THEN** direct input validation, rendering and final length use the decoded count instead of truncating or demanding extra original samples

#### Scenario: Truly incomplete model output
- **WHEN** output still lacks source-timeline samples after encoder alignment
- **THEN** generation fails clearly without silently padding the result or registering an incomplete song

#### Scenario: Retained assets and replay
- **WHEN** a corrected direct song is replayed after moving its complete Library
- **THEN** its original audio and saved generated audio remain unchanged and replay requires no new inference
