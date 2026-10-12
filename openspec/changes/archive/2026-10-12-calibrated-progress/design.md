# Design

## Context

One Python worker serializes heavy operations. Existing callbacks report messages/fractions but the upstream music runtime's progress timer guesses rather than counts diffusion work. WRK-11 adds conditioned and postmix modes before this change; timing must distinguish those paths and their real preprocessing work. Every request uses a fresh isolated inference process, so model loading is not a persistent warm-model session.

## Goals / Non-Goals

Goals: actual completed work/stages, usable conservative ranges where evidence supports them, responsive queue/cancel/reconnection, input/model/cache/device partitioning, honest initial setup progress, measured local prediction error.

Non-goals: adding models/controls, new ML dependencies, cloud inference, promising exact completion times, pretending GPU contention or OS file caching can be known perfectly, or enabling eager stems before the final spike.

## Decisions

1. Count completed diffusion decoder forwards with a pre-hook establishing the generating boundary, synchronizing CUDA before the completion event. Suppress upstream guessed callbacks/progress bars. Wrap actual decoder invocation for decoding boundaries, and report separation chunks, voice-analysis segments, sample transforms, render slots and saves as actual units. Unknown-duration work remains indeterminate with elapsed time. Running stages never report 100%; only successful terminal completion does.
2. Maintain local timing metadata alongside settings, partitioned by operation/model/runtime, platform/CPU/GPU/backend, offload/precision/quantization, duration/steps/output count, input complexity, conditioning mode/adherence and cache status. Retain at most twelve samples per context and 256 contexts. Atomic writes and corrupt/read-only metadata degradation must not fail audio jobs. Record only successful jobs/items and genuinely completed stages; exclude unfinished failed/canceled work.
3. Require three compatible observations for a local-history range. Use the observed envelope plus margin, explicitly a small-sample estimate rather than a statistical coverage guarantee. Actual unit rates supply smoothed provisional stage ranges after several observations. Update rates for slowdown; if a historical upper bound is exceeded without usable live units, show taking longer/estimating and elapsed time rather than a zero countdown. Queue wait, stage, current output and whole request remain distinct. Item measurements may estimate remaining sequential outputs when whole-request history is unavailable.
4. Enrich existing job responses additively. Snapshots compute live elapsed/queue durations and clear terminal ranges. Queue prediction includes only earlier active requests; a canceled queued operation does not add expected DSP time. Browser polling/reload/navigation continues to follow the same job IDs and shows cancellation requested until the worker acknowledges it. Keep readable themed summaries, counts, destination and byte progress; no tuning/debug fields in normal forms.
5. Keep model downloads' partial files in the installation's selected-model cache rather than the checkpoint root. Record a closed changed/resumed partial on cancellation/failure so default uninstall can remove it safely; preserve unowned legacy partials and mismatched final files. Distinguish known required model-asset bytes/reuse/resumption from verification, extraction, unknown-sized wheel/runtime installation and offline import loading. Asset bytes reaching their total is not whole setup completion.
6. Test fake-clock learning/slowdown/hardware partitions, request queues/cancel/terminal/reconnection and download ownership/range behavior with synthetic fixtures. Benchmark the actual locked Windows runtime on 60/120-second Base and conditioned/postmix paths, GPU/CPU extraction and cached FX. Report sample sizes, prediction-vs-actual median/tail error and remaining limitations; target qualified median relative midpoint error at most 25% and observed p90 at most 50% on the measured set, without treating a tiny sample as universal accuracy.

## Risks / Trade-offs

Fresh process imports/model loading, file cache state and desktop contention dominate some runs and cannot be inferred perfectly. Conservative ranges and explicit provisional/estimating states are preferable to invented precision. Instrumentation can synchronize GPU work and must be benchmarked for material overhead. Timing history stores performance context only, never lyrics, audio, credentials or absolute media paths. Long DSP/hash operations need safe cancellation checkpoints while preserving successful outputs and original storage.
