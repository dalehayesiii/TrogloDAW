# Proposal

## Why
Users want editable automatically written lyrics, model-determined song length and up to five-minute songs. Existing generation has no local language-model planner and new drafts start with one output.

## What Changes
- Add an explicit local lyric-writing action, preserving manual lyrics and blank instrumentals.
- Resolve automatic duration with ACE's supported local metadata planner before arranging inputs; accept explicit 10–300 seconds.
- Default fresh drafts/omitted counts to two independently generated sequential songs; preserve saved counts.
- Install pinned optional ACE 1.7B metadata-planner and Qwen 0.6B lyric-writer assets in selected model storage with existing verified download, cancellation, ownership and progress safeguards. Existing music readiness remains usable without it for explicit durations.
- Save planning provenance and document upgrade/reuse requirements.

## Capabilities
### New Capabilities
None.
### Modified Capabilities
- `song-generation`: lyric generation, automatic bounded duration, fresh default count.
- `local-model-storage`: optional verified planner installation and independent readiness.

## Impact
Python inference/service/model management, static Angular lyrics/setup controls, tests, documentation and model manifest. No remote generation or new runtime dependency. Native supported planning runs in its own process before DiT so model memory is released sequentially.
