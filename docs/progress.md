# Progress and time remaining

Progress follows completed work: diffusion steps, separation chunks, voice-analysis
segments, automatically derived samples, rendered segments, verified/copied files
and downloaded or hash-verified bytes. Loading, runtime installation and unknown
work stay indeterminate. A timer never advances the progress bar. Current-stage
completion does not mean the complete request is finished.

The shared status shows elapsed time, queue wait, stage time remaining, the current
song and complete-request ranges, plus completed output counts. Navigation and
browser reload reconnect to the existing backend job without resubmitting it.
Cancellation remains requested until a safe checkpoint acknowledges it. Songs
already committed remain available when a later output fails or is canceled.

## Estimates that keep learning

The app records successful stage, song and request durations locally. At least
three compatible observations qualify a history estimate. Context includes the
operation, model/asset manifest and pinned runtime, actual CPU/GPU and precision,
offload/cache policy, output duration/count, input duration/count, arrangement
mode and relevant processing options. Hardware must be confirmed for the current
job before previous GPU timings can be used for a CPU fallback. Storage context
uses drive roots, never media filenames. Failed/canceled requests do not train
successful request totals; successful completed outputs and stages can be retained.

History retains at most 12 measurements per context and 256 contexts in
`timing-history.json` in the settings folder. This is local history, not a shipped
benchmark constant. Corrupt/missing/read-only history never blocks processing.
History contains hashed context keys and durations, not lyrics, recordings or
absolute media paths.

The observed range uses the local minimum/maximum and median with margins; it is
not a statistical confidence interval. After actual work units advance, a smoothed
live rate can estimate that stage even on a first run. Whole-request estimates
remain **Estimating…** until compatible request/song history exists. Slowdowns,
stalled events and exceeded ranges show **Taking longer** and can withdraw the
estimate; the bar remains tied to actual work. Terminal jobs freeze elapsed time
and clear all time-remaining ranges.

## Model setup

Setup shows the destination, elapsed time, current file and resumed bytes, all
model-file bytes present and file-verification count. One top line gives the local
start time and combined download/installation remaining range. Overall/current-stage
bars initially describe **Download**, using actual bytes and measured transfer speed.
Already present files and owned partial downloads reduce the transfer budget.
Once those bytes are present, both scopes switch to **Installation**. Its overall bar
counts completed asset-verification and runtime checkpoints; it is a work count,
not an elapsed-time percentage. Its current-stage bar follows actual work units.

Hash verification is a separate byte-counted stage and does not reset downloaded
bytes. Code extraction, dependency/runtime installation and the offline readiness
probe must also finish. Dependency-download totals are not reliably available;
these stages remain indeterminate unless compatible whole-setup history exists.
Runtime status identifies recognized package downloads/completions and package counts,
shows elapsed time for the current stage, and reports when the tool is still running
without new package output. Large wheel downloads can be quiet. Recording runtime/cache
files for safe uninstall is a separate stage with measured file counts, not a blank install bar.
The transfer ETA is explicitly not a promise that the entire setup finishes then.
Interrupted owned downloads resume safely; unrelated partial files remain untouched.

## Measured validation

Measured on 2026-10-12 with an RTX 3070 8 GiB, Windows driver 617.14, the pinned
PyTorch 2.7.1+cu128 runtime and ordinary display activity. Tests used a temporary
library and synthetic inputs. Generation used Base, 32 steps, BF16, CPU/DiT offload,
unchanged lyrics and a four-second input automatically sampled and arranged.

| Workload | First three successful runs (s) | Held-out run (s) | First qualified predicted total (s) | Absolute error |
| --- | --- | --- | --- | --- |
| 60 s, conditioned generation | 39.5 / 38.8 / 40.6 | 39.9 | 41.16 | 3.1% |
| 120 s, conditioned generation | 52.9 / 52.9 / 52.6 | 50.4 | 55.44 | 10.0% |
| 60 s, post-generation mix | 37.8 / 36.5 / 36.8 | 35.9 | 38.53 | 7.3% |
| 60 s, fresh GPU voice preparation | 11.4 / 9.1 / 9.2 | 9.2 | 10.44 | 13.5% |
| 120 s, fresh GPU voice preparation | 12.0 / 12.0 / 12.8 | 12.5 | 12.56 | 0.5% |
| 120 s, cached vocal FX | 8.1 / 8.0 / 8.2 | 8.5 | 8.44 | 0.7% |
| 60 s, fresh CPU voice preparation | 18.7 / 18.7 / 19.5 | 18.8 | 19.64 | 4.5% |
| 60 s, final generation profile | 50.9 / 48.0 / 41.8 | 44.5 | 47.76 | 7.3% |

The CPU forecast is evaluated only after actual CPU selection. The final profile
also partitions driver-aware memory policy. A two-output 10-second conditioned
batch took 65.6 seconds against an initial item-history-derived total of 41.64
seconds: 36.5% error, demonstrating why stage and whole-batch estimates differ.
Including that batch, nine qualified forecasts had 7.3% median and 36.5% observed
nearest-rank p90 absolute relative error, meeting the 25%/50% validation targets.
Predicted total is the first qualified range midpoint plus elapsed time.

These are small local measurements, not population accuracy guarantees. Cached
120-second preparation took about 0.3 seconds; fresh CPU preparation took 29.8
seconds. Other GPUs, the unbenchmarked SFT checkpoint, different input complexity,
storage, network speed and background workloads need their own observations.
Cached setup reverified all 24 files (6,769,517,637 bytes), extracted/reused code
and passed the offline runtime probe in 29.3 seconds without a download.
Controlled fixtures validate download speed changes, resumptions and cancellation;
the production model files were reused and reverified rather than redownloaded
solely to fabricate a network benchmark.

Windows CUDA process-budget reporting can exceed physically available memory under
WDDM. When available, a UUID-matched `nvidia-smi` driver reading is combined with
CUDA using the lower free-memory value. Generation still requires 5.5 GiB and
voice separation uses CPU below 2 GiB. Missing driver tooling uses the CUDA reading.
The actual CPU-fallback benchmark held driver-visible free memory near 1.3 GiB,
while CUDA reported roughly 7.5 GiB; the final guard correctly chose CPU.

See [PR #7 for real-job review screenshots](https://github.com/dalehayesiii/music-maker/pull/7) and
[model limits](local-models.md).
