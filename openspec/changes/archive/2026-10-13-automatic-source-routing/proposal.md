# Proposal

## Why

Selecting a Library song currently demands confirmation of fixed pitch, speed and cut-length defaults. Those defaults do not analyze finished mixes or distinguish accompanying recordings, and the extra prompt interrupts normal generation.

## What Changes

- Remove the prior-song defaults prompt and replace it with automatic per-source routing using trusted Library metadata.
- Account for all eight single/multiple prior-song and recording combinations with different cut budgets, phrase/accent roles, transformations and density.
- Select measured rhythmic anchors in finished mixes, avoid unsupported non-octave harmonic shifts and retain separate recording phrase material.
- Preserve requested draft fields and legacy replay; record effective routing, analysis, sample decisions and placements.
- Document measured comparison with fixed presets, conditional-only routing, analyzed routing and optional stem extraction, including limits.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `song-generation`: automatic source-aware sampling replaces the explicit preset decision.
- `local-library`: Use as Input Audio adds a prior song directly without confirmation.

## Impact

Existing offline DSP arrangement, song orchestration, Input Audio feedback, real-service regressions and user documentation. No new model assets, dependency, cloud inference or manual sample workflow. WRK-25 will reuse this source-aware arranger with a fixed backing song.
