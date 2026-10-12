## MODIFIED Requirements

### Requirement: Persistent recoverable library selection
Initial setup and Settings SHALL use a native Windows folder picker, display/persist the complete library location and prompt to move detected current/default managed data or use the destination without moving. Selection SHALL validate write access, storage and destination conflicts without silent fallback. Moves SHALL verify managed catalog/audio/recipe assets before committing preferences and removing unchanged originals. Portable references and existing registered media SHALL remain playable after the move; changed/unrelated originals SHALL be retained.

#### Scenario: Interrupted relocation
- **WHEN** copying fails or a drive disappears before verification
- **THEN** the original library remains intact/active and the app reports failure without losing data or selecting an incomplete destination

#### Scenario: Existing destination
- **WHEN** relocation targets existing conflicting content
- **THEN** the app refuses destructive overwrite and offers explicit existing-library reuse

#### Scenario: Play after moving
- **WHEN** a selected library moves successfully to an empty destination
- **THEN** its songs and saved recipes resolve after restart, existing media tokens point to the verified new files and unrelated files remain in the original folder
