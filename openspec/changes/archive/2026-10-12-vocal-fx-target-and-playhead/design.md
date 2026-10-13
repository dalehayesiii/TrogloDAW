## Context
Voice analysis assigns three-second slots to uncertain candidates. Sorted IDs do not guarantee chronological order or one group per singer. In the observed song g0 starts at 12s; g1–g4 occupy the opening four slots. The renderer correctly processes only submitted group settings. Synthetic 220Hz input shifts to approximately 440Hz from the opening 50ms window, both as one buffer and fixed three-second slots, so this is targeting rather than a five-second pitch-plugin delay.

## Goals / Non-Goals
Make the ordinary whole-vocal pitch edit work from the beginning, retain specific-group independence, show playback location and match the requested sample-mixing default. Do not change diarization/model confidence, DSP, segment boundaries, cache identity or existing FX recipe shapes; postmix recipes add balance measurements and retain gain-bearing placements.

## Decisions
All vocals is a UI target that writes changed settings into every actual group. Backend rendering still receives real group IDs. Preparing FX exposes the existing full vocal-stem media token; solo playback uses it for the all target. Opening another song defaults to all; regrouping retains a still-valid current target.

All-target fields derive common/default effective values. Different group values appear as Mixed rather than claiming one shared value; an explicit control change applies only that parameter to all groups. Other parameters and individual overrides remain intact.

A lightweight DOM playhead overlays the existing canvas and follows the audio element's actual current time. It is visible at start/end, follows seek/time/metadata events and resets with source changes; waveform samples remain cached. It uses theme colors and has no pointer interception.

Fresh drafts and requests omitting audio_mode use postmix. Persisted explicit conditioned/postmix values continue to win; no ambiguous legacy draft migration rewrites user settings. Conditioning remains an explicit unchecked mode with active adherence on supported models.

## Risks / Trade-offs
All-vocal edits intentionally affect every candidate, including uncertain groups. Users can select a specific group for independent effects. Mixed values must not silently reset controls or flatten overrides until the user changes that parameter. Existing drafts can retain their old choice; this is an intentional preservation policy.

## Validation
Synthetic late-first-group fixture verifies initial pitch is affected for all vocals and only assigned slots change for one group. Reopen/saved and preview paths share the existing renderer. Real-service browser tests exercise scope changes/mixed values and waveform seeking/play/pause/replacement across workflows in both themes/sizes. Default-mode tests verify postmix, explicit conditioning, saved draft preservation and no double overlay. Standard local and installed CI gates remain.

## Generated-song sample loudness
Postmix samples default to matching the generated vocal stem, or generated song for instrumental requests and effectively silent stems. Use the installed HDemucs separator without speaker analysis, offline and sequentially after generation. Nonempty lyrics trigger separation; stems below -60 LUFS or more than 30 LU below the song count as unusable vocal references. This is an estimate, not perfect singer detection. Each short transformed gesture is measured with existing gated K-weighted loudness (repeat gestures shorter than 400 ms for measurement only), automatic correction is bounded to +/-30 dB, and manual clip volume is a relative offset. Fresh volume and new prior-song preset v2 use 0 dB; explicit saved offsets stay unchanged. Persist reference, measurements and effective placement gains; replay uses those gains without separation. Final mastering provides mix headroom. Conditioned generation and existing rendered recipes keep their semantics.
