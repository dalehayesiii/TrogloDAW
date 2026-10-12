## MODIFIED Requirements

### Requirement: Persistent recoverable library selection
Initial setup and Settings SHALL offer a native Windows folder picker and show/persist the complete library location. Selection SHALL validate access, space and conflicts without silent fallback, prompting to move detected data, reuse the destination or cancel. Moves SHALL verify managed assets before committing preferences and deleting unchanged originals, retaining changed/unrelated files. Portable recipes and existing registered media SHALL remain playable.

#### Scenario: Interrupted relocation
- **WHEN** copying fails or a drive disappears before verification
- **THEN** the original library remains intact/active and the app reports failure without losing data or selecting an incomplete destination

#### Scenario: Existing destination
- **WHEN** relocation targets existing conflicting content
- **THEN** the app refuses destructive overwrite and offers explicit existing-library reuse

#### Scenario: Play after moving
- **WHEN** a selected library moves successfully to an empty destination
- **THEN** its songs and saved recipes resolve after restart, existing media tokens point to the verified new files and unrelated files remain in the original folder
