# Design

## Context

See proposal.md for the reported failure. The pinned Oobleck VAE config specifies 48 kHz and downsampling ratios 2×4×4×6×10 = 1,920 samples (40 ms). A CPU/meta shape probe of the actual installed diffusers implementation encodes 63.003 seconds into 1,575 frames and decodes 63.000 seconds, dropping 144 end samples. Integer-second 1/7/63-second research fixtures did not expose this. The catalog separately rounds duration to 3 decimals.

## Goals / Non-Goals

Preserve the full accepted source through encoding and the exact final timeline. Keep source-guidance, vocal semantics, offline acquisition and saved replay. Phrase-selection improvements are the subsequent user-authorized change; this repair does not alter that layer.

## Decisions

- Resolve direct duration from its saved/uploaded decoded WAV, not rounded catalog display metadata. Other workflows retain existing duration handling.
- Wrap only direct mode's tiled encoder, after the handler resamples to 48 kHz. Require the verified 1,920-sample frame config; append at most 1,919 zero samples along time with non-mutating padding. This handles full and tiled encoding consistently, with no installed weight/code mutation or source-file rewrite.
- Derive final expected output frames from the conditioning WAV's exact frames/rate. Keep strict rejection for genuinely short outputs. Do not zero-pad already truncated generated audio: that would hide lost content. Remove extra generated tail only, and record encoder padding plus expected frames in inference provenance.
- Validate aligned/unaligned lengths, exact waveform prefix/end retention, invalid decoder configuration, millisecond rounding, two-output direct jobs and portable replay. Use the pinned decoder's actual shape probe without model computation or GPU allocation, then perform bounded native inference only when GPU work is idle.

## Risks / Trade-offs

- Extra frame can influence the learned ending → less than 40 ms encoder silence, no stretching/overlay, trim generated tail, retain honest fidelity limitations.
- Model versions with a different frame config → reject unsupported direct alignment explicitly rather than guess.
- Source/model resampling → calculate from exact accepted file frames; core final renderer already normalizes to source processing rate.

## Migration Plan

Retry failed direct drafts after updating. Existing catalog records, complete songs and recipes require no conversion. No model redownload. Rollback restores the prior adapter without modifying user assets.
