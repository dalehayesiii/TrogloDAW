## Why

Initial setup exposes typed paths and several overlapping open/relocate/install actions. Users need a simple directory picker and clear choices for moving existing models and library data, including when returning through Settings.

## What Changes

- Use an explicit native Windows Choose folder action with a readable selected location in initial setup and Settings.
- Detect current/default model or library data and prompt to move it, use the destination without moving or cancel.
- Copy and verify managed data before switching locations and removing unchanged originals; retain shared, unrelated or changed files and keep registered playback paths valid.
- Keep model installation/verification a distinct primary action and retain elapsed time, destination and actual-byte download time remaining.

## Capabilities

### Modified Capabilities
- `local-model-storage`: Simple folder selection and verified ownership-aware moves.
- `local-library`: Verified managed-data moves with portable paths and active media preserved.
- `frontend-service`: Shared initial/setup settings folder workflow and explicit native picker boundary.

## Impact

Stdlib Windows folder-dialog adapter, same-origin API, storage transfer/cleanup and media retargeting, Angular Settings, synthetic boundary/storage/browser tests, Windows payload and current guides. No model/download dependencies or desktop automation requirement.
