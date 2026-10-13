# Proposal

## Why

Settings names the music model but only describes lyric-writing and length-planning tools by installation status. Users cannot see which models serve those roles or voice processing.

## What Changes

- Expose role-specific model identities alongside the existing planner status, derived from the configured music model's manifest association.
- Show lyric writing and automatic song-length model names in the shared Settings/setup controls.
- Identify fixed vocal-separation and voice-grouping models through a compact disclosure.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `local-model-storage`: identify configured model roles separately from readiness.

## Impact

Additive model-description metadata, Angular Settings presentation, API/E2E regressions and the existing audit record. No provider selection, download, inference, dependency or persistence changes. Delivered in the existing frontend audit PR.
