## ADDED Requirements

### Requirement: Visible shared-player playhead
Every playable shared audio waveform SHALL show a distinct playhead at the current playback position, including recordings, source clips, Library songs, stems, FX previews and outputs. It SHALL track playback and seeking while paused, stay visible at the beginning/end, reset for a replacement source and remain readable in both themes without blocking waveform clicks.

#### Scenario: Seek and pause
- **WHEN** the user seeks in a waveform or pauses during playback
- **THEN** the marker reflects the actual audio time and remains visible at the paused position

#### Scenario: Source and layout change
- **WHEN** the audio source, theme or viewport changes
- **THEN** the marker resets or repositions to the correct source/time within the visible waveform bounds
