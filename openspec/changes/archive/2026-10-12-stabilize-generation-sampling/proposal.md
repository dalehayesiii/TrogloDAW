# Proposal

## Why
The current Weirdness mapping switches to the pinned checkpoint's SDE sampler above 50. A reported two-song instrumental run produced steady noise; the SDE branch renoises with a linear time while decoding shifted time, so both independent outputs are affected.

## What Changes
- Use the supported ODE sampler across the Weirdness range; keep its independently recorded timestep-shift mapping.
- Verify separate sequential outputs, extreme slider values, and the same-seed real-model comparison.
- Document affected saved settings and recovery without modifying original songs.

## Capabilities
### New Capabilities
None.
### Modified Capabilities
- `song-generation`: validated sampler selection throughout exposed slider ranges.

## Impact
Backend parameter mapping, focused regression coverage, song workflow documentation. No dependency, asset, catalog or UI format changes. This is separate from automatic lyrics and style prompt research.
