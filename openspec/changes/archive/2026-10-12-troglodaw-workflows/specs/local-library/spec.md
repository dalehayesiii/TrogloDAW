# Spec Delta

## ADDED Requirements

### Requirement: Persistent song organization
Library SHALL list/play generated songs and FX versions with persistent folders, move/rename and search. Organization SHALL preserve song IDs, source/recipe references, assets and FX lineage. Legacy songs SHALL remain playable without destructive metadata migration.

#### Scenario: Move and rename
- **WHEN** a song moves to a folder and is renamed
- **THEN** its ID, recipe, inputs and assets still resolve after restart

### Requirement: Direct song reuse actions
Song selection SHALL offer Use as Input Audio, Reuse Creation Ingredients and Edit Vocal FX. Each SHALL immediately open the destination tab with the selected song/context without manual re-upload.

#### Scenario: Use a finished song
- **WHEN** Use as Input Audio is selected
- **THEN** Generation adds that rendered song with source ID/lineage and prompts the required prior-song preset decision

### Requirement: Persistent recoverable library selection
Settings SHALL show/select/persist the complete library root and distinguish opening an existing library from relocating the current one. Selection SHALL validate write access, storage and destination conflicts without silent fallback. Relocation SHALL verify the complete copied data before removing old data, preserve portable references and recover from interruption.

#### Scenario: Interrupted relocation
- **WHEN** copying fails or a drive disappears before verification
- **THEN** the original library remains intact/active and the app reports failure without losing data or selecting an incomplete destination

#### Scenario: Existing destination
- **WHEN** relocation targets existing conflicting content
- **THEN** the app refuses destructive overwrite and offers explicit existing-library reuse
