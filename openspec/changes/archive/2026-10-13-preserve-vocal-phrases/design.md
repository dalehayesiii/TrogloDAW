# Design

## Context

The existing activity pass joins short gaps, but candidate expansion immediately inserts uniform windows, phrase thirds and 350 ms active-frame motifs. Prior-song onset candidates can cross vocals. The nominal two-second preference becomes a hard phrase limit. Selection and placement already save source offsets, use bounded transformations and reject arrangements that cannot fit, so preserve those contracts while replacing unsafe candidate generation.

## Goals / Non-Goals

Keep complete detected vocal phrases, use real pauses as boundaries, preserve uncertain material conservatively and retain source-aware instrumental arranging. Do not transcribe, rewrite words, add sampler controls, silently change historical layouts or promise perfect linguistic recognition.

## Decisions

- Use Silero VAD v6.2.3 JIT at revision `5cd7945676eb32225748052e2e6a0580e4686a08`, 2,272,526 bytes, SHA-256 `e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720`. It uses the existing torch runtime on CPU, with no new dependency. Acquire the optional asset only through existing explicit model verification; allow its verified entries without making it a readiness requirement for old installations.
- Native offline CPU research on three Windows-synthesized sentences plus 500 ms pauses produced strong speech activity with and without a continuous harmonic bed; a pure instrument tone produced no speech frames. Treat this as bounded classifier evidence, not a universal singing/word guarantee.
- Analyze normalized copies, never source edits, at 16 kHz/512-sample frames on one CPU thread. Use hysteresis, sufficiently long pauses and generous endpoint context, with no maximum-utterance forced split. Save protected spans, probability/confidence summary and provenance. Pure/isolated instrument regions can retain onset-oriented best effort; uncertain material uses complete acoustic phrases.
- Cache by accepted waveform hash, detector asset/revision and analysis version in managed Library assets. Validate all timestamps and source dimensions on read. Record cache/fallback relative references, forward actual chunk progress, honor cancellation and retain completed outputs.
- Remove all artificial interior vocal candidates, let safe phrase duration exceed nominal preference, and preserve seeded scoring/bounded family budgets and source-aware return/density policies. Instrument candidates must not intersect protected spans. Do not replace an unsegmentable uncertain finished mix with a blind full-song layer; explain no-safe-fit recovery instead.
- Keep saved selection/placement reuse ahead of fresh analysis. Direct mode remains untouched. Settings identifies the optional CPU model/readiness through existing progressive disclosure; inspect that affected flow using the local UI/UX skill.

## Risks / Trade-offs

- VAD is imperfect on singing/noise/overlap → conservative boundary context and uncertain-material fallback; no claimed exact transcript or universal word recognition. Whisper word timestamps are also approximate, so transcription alone is not accepted as a cutting authority.
- Longer safe phrases can reduce sample count or fail a short/many-source timeline → count is a cap, not a quota; provide useful longer-duration/shorter-input recovery and do not slice to hide the problem.
- Optional assets may be absent after upgrade → preserve existing ready states and offline CPU fallback; explicit verification installs the small extra file without redownloading unchanged weights.
- Analysis startup adds time → CPU-only fresh process, valid cache reuse for batch outputs, real progress and cancellation.

## Migration Plan

Existing songs and saved layouts replay as stored. New sampling uses `phrase-motifs-v4`. To enable the trained detector on an existing installation, use Install / verify selected model; missing detector assets do not require that action before generating. No catalog conversion or new user configuration. Provide active workflow/model/recovery guidance and synthetic validation evidence, leaving dated comparisons untouched.

Primary references: [Silero VAD](https://github.com/snakers4/silero-vad/tree/5cd7945676eb32225748052e2e6a0580e4686a08) and its [MIT license](https://github.com/snakers4/silero-vad/blob/5cd7945676eb32225748052e2e6a0580e4686a08/LICENSE); [Whisper timestamp limitation](https://github.com/openai/whisper/discussions/1855). No upstream helper code is copied; the pinned JIT asset is explicitly acquired.
