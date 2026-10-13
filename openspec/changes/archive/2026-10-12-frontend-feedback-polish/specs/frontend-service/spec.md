## REMOVED Requirements

### Requirement: Truthful audio control feedback

**Reason**: The user requested removal of local-link copying. The former combined playback/clipboard contract is replaced by the playback/download contract below.

**Migration**: Retain playback, mute, source-state resets and download. Remove the local-link copy action and clipboard scenarios; no catalog or API migration is needed.

## ADDED Requirements

### Requirement: Truthful audio playback and download controls
Audio previews SHALL visibly distinguish mute from unmute, reflect the actual playing state and explain playback failure with a recovery action. Changed media SHALL reset stale waveform/time/transport state. Audio sharing SHALL use the download action without a local-link copy control. Small audio actions SHALL have at least 32px click targets and long titles SHALL not overlap those actions.

#### Scenario: Playback rejects an action
- **WHEN** the browser rejects playback
- **THEN** the player displays actionable feedback and remains usable for retry or download

#### Scenario: Change the source
- **WHEN** a different preview replaces the current audio
- **THEN** the old waveform is removed and displayed playback speed/mute/state agree with the new audio element

#### Scenario: Download audio
- **WHEN** the user wants to share a preview
- **THEN** the player offers an audio download and has no ambiguous local-link copy action

### Requirement: Centered success notification placement
Success notifications SHALL be horizontally centered near the bottom of the main page. In a foreground dialog, they SHALL be centered within the dialog and remain readable without overflowing its bounds. Their existing dismissal and eight-second expiry SHALL remain unchanged.

#### Scenario: Page success notification
- **WHEN** folder creation succeeds at desktop or narrow width
- **THEN** its notification is centered horizontally in the viewport

#### Scenario: Foreground dialog notification
- **WHEN** a success notification remains visible while Settings opens
- **THEN** it is centered inside the dialog with no inherited page translation

### Requirement: Distinct folder creation action
Create folder SHALL be separated from the New folder name field by at least 12px so the action reads as a separate button rather than an attached input segment.

#### Scenario: Expanded folder creation
- **WHEN** Create a folder is expanded
- **THEN** the input and Create folder button remain distinct at desktop and narrow widths in both themes
