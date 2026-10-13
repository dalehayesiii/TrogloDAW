## ADDED Requirements

### Requirement: Selection-owned Library preview
Library preview audio and assets SHALL correspond to the latest selected song. Switching selection SHALL remove the previous playable preview while loading. Late success or failure for an earlier selection SHALL not replace the current preview or its feedback. A failed current preview SHALL expose a retry action.

#### Scenario: Select another song before loading completes
- **WHEN** song A loads after the user has selected song B
- **THEN** B remains selected and A's audio/assets do not appear under B's title

#### Scenario: Current preview fails
- **WHEN** the current selected song's preview cannot load
- **THEN** the interface explains the failure and offers retry without playing the previous song

### Requirement: Truthful audio control feedback
Audio previews SHALL visibly distinguish mute from unmute, reflect the actual playing state and explain playback or local-link copying failure with a recovery action. Changed media SHALL reset stale waveform/time/transport state. Copying SHALL confirm success and identify the link as local to the running app. Small audio actions SHALL have at least 32px click targets and long titles SHALL not overlap those actions.

#### Scenario: Playback or clipboard rejects an action
- **WHEN** the browser rejects playback or local-link copying
- **THEN** the player displays actionable feedback and remains usable for retry or download

#### Scenario: Change the source
- **WHEN** a different preview replaces the current audio
- **THEN** the old waveform is removed and displayed playback speed/mute/state agree with the new audio element

### Requirement: Contextual empty states and count validation
Library SHALL distinguish an empty library, an empty folder and no search matches. Empty audio/reference pickers SHALL explain how to add suitable items. Invalid generation counts SHALL receive nearby feedback and SHALL not submit a job; the valid contract remains integers from one through 32.

#### Scenario: No search results
- **WHEN** a search finds no matching songs in a nonempty library
- **THEN** the UI identifies the unmatched search and offers clearing search/filters

#### Scenario: Invalid generation count
- **WHEN** the user submits an empty, fractional or out-of-range count
- **THEN** the field explains the accepted range, keeps the draft and prevents a job submission

### Requirement: Contained user-provided names
Song names and headings SHALL remain contained in their workflow columns and list rows at desktop and narrow widths, including valid unbroken 120-character names. Player title truncation SHALL retain the complete title through a tooltip without covering audio actions.

#### Scenario: Long unbroken song name
- **WHEN** the user selects a song whose name is a valid 120-character string without spaces
- **THEN** its name wraps within the list and preview columns without creating horizontal page overflow
