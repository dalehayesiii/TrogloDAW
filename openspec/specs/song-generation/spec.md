# song-generation Specification

## Purpose

Define offline generative song creation with reusable source samples, preserved lyrics, meaningful controls and portable provenance.

## Requirements

### Requirement: Real local music inference
Songs SHALL use a pinned, hardware-validated local generative music backend. Lyrics-only and text/style requests SHALL work without audio input, preserve supplied lyrics and save generated audio. Runtime inference SHALL require no remote generation/storage service.

#### Scenario: Lyrics without a recording
- **WHEN** supplied lyrics and styles are submitted without input audio
- **THEN** a song with generated singing and music is created using those lyrics, with model/checkpoint identity and requested/effective settings retained

### Requirement: Multi-source sample arrangement
Every selected audio source SHALL be analyzed, sliced, transformed and placed as samples in the final song. Generated musical assets SHALL remain separate from source-derived samples. Source IDs, transformations, placements, prompts and seeds SHALL persist in portable recipes.

#### Scenario: Mixed audio collection
- **WHEN** uploads, microphone takes and prior songs are selected together
- **THEN** each source contributes identifiable transformed samples and timeline placements rather than only the first clip or an unchanged full recording overlay

### Requirement: Recording and retakes
Generation SHALL request microphone access on recording initiation, show capture state, preview/accept/discard takes and replace individual accepted clips without resetting other clips or draft fields. Capture SHALL stop/release on stop, cancel, flow exit or shutdown. Device/permission/format failures SHALL be explained.

#### Scenario: Discard a retake
- **WHEN** a replacement recording is discarded
- **THEN** the previous accepted take and all other inputs remain selected

#### Scenario: Microphone permission failure
- **WHEN** access is denied or capture is unavailable
- **THEN** a useful error appears, capture resources are released and the existing draft remains usable

### Requirement: Input guidance
Upload and microphone flows SHALL expose hover/focus/tap guidance: "Audio inputs are intended to be vocal recordings. Previously generated songs can also be used and may benefit from prior-song presets."

#### Scenario: Keyboard help
- **WHEN** a user focuses or activates the input information control
- **THEN** the same guidance available on hover is readable

### Requirement: Prior-song preset decision
Adding a prior song SHALL prompt Apply recommended prior-song defaults or Keep current settings. The versioned preset SHALL disclose sample/morphing changes, preserve styles/lyrics and unrelated values, and retain the choice and effective settings. An unchanged source SHALL not repeatedly prompt.

#### Scenario: Decline full-song defaults
- **WHEN** a prior song is added and the user keeps current settings
- **THEN** generation uses the existing draft and saves the declined decision with that source

### Requirement: Selective creation reuse
Prior Song Reference SHALL import only selected available recipe ingredients, preserving unselected draft fields. Unavailable legacy fields SHALL be visible. Using a song as Input Audio SHALL resample its rendered audio; reusing ingredients SHALL reference original inputs/settings.

#### Scenario: Reuse styles only
- **WHEN** styles alone are selected from a prior recipe
- **THEN** styles change while lyrics, title, audio collection and other settings remain untouched

### Requirement: Meaningful generation controls
More Options SHALL contain only Vocal Gender, Duration, Weirdness, Style Influence and Variety. Each SHALL have a documented, validated local mapping. Gender SHALL steer new vocals only; duration SHALL preserve requested/effective length and reject unsupported values. Weirdness and style adherence SHALL have independent effects.

#### Scenario: Backend cannot honor a control
- **WHEN** a selected backend lacks the requested conditioning capability
- **THEN** the app explains that incompatibility rather than presenting an inert control or silently replacing its value

### Requirement: Bounded prompt variety
Variety zero SHALL preserve original styles exactly. Higher values SHALL produce bounded effective style variations per output without rewriting lyrics. Original/effective styles SHALL be shown and saved; changing seeds alone SHALL not count as Variety.

#### Scenario: Multiple varied songs
- **WHEN** multiple outputs are requested with Variety enabled
- **THEN** each retains its effective prompt, original styles and unchanged supplied lyrics

### Requirement: Sequential independent outputs
Number of Generations SHALL be a positive integer defaulting to one. Each output SHALL be independently cataloged with separate seed/settings and success/failure state. GPU-heavy stages SHALL run sequentially when memory requires; count SHALL not imply concurrent GPU batch size.

#### Scenario: One output fails in a request
- **WHEN** a generation fails after an earlier output completed
- **THEN** the completed song remains available and each requested output has an explicit outcome

### Requirement: Inspectable reusable assets
Song recipes SHALL preserve original inputs, generated music, transformed samples and placement assets sufficient to inspect and rerender the saved arrangement. Renaming/folder changes SHALL not invalidate references. Missing assets SHALL be reported without inventing reproducibility from a seed alone.

#### Scenario: Reload a relocated song
- **WHEN** a complete library is moved and a new song's recipe is reopened
- **THEN** its source/sample/generated assets resolve relative to the library and its placements remain reproducible
