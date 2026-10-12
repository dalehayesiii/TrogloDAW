# Spec Delta

## MODIFIED Requirements

### Requirement: Multi-source sample arrangement
Every selected source SHALL contribute audible, content-selected samples using a bounded budget, individual transformations and a shared full-song arrangement. Original inputs, transformed samples, arrangement and model output SHALL remain inspectable separately. Portable recipes SHALL retain source IDs, selection decisions, transformations, gains, placements, prompts and seeds. Silent sources SHALL fail clearly.

#### Scenario: Mixed audio collection
- **WHEN** uploads, microphone takes and prior songs are selected together
- **THEN** each source contributes identifiable transformed samples and timeline placements rather than only the first clip or an unchanged full recording overlay

#### Scenario: Uneven active material
- **WHEN** a clip contains silence and contrasting audible regions
- **THEN** selection favors audible diverse content, avoids redundant cuts and records the effective sample budget

### Requirement: Inspectable reusable assets
Recipes SHALL preserve source, sample, arrangement and model assets sufficient for portable inspection and rerender. Conditioned songs SHALL replay the saved generated mix without another sample overlay; postmix songs SHALL reconstruct gain-bearing placements over saved generated music. Existing recipes SHALL retain their original replay semantics. Missing assets SHALL report errors.

#### Scenario: Reload a relocated song
- **WHEN** a complete library is moved and a new song's recipe is reopened
- **THEN** its source/sample/generated assets resolve relative to the library and its placements remain reproducible

#### Scenario: Reuse conditioning settings
- **WHEN** generation controls and arrangement are imported from a new song recipe
- **THEN** the chosen mode/adherence and available arrangement can be reused without overwriting unselected ingredients

## ADDED Requirements

### Requirement: Arrangement-conditioned generation
With input clips and a compatible model, generation SHALL default to conditioning on the complete transformed arrangement WAV alongside unchanged lyrics and effective styles. The resulting whole mix SHALL be saved without double-overlaying samples. Recipes SHALL disclose requested/effective mode and model capability. Without clips generation SHALL use text/style inference.

#### Scenario: Full-song audio conditioning
- **WHEN** a compatible model generates from several clips
- **THEN** it receives one full-duration arrangement containing every selected source before inference, and the final mix preserves the model output rather than adding those samples again

### Requirement: Optional post-generation sample mix
Input Audio SHALL offer Mix samples after generation. Selected mode SHALL persist in drafts/recipes and remain reusable. This mode SHALL generate without audio conditioning and mix the improved arrangement afterward. Unsupported conditioning SHALL use this fallback with a visible explanation and retained requested/effective mode; it SHALL not claim active audio adherence.

#### Scenario: Explicit postmix choice
- **WHEN** the user enables Mix samples after generation
- **THEN** inference runs independently of the arrangement and the saved output includes the arranged samples afterward

#### Scenario: Unsupported model
- **WHEN** conditioning is requested with a model lacking that capability
- **THEN** the app explains postmix fallback and preserves the request and effective behavior in the recipe

### Requirement: Independent audio adherence
Audio adherence SHALL appear only with selected clips and apply only in conditioned mode on a supported model. It SHALL have a validated mapping distinct from Style Influence and sample gain. Zero SHALL disable source conditioning; higher values SHALL increase its effective influence without guaranteeing exact waveform, voice identity or words.

#### Scenario: Change adherence only
- **WHEN** the same seed, arrangement, lyrics and styles are generated with different adherence
- **THEN** requested/effective adherence is saved and materially different conditioning produces different generated audio while text guidance and supplied lyrics remain unchanged
