# Recovering noisy generation

## Recording + style reports an incomplete timeline

If both outputs fail with **The model did not render the complete recording
timeline**, update to a release containing the recording-frame repair and retry
the retained draft. No source conversion, model redownload or Library migration
is needed. This can affect an upload shown as 1:03: the displayed length hides
fractions of a second.

The pinned decoder operates on 40 ms frames. Earlier direct generation could
drop the final partial frame and then reject that shorter output; the catalog
also rounded source duration to milliseconds. Direct generation now uses exact
decoded source samples and appends less than 40 ms of silence inside the encoder
to retain the complete ending. Only excess generated tail is removed afterward.
Original recordings, complete saved songs and historical replay remain unchanged.
Genuinely incomplete output still fails; the repair does not conceal it with
silence or promise exact words/voice fidelity.

The repair was checked with the pinned VAE configuration and actual installed
diffusers encoder/decoder shape operations at nine durations from 1 to 300 seconds.
For 63.003 seconds at 48 kHz, the old path loses 144 samples; the aligned path
retains the complete ending and yields 1,776 extra generated-frame samples to trim.
Waveform regressions verify unchanged source samples, exact final lengths and
continued rejection of genuinely short output. A fresh full music inference
attempt stopped at the 12 GiB available-RAM guard before loading; these checks do
not claim a new full native 63-second performance or listening benchmark.

## Older high-Weirdness sampler failure

Older versions selected the checkpoint's SDE sampler when **Weirdness exceeded
50**. The pinned checkpoint's SDE branch renoises using linear time while the
slider also changes the timestep schedule. This combination can produce poor or
noise-like output for a single song or every song in a run. Two outputs already
run sequentially in separate inference processes; this defect is in sampler
selection rather than parallel batch allocation.

New generation uses ACE's supported default ODE sampler throughout the Weirdness
range. Weirdness still independently changes schedule shift from 1 to 5, while
Style Influence changes guidance. Existing songs, recipes and assets stay intact.
After updating, reuse the affected creation ingredients and generate again. Until
updating, set Weirdness to 50 or lower. Changing an existing recipe does not repair
its already rendered audio; replay intentionally uses the saved original.

An isolated RTX 3070 comparison used the reported two-minute city-pop settings,
seed, shift 3.64 and guidance 11.5. ODE completed in 29.39 seconds of model inference
with 4.69 GiB peak CUDA allocation. We also checked six slider boundary/extreme
values and that one output is cataloged before the next inference starts.
These checks establish execution and the supported parameter path, not guaranteed
musical quality, style matching or vocals. No personal audio is included in tests.

See [song controls](song-workflows.md) and the upstream
[inference parameter documentation](https://ace-step.github.io/ACE-Step-1.5/en/INFERENCE).
