# Proposal

## Why

The tracked root requirements.txt duplicates uv.lock but neither development setup
nor Windows dependency installation reads it. Shipping that export and documenting
manual maintenance creates an unnecessary second representation of dependencies.

## What Changes

- Delete the tracked compatibility export and omit it from the installed app.
- Keep the Windows build's temporary hashed export generated from uv.lock.
- Update dependency instructions and obsolete pip/pandas references in helpers.
- Correct the README's outdated reference to a separate Library tab.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `delivery-workflow`: Declare one source for Python dependency declarations and
  resolution, with only temporary build exports and no shipped requirements copy.

## Impact

Root requirements.txt, Windows build helper, agent/development instructions,
dependency recovery text and README. Dependency versions, audio behavior, API,
frontend and release policy remain unchanged.
