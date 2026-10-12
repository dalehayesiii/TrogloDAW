# Design

## Context
ACE's pinned inference API exposes metadata planning; native create_sample produced coherent lyrics but ignored the requested topic in target-hardware testing. A pinned Qwen3 0.6B instruction model follows lyric ideas more reliably in the tested English/Spanish examples. The current runtime includes its PyTorch/Transformers dependencies but not 5Hz planner weights. The 1.7B checkpoint is the upstream default; primary issue reports find 4B less reliable for instruction following. Existing Base/SFT model assets and catalogs must remain reusable.

## Goals / Non-Goals
Provide actual local generative lyrics and native duration planning on the RTX 3070; maintain inspectable original/effective choices. Do not silently rewrite manually supplied lyrics/styles, enable LM audio-code generation or claim Suno-equivalent quality. Style improvements remain a separate research issue.

## Decisions
- Use pinned ACE 5Hz LM 1.7B assets from the existing pinned shared model revision plus Qwen3 0.6B instruction weights/tokenizer and license for lyrics. Explicit setup may add the planner; no implicit downloads during generation. Music readiness accepts its original asset set and independently verified optional planner assets.
- Use the native PyTorch backend in a fresh subprocess. Initialize ACE with its supported CPU offload option so BF16 conversion precedes GPU transfer; use supported last-token logits and metadata-only stopping. The lyric writer uses local-only Transformers, trust_remote_code=False and the official non-thinking sampling settings. Planner and music weights are never loaded concurrently; the existing single DSP worker sequences lyric and song requests. Emit actual decode-pass counts while unknown completion totals remain indeterminate.
- A Generate lyrics button exposes a song idea and language selection within Input Lyrics. Resulting text remains editable; blank manual text stays instrumental. Success replaces lyrics only for the active request and persists the draft; historical jobs never overwrite a later draft.
- Auto duration invokes the native format prompt and constrained metadata-only decoding for the original caption and optional lyrics. Preserve the original caption/lyrics, use only validated duration/metadata, record raw suggestion and the 10–300-second cap. Missing planner produces an actionable setup/explicit-duration error.
- Default fresh/omitted counts to two without overriding existing draft choices. Each song gets separate planning/inference/output state and a different seed.

## Risks / Trade-offs
[Additional ~4.91 GiB assets and planning latency] → disclose exact bytes, reuse pins and show real activity. [Planner changes intent or predicts poor length] → preserve manual words/styles, record metadata, allow explicit duration and editing. [Five-minute memory] → validate real target hardware, preserve memory guard and tiled decode; fail clearly rather than truncate.

## Migration Plan
No catalog/config relocation. Previously installed music models continue generating explicit durations without the planner. Auto length and lyric generation require explicit planner setup in the retained model folder; download only missing assets. Existing selected counts and rendered audio remain intact. Provide a docs guide linked from README. Reverting app code leaves planner assets safely owned/reusable.
