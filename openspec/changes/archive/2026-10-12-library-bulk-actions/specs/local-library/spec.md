## ADDED Requirements

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
