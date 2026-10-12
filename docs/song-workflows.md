# TrogloDAW Song workflows

Expensive jobs remain visible above the workflows, including after navigation or
reload. The status distinguishes queue waiting from active elapsed time and,
when evidence supports them, stage/current-song/whole-request remaining ranges.
Diffusion steps, separation chunks, voice slots and sample/render work drive live
progress. Completed local runs continually improve comparable estimates; unknown
stages remain indeterminate. Cancel requests stay visible until acknowledged and
earlier completed songs survive a canceled batch. See [progress](progress.md).

TrogloDAW has three browser tabs: **Generation**, **Library** and **Vocal FX**. Settings
contains the initial model setup and separate library/model locations. After setup,
audio processing and storage work offline. See [model setup and measured limits](local-models.md).

## Generation

Add multiple uploaded clips, microphone takes or Library songs. Each clip can be
previewed, labeled, removed, replaced or retaken independently. A new recording
requests microphone permission only when initiated. Stop, preview and keep a take,
or discard/record again. The old take stays selected until a replacement is kept.
Capture stops on stop/cancel/dialog exit/tab change/shutdown. Browser recording
requires localhost or another secure browser context. Permission, missing-device,
unsupported-format and empty-audio errors preserve existing inputs. Automated tests
use real MediaRecorder with a synthetic WebAudio stream; a physical microphone
check is optional after delivery.

Every selected input contributes to a full-song sample arrangement. Selection uses
phrase boundaries, audible energy and spectral diversity, with a budget based on
active material. Phase-canceling stereo uses a recorded dominant-channel strategy
for samples/conditioning while retaining the original unchanged. Short clips are not duplicated merely to fill a sample count;
longer contrasting recordings yield more distinct cuts. Each cut receives seeded
pitch/speed variation around its clip adjustments, limited volume balancing and
edge fades. A shared detected tempo (or 90 BPM fallback), recurring motifs and
section dynamics spread the samples across the selected duration. These are
inspectable heuristics, not a guarantee of artistic arrangement or key matching.

By default, the compatible Base model receives this complete arrangement WAV
**before generation**, alongside lyrics and styles. It produces the whole song;
the app saves that mix directly rather than overlaying the same samples again.
Inside Input Audio, expand **Audio arrangement settings** for **Audio adherence**
(default 75%). It maps to the fraction of diffusion steps using source-audio
conditioning, rounded down to whole steps out of 32; requested/effective values are
saved. 0% disables that influence, 100% uses it throughout. It is independent
of Style Influence, pitch, speed and volume. The model can reinterpret or blur
samples, change timbre and pronounce words imperfectly; adherence does not promise
exact sample preservation or singer identity.

Enable **Mix samples after generation** to keep the independent generation approach:
the same improved arrangement is mixed over the generated music afterward. Audio
adherence is inactive in that mode. A model without supported conditioning uses
this postmix fallback with an explanation; requested/effective modes stay in the
recipe. Without input clips, generation uses lyrics/styles directly and these
Input Audio settings are hidden.

Original input copies, transformed sample WAVs, complete arrangement audio, model
output and gain-bearing placements remain separate inspectable assets. Conditioned
rerender uses the saved model mix; postmix rerender reconstructs the samples over
saved music. Older recipes retain their previous replay behavior. Selecting a
finished song as Input Audio samples its rendered mix. Recommended prior-song
settings cap selection at eight one-second cuts, with +2 semitones, 1.1� speed and
-12 dB volume before individual variations. Apply or keep settings explicitly.
The decision/version stays with the clip; unchanged clips do not repeatedly prompt.

Lyrics/styles work without audio input. The exact supplied lyrics reach the local
model. Blank titles derive from up to six lyric/style words. **Number of
Generations** defaults to one, supports 1–32, and runs independent seeds
sequentially. Each song is separately cataloged; earlier successes remain if
another output fails or the request is canceled. Completed outputs are visible
while later outputs run. Model quality can repeat material or pronounce lyrics
imperfectly; this is documented rather than hidden by rewriting lyrics.

**More Options** is initially collapsed and contains only:

| Control         | Local mapping                                                                                                                                                                                                |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Vocal Gender    | Unset/Male/Female caption guidance for newly generated voices; a preference, not guaranteed classification or an effect on source recordings                                                                 |
| Duration        | Auto derives seconds from lyric words/2.2 plus 12 seconds of structure, or from the longest selected sample budget times 1.25, with minimum 10; explicit or auto results outside 10–120 seconds fail clearly |
| Weirdness       | 0–100 maps to schedule shift 1–5; above 50 uses SDE, otherwise ODE; independent of style guidance                                                                                                            |
| Style Influence | 0–100 maps to Base-family classifier-free guidance 1–15                                                                                                                                                      |
| Variety         | Zero retains styles exactly; higher values append one to three bounded structural/style phrases chosen per seed; lyrics stay unchanged                                                                       |

These are validated local parameter mappings, not a claim to implement Suno's
undisclosed algorithms. Original/effective styles, options, automatic-duration
reasoning, source IDs, transformations, placements, seed and exact model identity
are retained per output. Saved generated WAVs are the reproducibility source;
seeds alone do not promise identical future inference.

**Prior Song Reference** shows individually selectable saved ingredients and their
values: original audio, lyrics, styles, title, controls and sample arrangement.
Only checked fields replace the draft. Unavailable legacy fields remain labeled.
Legacy procedural songs expose actual stored style/title; older mixes expose their
input voice if still available. Tab navigation and browser reload preserve the
Generation draft. Library recipe inspection includes original input, sample and
generated-audio players; missing assets are explicit.

## Library and Vocal FX

Search, play and rename songs, create folders and move songs without changing IDs
or asset references. Song actions open Generation/Input Audio, selective recipe
reuse or Vocal FX directly. Existing catalogs and legacy CLI recipes stay usable.
Opening an existing library and relocating the current one are separate Settings
actions. Relocation uses a verified staging copy, preserves the original recovery
copy and does not overwrite a populated destination.

Vocal FX looks up source-content/model/runtime-version caches and extracts missing
vocals automatically in a background job. Candidate voices are uncertain, with
solo previews and timeline correction/grouping. The effects are the existing pitch,
stretch, gain, low/high-cut EQ, compression, chorus, robot, echo/delay, reverb,
trim and normalization controls; details are progressively disclosed.

Each group occupies fixed original timeline segments. Trim retains its starting
offset; stretching is padded/cropped to the slot; tails are clipped at slot/song
end. Final sample rate/count/duration match the original. The edited vocals replace
the extracted vocals over the residual accompaniment, avoiding double vocals.
First save creates a distinct `_FX` song with lineage. Later saves explicitly offer
**Update this FX version** or **Save a new FX version**. Every edit starts from
cached unprocessed source stems, avoiding repeated baking of earlier effects.
Changing source audio or relevant processor versions invalidates cached stems.
Source/cache/edited assets and recipes remain with the complete portable library.
