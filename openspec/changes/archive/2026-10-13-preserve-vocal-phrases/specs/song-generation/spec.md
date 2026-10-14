## MODIFIED Requirements

### Requirement: Phrase-aware automatic source derivation
Automatic sampling SHALL retain complete protected vocal phrases at pause boundaries; uniform windows, phrase thirds and interior motifs SHALL NOT split them. Sample-length preferences SHALL NOT override vocal boundaries: keep longer phrases or explain when none fits. Instrumental cuts remain best effort outside protected spans. Eligible short clips SHALL sometimes contribute complete audio. Decisions SHALL remain bounded, seeded and inspectable.

#### Scenario: Articulated seven-second input
- **WHEN** a short source contains a sustained phrase with brief articulation gaps
- **THEN** articulation gaps are bridged and complete meaningful phrases remain instead of arbitrary neighboring fragments

#### Scenario: Whole short source
- **WHEN** an eligible short clip is sampled across independent seeds
- **THEN** some arrangements include its complete source span as one transformed sample, alongside complete derived phrases where the budget permits

#### Scenario: Preference shorter than words
- **WHEN** a detected vocal phrase exceeds the nominal sample-length preference
- **THEN** selection retains its full span and records the longer effective length rather than cutting inside it

#### Scenario: No complete phrase fits
- **WHEN** no protected complete phrase can fit the requested shared timeline
- **THEN** the request explains how to use a longer timeline or shorter source collection instead of silently truncating vocal content

### Requirement: Collection-aware sampling roles
Automatic planning SHALL handle all single/multiple prior-song and recording combinations independently. Finished mixes SHALL favor bounded safe hooks/accents, restrained density and octave shifts; protected vocals SHALL retain complete phrases regardless of lineage. Every selected source SHALL contribute seeded, inspectable cuts/transforms/placements and effective budgets. Uncertain long finished mixes SHALL NOT become indiscriminate full-song overlays.

#### Scenario: Eight collection combinations
- **WHEN** planning uses one prior, one recording, several priors, several recordings, or any single/multiple combination of both
- **THEN** counts and independent source roles are recorded and accompanying recordings are not treated as finished mixes

#### Scenario: Mixed accompaniment
- **WHEN** finished mixes and recordings are arranged together
- **THEN** finished-mix returns remain restrained, recording phrases retain their role and the guide avoids indiscriminate full-song overlays or uniform cycling

#### Scenario: Prior-song vocals
- **WHEN** a finished mix contains a detected vocal phrase
- **THEN** onset-based musical candidates cannot cut through it simply because the source is a prior song
