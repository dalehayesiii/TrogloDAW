# Proposal

## Why

The arranged guide passed to ACE-Step cover conditioning is assembled from raw, pitch/time-shifted voice recordings. Offline measurements of a real guide built by `Songs.arrange()` showed it is quiet (about −28 LUFS on its busiest 30 seconds), harsh in the 2–5 kHz band and carries the recording's noise floor between phrases, and the model can reproduce those qualities. A bounded, inspectable pre-conditioning step can give the model a cleaner guide without changing the arrangement itself.

## What Changes

- Add an optional guide-enhancement step that runs after the full-duration arrangement is final (fresh or saved-arrangement reuse) and before it reaches the model, only for audio-conditioned generation.
- Offer three choices: Off, Light (bundled local DSP: discontinuity repair, 70 Hz high-pass, de-harsh EQ near 3.5 kHz, gentle compression, gap gate, bounded loudness lift toward about −20 LUFS, existing 0.8 peak ceiling) and AI clean (DeepFilterNet3 denoise). AI clean is shown as unavailable in this change because DeepFilterNet's published native library has no Python 3.12 wheels; requests for it use Light with a visible note.
- Add a strength control (0–100, default 50) that scales the enhancement.
- Default to Light for fresh drafts and for drafts saved before this change.
- Fall back to the unchanged guide when the enhanced audio is non-finite, silent or spectrally far (>8 dB level-matched log-spectral distance) from the original, and report the reason through existing job progress.
- Keep the unenhanced guide as `sample-arrangement.raw.wav` beside the conditioning file and record versioned settings/outcome in the recipe and parameters. Add a before/after guide preview to generation results.
- Allow Prior Song Reference to reuse the enhancement settings like other generation controls.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `song-generation`: guide pre-conditioning enhancement, its controls, provenance, fallbacks and the unavailable AI clean add-on state.

## Impact

Backend `songs.py` (generation orchestration and ingredient reuse) and a new `backend/guide_enhance.py`; frontend Generation draft/controls/results; synthetic pytest coverage; docs (`docs/guide-enhancement.md`, README, workflow guide). No new runtime dependency (numpy/scipy/pedalboard already ship), no model download, no network use. Postmix and text-only generation are unchanged; existing songs/recipes replay unchanged. ACE-Step output quality with enhanced versus raw guides is not yet validated on GPU hardware.
