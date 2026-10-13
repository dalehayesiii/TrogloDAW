## MODIFIED Requirements

### Requirement: Multi-source sample arrangement
In sampled song generation, every selected source SHALL contribute audible, content-selected samples using a bounded budget, individual transformations and a shared full-song arrangement. Original inputs, transformed samples, arrangement and model output SHALL remain inspectable separately. Portable recipes SHALL retain source IDs, selection decisions, transformations, gains, placements, prompts and seeds. Silent sources SHALL fail clearly.

#### Scenario: Mixed audio collection
- **WHEN** uploads, microphone takes and prior songs are selected together in sampled generation
- **THEN** each source contributes identifiable transformed samples and timeline placements rather than only the first clip or an unchanged full recording overlay

#### Scenario: Uneven active material
- **WHEN** a clip contains silence and contrasting audible regions
- **THEN** selection favors audible diverse content, avoids redundant cuts and records the effective sample budget

### Requirement: Input guidance
Upload and microphone flows SHALL expose hover/focus/tap guidance describing the selected workflow: automatic independent sampling for mixed sources, recording arrangement over a preserved backing, or direct intact-recording conditioning. Audio-mode guidance SHALL explain whether generation hears the source, whether exact transformed samples are mixed afterward, and that conditioning can reinterpret sounds.

#### Scenario: Keyboard help
- **WHEN** a user focuses or activates an input or audio-mode information control
- **THEN** the same guidance available on hover is readable

### Requirement: Arrangement-conditioned generation
Fresh sampled generation with clips and a compatible model SHALL condition on the complete transformed arrangement WAV alongside unchanged lyrics and effective styles. Explicit saved postmix choices SHALL remain effective. The resulting whole mix SHALL be saved without double-overlaying samples. Recipes SHALL disclose requested/effective mode and model capability. Without clips generation SHALL use text/style inference.

#### Scenario: Full-song audio conditioning
- **WHEN** a compatible model generates from several clips without an explicit saved postmix choice
- **THEN** it receives one full-duration arrangement containing every selected source before inference, and the final mix preserves the model output rather than adding those samples again

### Requirement: Optional post-generation sample mix
Sampled generation SHALL offer Mix samples after generation, unchecked for fresh drafts and API requests without a mode. Explicit saved choices SHALL persist in drafts/recipes and remain reusable. Postmix SHALL generate without source audio conditioning and mix the improved arrangement afterward. Unsupported conditioning SHALL use this fallback with a visible explanation and retained requested/effective mode; it SHALL not claim active audio adherence.

#### Scenario: Explicit postmix choice
- **WHEN** the user enables Mix samples after generation
- **THEN** inference runs independently of the arrangement and the saved output includes the arranged samples afterward

#### Scenario: Unsupported model
- **WHEN** sampled conditioning is requested with a model lacking that capability
- **THEN** the app explains postmix fallback and preserves the request and effective behavior in the recipe

#### Scenario: Fresh and persisted mode
- **WHEN** a fresh draft or mode-less request is created
- **THEN** conditioning is selected by default, while restoring a draft with explicit postmix preserves that choice

### Requirement: Editable local automatic lyrics
Sampled generation SHALL offer explicit local lyric writing from a song idea and language preference. Successful text SHALL become editable input lyrics; failures SHALL preserve the previous text. Manual lyrics SHALL remain unchanged during music generation and blank lyrics SHALL remain instrumental in this workflow. Historical job restoration SHALL not overwrite a newer draft. Direct recording generation SHALL not offer lyric writing.

#### Scenario: Generate and edit words
- **WHEN** a user generates lyrics from an idea with an installed planner in sampled generation
- **THEN** the local planner writes lyrics, the user can edit them before generating music, and an expiring dismissible notification reports completion

#### Scenario: Failed writing preserves manual text
- **WHEN** local lyric writing fails or is canceled
- **THEN** existing lyrics remain available without a partial replacement

### Requirement: Guide enhancement before audio conditioning
Sampled audio-conditioned generation SHALL offer Off, Light and AI clean guide enhancement with a 0–100 strength, defaulting to Light at strength 50 when no choice is saved. Enhancement SHALL run after the full-duration guide is final, including saved-arrangement reuse, and before the model receives it. Postmix, text-only and direct intact-recording generation SHALL NOT be enhanced.

#### Scenario: Default conditioned generation
- **WHEN** a sampled draft without a saved enhancement choice generates in conditioned mode
- **THEN** the model receives the Light-enhanced guide, the raw guide is saved separately, and the recipe records Light at strength 50

#### Scenario: Enhancement off
- **WHEN** the user selects Off
- **THEN** the model receives the unchanged guide and no separate raw guide is needed

#### Scenario: Postmix
- **WHEN** samples are mixed after generation
- **THEN** the mixed layer is the unenhanced arrangement and replay is unchanged

#### Scenario: Reuse enhancement settings
- **WHEN** generation controls are imported from a song recipe with enhancement settings
- **THEN** the enhancement tier and strength are reused without changing unselected ingredients

## ADDED Requirements

### Requirement: Three persistent generation workflows
Generation SHALL offer sampled song generation, preserved-backing arrangement and direct recording with style in the existing tab. Each workflow SHALL retain its draft across switches/reloads. Existing drafts and recipes SHALL remain compatible; absent workflow SHALL mean sampled generation. Hidden inactive inputs SHALL not affect processing.

#### Scenario: Switch away from a recording
- **WHEN** a user edits one recording/style draft, switches to a mixed-source draft, and returns after reload
- **THEN** each retains its own accepted audio and applicable fields without discarding the other draft

### Requirement: Direct intact recording generation
Direct recording generation SHALL accept exactly one uploaded or microphone recording with style instructions and feed its complete decoded audio to a compatible model without sample selection, morphing, guide enhancement or postmix. Lyrics, lyric writing, Library priors and Prior Song Reference SHALL be unavailable. Invalid collections, prior-song lineage, supplied lyrics and unsupported capabilities SHALL fail clearly server-side.

#### Scenario: Intact recording reaches the model
- **WHEN** one valid recording and styles generate in direct mode
- **THEN** the model receives the intact recording, effective styles and its validated source length, with no sample arranger or second audio overlay

#### Scenario: Reject hidden inputs
- **WHEN** direct mode receives multiple clips, a prior song, lyrics or a saved sample arrangement
- **THEN** it rejects the request without changing the accepted recording or cataloging a song

### Requirement: Direct recording vocal and duration semantics
The direct recording workflow SHALL follow its source timeline within validated model limits and hide model-duration controls. Absent user lyrics SHALL not force source vocals instrumental. It SHALL preserve the source and record any source-derived conditioning honestly, without inventing words or guaranteeing voice, melody or waveform preservation.

#### Scenario: Vocal source without lyrics field
- **WHEN** a vocal recording generates with style instructions and no user lyrics
- **THEN** source conditioning remains active without an instrumental override or generated replacement lyrics

#### Scenario: Short recording decoder padding
- **WHEN** the decoder pads a short recording's generated output beyond its source duration
- **THEN** only the generated tail is removed and the complete original recording remains unchanged

### Requirement: Internal capability-aware musical planning
Compatible text-driven generation SHALL use installed verified musical metadata blueprint planning automatically, without planning configuration or caption/lyric rewriting. Literal tempo/key/meter SHALL take precedence over suggestions. Actual source audio SHALL remain authoritative in conditioned workflows; incompatible text blueprints SHALL be bypassed. Fixed-backing DSP SHALL retain its backing without music-model planning. Original/effective inputs and planning status/reason SHALL be saved.

#### Scenario: Text blueprint without source override
- **WHEN** a supported installed planner creates text-driven or explicit postmix music
- **THEN** its musical blueprint guides rendering with unchanged supplied words/styles and no source audio, and any exact postmix samples are added afterward

#### Scenario: Unqualified semantic codes
- **WHEN** a planning result includes semantic audio codes rejected by native fidelity comparisons
- **THEN** the result cannot replace text or source conditioning and generation reports original-input fallback

#### Scenario: Source structure remains authoritative
- **WHEN** sampled or direct recording conditioning uses the pinned model
- **THEN** it keeps source audio active and records why a competing text blueprint is bypassed

### Requirement: Recoverable portable blueprint assets
Blueprint planning SHALL run sequentially before rendering, using measured memory guards and real progress/cancellation. Missing assets or unsupported models SHALL retain supported generation without downloads. Planning failures SHALL preserve original inputs with a visible recorded fallback. Used blueprints, model revisions and seeds SHALL be retained as portable managed assets; replay SHALL use saved audio without new planning.

#### Scenario: Missing optional planner
- **WHEN** a ready music model lacks installed blueprint assets and explicit duration is chosen
- **THEN** generation continues through its supported existing path with an unavailable planning status and no network acquisition

#### Scenario: Planner fails or cancels
- **WHEN** a blueprint stage fails or is canceled
- **THEN** failure explains original-input fallback, cancellation stops the request, and previously completed songs remain available

#### Scenario: Relocated planned song
- **WHEN** a planned song is inspected or replayed after moving the complete Library
- **THEN** its blueprint/source/audio references resolve relative to the Library and replay requires no inference
