# Input Audio before and after

These captures use the real local FastAPI service and two synthetic four-second
recordings. **Before** uses the final branding PR's compiled interface; **after**
uses the audio correction with expanded settings inside Input Audio. The visible
previous result is an actual postmix generation from those inputs. The separate
conditioned-assets capture shows an actual Base-conditioned song's saved assets.
No personal audio or inference caches are included in this gallery.

| Mode | Before | After |
| --- | --- | --- |
| Light | ![Before: input clips and collapsed clip adjustments](before-light.png) | ![After: audio conditioning settings inside Input Audio](after-light.png) |
| Dark | ![Before in dark mode](before-dark.png) | ![After in dark mode](after-dark.png) |

| Additional state | Capture |
| --- | --- |
| Explicit post-generation mixing, light | ![Postmix settings in light mode](postmix-light.png) |
| Explicit post-generation mixing, dark | ![Postmix settings in dark mode](postmix-dark.png) |
| Narrow conditioning controls | ![Narrow dark interface](after-narrow-dark.png) |
| Real conditioned result and saved assets | ![Portable conditioned song assets](conditioned-assets-dark.png) |

The source and installed browser suites validate applicable controls, persistence,
mode selection, recording workflows and both themes. Hardware results and the
checkpoint compatibility repair are described in [model validation](../../local-models.md).
