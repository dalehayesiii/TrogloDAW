## MODIFIED Requirements

### Requirement: Input guidance
Upload and microphone flows SHALL expose hover/focus/tap guidance explaining that recordings and finished Library songs are analyzed independently and automatically sampled into a shared arrangement, without a prior-song defaults confirmation.

#### Scenario: Keyboard help
- **WHEN** a user focuses or activates the input information control
- **THEN** the same guidance available on hover is readable

### Requirement: Bounded sample balance and manual offsets
Short samples SHALL be measured without silence dilution. Automatic correction SHALL be bounded to plus/minus 30 dB. Manual clip volume SHALL remain a relative offset, defaulting to zero for fresh clips. Explicit saved offsets SHALL remain unchanged.

#### Scenario: Explicit clip volume and short gestures
- **WHEN** the user chooses a negative volume offset for a gesture shorter than 400 milliseconds
- **THEN** loudness measurement preserves its active energy and mixing applies that quieter offset after bounded automatic correction

## REMOVED Requirements

### Requirement: Prior-song preset decision
**Reason**: Fixed setting changes and a confirmation do not provide source-aware planning.
**Migration**: Add Library songs directly. Automatic routing replaces the prompt; explicit saved numerical clip settings and existing recipe replay remain.

## ADDED Requirements

### Requirement: Automatic independent source routing
Library songs SHALL receive automatic finished-song sampling without confirmation or replacement of lyrics, styles or manual clip settings. Recordings in the same collection SHALL retain independent recording handling. Classification SHALL use trusted catalog/saved-source lineage, not uploaded filenames. Legacy preset flags SHALL remain accepted without requiring or reapplying them.

#### Scenario: Add a prior song
- **WHEN** a finished Library song is added to Input Audio
- **THEN** it is immediately usable without a defaults modal and unrelated draft fields remain unchanged

#### Scenario: Misleading uploaded filename
- **WHEN** an uploaded recording has a name suggesting it is a finished song
- **THEN** the filename does not override its source classification

### Requirement: Collection-aware sampling roles
Automatic planning SHALL account for single/multiple prior songs, single/multiple recordings and their combinations. Finished mixes SHALL favor bounded hooks/accents with restrained density and added harmonic shifts; recordings SHALL retain useful phrases. Every selected source SHALL contribute, with seed-reproducible cuts/transforms/placements and recorded effective policy/budget.

#### Scenario: Eight collection combinations
- **WHEN** planning uses one prior, one recording, several priors, several recordings, or any single/multiple combination of both
- **THEN** counts and independent source roles are recorded and accompanying recordings are not treated as finished mixes

#### Scenario: Mixed accompaniment
- **WHEN** finished mixes and recordings are arranged together
- **THEN** finished-mix returns remain restrained, recording phrases retain their role and the guide avoids indiscriminate full-song overlays or uniform cycling

### Requirement: Confidence-gated rhythmic source analysis
Finished-song sampling SHALL use measured audible/onset context and trust tempo only when analysis meets its confidence threshold. Uncertain material SHALL use a recorded fallback without claiming reliable beat, key, speaker or semantic understanding. Automatic full-mix pitch variations SHALL preserve pitch classes through octave variation; explicit user offsets SHALL remain recorded and effective.

#### Scenario: Uncertain rhythm
- **WHEN** a source has no reliable tempo
- **THEN** sampling still uses audible material, records fallback timing and does not claim detected beat alignment

#### Scenario: Polyphonic finished mix
- **WHEN** additional pitch variants are derived from a finished mix
- **THEN** automatic intervals are octave-based and the original-register variant is retained
