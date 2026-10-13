## MODIFIED Requirements

### Requirement: Arrangement-conditioned generation
When the user explicitly disables Mix samples after generation with input clips and a compatible model, generation SHALL condition on the complete transformed arrangement WAV alongside unchanged lyrics and effective styles. The resulting whole mix SHALL be saved without double-overlaying samples. Recipes SHALL disclose requested/effective mode and model capability. Without clips generation SHALL use text/style inference.

#### Scenario: Full-song audio conditioning
- **WHEN** a compatible model generates from several clips with conditioning explicitly selected
- **THEN** it receives one full-duration arrangement containing every selected source before inference, and the final mix preserves the model output rather than adding those samples again

### Requirement: Optional post-generation sample mix
Input Audio SHALL offer Mix samples after generation, enabled for fresh drafts and API requests without a mode. Explicit saved choices SHALL persist in drafts/recipes and remain reusable. Postmix SHALL generate without audio conditioning and mix the improved arrangement afterward. Unsupported conditioning SHALL use this fallback with a visible explanation and retained requested/effective mode; it SHALL not claim active audio adherence.

#### Scenario: Explicit postmix choice
- **WHEN** the user enables Mix samples after generation
- **THEN** inference runs independently of the arrangement and the saved output includes the arranged samples afterward

#### Scenario: Unsupported model
- **WHEN** conditioning is requested with a model lacking that capability
- **THEN** the app explains postmix fallback and preserves the request and effective behavior in the recipe

#### Scenario: Fresh and persisted mode
- **WHEN** a fresh draft or mode-less request is created
- **THEN** postmix is selected by default, while restoring a draft with an explicit conditioned mode preserves that choice

## ADDED Requirements

### Requirement: Default sample loudness matching
New postmix songs SHALL match each transformed sample to estimated generated-vocal loudness, using generated-song loudness for instrumental requests or effectively silent vocal stems. Recipes SHALL retain the reference, measurements and effective placement gains for replay without new inference. Conditioned songs and existing rendered recipes SHALL retain their semantics. Final mastering MAY affect perceived balance; separation is an estimate, not guaranteed singer identification.

#### Scenario: Quiet input with generated singing
- **WHEN** new postmix generation uses quiet source gestures and a usable generated vocal stem
- **THEN** each gesture receives measured loudness correction plus its manual offset, and saved replay reproduces the result without separation

### Requirement: Local vocal loudness reference
Vocal separation SHALL be local, sequential and use installed verified assets without speaker analysis. Nonempty lyrics SHALL trigger vocal-reference measurement. Stems below -60 LUFS or more than 30 LU below the generated song SHALL fall back to song loudness; instrumental requests SHALL use the song directly.

#### Scenario: Instrumental or silent vocal reference
- **WHEN** lyrics are empty or measured vocal separation is effectively silent
- **THEN** sample loudness targets the generated song, and an instrumental request needs no separation

### Requirement: Bounded sample balance and manual offsets
Short samples SHALL be measured without silence dilution. Automatic correction SHALL be bounded to plus/minus 30 dB. Manual clip volume SHALL remain a relative offset, defaulting to zero for fresh clips and new prior-song preset v2. Explicit saved offsets SHALL remain unchanged.

#### Scenario: Explicit clip volume and short gestures
- **WHEN** the user chooses a negative volume offset for a gesture shorter than 400 milliseconds
- **THEN** loudness measurement preserves its active energy and mixing applies that quieter offset after bounded automatic correction
