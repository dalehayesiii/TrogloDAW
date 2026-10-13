# Design

## Context

See proposal.md. `Songs.generate()` builds or reuses a full-duration stereo 44.1 kHz float guide, caps its peak at 0.8, writes `sample-arrangement.wav` and passes it to the inference runner as `conditioning_audio` when the effective mode is `conditioned`. Postmix mixes the same layer into the generated music afterward. The core app runtime ships numpy, scipy and pedalboard; torch exists only in the separately installed inference runtime inside model storage.

Offline evaluation (personal audio, not committed) on a real 120-second guide: Light-style DSP plus DeepFilterNet3 took about 3 s per minute of audio on CPU; Resemble Enhance and Apollo took about 5 minutes per minute, and Resemble's full enhancer moved the spectrum ~15 dB from the source (a re-synthesis risk for conditioning). Apollo targets codec damage the guide does not have and is CC BY-SA.

## Goals / Non-Goals

**Goals:** Cleaner, louder, less harsh conditioning guide; deterministic, bounded and fast processing; inspectable before/after; safe fallbacks; backward-compatible drafts/recipes.

**Non-Goals:** Changing arrangement decisions, postmix output, final mastering, the Strong/Resemble tier, new model downloads, or claiming improved ACE-Step output before GPU A/B validation.

## Decisions

- **Hook location.** Enhance in `Songs.generate()` after the final peak cap and `generation_mode()` resolution, immediately before writing `sample-arrangement.wav`, and only when the effective mode is `conditioned`. Both the fresh `arrange()` path and saved-arrangement reuse converge there. The conditioning file keeps its name and remains what the model received; the raw guide is written to `sample-arrangement.raw.wav` only when enhancement changed it. Postmix keeps mixing the raw layer, so its replay semantics are untouched. Alternative (inside `arrange()`) would miss reuse and would also alter postmix.
- **Light chain (`backend/guide_enhance.py`).** All numpy/scipy/pedalboard, no new dependency:
  1. Repair isolated discontinuities: second-difference spikes far above the local robust level are linearly bridged over ≤1 ms, capped in count.
  2. 70 Hz high-pass; peak cut at 3.5 kHz (−1 to −4 dB by strength); compressor (ratio 1.5–3.5 by strength, −20 dB threshold).
  3. Gap gate relative to the guide's own active level (opening over the 32–20 dB range below its 95th-percentile 50 ms level, not an absolute floor), smoothed over 20 ms; reduction depth 40–90% by strength.
  4. Loudness lift toward −20 LUFS using an approximate BS.1770 K-weighted, gated meter, bounded to +12 dB so quiet input cannot cause unbounded noise gain (only lifts, never lowers); a smooth gain-reduction peak limiter without make-up gain (pedalboard's Limiter adds make-up gain, so it was rejected), then the existing 0.8 peak ceiling (attenuate only).
  Strength 0–100 (default 50) scales EQ depth, ratio and gate depth; strength 50+ reaches the loudness target and lower values lift proportionally less. Strength 0 leaves only discontinuity repair and the peak ceiling. Light measured about 4 s for a real 120 s guide on an 8-core CPU (−28.9 → −20.1 LUFS, 3.3 dB spectral distance).
- **Safety.** Output replaced by the raw guide when it contains non-finite values, is silent while the raw guide was audible, or its level-matched log-spectral distance over active frames exceeds 8 dB. The reason is recorded and sent as a progress message (`stage="guide_enhancement"`).
- **AI clean.** DeepFilterNet 0.5.6 depends on `deepfilterlib`, whose PyPI wheels stop at CPython 3.11 (embedded runtime is 3.12.10) and whose Python package pins numpy<2 and imports a removed torchaudio module. Building the Rust library in CI or re-implementing libDF feature extraction for its ONNX export is out of scope for this change. The tier is accepted by the API for forward compatibility but resolves to Light with an explicit `fallback_reason`; the UI shows the option disabled with "add-on unavailable". Follow-up: a verified, manifest-listed add-on (ONNX models + a cp312 libDF build or numpy feature extraction) installed through the existing Settings flow.
- **Default Light.** It is bundled, CPU-fast (about 0.5 s per 30 s), only applies to conditioned generation, keeps the raw guide and auto-falls back. Off remains one click away. Drafts lacking the field use Light; saved recipes record the effective tier so previous songs remain explicable.
- **Provenance.** `parameters["guide_enhancement"]` and `recipe["guide_enhancement"]` hold `{version, requested, effective, strength, applied, fallback_reason, metrics}`; `recipe["conditioning_raw_file"]` is a library-relative path when written. Draft fields `guide_enhancement` and `guide_enhancement_strength` are reusable ingredients.

## Risks / Trade-offs

- [Model may prefer the raw guide's character] → Light is conservative, Off is available, both guides are kept and previewable; GPU A/B is a documented follow-up.
- [Gate may cut soft breaths] → relative threshold, smoothing, depth bounded by strength.
- [Loudness lift could amplify noise] → +12 dB cap, gate first, safety fallback.
- [AI clean expectation] → disabled with explicit reason in UI, recipes and docs.

## Migration Plan

No storage/config/installer migration. Older drafts gain the Light default on their next conditioned generation; existing songs and recipes are not rewritten. Rollback: choose Off or revert the change.
