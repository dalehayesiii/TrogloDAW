## Why
The default FX target is the first sorted candidate group, which may not begin until late in the song. A real prepared song placed that group at 12 seconds, leaving four earlier groups unedited. Audio previews have no playhead marker. Fresh generation drafts also leave Mix samples after generation unchecked despite the user's intended default.

## What Changes
- Default Vocal FX to All vocals, while retaining independent per-group editing and showing mixed settings truthfully.
- Expose the existing complete vocal stem for the All vocals solo preview; retain the current sample-aligned processing and recipe schema.
- Show a position marker on every shared audio waveform, including seeking, paused playback and source replacement.
- Match new postmix gestures to estimated vocal/song loudness with bounded correction and relative manual volume.
- Enable post-generation sample mixing for fresh drafts and omitted-mode API requests, preserving saved explicit choices and optional conditioning.

## Capabilities
### New Capabilities
- None.
### Modified Capabilities
- `song-vocal-editing`: default all-vocal target and mixed-setting feedback.
- `frontend-service`: visible shared-player playback position.
- `song-generation`: default post-generation sample mixing and measured sample loudness.

## Impact
Angular controls, a prepared-stem media field, generation-mode default and postmix balance. Adds an offline HDemucs reference-only pass for songs with lyrics, portable measurements and effective gains. No new models/dependencies, cache invalidation or timeline changes.

## Generated-song sample loudness
Postmix samples default to matching the generated vocal stem, or generated song for instrumental requests and effectively silent stems. Use the installed HDemucs separator without speaker analysis, offline and sequentially after generation. Nonempty lyrics trigger separation; stems below -60 LUFS or more than 30 LU below the song count as unusable vocal references. This is an estimate, not perfect singer detection. Each short transformed gesture is measured with existing gated K-weighted loudness (repeat gestures shorter than 400 ms for measurement only), automatic correction is bounded to +/-30 dB, and manual clip volume is a relative offset. Fresh volume and new prior-song preset v2 use 0 dB; explicit saved offsets stay unchanged. Persist reference, measurements and effective placement gains; replay uses those gains without separation. Final mastering provides mix headroom. Conditioned generation and existing rendered recipes keep their semantics.
