# Proposal

## Why

WRK-6 needs useful local completion estimates for costly song/model/editing work. Existing progress fractions reset between phases and upstream generation includes a timer-based callback, without elapsed/queue/item estimates or hardware/cache calibration.

## What Changes

- Instrument actual stages, diffusion decoder work, separation chunks, voice-analysis segments, sample processing, rendering/export and explicit model setup.
- Add bounded local stage/job timing history partitioned by operation/model/runtime, hardware/backend/offload, duration/steps/output count, cache state and input complexity; use measured current work-unit rates where available.
- Report queue wait separately from active stage/item/request ranges, elapsed time and measured progress. Use estimating/provisional states until evidence qualifies; update slowdowns and clear estimates at terminal states.
- Preserve visibility through navigation/reload and show readable themed status without exposing tuning/debug data in normal forms.
- Make resumed model downloads' bytes/destination/asset progress visible, retain cancellable progress and safely own partial download caches for uninstall cleanup.
- Benchmark real 60/120-second Base generation and GPU/CPU/cached editing, report prediction errors/targets and complete the OpenSpec lifecycle.

## Capabilities

### New Capabilities

- `job-progress`: Actual work/stage progress, local calibration, honest queue/stage/item/request estimates, elapsed and terminal/reconnection behavior.

### Modified Capabilities

- `frontend-service`: Extend the local worker/API status contract with calibrated progress/estimates while preserving existing operations.
- `local-model-storage`: Own/resume partial download caches and expose accurate explicit acquisition progress without touching unrelated files.

## Impact

Python worker/timing persistence, isolated model hooks and setup events, Angular progress presentation, locked Windows payload modules, synthetic clock/queue/cancel/browser tests, real local benchmarks and documentation. No new generation controls/model dependencies, planner/Turbo support, eager-stem product behavior or remote audio processing.
