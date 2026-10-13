# Design

## Context

See proposal.md for motivation. Generation retains literal lyrics and original/Variety style fields, then invokes pinned offline music inference. Setup stores verified assets and a locked inference graph in selected model storage. Existing readiness rejects unexpected verification entries or a changed runtime lock. WRK-25 bypasses models for preserved-backing DSP; merged WRK-27 supplies three workflows and source-authoritative musical metadata planning.

Private trials rejected smaller writers and ungated 7B output. The current candidate uses a pinned Qwen2.5 7B NF4 writer plus a bounded JSON conflict check. Its complete pipeline processed forty invented intent fixtures. Ten matched music-seed pairs improved in four cases on the CLAP original-caption proxy, worsened in four and retained the unchanged baseline in two; the median delta was zero. Salsa improved at both seeds, dark ambient worsened at both, and city pop/bluegrass were mixed. Native setup/worker checks passed, but the profile remains inactive pending the human's decision about these experimental limits and resource costs. This finite evidence does not establish reliable universal musical improvement or semantic understanding. See docs/prompt-enrichment-research.md.

## Goals / Non-Goals

Keep one retained default-on toggle. Augment musical direction without replacing editor text, literal lyrics, source audio or source-authoritative planning. Do not add a suggestion review flow, generated text preview, provider selector, tuning knobs, remote calls or word/topic moderation. Do not duplicate WRK-27 modes.

## Decisions

Use versioned manifest profiles associated with a qualified music asset/runtime identity. Unknown identities have no profile. A profile names pinned writer assets, prompts, codec and a bounded output budget. The initial candidate uses Qwen2.5-7B-Instruct revision `a09a35458c702b33eeacc393d103063234e8bc28`, standard bitsandbytes 0.50.2 NF4/double quantization and existing Torch/Transformers. Pure CPU/disk offload was rejected after ~373s without a first usable response; unsupported/unvalidated configurations fall back to the original caption.

Run one additive proposal (maximum 120 characters) and one compatibility decision in a single isolated process per request, before music workers. Accept only a valid JSON decision with ACCEPT and an empty conflict; reject malformed, oversized or uncertain responses without a retry loop. Empty additions preserve original intent. Leave lyrics outside rewriting and pass only instrumental/source-authority context with the original caption. Retain that caption verbatim as the authoritative prefix. Use a shared base caption independent of per-output Variety; apply accepted additions to each output's inference caption while retaining its original/Variety fields. Disable bypasses the writer entirely. Cancellation propagates, while optional enrichment failures use original-caption fallback.

Keep quantization as a separately locked optional dependency group and package target. The music runtime fingerprint/contents stay unchanged. Export/install only add-on packages absent from the music graph with locked hashes; combine package paths in the isolated worker. Store separate profile verification/readiness metadata, not extra entries that invalidate legacy music state. Existing setup explicitly downloads recommended supporting assets and registers ownership; never acquire weights during inference. Existing installed music remains usable while additions are absent or fail. No large bundled weights or new dedicated setup flow.

Persist requested/effective enrichment, profile/writer/revision/codec, original and effective caption, accepted additions, decision/fallback and actual timing in recipes. Ordinary results/creation reuse show original user fields, not generated details. Saved-audio replay does not invoke enrichment. Enrichment has no authority over audio-source paths, durations, lyrics or semantic codes. Song-length and musical metadata planning receive original captions, including explicit tempo/key/meter; source structure bypass remains intact. Fixed-backing mode bypasses enrichment.

Expose one Enrich prompt checkbox beside styles in applicable model workflows. Unknown-model/absent-asset state is truthful and uses existing Settings setup, without new model-choice controls. Keep the choice editable while idle, even if support is absent, so users can retain an explicit off preference. Restore historical per-workflow drafts with the new default rather than showing an unchecked undefined value while the backend defaults on. Status reports actual preparation/decode checkpoints/cancellation without suggestion text. WRK-27's sampled and intact-recording workflows use this shared layer; fixed backing hides/bypasses it.

## Risks / Trade-offs

- Semantic checks can misclassify novel requests → conservative rejection/fallback, held-out preservation tests, unchanged authoritative text and explicit off. No universal musical-quality claim.
- Candidate adds ~15.2 GB raw supporting weights and measured ~5.43 GiB Torch allocation → disclose setup role/size, selected-drive storage, validated memory guards and sequential process release. Do not ship an unvalidated CPU/disk fallback.
- Cold loading varied approximately 18–75s in private trials → once-per-request loading and measured stage history; no timer-derived fake percentages or latency promise.
- Add-on failures must not break retained installations → independent optional graph/state, core-readiness regression tests, recoverable explicit setup and ownership-aware cleanup.
- Subjective genre benefit differs by request → qualification includes paired music outputs and listening/appropriate measurements, with no claim derived solely from RMS or text compliance.

## Migration Plan

No catalog/config migration. Missing draft flag defaults on; saved explicit off persists; old rendered songs/replay stay unchanged. Existing setups reuse their music graph/assets and can explicitly install missing recommended support in Settings. Document this refresh in installation recovery with a README link; do not reopen onboarding or silently download on startup/generation. Keep the implementation and complete synced/archive lifecycle in one PR after profile qualification.
