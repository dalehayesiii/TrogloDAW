## Why
Installed-app validation exposed enabled submission controls while the API was still accepting a render request. A second click can be lost during the transition to active-job state. Feedback must cover the entire request, not only backend polling.

## What Changes
- Mark job submissions busy immediately and retain that state through polling/refresh.
- Keep model-install busy state separate from ordinary processing as before.
- Exercise a held render submission and wait for confirmed folder success before testing reload persistence.

## Capabilities
### New Capabilities
- None.
### Modified Capabilities
- `frontend-service`: immediate submission busy feedback.

## Impact
Frontend submission state and real-service regressions only. No runtime dependencies, persistence or backend job changes.
