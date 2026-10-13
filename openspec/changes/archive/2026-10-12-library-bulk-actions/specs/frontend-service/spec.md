## ADDED Requirements

### Requirement: Visible scoped Library selection
Library SHALL provide independent song checkboxes, a selected count, Select all shown and Clear selection in folder and search lists. Playback preview SHALL remain independent. Search/folder changes SHALL clear selection; refresh SHALL drop absent or hidden IDs. Navigation SHALL preserve selection while its scope remains unchanged.

#### Scenario: Select search results
- **WHEN** the user searches and selects all shown songs
- **THEN** only the visible matches are selected and changing the search clears the selection

### Requirement: Confirmed recoverable bulk actions
Selected songs SHALL offer bulk move and delete. Delete SHALL show the exact count and names in a centered confirmation; cancel SHALL change nothing. Move SHALL offer existing/new logical folders and Unfiled. Duplicate actions SHALL be disabled during work. Success SHALL use an expiring toast; partial failures SHALL show persistent dismissible details and retain failed/unprocessed selections for retry.

#### Scenario: Retry failed deletion
- **WHEN** some songs cannot be deleted
- **THEN** successful songs disappear, remaining selections are preserved, and the Library error identifies failures without claiming complete success

#### Scenario: Cancel confirmation
- **WHEN** the user cancels the bulk-delete confirmation
- **THEN** all selected songs and selection remain unchanged
