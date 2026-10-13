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
Variety zero SHALL preserve original styles exactly. Higher values SHALL produce bounded effective style variations per output without rewriting lyrics. Original/effective styles SHALL be shown and saved. Added directions SHALL defer to requested sound sources, delivery and form, without imposing instruments or song sections. Speech, vocal-only and sparse requests SHALL retain their exclusions; changing seeds alone SHALL not count as Variety.

#### Scenario: Multiple varied songs
- **WHEN** multiple outputs are requested with Variety enabled
- **THEN** each retains its effective prompt, original styles and unchanged supplied lyrics

#### Scenario: Spoken or vocal-only request
- **WHEN** a request specifies speech, no music, a cappella or no instruments with Variety enabled
- **THEN** added variation directions preserve the requested sources and delivery without adding accompaniment, beats or song sections

#### Scenario: Solo or sparse request
- **WHEN** a solo-instrument or sparse request uses Variety
- **THEN** additions remain within the requested sound sources and form without requiring a fuller arrangement or new instrumentation

### Requirement: Sequential independent outputs
Number of Generations SHALL be a positive integer defaulting to two for fresh drafts and omitted counts. Saved explicit counts SHALL remain unchanged. Each output SHALL be independently cataloged with separate seed/settings and success/failure state. GPU-heavy stages SHALL run sequentially when memory requires; count SHALL not imply concurrent GPU batch size.

#### Scenario: One output fails in a request
- **WHEN** a generation fails after an earlier output completed
- **THEN** the completed song remains available and each requested output has an explicit outcome

#### Scenario: Upgrade a saved one-output draft
- **WHEN** an existing draft explicitly requests one output
- **THEN** it continues requesting one while fresh drafts default to two

### Requirement: Inspectable reusable assets
Recipes SHALL preserve source, sample, arrangement and model assets sufficient for portable inspection and rerender. Conditioned songs SHALL replay the saved generated mix without another sample overlay; postmix songs SHALL reconstruct gain-bearing placements over saved generated music. Existing recipes SHALL retain their original replay semantics. Missing assets SHALL report errors.

#### Scenario: Reload a relocated song
- **WHEN** a complete library is moved and a new song's recipe is reopened
- **THEN** its source/sample/generated assets resolve relative to the library and its placements remain reproducible

#### Scenario: Reuse conditioning settings
- **WHEN** generation controls and arrangement are imported from a new song recipe
- **THEN** the chosen mode/adherence and available arrangement can be reused without overwriting unselected ingredients

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

### Requirement: Editable local automatic lyrics
Generation SHALL offer explicit local lyric writing from a song idea and language preference. Successful text SHALL become editable input lyrics; failures SHALL preserve the previous text. Manual lyrics SHALL remain unchanged during music generation and blank lyrics SHALL remain instrumental. Historical job restoration SHALL not overwrite a newer draft.

#### Scenario: Generate and edit words
- **WHEN** a user generates lyrics from an idea with an installed planner
- **THEN** the local planner writes lyrics, the user can edit them before generating music, and an expiring dismissible notification reports completion

#### Scenario: Failed writing preserves manual text
- **WHEN** local lyric writing fails or is canceled
- **THEN** existing lyrics remain available without a partial replacement

### Requirement: Bounded model-planned song duration
Explicit duration SHALL support 10–300 seconds. Missing, blank or auto duration SHALL invoke an installed local planner before sample arrangement, preserve supplied lyrics/styles and bound its finite positive suggestion to 10–300 seconds. Recipes SHALL retain the request, raw suggestion, effective length and planner provenance. Unavailable planning SHALL explain setup or explicit-duration alternatives.

#### Scenario: Automatic instrumental duration
- **WHEN** styles are supplied, lyrics are blank and duration is unspecified
- **THEN** the local planner chooses a bounded length without a fixed one-minute default and the rendered song remains instrumental

#### Scenario: Five-minute explicit song
- **WHEN** duration is 300 seconds
- **THEN** generation attempts the complete requested length with existing memory safeguards and reports failure rather than silently truncating

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

### Requirement: Guide enhancement before audio conditioning
Audio-conditioned generation SHALL offer Off, Light and AI clean guide enhancement with a 0–100 strength, defaulting to Light at strength 50 when no choice is saved. Enhancement SHALL run after the full-duration guide is final, including saved-arrangement reuse, and before the model receives it. Postmix and text-only generation SHALL NOT be enhanced.

#### Scenario: Default conditioned generation
- **WHEN** a draft without a saved enhancement choice generates in conditioned mode
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

### Requirement: Bounded light guide enhancement
Light SHALL use bundled local processing only, reduce harshness, gaps and discontinuities, raise quiet guides by a bounded amount toward about −20 LUFS and retain the existing peak headroom.

#### Scenario: Quiet harsh guide
- **WHEN** a quiet guide with harsh upper-mid energy and noisy gaps is enhanced with Light
- **THEN** its loudness rises by a bounded amount, upper-mid share and gap noise fall, and its peak stays within the existing headroom

### Requirement: Inspectable guide enhancement provenance
The unenhanced guide SHALL remain inspectable beside the enhanced conditioning audio. Recipes SHALL record the requested/effective tier, strength, version and outcome with library-relative paths, and generation results SHALL offer before/after guide previews.

#### Scenario: Relocated library
- **WHEN** a library containing an enhanced song is moved
- **THEN** both raw and enhanced guides resolve relative to the library and the song replays unchanged

### Requirement: Safe guide enhancement fallback
If enhanced audio is non-finite, silent while the original guide was audible, or differs from the original by more than about 8 dB level-matched spectral distance, the model SHALL receive the original guide. The reason SHALL appear as a job progress message and be saved in the recipe.

#### Scenario: Unsafe enhancement result
- **WHEN** enhancement produces invalid or excessively altered audio
- **THEN** generation continues with the raw guide and reports why enhancement was skipped

#### Scenario: Safety measurement fails
- **WHEN** DSP or its safety/loudness measurement raises an error, returns an invalid measurement or changes audio shape
- **THEN** generation retains the original guide and records the fallback instead of failing

#### Scenario: Opposite-phase stereo
- **WHEN** stereo channels cancel when averaged but enhancement changes their audible spectra substantially
- **THEN** channel-power comparison detects the change and applies the same safety threshold

### Requirement: AI clean add-on availability
AI clean SHALL never be bundled in the installer and SHALL only run from an explicitly installed, verified local add-on. While no compatible add-on is available for the embedded runtime, the option SHALL be visibly disabled as unavailable, and any request for it SHALL use Light with a visible, recorded explanation.

#### Scenario: Saved AI clean request without add-on
- **WHEN** a draft or API request asks for AI clean and the add-on is unavailable
- **THEN** generation uses Light, reports the substitution in progress and records requested AI clean with effective Light
