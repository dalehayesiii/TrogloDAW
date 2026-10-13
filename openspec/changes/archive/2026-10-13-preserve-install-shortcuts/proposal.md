# Proposal

## Why

The Windows installer overwrites every shortcut on each update or reinstall. This resets desktop placement and discards user customizations even though the target is unchanged.

## What Changes

- Reuse existing desktop and Start Menu shortcuts for the registered installation when its directory is unchanged.
- Create missing shortcuts and refresh shortcuts when the installation directory changes.
- Test preservation across native reinstall and the actual updater handoff, while retaining uninstall cleanup.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `delivery-workflow`: Preserve shortcut files on same-directory upgrades and reinstalls.

## Impact

NSIS installer, native installed-app regression tests and installation documentation. No runtime dependencies, audio processing or configuration migrations.
