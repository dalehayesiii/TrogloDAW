# Proposal

## Why

On 2.3.0 the user observed no visible response after Check for updates. Current checks retain their old message while network work runs, and ordinary status polling failures are silently ignored as though every failure were an installer handoff.

## What Changes

- Show Checking immediately on manual and background release checks.
- Show ordinary polling failures inline and clear them when status reads recover.
- Keep expected installer handoff interruptions quiet.
- Verify slow checks and polling recovery through synthetic backend/browser tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `app-updates`: Observable pending checks and status-read failures.

## Impact

Update worker messages, Angular update controls/polling, synthetic browser fixture, regression tests and update documentation. Authentication and explicit download/install behavior remain.
