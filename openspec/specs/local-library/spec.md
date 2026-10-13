# local-library Specification

## Purpose

Describe TrogloDAW's local configuration, portable catalog, song organization and recoverable library selection shared by the UI and CLI.

## Requirements

### Requirement: Local configuration precedence
The app SHALL resolve runtime settings from environment variables, then config.local.json, then config.json, then defaults. TROGLODAW_CONFIG_DIR SHALL select the config folder. It SHALL accept UTF-16 installer configs and default to localhost and a library next to the source app. Current CLI/environment identifiers SHALL use the TrogloDAW namespace without old-name aliases.

#### Scenario: Machine override
- **WHEN** port is configured in both files and TROGLODAW_PORT is set
- **THEN** TROGLODAW_PORT wins, with the local file taking precedence if the variable is absent

### Requirement: Import and catalog persistence
The app SHALL decode supported input audio using bundled/configured ffmpeg,
store 44.1 kHz stereo audio in the library, and record items with id, name, type,
duration, source, creation time, tags and applicable recipe. Catalog writes SHALL
use a process/thread lock and atomic replacement. Managed file paths SHALL be
relative to the library so the catalog can move with its files.

#### Scenario: Import a voice
- **WHEN** a user imports a supported recording as a voice
- **THEN** it is saved under voices and listed in the catalog with a relative file path

#### Scenario: Relocate library
- **WHEN** a library and its catalog move together and library_dir is updated
- **THEN** stored relative paths resolve against the new library directory

### Requirement: Library operations
The app SHALL support type/tag filtering, full id or unique prefix lookup,
latest exact-name lookup, tagging, renaming, deleting, and importing inbox files.
Deleting an item SHALL remove its catalog entry and managed audio by default.
Ambiguous id prefixes and unknown references SHALL report an error.

#### Scenario: Rename and delete
- **WHEN** an item is renamed and later deleted
- **THEN** the new name resolves before deletion and the item/files are absent afterwards

### Requirement: Persistent song organization
Library SHALL list/play generated songs and FX versions with persistent folders, move/rename and search. Organization SHALL preserve song IDs, source/recipe references, assets and FX lineage. Legacy songs SHALL remain playable without destructive metadata migration.

#### Scenario: Move and rename
- **WHEN** a song moves to a folder and is renamed
- **THEN** its ID, recipe, inputs and assets still resolve after restart

### Requirement: Direct song reuse actions
Song selection SHALL offer Use as Input Audio, Reuse Creation Ingredients and Edit Vocal FX. Each SHALL immediately open the destination tab with the selected song/context without manual re-upload.

#### Scenario: Use a finished song
- **WHEN** Use as Input Audio is selected
- **THEN** Generation adds that rendered song with source ID/lineage and automatic per-source handling without a defaults confirmation

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

### Requirement: Bulk song organization
Library SHALL move multiple exact song IDs to an existing folder, Unfiled, or a newly named logical folder in one validated catalog update. Invalid IDs or folder names SHALL leave the catalog unchanged. Moving SHALL preserve IDs, audio paths, recipes and FX lineage.

#### Scenario: Move a selection to a new folder
- **WHEN** selected songs are moved to a valid new folder
- **THEN** the folder and all selected assignments persist together and the songs remain playable

#### Scenario: Stale selection
- **WHEN** any selected ID is missing or is not a song
- **THEN** the move fails without changing other songs or creating a folder

### Requirement: Recoverable bulk song deletion
Bulk deletion SHALL validate exact song IDs before changing anything, protect files outside managed library storage and preserve shared assets. It SHALL report each song's success or failure, retain failed entries for retry, and preserve already completed outcomes if canceled. Filesystem or catalog failures SHALL restore staged files for the affected song.

#### Scenario: Partial deletion failure
- **WHEN** one selected song's audio cannot be removed
- **THEN** that song remains available with its files and the result identifies successful and failed songs separately

#### Scenario: Cancel remaining deletion
- **WHEN** cancellation occurs between songs
- **THEN** completed deletions remain reported and unprocessed songs remain intact

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
