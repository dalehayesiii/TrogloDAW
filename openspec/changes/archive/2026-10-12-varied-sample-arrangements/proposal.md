# Proposal

## Why

The current arranger can shorten every cut to a sub-second energy run and cycle a few nearby cuts uniformly for an entire song. A real seven-second input produced three 0.52-second cuts repeated 67 times, so the generated guide does not meet the requested varied sample arrangement.

## What Changes

- Select mixed-length audible phrases, motifs and accents from the original inputs, with robust level-relative detection and occasional complete short-clip inclusion.
- Transform each derived cut and create bounded, purpose-specific variations with safe peak headroom.
- Arrange intro/body/refrain/bridge/outro sections, call/response motifs, intentional rests and limited spaced repeats instead of a uniform modulo cycle.
- Preserve source assets, seed reproducibility, current duration support, calibrated work progress and portable exact replay in both conditioning and postmix modes.
- Keep the existing interface, correcting only explanations of the automatic process and its heuristic/model limits.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `song-generation`: phrase-aware sample derivation, bounded evolving arrangements and robust level handling.

## Impact

Backend arrangement and song orchestration, synthetic quality regressions, recipe decision metadata and documentation. No new dependency, model, network service or user-managed sample editor. Personal audio is investigated read-only and is excluded from committed tests and artifacts. Coordinate GPU/native tests with concurrent roadmap work.
