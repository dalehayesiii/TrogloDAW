# Recovering noisy generation

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
