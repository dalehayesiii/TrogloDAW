# Design

## Context

Library already stores portable 44.1 kHz stereo songs and supports logical folders. Upload acceptance currently creates voice items. Song generation validates model readiness and model-only options before building a sample guide. WRK-9 provides versioned per-source roles and confidence-gated rhythmic sampling. See proposal.md for motivation.

## Goals / Non-Goals

Import a WAV as a playable prior and arrange recordings over a fixed backing without model inference. Preserve drafts and replay through existing Library assets. Do not add a DAW, stems picker, enrichment settings or the WRK-27 intact-recording workflow.

## Decisions

Use `workflow: model | arrange-over-song` in drafts/recipes, defaulting missing values to model for existing callers. Dispatch fixed-backing processing before model readiness or generation-parameter validation. Unknown workflows fail clearly. Model-only lyrics/styles/options/audio-conditioning/enrichment values do not enter fixed-backing processing; retained editor values remain available when switching back. Shared title/count and per-clip adjustments retain their documented effects. The backing selector is separate from sampled Input Audio; reject using the same backing as a sampled input.

Library import accepts one uploaded, decoded WAV with title and optional existing logical folder. Validate format, frames, finite audio and a twenty-minute bound before writes. Keep an exact original WAV copy and a converted playable Library mix; record conversion/headroom if required and honest imported-file provenance. Prepare files before atomic catalog registration and clean only owned new files after failures/cancellation. Never overwrite an existing song or external source.

Fixed backing uses its exact decoded sample count, supports one second through twenty minutes and exposes no unrelated model-duration control. Copy the backing into new portable assets. Reuse source derivation/transforms, adding optional backing context to placement: confident tempo, measured beat phase and energy/density favor less busy positions while preserving required source coverage, fades/rests and repeat caps. Reliable key information may align sung recordings; uncertain/polyphonic estimates never force harmonic transposition. The backing itself is never sampled, duplicated or replaced by model output.

Balance samples against the backing using the existing bounded loudness matcher without invoking vocal separation, then master the combined song with safe headroom. Save `op: song`, `workflow: arrange-over-song`, `render_mode: postmix`, immutable backing (`musical_file`), source WAVs/variants/placements/gains and seed/effective context. This permits existing saved-asset rerender with no model. Imported WAVs have no invented generation recipe/stems. Generation ingredients expose workflow/backing/input/title/count for new arrangements; stale model fields are inactive.

## Risks / Trade-offs

- Energy gaps are not guaranteed vocal gaps, and tempo/key estimates can be ambiguous. Confidence gates and recorded fallbacks avoid false claims of semantic or singer understanding.
- Mastering changes overall output gain; the unmodified backing copy/source remains available and its timeline is preserved. Exact reconstruction refers to saved recipe replay, not an unchanged final master amplitude.
- Very short/dense material may not accommodate every source with meaningful rests; fail clearly rather than looping or silently dropping recordings.
- Longer CPU DSP requires RAM/disk and can take time. The length bound limits allocation; progress/cancellation occurs between analysis, sample transforms, placements and outputs. Only supported shorter fixtures are performance-measured; no universal runtime guarantee.

## Migration Plan

No configuration/data migration. Old drafts/recipes default to model generation and retain their replay. New discriminator is extensible for WRK-27; fixed-backing mode remains independent of its future default-conditioning and semantic-code choices.
