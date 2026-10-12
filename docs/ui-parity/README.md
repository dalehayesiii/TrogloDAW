# Gradio to Angular parity

Baseline: initial commit `4aae81d`, Gradio 6.30.0, before replacement. Both sets
use the same Chromium/Edge build, light theme and a **1440 × 1100 viewport**.
These are full-page captures: height follows visible content, while viewport stays
constant. Synthetic voice/beat/mix fixtures are shared. IDs/timestamps of newly
rendered results can differ. No personal audio was used.

The initial app has **four tabs**, with Library inside AI Producer; that is retained.
The same fonts, colors, labels, defaults, ranges, grouping and two-column layout
are used. Audio transport is recreated around browser audio/canvas. Framework
utility details (attribution, local API docs, icons/native selects) use the new stack.
Screenshots are review evidence, not a claim of pixel-identical framework widgets.
Broader redesign is deferred.

| State | Before: Gradio | After: Angular/Tailwind |
| --- | --- | --- |
| Producer / empty library | ![Before](before/producer-library.png) | ![After](after/producer-library.png) |
| Overrides | ![Before](before/producer-overrides.png) | ![After](after/producer-overrides.png) |
| Voice FX | ![Before](before/voice-fx.png) | ![After](after/voice-fx.png) |
| Generator | ![Before](before/generator.png) | ![After](after/generator.png) |
| Mixer | ![Before](before/mixer.png) | ![After](after/mixer.png) |
| Missing-source error | ![Before](before/mixer-error.png) | ![After](after/mixer-error.png) |
| Populated library / playback | ![Before](before/library-populated.png) | ![After](after/library-populated.png) |
| FX preview | ![Before](before/voice-fx-preview.png) | ![After](after/voice-fx-preview.png) |
| Mix recipe | ![Before](before/mixer-recipe.png) | ![After](after/mixer-recipe.png) |
| Mix / MP3 result | ![Before](before/mixer-result.png) | ![After](after/mixer-result.png) |
| Generated beat | ![Before](before/generator-result.png) | ![After](after/generator-result.png) |
| Producer analysis / result | ![Before](before/producer-result.png) | ![After](after/producer-result.png) |

Functional evidence goes further: pytest compares seeded API waveform output to
the original core renderer and checks imports/media, FX, recipes/export, producer,
config/catalog and shutdown. Vitest covers control defaults/reset and uploads.
Playwright uses real FastAPI for upload/import, rename/tag/delete, preview/save,
generate, mix/download, load-recipe, production/progress/results and shutdown.
CI repeats browser tests against the installed embedded runtime on Windows.

To reproduce, run the original Git commit with Gradio 6.30.0 and synthetic fixtures,
then the current locked uv environment and compiled frontend. Use the same browser,
viewport/theme and initial catalog for each pass. Original code stays in Git history,
and is not included as an extra app runtime.
