# Spec Delta

## ADDED Requirements

### Requirement: Phrase-aware automatic source derivation
Automatic sampling SHALL derive a bounded mixture of audible phrase, motif and accent cuts from each original input instead of forcing every cut to one short activity-run width. Eligible short clips SHALL sometimes contribute their complete audio as a transformed sample. Decisions SHALL be seed-reproducible and inspectable without requiring manual sample management.

#### Scenario: Articulated seven-second input
- **WHEN** a short source contains a sustained phrase with brief articulation gaps
- **THEN** its derived set retains meaningful phrase material and varied smaller cuts instead of selecting only neighboring sub-second fragments

#### Scenario: Whole short source
- **WHEN** an eligible short clip is sampled across independent seeds
- **THEN** some arrangements include its complete source span as one transformed sample, alongside derived cuts where the budget permits

### Requirement: Evolving source motifs with intentional rests
The full-song guide SHALL use varied section densities, motif/response transformations, intentional rests and bounded spaced returns. It SHALL NOT fill the song by uniformly cycling a few samples. Exact-waveform and source-family repetitions SHALL be limited, adjacent family repeats avoided when alternatives exist, and every selected source retained. Both conditioning and postmix SHALL use this guide.

#### Scenario: Long guide from a short source
- **WHEN** a short recording guides a much longer song
- **THEN** placements contain purposeful gaps, varied intervals and changing motif variants across sections rather than back-to-back or uniform repeated fragments

#### Scenario: Reproduce decisions
- **WHEN** the same source, seed and duration are arranged again
- **THEN** derived cuts, transformations and placements reproduce, with portable metadata explaining sections, variants and returns

### Requirement: Robust audible selection and sample headroom
Audible-region decisions SHALL be robust to supported level changes in the same input and isolated loud transients. Original recordings SHALL remain unchanged. Individual DSP variants and the full guide SHALL retain safe peak headroom with recorded attenuation; quiet input SHALL NOT trigger unbounded gain/noise amplification or justify repeated placement.

#### Scenario: Quiet and louder copies
- **WHEN** the same synthetic source is provided at different audible levels
- **THEN** its meaningful cut boundaries and budget remain equivalent while transformations apply bounded level handling

#### Scenario: Transient and loud effect
- **WHEN** a source has an isolated pop or a pitch/effect variant raises its peak
- **THEN** phrase selection is not reduced to the pop's threshold alone and saved transformed samples/guide have bounded peaks without modifying the original
