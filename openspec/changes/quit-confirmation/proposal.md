# Proposal

## Why

Quit currently leaves the working interface visible with a small status message after the local service stops. Users should see an unmistakable completion page telling them they can close the browser window.

## What Changes

- Replace the entire interface with a themed, accessible stopped confirmation after shutdown is acknowledged.
- Stop recording and audio playback, close dialogs and remove interactive workflows from the stopped page.
- Preserve the interface and show a recoverable error if shutdown is not acknowledged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `frontend-service`: full-page completion after the existing Quit action.

## Impact

Angular presentation/state, real-backend browser regression tests and user-facing Quit documentation. The local shutdown endpoint and retained libraries remain unchanged.
