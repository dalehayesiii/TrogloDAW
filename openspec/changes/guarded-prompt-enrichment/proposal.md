# Proposal

## Why

Genre and instrumental character can be weak with short prompts. Users want automatic local production guidance behind one toggle while retaining literal lyrics, speech, solo-instrument and sparse requests.

## What Changes

- Add default-on prompt enrichment with explicit off bypass, without suggestion previews, Apply actions, generated details or extra tuning controls.
- Use a pinned, validated per-music-model profile to propose bounded additive guidance and reject incompatible proposals before music inference. Unknown models, missing assets and uncertain/failed proposals use the original request.
- Preserve editor inputs and literal lyrics; retain original/effective caption and profile/fallback provenance in portable recipes, without exposing generated text in the normal UI.
- Install recommended supporting assets only through explicit existing model setup in selected storage. Keep enrichment dependencies/readiness separate so existing music installations continue to work.
- Run enrichment once per request and release its GPU process before sequential music generation. Preserve progress/cancellation and fixed-backing bypass.
- Document measured resource/preservation results and paired audio evidence; activate a profile only after benefit validation.

## Capabilities

### New Capabilities

- `prompt-enrichment`: optional automatic local musical prompt augmentation, qualified profiles, preservation checks, bypass/fallback and provenance.

### Modified Capabilities

- `song-generation`: distinguish unchanged editor/Variety styles from a separately enriched inference caption while preserving source authority and literal lyrics.
- `local-model-storage`: explicit recommended enrichment assets and separate add-on readiness without invalidating an existing music runtime.
- `frontend-service`: one retained enrichment toggle in applicable model workflows; correct stale fresh-count documentation to the existing default of two.

## Impact

Python song/model/inference helpers, Angular Generation, model manifest, independently locked optional quantization dependency, tests and documentation. No remote generation/storage, bundled weights, provider selector or data migration. WRK-27 owns three-workflow/source-semantic planning; this change must integrate with its contracts without duplicating that work. The listening comparison remains part of profile qualification, not an in-app review workflow.
