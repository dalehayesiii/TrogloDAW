# Design

## Context

See proposal.md for motivation. Start from merged WRK-9/31 and WRK-25/32 at a8bb016. The existing `workflow` discriminator separates `model` inference from `arrange-over-song` CPU DSP; portable v2 recipes already save immutable model/backing audio and source/sample assets. The pinned ACE-Step runtime is ca1e85fe9430179831e6bc6be790c332190a3866, with a Base/SFT CFG adapter and optional separately installed 1.7B LM.

## Goals / Non-Goals

Keep original source audio and supplied words/styles authoritative. Provide three approachable flows with independent drafts and no planner controls. Preserve offline explicit acquisition, sequential 3070 execution and historical replay. No framework/server migration, DAW editor, caption enrichment implementation, voice-cloning guarantee, or implicit additional model download is involved.

## Decisions

### Workflow and draft boundaries

Add `recording-style` beside existing workflow values. Keep the existing legacy current-draft key, and save per-workflow snapshots under an additional key. A switch stores the old snapshot before selecting the new one; accepted recording replacement does not discard the old clip until acceptance succeeds. The initial backing draft can reuse existing shared ingredients, while the direct recording draft starts with no clips/lyrics/priors. Reload restores all snapshots. Library cross-tab sample actions intentionally enter sampled generation.

Direct mode allows exactly one upload/microphone source, verified through catalog/saved-source lineage. Reject prior songs, extra sources, supplied lyric/writer/reference/arrangement payloads and unsupported audio conditioning. The interface hides those inputs and removes inactive values from the submitted snapshot. Sample pitch/speed/gain are not applied to this source. Only validated inference controls remain applicable.

### Audio behavior

Change missing/fresh `audio_mode` to conditioned for sampled generation, retaining explicit persisted choices. Keep existing unsupported-model postmix fallback and recorded effective mode. Add shared hover/focus/tap information to the checkbox and adherence control. Guide enhancement remains available only for sampled conditioning; it must not modify a direct recording.

For direct mode, save the complete decoded recording as a relative source/conditioning asset, use validated Cover-nofsq with its full latent source and style, and never call sample selection or add the source again. This path retained the invented vocal phrase better than ordinary Cover in native validation. Hide duration controls and support 1–300-second sources. The decoder's 5.12-second minimum creates tail padding for very short clips; remove only that generated tail, leaving the whole source intact. Absent lyrics must not imply an instrumental override. Retain a whole-mix conditioned recipe with empty sample/placement collections so saved-audio replay can be reused.

### Musical blueprints and source authority

The upstream music LM offers metadata-only and metadata-plus-semantic-code phases. Native semantic-code renders at full and half strength changed recognized lyrics; these candidates do not qualify for automatic use. Add a separate isolated metadata blueprint stage for explicitly supported checkpoints in text-driven/postmix generation when existing verified planner assets are ready. Disable caption/language/lyric rewriting, pass exact supplied text and effective duration, validate tempo/key/meter, save the actual blueprint as managed JSON, and pass only validated musical metadata to the renderer. Literal numeric BPM, named major/minor key and supported meter in styles take precedence. Suggested text/language/duration never replace inputs. The planner process exits before music weights load.

Source-conditioned tasks intentionally bypass upstream text planning: generated codes preempt real `src_audio`. Their source-derived structure is already the musical guide. Record a source-authoritative bypass rather than enabling an ineffective or destructive Think flag. Fixed backing stays CPU DSP and does not invoke the music planner. Missing optional assets, unsupported checkpoints and planner failures get explicit status/reasons; failures fall back visibly to unchanged inputs, while cancellation propagates. Existing duration-planning failures retain their established explicit-duration recovery contract.

Source-understanding metadata is a research candidate, not trusted transcription. Its empty-code path invents a sample example, so it cannot silently replace supplied text. Likewise Remiqora's LEGO/complete tasks are experimental candidates for complementary music; evaluate copying, source/lyric/exclusion fidelity, and memory before choosing them. Preserve the user's independent-postmix checkbox semantics. Do not assume a correlation threshold or changed waveform proves improved music.

### Provenance and progress

Persist workflow, original source identity/audio, requested/effective modes, planning status/reason/revisions, actual blueprint reference, seed, effective metadata and model audio. Keep all artifact references relative. Return applicable source/planning information without new configuration or prompt-review UI. Include workflow/planning strategy in timing profiles and actual planner decode activity; do not estimate unknown token totals from timers. Replay uses saved model/backing audio and saved placements, never new planning.

## Risks / Trade-offs

- Longer planning/code decode and fresh-process startup → measure on RTX 3070, bound code/duration budgets, keep heavy stages sequential and optional-assets absence usable.
- Source vocals may drift with blank lyric conditioning → real source-conditioned tests and honest limitations; no fabricated internal lyric writing.
- Third-flow length differs from sampled generation → use source timeline, reject unsupported lengths clearly, document validated bounds without silent resizing.
- Bad planner metadata/codes → validate and record fallback; preserve exact user inputs and existing saved audio.
- New source tasks may copy context or degrade fidelity → controlled comparisons and separate documented outcome, not automatic adoption from another UI.
- Stale workflow drafts/payloads → synchronous snapshots, immutable submission, backend boundary tests and reload/retake browser regressions.

## Migration Plan

No data conversion or installation break. Existing current-draft JSON remains readable and explicit audio mode choices remain unchanged; new per-flow storage adds recoverable snapshots. Legacy recipes keep saved replay semantics. Optional planner setup uses existing pinned assets and ownership rules. Rollback to the previous app leaves old audio/recipes usable, although the new flow itself requires this version to generate again.
