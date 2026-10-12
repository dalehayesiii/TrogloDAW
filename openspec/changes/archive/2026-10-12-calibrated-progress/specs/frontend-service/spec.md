## MODIFIED Requirements

### Requirement: Same-origin local API and worker
FastAPI SHALL serve compiled assets and library/item/recipe/upload/job/media/shutdown endpoints on the same configured local origin. DSP jobs SHALL use one background worker and report queued/running/completed/failed/canceled states with actual stage/work progress, elapsed time, output counts and evidence-qualified remaining ranges. Media SHALL expose only opaque server-registered file tokens. Browser mutations SHALL require a custom request header without enabling cross-origin access.

#### Scenario: Running production
- **WHEN** a DSP job is processing
- **THEN** HTTP status/progress requests remain responsive and failures reach the UI

#### Scenario: Browser cross-origin form
- **WHEN** a form posts without the custom header
- **THEN** the mutation is rejected

#### Scenario: Follow ongoing work
- **WHEN** the UI navigates/reloads during a costly operation
- **THEN** existing job IDs expose current stage/elapsed/count/estimate information and acknowledged terminal results without duplicate submission
