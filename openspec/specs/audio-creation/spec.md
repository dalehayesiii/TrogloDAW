# audio-creation Specification

## Purpose
Describe the initial offline effects and seeded pattern synthesis capabilities, including their existing limitations.

## Requirements

### Requirement: Voice effects
The app SHALL preview or save voice processing with pitch, stretch, gain, EQ,
compression, chorus, robotization, delay, reverb, silence trimming and normalization.
Saving SHALL create a new voice item recording source id and effect settings.
The robot effect SHALL be described as robotization rather than a carrier/modulator vocoder.

#### Scenario: Save processed voice
- **WHEN** a user applies effects and saves a result
- **THEN** the source remains and a new voice with a voice-fx recipe is cataloged

### Requirement: Seeded pattern generator
The app SHALL synthesize original stereo beats with supported drum styles,
bass and chord pads using key, progression, BPM, bar count, swing and seed.
Generated items SHALL retain resolved settings and seed for repeatable rerendering.
The baseline SHALL not claim MIDI export, separate stems or an independent melody generator.

#### Scenario: Repeat a seed
- **WHEN** a generated item's recipe is rerendered under the same runtime
- **THEN** a new generated item reproduces the saved waveform/settings

### Requirement: Synthetic test voice
The app SHALL offer a TTS test voice using optional espeak when installed and
a synthesized sung phrase otherwise, without requiring a remote service.

#### Scenario: Offline fallback
- **WHEN** no espeak executable is available
- **THEN** the test voice is synthesized locally and stored as a voice item
