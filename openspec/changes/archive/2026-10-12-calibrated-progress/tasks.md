## 1. Work and calibration
- [x] 1.1 Implement bounded, context-specific stage/item/request history and fake-clock evidence-qualified ranges.
- [x] 1.2 Instrument actual diffusion/encoding/decoding, extraction/grouping, sample/render/export and storage stages with safe cancellation checkpoints.
- [x] 1.3 Add job snapshots with separate elapsed/queue/stage/item/request estimates, output counts, slowdown and terminal behavior.
- [x] 1.4 Expose themed status across navigation/reload and explicit setup byte/destination/runtime progress without fake precision.
- [x] 1.5 Own/resume interrupted download caches safely and preserve unrelated assets.

## 2. Validation and delivery
- [x] 2.1 Test cold/unknown and qualified contexts, GPU/CPU/cache partitions, long input, queue/cancel/failure/partial outcomes, slowdown and reconnect.
- [x] 2.2 Benchmark 60/120-second generation, conditioned/postmix paths, fresh GPU/CPU extraction and cached FX; publish prediction error and limitations.
- [x] 2.3 Update README/workflow/model/development docs and themed real-job screenshot evidence.
- [x] 2.4 Package the new module and run all documented Python/frontend/integration/native installed/release/spec checks.
- [x] 2.5 Sync canonical requirements and archive the completed change before opening the final PR.
