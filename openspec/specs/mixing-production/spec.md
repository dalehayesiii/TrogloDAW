# mixing-production Specification

## Purpose
Describe the initial mix recipe, remix/export and automatic offline production contracts for saved audio.

## Requirements

### Requirement: Mix and remix recipes
The app SHALL mix one voice with one music track using volume, offset, ducking,
fades, looping and optional voice effects. Mixes SHALL store source ids and settings.
Remix SHALL apply overrides without mutating the original recipe and record the parent.
The baseline SHALL not automatically match tempo/key or provide arbitrary multitrack stems.

#### Scenario: Rebalance a saved mix
- **WHEN** a user remixes with a different music volume
- **THEN** a new item records the override and original mix id as parent

### Requirement: Rerender and export
The app SHALL rerender generated, voice-fx and mix items from recipes as new items,
and rerun producer recipes using saved parameters/seed. Unsupported recipes SHALL
report an error. Export SHALL support WAV/MP3 and requested ffmpeg formats.

#### Scenario: Export a remix
- **WHEN** a saved remix is exported as WAV and MP3
- **THEN** both files are created using its rendered audio

### Requirement: Offline producer
The producer SHALL analyze a vocal for tempo, pitch/key confidence, sung/spoken
characteristics, phrase gaps, loudness and energy; select or accept style/tempo/key;
generate an arranged beat; process and place vocal phrases; duck music; and master
the result targeting configured loudness (default -14 LUFS) and a -1 dBTP ceiling.
It SHALL save WAV/MP3 and a recipe containing analysis, choices, source ids and seed.

#### Scenario: Produce a song
- **WHEN** a user supplies one vocal and a fixed seed
- **THEN** the app creates processed vocal, generated beat and mastered mix items
  with retained production parameters and exported MP3

#### Scenario: Pitch correction gating
- **WHEN** tuning is auto and a vocal is spoken or its key is unreliable without an override
- **THEN** the producer avoids automatic pitch correction

### Requirement: Heuristic production limits
Detection and arrangement SHALL be documented as heuristic, with unreliable speech
key estimation and no word-level beat alignment.

#### Scenario: Speech input
- **WHEN** a recording is spoken rather than rhythmically sung
- **THEN** phrase placement uses silence gaps rather than claiming word-level timing
