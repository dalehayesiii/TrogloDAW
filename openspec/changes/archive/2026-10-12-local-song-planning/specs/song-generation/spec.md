## MODIFIED Requirements

### Requirement: Sequential independent outputs
Number of Generations SHALL be a positive integer defaulting to two for fresh drafts and omitted counts. Saved explicit counts SHALL remain unchanged. Each output SHALL be independently cataloged with separate seed/settings and success/failure state. GPU-heavy stages SHALL run sequentially when memory requires; count SHALL not imply concurrent GPU batch size.

#### Scenario: One output fails in a request
- **WHEN** a generation fails after an earlier output completed
- **THEN** the completed song remains available and each requested output has an explicit outcome

#### Scenario: Upgrade a saved one-output draft
- **WHEN** an existing draft explicitly requests one output
- **THEN** it continues requesting one while fresh drafts default to two

## ADDED Requirements

### Requirement: Editable local automatic lyrics
Generation SHALL offer explicit local lyric writing from a song idea and language preference. Successful text SHALL become editable input lyrics; failures SHALL preserve the previous text. Manual lyrics SHALL remain unchanged during music generation and blank lyrics SHALL remain instrumental. Historical job restoration SHALL not overwrite a newer draft.

#### Scenario: Generate and edit words
- **WHEN** a user generates lyrics from an idea with an installed planner
- **THEN** the local planner writes lyrics, the user can edit them before generating music, and an expiring dismissible notification reports completion

#### Scenario: Failed writing preserves manual text
- **WHEN** local lyric writing fails or is canceled
- **THEN** existing lyrics remain available without a partial replacement

### Requirement: Bounded model-planned song duration
Explicit duration SHALL support 10–300 seconds. Missing, blank or auto duration SHALL invoke an installed local planner before sample arrangement, preserve supplied lyrics/styles and bound its finite positive suggestion to 10–300 seconds. Recipes SHALL retain the request, raw suggestion, effective length and planner provenance. Unavailable planning SHALL explain setup or explicit-duration alternatives.

#### Scenario: Automatic instrumental duration
- **WHEN** styles are supplied, lyrics are blank and duration is unspecified
- **THEN** the local planner chooses a bounded length without a fixed one-minute default and the rendered song remains instrumental

#### Scenario: Five-minute explicit song
- **WHEN** duration is 300 seconds
- **THEN** generation attempts the complete requested length with existing memory safeguards and reports failure rather than silently truncating
