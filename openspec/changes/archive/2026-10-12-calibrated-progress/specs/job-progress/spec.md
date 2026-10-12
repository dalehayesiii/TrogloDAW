## Purpose

Define measured local work progress, honest calibrated time ranges and observable queue, cancellation, terminal and reconnection behavior for expensive song/model operations.

## ADDED Requirements

### Requirement: Actual stage and work progress
Costly operations SHALL report their actual active stages and completed work units where available. Unknown work SHALL remain indeterminate with elapsed time; guessed timer progress SHALL NOT masquerade as completed inference. Running operations SHALL NOT report whole-request completion.

#### Scenario: Count diffusion work
- **WHEN** a local song is generated
- **THEN** progress follows completed decoder steps, with distinct initialization/loading/encoding/generating/decoding/rendering/saving stages where those operations actually occur

#### Scenario: Chunked processing
- **WHEN** source extraction, voice grouping, sample transforms or FX rendering runs
- **THEN** completed chunks/segments/samples/slots are visible and unfinished operations never show successful 100% completion

### Requirement: Compatible bounded calibration
Estimates SHALL use bounded local measurements partitioned by relevant operation, model/runtime, device/backend/offload/precision, duration/steps/output count, cache state, conditioning and input complexity. Incompatible GPU/CPU, cached/fresh and model paths SHALL NOT silently pool timing observations. Unfinished failed/canceled work SHALL NOT train successful request estimates.

#### Scenario: CPU fallback
- **WHEN** extraction falls back from CUDA to CPU
- **THEN** its estimate uses compatible CPU evidence or an explicit estimating/provisional state rather than CUDA timings

#### Scenario: Unknown context
- **WHEN** a model or workload has insufficient compatible history
- **THEN** the app shows estimating with elapsed time or an explicitly provisional live-unit range, without claiming calibrated precision

### Requirement: Separate queue stage item and request ranges
The app SHALL distinguish queue wait from active processing and provide remaining ranges for the current stage, current output and entire sequential request when supported by evidence. Multi-output requests SHALL show current/completed/total output counts and preserve individual outcomes.

#### Scenario: Sequential batch
- **WHEN** output two of a three-song request is generating
- **THEN** the app shows completed/current/total counts and distinguishes current-stage, current-output and whole-request estimates

#### Scenario: Pending request
- **WHEN** an operation waits behind active work
- **THEN** queue wait and any compatible estimated wait are separate from its own processing estimate and exclude jobs queued behind it

### Requirement: Honest slowdown and terminal estimates
Ranges SHALL adapt to observed processing rate changes and expose limited evidence. If no defensible remaining range exists, the app SHALL show estimating or taking longer with elapsed time. Completion, failure and cancellation SHALL clear live estimates and retain clear terminal results.

#### Scenario: Unexpected slowdown
- **WHEN** processing exceeds a historical range or work units slow substantially
- **THEN** the displayed estimate adapts or becomes taking longer/estimating without sticking at a false zero

#### Scenario: Cancel a batch
- **WHEN** cancellation is requested while a later output runs
- **THEN** the app shows cancellation requested until acknowledged, retains earlier successful songs and clears remaining ranges at the canceled terminal state

### Requirement: Reconnection and calibration evidence
Job stages, counts, elapsed time and estimates SHALL remain observable after tab navigation or browser reload/reconnection. Delivery evidence SHALL report actual representative timing predictions, measured error/sample sizes and hardware/cache limitations.

#### Scenario: Reload during inference
- **WHEN** the browser reloads while a job runs
- **THEN** it resumes following the existing job with current progress/elapsed/estimate/outcome information without submitting it again
