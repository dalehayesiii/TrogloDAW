# Spec Delta

## ADDED Requirements

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

### Requirement: AI clean add-on availability
AI clean SHALL never be bundled in the installer and SHALL only run from an explicitly installed, verified local add-on. While no compatible add-on is available for the embedded runtime, the option SHALL be visibly disabled as unavailable, and any request for it SHALL use Light with a visible, recorded explanation.

#### Scenario: Saved AI clean request without add-on
- **WHEN** a draft or API request asks for AI clean and the add-on is unavailable
- **THEN** generation uses Light, reports the substitution in progress and records requested AI clean with effective Light
