# Proposal

## Why

Input clips currently yield evenly spaced cuts mixed over music generated independently of those clips. The requested workflow needs content-aware sample selection, individual transformations and an arrangement that actually conditions generation.

## What Changes

- Select audible, varied source regions with a bounded content-aware sample budget, transform each sample and assemble a coherent full-duration conditioning WAV.
- Default to supported local audio-conditioned generation with independent Audio adherence; retain an explicit Mix samples after generation toggle and explain automatic fallback for unsupported models.
- Keep both controls inside Input Audio, applicable only with selected clips; preserve drafts, ingredients and portable assets.
- Save the conditioned model's complete mix directly, avoiding a second overlay of the same samples, and retain legacy postmix rerender semantics.
- Validate the pinned Base checkpoint's cover conditioning and narrow compatibility repairs through offline real-model runs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `song-generation`: intelligent sampling, audio-conditioned/postmix modes, adherence and portable replay.
- `frontend-service`: collapsed Input Audio controls and applicable mode presentation.

## Impact

Backend arrangements/inference, model capability metadata, Generation controls, recipes, Windows payload, tests and user documentation. No new inference dependency or remote service is required. Existing songs remain playable and rerenderable.
