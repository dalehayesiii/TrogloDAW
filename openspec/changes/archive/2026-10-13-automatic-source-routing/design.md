# Design

## Context

The current preset changes clip settings to one-second cuts, +2 semitones and 1.1x speed after confirmation. Selection analyzes all inputs as vocals, uses an overly permissive tempo-confidence threshold and ignores whether samples contain completed accompaniment. Existing phrase/motif planning already supports seeded variation, rests, bounded repeats, portable assets and both conditioning/postmix. See proposal.md for motivation.

## Goals / Non-Goals

Automatically distinguish finished Library mixes from recordings and give mixed collections differentiated sample roles. Preserve manual values and old rendered recipes. Do not add a dialog, speculative semantic model, eager stems, genre dictionaries or a new sample editor. This change does not implement WRK-25's fixed backing mode or WRK-27's intact-recording/blueprint workflow.

## Decisions

Use server-resolved catalog IDs and verified saved-source lineage. Uploaded filenames never establish prior-song status. Counts identify one of eight collection combinations; per-source policies distinguish finished-mix hooks/accents from recording phrases/call-response. The policy is versioned and saved independently of requested settings. Legacy preset flags are accepted but never required or reapplied; explicit saved numerical values remain.

For full mixes, use smaller bounded budgets, measured energy/onset anchors and tempo-relative cut limits. Retain short hooks and accents, omit whole-song overlays, and restrict added pitch variation to octaves so polyphonic intervals do not acquire arbitrary new pitch classes. Recordings retain existing phrase/whole-short-clip behavior and mixed collections prioritize their phrase material. Repetition/density is lower for full mixes, which already contain accompaniment. Sources remain nonoverlapping on the guide timeline, with measured rests and fair duration budgets. Confidence must exceed the existing analyzer's documented 2.0 threshold before tempo is trusted; prioritize finished-mix tempo over uncertain speech estimates.

Keep source copies, selected regions, variants and gain-bearing placements. Record collection type, source classification/role, requested/effective budgets, analysis and policy version. Recipe replay uses saved WAVs/placements, not a rerun of the new planner. Lyrics/styles/options are never replaced by automatic routing.

Compare fixed-preset, conditional-only and analyzed policies using synthetic source matrices; retain timing, placement, pitch and coverage measurements. Existing WRK-7 native GPU/CPU stem measurements inform the optional-stem comparison. Demucs can isolate estimated tracks, but adds processing/storage and leakage; do not make it mandatory to use audio inputs. Free-text model prompting was rejected as the sole sample planner because text does not supply authoritative waveform cut/timing positions.

## Risks / Trade-offs

- Onset/tempo analysis can fail on ambient/noisy/irregular material: use audible-region selection and a recorded fallback grid, without guessing a genre or speaker identity.
- Octave-only full-mix variations can still change timbre: original-register variants remain available, explicit pitch settings remain authoritative and each transformation is saved.
- A Library vocal-only song is treated as a finished song by lineage, not claimed to contain instruments; source analysis still selects its audible material. Reuploaded finished songs lack trustworthy lineage and remain recordings.
- This is an inspectable heuristic arranger, not a learned semantic composer or proof of universal genre/lyric fidelity. Objective synthetic checks and prior measured extraction costs cannot replace subjective listening judgments.

## Migration Plan

No storage/configuration migration. Remove the obsolete modal and choice validation. Existing saved numerical settings, waveform assets and replay semantics remain. Source-conditioned generation continues passing the actual full-duration guide as authoritative audio; no generated semantic codes are substituted.
