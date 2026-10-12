## ADDED Requirements

### Requirement: Nested input clip adjustments
Input Audio SHALL contain an initially collapsed, clearly named Clip adjustments disclosure for each selected clip. It SHALL explain and expose existing pitch, speed/stretch, volume and replacement choices within the Input Audio widget rather than adding a separate task panel. Adjustments SHALL remain available to uploaded, recorded and prior-song clips because they affect every input source. Existing draft/recipe settings and explicit prior-song preset decisions SHALL be preserved.

#### Scenario: Adjust a recorded clip
- **WHEN** a recording is accepted and Clip adjustments is expanded
- **THEN** the user can change that clip's existing pitch, speed and volume before arrangement without adding a new workflow or changing other clips

#### Scenario: Default input disclosure
- **WHEN** a clip is added to Input Audio
- **THEN** its audio preview/actions are visible and Clip adjustments is closed until requested
