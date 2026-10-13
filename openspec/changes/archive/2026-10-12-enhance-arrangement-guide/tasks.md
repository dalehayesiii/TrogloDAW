# Tasks

## 1. Enhancement engine

- [x] 1.1 Add `backend/guide_enhance.py` with Off/Light, strength scaling, bounded loudness lift, peak ceiling and safety fallbacks; verify with synthetic pytest cases (harsh/noisy/clicky guide improves metrics, quiet input lift bounded, silence/NaN/excessive change fall back, strength 0 and Off leave audio nearly unchanged).
- [x] 1.2 Resolve AI clean to Light with a recorded reason; verify by pytest.

## 2. Generation integration

- [x] 2.1 Hook enhancement into `Songs.generate()` before writing `sample-arrangement.wav` for conditioned mode only, save `sample-arrangement.raw.wav`, record provenance in parameters/recipe, emit progress notes and expose before/after previews; verify with pytest for conditioned, postmix, Off, saved-arrangement reuse, relocated library and ingredients reuse.

## 3. Interface and documentation

- [x] 3.1 Add Enhance guide select (AI clean disabled as add-on unavailable) and strength slider in Audio arrangement settings, draft defaults, reference labels and before/after preview; verify with ESLint, Vitest and strict build, and review the flow per the ui-ux-audit skill.
- [x] 3.2 Document behavior, limits and the AI clean follow-up in `docs/guide-enhancement.md`, README and the workflow guide; verify links.

## 4. Validation

- [x] 4.1 Run Ruff, ty, pytest, Prettier, ESLint, Vitest, strict build, CLI smoke and `npm run specs:check`; record results.
- [x] 4.2 Sync the canonical song-generation spec and verify strict validation passes.

## Workflow follow-up

- Archive the change before opening the PR; monitor required CI on the latest head; GPU A/B of ACE-Step output with raw versus enhanced guides remains outstanding.

## PR review corrections

- [x] Guard DSP and all measurements, shape/invalid results and opposite-phase stereo with synthetic regressions; include the module in CI formatting.
