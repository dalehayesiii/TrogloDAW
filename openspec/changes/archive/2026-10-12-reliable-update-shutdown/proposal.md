## Why
A real Windows update stopped HTTP service but left the old Python process alive in Uvicorn shutdown. The updater timed out before opening its status listener, leaving the browser stuck and the launcher lock held.

## What Changes
- Bound HTTP graceful shutdown, preserving normal audio-worker cleanup.
- After acknowledged idle handoff, terminate only the validated original process if graceful exit times out.
- Expose recoverable helper failures even before installation and verify restarted service health/identity before helper success.
- Show bounded unavailable-status feedback in the browser, retaining polling for late recovery.
- Cover stalled HTTP shutdown and native timeout/restart failures with synthetic isolated tests; document recovery.

## Capabilities
### New Capabilities
- None.
### Modified Capabilities
- `app-updates`: bounded original-process exit, visible failures and confirmed restart.
- `frontend-service`: bounded HTTP shutdown releases the launch lock after worker cleanup.

## Impact
Uvicorn configuration, external Windows helper and update feedback/tests. No dependency, catalog/model format, credentials or release identity changes.
