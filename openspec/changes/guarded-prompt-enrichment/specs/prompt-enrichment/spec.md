## Purpose

Define optional local musical prompt augmentation with qualified model profiles, unchanged user intent, conservative fallback and portable provenance.

## ADDED Requirements

### Requirement: Automatic retained enrichment choice
Applicable model generation SHALL default prompt enrichment on when no explicit choice is saved. Explicit off SHALL bypass enrichment inference entirely. The normal editor SHALL expose only one toggle, without generated suggestions, Apply actions, added tuning or a separate review/setup workflow. Fixed-backing DSP SHALL bypass enrichment.

#### Scenario: Fresh and retained choices
- **WHEN** a fresh draft or an explicit off draft is restored
- **THEN** the fresh draft defaults on and explicit off remains off across navigation/reload

#### Scenario: Preserved backing
- **WHEN** recordings are arranged over an existing backing
- **THEN** enrichment controls/inference do not affect that workflow

### Requirement: Qualified per-model profiles
Enrichment SHALL run only for a qualified profile matching the selected music asset/runtime identity and verified supporting assets. Unknown or changed identities SHALL receive no enhancement until evaluated. Profile qualification SHALL include preservation tests and paired music-benefit evidence; text compliance or RMS alone SHALL not establish musical benefit.

#### Scenario: Unexplored model
- **WHEN** a newly configured model has no matching qualified profile
- **THEN** inference uses original musical direction without applying another model's enhancement

### Requirement: Authoritative original request
Enrichment SHALL retain literal supplied lyrics and editor styles unchanged, adding only bounded compatible musical directions to the inference caption. It SHALL preserve genre, era, source/instrument limits, vocal delivery, language and negative constraints. It SHALL NOT add subject matter, censor words/topics or override authoritative input audio/semantic planning. Uncertain proposals SHALL use original-caption fallback.

#### Scenario: Speech or sparse intent
- **WHEN** the request excludes music/instruments/singing or specifies sparse/solo material
- **THEN** augmentation retains those constraints or falls back without forcing accompaniment

#### Scenario: Literal words
- **WHEN** supplied lyrics include profanity or political subject matter
- **THEN** the same words reach music inference without enrichment rewriting or blocking them

### Requirement: Bounded checked augmentation
A profile SHALL propose bounded additions and check compatibility before applying them. Empty, malformed, oversized, rejected or failed proposals SHALL preserve the original caption. No retry loop SHALL repeatedly rewrite a request. Optional enrichment failure SHALL not discard valid music inputs; cancellation SHALL remain cancellation.

#### Scenario: Conflicting proposal
- **WHEN** a proposal adds excluded instruments, another genre or extraneous effects
- **THEN** it is rejected and generation proceeds from original direction

#### Scenario: Canceled preparation
- **WHEN** enrichment is canceled
- **THEN** the request stops and preserves earlier completed outputs rather than treating cancellation as permission to generate

### Requirement: Sequential once-per-request work
Enrichment SHALL run at most once per multi-output request and release its model process before GPU-heavy music generation. It SHALL report actual preparation/work/cancellation and use validated resource guards. Unsupported resource conditions SHALL use original-caption fallback rather than an unvalidated slow offload strategy.

#### Scenario: Two outputs
- **WHEN** two songs are requested with enrichment
- **THEN** one checked addition is reused with their independent music seeds/settings and enrichment does not run concurrently with either music worker

### Requirement: Portable inspectable provenance
Recipes SHALL retain requested/effective enrichment, profile/writer/revision/codec, original/effective inference caption, accepted additions and fallback/timing. Ordinary results and creation reuse SHALL keep original editor fields instead of displaying generated details. Saved-audio replay SHALL not invoke enrichment or require its model.

#### Scenario: Relocated replay
- **WHEN** an enriched song's complete Library is relocated and replayed
- **THEN** saved assets reproduce the song without fresh enrichment and original inputs/provenance remain available
