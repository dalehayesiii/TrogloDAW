# Current workflow evidence

WRK-4 screenshots use the real FastAPI service and compiled Angular interface,
1440 x 1100 desktop and 390 x 844 narrow viewports. Uploaded recordings and cached
voice groups are explicitly synthetic test fixtures. Their cached group labels
are not evidence of live singer recognition. Separate real-model inference,
control comparisons and memory evidence are documented in [model validation](../../local-models.md).
No personal recordings or downloaded model weights are committed.

| State | Capture |
| --- | --- |
| Initial setup | [setup](setup.png) |
| Generation | [main form](generation.png), [five expanded options](generation-options.png) |
| Library | [selection and actions](library.png) |
| Prior-song choice | [apply/keep preset](prior-song-preset.png) |
| Selective reuse | [available/unavailable ingredients](reference.png) |
| Vocal FX | [candidate and effects](vocal-fx.png), [correction and detailed effects](vocal-fx-details.png) |
| Real model setup | [verified ready state](setup-ready.png) |
| Real N=2 model results | [outputs](generation-results.png), [invalid duration](generation-error.png) |
| Narrow browser | [Generation](generation-narrow.png) |

The baseline visual vocabulary is retained for this workflow PR. The subsequent
WRK-5 theme PR replaces the branding/palette and adds persisted light/dark themes.
Functional checks cover actual audio uploads, metadata organization, preset choices,
cached FX derivatives, storage changes, errors, shutdown and real MediaRecorder
keep/discard/retakes with a synthetic WebAudio stream. Native Windows tests repeat
these browser checks, verify upgrade retention and exercise both uninstall choices.
