## Why

Main's installed-app verification repeatedly fails its updater tamper-rejection check. A reproduced preflight rejection can bind the status port and wait ten minutes even though handoff has not begun.

## What Changes

- Record rejected-plan status and exit promptly before the original service is verified stopped.
- Retain the temporary recovery listener for failures after verified service exit.
- Exercise invalid-checksum preflight with both free and occupied ports using the actual Windows helper, and improve failure diagnostics in the native handoff test.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `app-updates`: distinguish rejected preflight from recovery after service exit.

## Impact

Shipped PowerShell update helper, isolated native regression fixtures, updater documentation and canonical specs. No dependency, UI, persisted-configuration or data migration change.
