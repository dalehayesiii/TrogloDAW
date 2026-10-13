## MODIFIED Requirements

### Requirement: Visible scoped Library selection
Library SHALL initially hide selection checkboxes and batch tools until Select songs is activated. Selection mode SHALL provide independent song checkboxes, a selected count, Select page, Clear selection and Done selecting. Playback preview SHALL remain independent. Selection SHALL include only the current page. Search/folder/page/page-size changes and Done selecting SHALL clear selection; refresh SHALL drop absent or hidden IDs. Tab navigation SHALL preserve selection while its scope remains unchanged.

#### Scenario: Select search results
- **WHEN** the user searches, activates Select songs and selects the page
- **THEN** only visible matches on that page are selected and changing the search clears selection

#### Scenario: Leave selection mode
- **WHEN** the user chooses Done selecting
- **THEN** checked IDs are cleared and checkboxes/batch tools disappear without changing playback

## ADDED Requirements

### Requirement: Paginated Library songs
Library SHALL paginate folder/search results with 20 songs per page by default and 10/20/50 page-size choices. Controls below the list SHALL show the current result range, total matches and page count with previous/next actions disabled at boundaries. Search/folder/size changes SHALL return to page one. Refresh after deletion SHALL clamp to a valid page. All matching songs SHALL remain searchable regardless of current page, and other audio/reference consumers SHALL retain the complete catalog.

#### Scenario: Browse and filter multiple pages
- **WHEN** 25 songs match and the user advances from the first page
- **THEN** the remaining five appear with their result range, and a new search returns to page one across the full catalog

#### Scenario: Delete the last page
- **WHEN** the last page's songs are deleted
- **THEN** refresh shows the preceding valid page with updated totals and no hidden selection
