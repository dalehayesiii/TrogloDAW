## Purpose
Describe the initial local configuration, portable audio catalog and library management contracts shared by the UI and CLI.

## ADDED Requirements
### Requirement: Local configuration precedence
The app SHALL resolve runtime settings from environment variables, then
config.local.json, then config.json, then defaults. MM_CONFIG_DIR SHALL select the
config folder. It SHALL accept UTF-16 installer configs and default to localhost
and a library next to the source app.

#### Scenario: Machine override
- **WHEN** port is configured in both files and MM_PORT is set
- **THEN** MM_PORT wins, with the local file taking precedence if the variable is absent

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
