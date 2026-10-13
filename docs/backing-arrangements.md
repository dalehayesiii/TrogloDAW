# Import and arrange over a song

In **Library → Import WAV song**, choose one WAV, give it a title, and optionally
choose an existing Library folder. The default is **Unfiled**. The imported song
appears in normal browsing, playback and prior/backing selection. Import works
without installing a music model.

The external file stays unchanged. The Library retains an exact original copy and
SHA-256, plus a 44.1 kHz stereo WAV/MP3 for playback. Excessive peaks are attenuated
for headroom; quiet files are not normalized upward during import. The recipe records
the original format and conversion, without inventing lyrics, styles or stems.
Library asset previews identify the imported original and preserved backing explicitly.
Invalid/non-finite WAVs, failed writes and canceled imports do not register a broken
song. Retry dismisses the earlier import failure using the normal notification policy.
Import supports nonempty WAV/WAVEX/RF64 audio up to twenty minutes.

In **Generation → Generation workflow**, choose **Arrange recordings over an
existing song**. Select one **Backing song** and add separate recordings in
**Input Audio**. The backing is used once as the preserved musical timeline; it
cannot also be selected as a sampled input. Library audio can be used as an input,
with finished songs retaining their source-aware hook/accent handling. Choose a
title or leave it blank to use the backing title with an arrangement suffix.

The backing determines the complete output length, from one second to twenty
minutes. This is independent of the generation model's ten-second to five-minute
limits. Each requested output runs sequentially; the default remains two. This
workflow needs no music model, lyric writer, separator or GPU inference. Lyrics,
styles, automatic writing, audio conditioning/adherence, guide enhancement and
model options are hidden and ignored by the backend. Switching back restores those
draft values. Per-clip sampling and transformation controls still apply.

## What the arrangement uses

The source-derived phrase/motif/accent planner remains responsible for sample cuts,
bounded variants, spaced returns, section dynamics, fades and source coverage.
See [source-aware sampling](source-aware-sampling.md) for prior/recording combinations.
Fixed-backing mode adds a measured context rather than generating replacement music:

* Up to three twelve-second windows estimate tempo and key. A sufficiently confident
  tempo drives a half-beat placement grid; onset analysis estimates its phase.
  Otherwise the recipe records a 90 BPM fallback.
* Quarter-second energy measurements across the backing favor quieter intervals
  within the planned sections while maintaining rests and repeat limits. These are
  energy gaps, not semantic phrases, bars or automatically separated vocal gaps.
* A confidently sung recording can be transposed toward the backing's key root only
  when all backing windows agree and the source/backing major/minor modes match.
  Manual pitch offsets are retained; alignment outside the supported range is skipped.
  Speech, ambiguous keys and conflicting key modes are not automatically retuned.
* Samples match bounded measured backing-song loudness with the clip Volume offset.
  No vocal separation runs. The existing bus compression, loudness and true-peak
  limiter master the combined mix, so the backing's final gain can change.

The original backing and input files remain unchanged. Each new song stores an
immutable decoded backing copy, source copies, derived samples, transforms, placements,
gains, seed and context. Keep the complete Library together: saved-asset replay works
after relocation and needs no new inference. Cancel preserves completed outputs and
cleans unfinished output files; partial failures are reported per output.

## Validation and limits

Synthetic tests cover imported/existing backings, short/quiet/stereo inputs,
invalid audio and storage failures, uncertain keys, phase-aligned placement in
quieter intervals, two sequential outputs, cancellation and relocated replay.
The real-service browser tests import/retry/play a WAV and arrange two outputs without
installed models, preserve model drafts, and check both themes at 1440/390 pixels.

This is a heuristic DSP workflow. Energy and onset measurements do not recognize
lyrics, musical intent or complete harmonic progressions. Key estimates can be wrong;
modulating songs may disable alignment. Independent source processing can still
produce awkward combinations or emphasize recording noise. The twenty-minute cap is
a supported input guard, not a performance promise: decoding and mastering use full
buffers, so longer songs consume more RAM and disk. No subjective quality score or
universal semantic accompaniment is claimed from synthetic fixtures.

Recipes use `workflow: arrange-over-song`; absent workflow keeps existing model
generation. The discriminator can accommodate the later intact-recording workflow
tracked in WRK-27. This change does not alter conditioned/postmix model-generation
defaults or require remote processing.
