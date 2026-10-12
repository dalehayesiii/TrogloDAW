## Why

The browser tab has no TrogloDAW icon, making it difficult to distinguish from other tabs.

## What Changes

- Serve a local SVG favicon using the existing purple stone, cave and lime waveform logo.
- Declare it in the static document head so source and installed browsers show the same identity.

## Capabilities

### Modified Capabilities
- `theme-system`: Recognizable local browser-tab identity.

## Impact

Frontend static assets and document head only; no network, dependencies or audio behavior changes.
