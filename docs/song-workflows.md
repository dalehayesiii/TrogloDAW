# Song workflows

The browser has three tabs: **Generation**, **Library** and **Vocal FX**. Settings
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

Every selected input is analyzed, sliced, transformed and placed in the song;
none is silently ignored. Original input copies, transformed sample WAVs and
placements are saved independently from generated musical parts. The generated
model audio is mixed with these arranged samples, then mastered. Selecting a
finished song as Input Audio samples its rendered mix. Recommended prior-song
settings affect only that clip: eight one-second slices, +2 semitones, 1.1x stretch
and -12 dB gain. Apply or keep settings explicitly. The decision/version stays with
the clip; unchanged clips do not repeatedly prompt. This starter preset does not
promise intelligent multi-track separation or prior-song-aware composition.

Lyrics/styles work without audio input. The exact supplied lyrics reach the local
model. Blank titles derive from up to six lyric/style words. **Number of
Generations** defaults to one, supports 1–32, and runs independent seeds
sequentially. Each song is separately cataloged; earlier successes remain if
another output fails or the request is canceled. Completed outputs are visible
while later outputs run. Model quality can repeat material or pronounce lyrics
imperfectly; this is documented rather than hidden by rewriting lyrics.

**More Options** is initially collapsed and contains only:

| Control | Local mapping |
| --- | --- |
| Vocal Gender | Unset/Male/Female caption guidance for newly generated voices; a preference, not guaranteed classification or an effect on source recordings |
| Duration | Auto derives seconds from lyric words/2.2 plus 12 seconds of structure, or from the longest selected sample budget times 1.25, with minimum 10; explicit or auto results outside 10–120 seconds fail clearly |
| Weirdness | 0–100 maps to schedule shift 1–5; above 50 uses SDE, otherwise ODE; independent of style guidance |
| Style Influence | 0–100 maps to Base-family classifier-free guidance 1–15 |
| Variety | Zero retains styles exactly; higher values append one to three bounded structural/style phrases chosen per seed; lyrics stay unchanged |

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
