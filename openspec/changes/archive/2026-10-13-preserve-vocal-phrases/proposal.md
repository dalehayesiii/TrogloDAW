# Proposal

## Why

The current sampler detects activity phrases, then reintroduces evenly spaced windows, phrase-third cuts and short motifs inside them. These artificial boundaries can split words and erase the phrase structure the user wanted to retain.

## What Changes

- Select complete detected vocal phrases with pause context; stop arbitrary subdivisions inside vocal or uncertain material, regardless of sample-length preference or source lineage.
- Use a pinned lightweight CPU voice-activity model when explicitly installed, including speech over a musical bed. Retain conservative acoustic phrase detection without it; use instrumental onset/window selection only outside protected vocal spans or for sufficiently confident non-speech material.
- Keep longer intact phrases rather than forcing small fragments. Explain when a complete phrase cannot fit the target timeline.
- Save detection, boundary confidence/fallback and selection provenance; reuse cached analysis and historical saved arrangements offline.
- Offer the small optional detector through existing model verification without invalidating ready music models or adding generation settings.

## Capabilities

### New Capabilities

- `source-phrase-analysis`: local CPU speech/pause analysis, conservative fallback and reusable source-derived boundary evidence.

### Modified Capabilities

- `song-generation`: complete vocal phrases take precedence over arbitrary short-cut budgets and apply to recordings and finished mixes in sampled/backing arrangements.
- `local-model-storage`: explicitly verified optional phrase assets preserve existing readiness and expose honest availability.

## Impact

Sampling, inference-process dispatch, model acquisition/readiness, recipes/cache and current guidance change. No additional dependency, transcription, caption rewriting, model provider setting or remote processing is introduced. Direct Recording + style remains outside sampling and keeps the independent timeline repair in PR #36. Coordinate with the separate prompt-enrichment prototype; do not modify its checkout.
