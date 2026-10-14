# Proposal

## Why

Recording + style can reject otherwise valid uploaded recordings with “The model did not render the complete recording timeline.” The adapter compares exact requested samples against frame-quantized decoder output, while catalog duration is rounded to milliseconds.

## What Changes

- Use the actual accepted source sample count for direct-workflow duration.
- Preserve the last source samples by aligning direct encoder input to the verified decoder frame boundary with only trailing silence.
- Remove generated padding only, retain the strict incomplete-output failure and record alignment provenance.
- Cover non-frame-aligned uploads around the reported 63-second duration and historical replay.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `song-generation`: clarify exact source length and safe encoder alignment in direct recording generation.

## Impact

Changes are confined to direct-workflow inference, precise source metadata, tests and recovery guidance. There are no new weights, dependencies, network requests or controls. Sampled phrase selection is a separate follow-up, after this prioritized repair. Preserve the unrelated prompt-enrichment PR's contracts.
