# Proposal

## Why

An external finished WAV cannot currently become a Library prior song directly, and Generation always invokes a music model. Users need to keep an existing song as the backing while automatically deriving, transforming and arranging recordings around its timeline.

## What Changes

- Add a Library WAV import with title and optional logical folder, validated managed copies and honest import provenance.
- Add an explicit Generation workflow for arranging recordings over one existing Library song, independent of model setup.
- Preserve the backing's timeline, use measured beat/energy context for source-derived placements, and save a new portable, replayable song.
- Retain model-generation drafts while disabling irrelevant lyrics/styles/writer/model controls in fixed-backing mode; enforce the separation server-side.
- Keep an extensible workflow discriminator for the separately planned WRK-27 mode.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `local-library`: managed WAV song import with persistent title/folder/provenance.
- `song-generation`: independent fixed-backing arrangement and retained workflow drafts.

## Impact

Existing Python Library/song/DSP helpers, API job dispatch, Angular Generation/Library and real installed-app tests. Reuses WRK-9 source policies. No new model, runtime dependency, remote processing or configuration migration. The normal generation mode retains its current conditioning/postmix semantics.
