# Proposal

## Why

WRK-5 gives the three delivered workflows a recognizable TrogloDAW identity and readable, complete light/dark themes. The baseline palette has weak secondary-text contrast and retained Music Maker branding across the UI and Windows distribution.

## What Changes

- Apply purple/lavender and pale lime semantic tokens, restrained cave/stone artwork, clear hierarchy and consistent responsive controls to every workflow, overlay, audio player and state.
- Follow system appearance on first use, allow an explicit persisted light/dark choice, and offer return to system preference without adding a primary tab.
- Brand the app, browser title, Windows display/shortcut/uninstall metadata and maintained documentation as TrogloDAW.
- Publish a TrogloDAW installer name while retaining the legacy installer alias and installed configuration/path/launcher identifiers needed by existing users and automation.
- Audit current versus intentional compatibility/historical names, preserve repository URLs, and complete the OpenSpec lifecycle with paired screenshots and regression checks.

## Capabilities

### New Capabilities

- `theme-system`: Semantic appearance, system/default choice, persistent overrides, consistent accessible themes and restrained product artwork.

### Modified Capabilities

- `frontend-service`: Replace the interim baseline visual contract with the TrogloDAW design while retaining workflows, controls and progressive disclosure.
- `delivery-workflow`: TrogloDAW release/installer presentation with legacy artifact and installed-path compatibility.

## Impact

Angular templates/styles/theme initialization and waveform colors; Windows icon/installer/launch messages; package/release/checksum callers and installer tests; current product/setup/development documentation and canonical spec descriptions. No new inference controls, audio algorithms or model dependencies. No remote repository rename.
