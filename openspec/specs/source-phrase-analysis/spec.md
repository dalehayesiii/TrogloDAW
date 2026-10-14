# source-phrase-analysis Specification

## Purpose

Define offline source-derived speech and pause evidence that helps sampling preserve complete vocal phrases without changing supplied words or source audio.

## Requirements

### Requirement: Local CPU vocal boundary analysis
Sampled generation and backing arrangements SHALL use explicitly installed verified speech activity analysis on CPU when available. Analysis SHALL identify protected vocal spans with conservative pause merging and endpoint context, never force duration-based splits or transcribe/rewrite lyrics. Direct Recording + style SHALL bypass this layer.

#### Scenario: Spoken phrases over music
- **WHEN** a source contains spoken phrases separated by pauses over a continuous instrumental bed
- **THEN** speech activity evidence protects complete vocal phrases even when full-mix energy never reaches silence

#### Scenario: Long continuous vocal phrase
- **WHEN** detected vocal activity has no reliable internal pause
- **THEN** it remains one protected span rather than being split at a fixed duration or an artificial motif boundary

### Requirement: Conservative boundary fallback
Missing assets, analysis failures and uncertain vocal boundaries SHALL use conservative acoustic phrase/pause evidence and preserve longer spans rather than introduce unverified interior cuts. Instrumental sampling SHALL remain best effort and respect all protected vocal spans. Runtime SHALL not acquire assets implicitly.

#### Scenario: Optional detector absent
- **WHEN** an old ready model lacks phrase assets or a CPU-only backing has no model setup
- **THEN** sampling uses complete acoustic phrases with a recorded fallback and no download or new model-readiness requirement

#### Scenario: Failed or uncertain analysis
- **WHEN** speech analysis fails or cannot qualify an instrumental-only region
- **THEN** uncertain material is protected conservatively and the recorded selection explains its evidence and fallback

### Requirement: Recoverable portable phrase evidence
Source analysis SHALL support progress/cancellation and retain content/model/version-keyed boundary evidence as relative managed Library assets. Identical inputs SHALL reuse valid evidence across sequential outputs. Invalid caches SHALL be recomputed or fall back safely. Saved songs/layouts SHALL replay without new analysis and remain portable.

#### Scenario: Second independent output
- **WHEN** another output uses unchanged input and detector identity
- **THEN** its sampler reuses valid boundary evidence while preserving independent seeds and recording the reuse

#### Scenario: Cancel or corrupt cache
- **WHEN** analysis is canceled or cached boundaries are invalid
- **THEN** cancellation stops the request without dropping completed songs, and invalid evidence is never accepted as a safe boundary

#### Scenario: Relocated Library
- **WHEN** the complete Library is moved and a saved arrangement is replayed
- **THEN** audio/layout and evidence references remain relative and replay requires no speech model
