# Proposal

## Why

Uninstall after canceled setup can report a model-cleanup failure even when cleanup succeeds. A native reproduction with 5,000 recorded cache files produces a roughly 950 KB output line that makes NSIS `ExecToLog` return `error` despite Python exiting successfully and removing every recorded file.

## What Changes

- Bound installer-facing cleanup output to removed/retained counts.
- Preserve ownership checks and nonzero exit status for actual unsafe or failed cleanup.
- Exercise thousands of synthetic canceled-setup/cache files in native uninstall validation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `local-model-storage`: successful cleanup must not become a false uninstall failure because many files are recorded.

## Impact

Python cleanup CLI, Python regression tests and native Windows installer tests. No new dependencies or user-data migration.
