# song-generation Specification

## Purpose

Define offline generative song creation with reusable source samples, preserved lyrics, meaningful controls and portable provenance.

## Requirements

### Requirement: Real local music inference
Model-generated songs SHALL use a pinned, hardware-validated local generative music backend. Lyrics-only and text/style requests SHALL work without audio input, preserve supplied lyrics and save generated audio. Runtime inference SHALL require no remote generation/storage service. The independent fixed-backing DSP workflow SHALL not require inference or model readiness.

#### Scenario: Lyrics without a recording
- **WHEN** supplied lyrics and styles are submitted without input audio in model-generation mode
- **THEN** a song with generated singing and music is created using those lyrics, with model/checkpoint identity and requested/effective settings retained

### Requirement: Multi-source sample arrangement
In sampled song generation, every selected source SHALL contribute audible, content-selected samples using a bounded budget, individual transformations and a shared full-song arrangement. Original inputs, transformed samples, arrangement and model output SHALL remain inspectable separately. Portable recipes SHALL retain source IDs, selection decisions, transformations, gains, placements, prompts and seeds. Silent sources SHALL fail clearly.

#### Scenario: Mixed audio collection
- **WHEN** uploads, microphone takes and prior songs are selected together in sampled generation
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
Upload and microphone flows SHALL expose hover/focus/tap guidance describing the selected workflow: automatic independent sampling for mixed sources, recording arrangement over a preserved backing, or direct intact-recording conditioning. Audio-mode guidance SHALL explain whether generation hears the source, whether exact transformed samples are mixed afterward, and that conditioning can reinterpret sounds.

#### Scenario: Keyboard help
- **WHEN** a user focuses or activates an input or audio-mode information control
- **THEN** the same guidance available on hover is readable

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
Sampled generation SHALL offer explicit local lyric writing from a song idea and language preference. Successful text SHALL become editable input lyrics; failures SHALL preserve the previous text. Manual lyrics SHALL remain unchanged during music generation and blank lyrics SHALL remain instrumental in this workflow. Historical job restoration SHALL not overwrite a newer draft. Direct recording generation SHALL not offer lyric writing.

#### Scenario: Generate and edit words
- **WHEN** a user generates lyrics from an idea with an installed planner in sampled generation
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
Short samples SHALL be measured without silence dilution. Automatic correction SHALL be bounded to plus/minus 30 dB. Manual clip volume SHALL remain a relative offset, defaulting to zero for fresh clips. Explicit saved offsets SHALL remain unchanged.

#### Scenario: Explicit clip volume and short gestures
- **WHEN** the user chooses a negative volume offset for a gesture shorter than 400 milliseconds
- **THEN** loudness measurement preserves its active energy and mixing applies that quieter offset after bounded automatic correction

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

### Requirement: Automatic independent source routing
Library songs SHALL receive automatic finished-song sampling without confirmation or replacement of lyrics, styles or manual clip settings. Recordings in the same collection SHALL retain independent recording handling. Classification SHALL use trusted catalog/saved-source lineage, not uploaded filenames. Legacy preset flags SHALL remain accepted without requiring or reapplying them.

#### Scenario: Add a prior song
- **WHEN** a finished Library song is added to Input Audio
- **THEN** it is immediately usable without a defaults modal and unrelated draft fields remain unchanged

#### Scenario: Misleading uploaded filename
- **WHEN** an uploaded recording has a name suggesting it is a finished song
- **THEN** the filename does not override its source classification

### Requirement: Collection-aware sampling roles
Automatic planning SHALL account for single/multiple prior songs, single/multiple recordings and their combinations. Finished mixes SHALL favor bounded hooks/accents with restrained density and added harmonic shifts; recordings SHALL retain useful phrases. Every selected source SHALL contribute, with seed-reproducible cuts/transforms/placements and recorded effective policy/budget.

#### Scenario: Eight collection combinations
- **WHEN** planning uses one prior, one recording, several priors, several recordings, or any single/multiple combination of both
- **THEN** counts and independent source roles are recorded and accompanying recordings are not treated as finished mixes

#### Scenario: Mixed accompaniment
- **WHEN** finished mixes and recordings are arranged together
- **THEN** finished-mix returns remain restrained, recording phrases retain their role and the guide avoids indiscriminate full-song overlays or uniform cycling

### Requirement: Confidence-gated rhythmic source analysis
Finished-song sampling SHALL use measured audible/onset context and trust tempo only when analysis meets its confidence threshold. Uncertain material SHALL use a recorded fallback without claiming reliable beat, key, speaker or semantic understanding. Automatic full-mix pitch variations SHALL preserve pitch classes through octave variation; explicit user offsets SHALL remain recorded and effective.

#### Scenario: Uncertain rhythm
- **WHEN** a source has no reliable tempo
- **THEN** sampling still uses audible material, records fallback timing and does not claim detected beat alignment

#### Scenario: Polyphonic finished mix
- **WHEN** additional pitch variants are derived from a finished mix
- **THEN** automatic intervals are octave-based and the original-register variant is retained

### Requirement: Independent fixed-backing workflow
Generation SHALL offer a fixed-backing arrangement workflow requiring one Library song and at least one separate input recording. It SHALL work without music-model readiness/inference and ignore inactive lyrics/styles/writer/enrichment/model controls server-side. Switching workflows SHALL retain model drafts. Missing workflow SHALL retain existing model-generation behavior; unsupported workflows SHALL fail clearly.

#### Scenario: Switch and return
- **WHEN** a model draft switches to fixed-backing mode and back
- **THEN** unrelated model controls are unavailable in fixed-backing mode and original values return unchanged

#### Scenario: No installed model
- **WHEN** a valid backing and recordings are arranged with no installed music model
- **THEN** local DSP produces the arrangement without invoking a model or requiring its setup

#### Scenario: Invalid backing collection
- **WHEN** the backing is missing, not a song, or also selected as a sampled input, or no recordings are selected
- **THEN** processing fails clearly without replacing the prior song

### Requirement: Backing-authoritative context arrangement
Fixed-backing mode SHALL keep the selected backing timeline and derive/transform/arrange recordings using measured rhythmic/density context, useful gaps, bounded variation/returns, fades and gain/headroom. Uncertain beat/key/semantic estimates SHALL use recorded fallbacks without forcing unsupported alignment. The backing SHALL not be resampled as another input or replaced by newly generated music. Supported backing length SHALL be one second to twenty minutes.

#### Scenario: Multiple quiet or short recordings
- **WHEN** several supported recordings are arranged over an existing song
- **THEN** each contributes derived samples with bounded gains and varied placements, while backing duration and original assets remain

#### Scenario: Uncertain context
- **WHEN** rhythm or tonal estimates are unreliable
- **THEN** arrangement uses documented timing/register fallbacks without claiming reliable musical or vocal-gap detection

### Requirement: Portable fixed-backing outputs
Fixed-backing mode SHALL save independent new Library outputs sequentially with workflow, backing/source IDs, immutable backing audio, derived sample assets, transforms, placements, gains, seed and effective context. Existing backing/inputs SHALL remain unchanged. Replay SHALL reconstruct saved assets without new inference, including after relocation. Progress/cancellation SHALL preserve already completed outputs.

#### Scenario: Relocated replay
- **WHEN** a completed fixed-backing recipe is replayed after library relocation
- **THEN** relative backing/source/sample assets resolve and the same saved mix is reconstructed without a model

#### Scenario: Cancel subsequent output
- **WHEN** a multi-output arrangement is canceled after one song completed
- **THEN** that song remains available and remaining work reports cancellation without altering the original backing

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
