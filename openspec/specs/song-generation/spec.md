# song-generation Specification

## Purpose

Define offline generative song creation with reusable source samples, preserved lyrics, meaningful controls and portable provenance.

## Requirements

### Requirement: Real local music inference
Songs SHALL use a pinned, hardware-validated local generative music backend. Lyrics-only and text/style requests SHALL work without audio input, preserve supplied lyrics and save generated audio. Runtime inference SHALL require no remote generation/storage service.

#### Scenario: Lyrics without a recording
- **WHEN** supplied lyrics and styles are submitted without input audio
- **THEN** a song with generated singing and music is created using those lyrics, with model/checkpoint identity and requested/effective settings retained

### Requirement: Multi-source sample arrangement
Every selected source SHALL contribute audible, content-selected samples using a bounded budget, individual transformations and a shared full-song arrangement. Original inputs, transformed samples, arrangement and model output SHALL remain inspectable separately. Portable recipes SHALL retain source IDs, selection decisions, transformations, gains, placements, prompts and seeds. Silent sources SHALL fail clearly.

#### Scenario: Mixed audio collection
- **WHEN** uploads, microphone takes and prior songs are selected together
- **THEN** each source contributes identifiable transformed samples and timeline placements rather than only the first clip or an unchanged full recording overlay

#### Scenario: Uneven active material
- **WHEN** a clip contains silence and contrasting audible regions
- **THEN** selection favors audible diverse content, avoids redundant cuts and records the effective sample budget

### Requirement: Recording and retakes
Generation SHALL request microphone access on recording initiation, show capture state, preview/accept/discard takes and replace individual accepted clips without resetting other clips or draft fields. Capture SHALL stop/release on stop, cancel, flow exit or shutdown. Device/permission/format failures SHALL be explained.

#### Scenario: Discard a retake
- **WHEN** a replacement recording is discarded
- **THEN** the previous accepted take and all other inputs remain selected

#### Scenario: Microphone permission failure
- **WHEN** access is denied or capture is unavailable
- **THEN** a useful error appears, capture resources are released and the existing draft remains usable

### Requirement: Input guidance
Upload and microphone flows SHALL expose hover/focus/tap guidance: "Audio inputs are intended to be vocal recordings. Previously generated songs can also be used and may benefit from prior-song presets."

#### Scenario: Keyboard help
- **WHEN** a user focuses or activates the input information control
- **THEN** the same guidance available on hover is readable

### Requirement: Prior-song preset decision
Adding a prior song SHALL prompt Apply recommended prior-song defaults or Keep current settings. The versioned preset SHALL disclose sample/morphing changes, preserve styles/lyrics and unrelated values, and retain the choice and effective settings. An unchanged source SHALL not repeatedly prompt.

#### Scenario: Decline full-song defaults
- **WHEN** a prior song is added and the user keeps current settings
- **THEN** generation uses the existing draft and saves the declined decision with that source

### Requirement: Selective creation reuse
Prior Song Reference SHALL import only selected available recipe ingredients, preserving unselected draft fields. Unavailable legacy fields SHALL be visible. Using a song as Input Audio SHALL resample its rendered audio; reusing ingredients SHALL reference original inputs/settings.

#### Scenario: Reuse styles only
- **WHEN** styles alone are selected from a prior recipe
- **THEN** styles change while lyrics, title, audio collection and other settings remain untouched

### Requirement: Meaningful generation controls
More Options SHALL contain only Vocal Gender, Duration, Weirdness, Style Influence and Variety. Each SHALL have a documented, validated local mapping. Gender SHALL steer new vocals only; duration SHALL preserve requested/effective length and reject unsupported values. Weirdness and style adherence SHALL have independent effects.

#### Scenario: Backend cannot honor a control
- **WHEN** a selected backend lacks the requested conditioning capability
- **THEN** the app explains that incompatibility rather than presenting an inert control or silently replacing its value

### Requirement: Bounded prompt variety
Variety zero SHALL preserve original styles exactly. Higher values SHALL produce bounded effective style variations per output without rewriting lyrics. Original/effective styles SHALL be shown and saved; changing seeds alone SHALL not count as Variety.

#### Scenario: Multiple varied songs
- **WHEN** multiple outputs are requested with Variety enabled
- **THEN** each retains its effective prompt, original styles and unchanged supplied lyrics

### Requirement: Sequential independent outputs
Number of Generations SHALL be a positive integer defaulting to one. Each output SHALL be independently cataloged with separate seed/settings and success/failure state. GPU-heavy stages SHALL run sequentially when memory requires; count SHALL not imply concurrent GPU batch size.

#### Scenario: One output fails in a request
- **WHEN** a generation fails after an earlier output completed
- **THEN** the completed song remains available and each requested output has an explicit outcome

### Requirement: Inspectable reusable assets
Recipes SHALL preserve source, sample, arrangement and model assets sufficient for portable inspection and rerender. Conditioned songs SHALL replay the saved generated mix without another sample overlay; postmix songs SHALL reconstruct gain-bearing placements over saved generated music. Existing recipes SHALL retain their original replay semantics. Missing assets SHALL report errors.

#### Scenario: Reload a relocated song
- **WHEN** a complete library is moved and a new song's recipe is reopened
- **THEN** its source/sample/generated assets resolve relative to the library and its placements remain reproducible

#### Scenario: Reuse conditioning settings
- **WHEN** generation controls and arrangement are imported from a new song recipe
- **THEN** the chosen mode/adherence and available arrangement can be reused without overwriting unselected ingredients

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

### Requirement: Stable sampling across generation controls
Every exposed Weirdness and Style Influence value SHALL use a validated sampler configuration. Changing Weirdness SHALL not silently select a sampler with an incompatible timestep schedule. Each output SHALL record effective sampler, shift and guidance; existing rendered songs SHALL remain unchanged.

#### Scenario: High Weirdness independent outputs
- **WHEN** a user requests two songs with Weirdness above 50
- **THEN** both use the supported stable sampler sequentially with separate seeds and output assets

#### Scenario: Reuse an affected draft
- **WHEN** a user generates again from a draft saved with the older sampler mapping
- **THEN** the current validated mapping is applied while the previous song and its recorded parameters remain intact

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
