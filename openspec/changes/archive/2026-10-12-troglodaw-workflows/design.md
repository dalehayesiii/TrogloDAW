# Design

## Context

See proposal.md for motivation. The baseline is a static Angular frontend served by FastAPI with a single DSP worker, catalog-relative file paths and legacy CLI recipes. The current machine is a Windows RTX 3070 with 8 GiB total VRAM; measured free VRAM is about 6.2 GiB with desktop activity. Model recommendation remains contingent on the required local tests.

## Goals / Non-Goals

Goals: extend the Python engine without destroying legacy recipes; retain inspectable audio assets; bound GPU concurrency; keep model and runtime caches under user-selected storage; deliver setup/uninstall ownership safely.

Non-goals: music-video generation, automatic eager stems for all songs, cloud inference, theme redesign and calibrated ETAs in this PR. Startup update checks are a later separate WRK-10 PR.

## Decisions

1. Use ACE-Step 1.5 Base as the first evaluation path because Base supports classifier-free style guidance. The pinned checkpoint expects an older misspelled CFG keyword, so a signature-checked compatibility adapter forwards the requested value rather than allowing silent default guidance. Same-seed waveform comparisons verify the controls affect inference. Turbo overrides this parameter and cannot expose the same control honestly. Pin upstream inference code and checkpoint revisions; validate Windows BF16/SDPA with CPU/DiT offload and one output at a time before declaring it recommended. Use independent schedule/sampling mappings for Weirdness, CFG for Style Influence, caption vocal-character guidance for Gender, and bounded prompt variations for Variety. Lyrics remain untouched. Auto duration derives from lyrics/input structure and retains its derivation; unsupported lengths fail rather than being silently clamped.
2. Keep heavyweight inference dependencies optional in pyproject/uv.lock. Initial setup uses a pinned bundled uv binary to install the hashed locked inference dependencies under the selected model folder. Generate any requirements export temporarily during setup; do not ship or track exports. Download and verify the pinned upstream runtime/checkpoints there. A child process uses those dependencies and code without changing the core service environment. Network is disabled for inference; upstream implicit acquisition is replaced by explicit verified prechecks. Alternatives were an oversized installer or an unmanaged external server, neither fitting the revised setup requirements.
3. Use torchaudio's local pretrained HDemucs path for vocal extraction and a local pretrained speaker-embedding path for conservative candidate grouping. Test exact runtime compatibility and thresholds before accepting the pipeline. Overlap remains an uncertain shared group; correction can regroup time segments. Cache source audio by content hash, model/processor identity and alignment version. Residual accompaniment is original minus extracted vocals, making bypass reconstruction numerically defined instead of adding edited vocals to an already vocal-containing mix.
4. Store a song-family asset directory with relative generated/sample/stem paths and immutable source provenance. Apply group effects to fixed timeline slots; trim keeps offset and stretch is padded/cropped to the slot, tails clipped at song end. Save derivatives from unprocessed source stems. Updating a derivative writes new assets first, then atomically changes catalog metadata; the original is separate.
5. Make folders catalog metadata. Reuse ingredients selectively in the frontend and validate referenced assets in the backend. Each accepted recording is imported as a normal voice item with source-type metadata. Keep old API/CLI operations callable but replace browser workflows. Model/settings and detailed edits are disclosed on demand; tab navigation preserves drafts.
6. Storage changes run through the worker, prevent concurrent writes, validate roots and available space, copy into staging with content verification and activate configuration only after completion. Keep original data for recovery; never overwrite a conflicting destination. Persist setup preferences atomically with existing config precedence. Fail clearly if environment overrides prevent a choice from taking effect.
7. Model setup maintains a per-install ownership manifest of verified assets and runtime files. The uninstaller offers default-checked model removal and calls the manifest-aware cleanup before removing its Python runtime. Resolve every removal target beneath the recorded root; reject unsafe paths/symlinks and preserve unowned content. Reused/shared assets require ownership handling; upgrades preserve manifests/preferences.

## Risks / Trade-offs

- Windows upstream dependencies or memory pressure may prevent the candidate from meeting acceptance → run real inference before shipping and keep incomplete tasks open; never substitute procedural beats.
- Voice embeddings trained on speech are less reliable for singing/overlap → report candidate uncertainty, retain mixed groups and require listening/correction evidence.
- Large setup downloads can fail → pin sizes/checksums, retain resumable partial assets and activate only after verification.
- Per-operation subprocess loading adds overhead → measure it separately; WRK-6 estimates distinguish model loading and inference.
- Shared model folders can make automatic deletion unsafe → manifest ownership and path validation take priority over default checkbox convenience.

## Migration Plan

Read legacy catalogs unchanged, add optional metadata/recipe types, retain existing installation and environment identifiers, and preserve configured roots across upgrades. Rollback can reopen the original copied library and original songs. No spec archive or PR is complete before hardware validation, functional tests, screenshots, canonical spec sync and all required checks.
