## MODIFIED Requirements

### Requirement: Real local music inference
Model-generated songs SHALL use a pinned, hardware-validated local generative music backend. Lyrics-only and text/style requests SHALL work without audio input, preserve supplied lyrics and save generated audio. Runtime inference SHALL require no remote generation/storage service. The independent fixed-backing DSP workflow SHALL not require inference or model readiness.

#### Scenario: Lyrics without a recording
- **WHEN** supplied lyrics and styles are submitted without input audio in model-generation mode
- **THEN** a song with generated singing and music is created using those lyrics, with model/checkpoint identity and requested/effective settings retained

## ADDED Requirements

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
