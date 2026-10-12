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

**Quit** replaces the complete page with a stopped confirmation telling you to close
the browser window. If shutdown cannot be confirmed, the interface remains available
with an error so you can retry.

![Quit completion after the local service exits](assets/quit-dark.png)

The product is designed for fully unfiltered local song creation, inspired by
frustration with tightening restrictions in hosted song tools such as Suno.
TrogloDAW adds no content moderation or word blacklists and passes supplied lyrics
to the local model unchanged. Supported lengths, input-size limits, memory guards
and the model's ability to deliver the requested words remain technical constraints.

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

Every selected input contributes to a full-song sample arrangement. A relative
energy analysis joins brief articulation gaps, retains audible phrase spans and
selects contrasting phrase, motif and accent cuts. A loud transient does not set
the threshold for the entire recording. Eligible 0.5–8-second inputs sometimes
contribute their complete clip as one sample when the song has enough space.
The `samples` budget caps distinct cut families (default eight, API maximum sixteen);
short inputs and short song durations can need fewer. Each cut has at most three
saved statement/response/fill variants, including bounded pitch, speed, filtering,
echo and gain differences. Statements retain phrase pitch/speed adjustments;
responses and fills evolve them. Prior-song presets retain their short-cut policy.

A shared detected tempo (or 90 BPM fallback) supports a section plan with quieter
openings/endings, fuller refrains, restrained bridges and intentional rests.
Placements use actual transformed lengths, avoid overlap and adjacent returns of
the same family when alternatives exist, and space family returns by at least eight
beats or twice the sample length. A transformed variant appears at most twice;
a family has two to six returns depending on song length, with complete clips
limited to two. Source selection, variants, sections and effective placement gains
are saved. The seed reproduces decisions; old recipes retain their saved layout.
[Synthetic before/after validation](sample-arrangements.md) shows the actual placements.
This is an inspectable heuristic arrangement, not a learned semantic composer or a
guarantee of musical harmony, sample identity or artistic quality. Key detection
and tempo estimation can be uncertain on speech or noisy recordings.

Phase-canceling stereo uses a recorded dominant-channel strategy for the guide;
original audio remains unchanged. Sample gain balancing is bounded to ±6 dB around
clip gain, and individual variants and the combined guide are attenuated if necessary
to retain a 0.8 peak ceiling. This protects against clipping without unlimited quiet
source/noise amplification. It does not make all recordings equally loud.

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

Lyrics/styles work without audio input. Expand **Write lyrics for me** to draft editable lyrics locally, or type your own and leave the field blank for an instrumental. See [local song planning](song-planning.md). The exact supplied lyrics reach the local
model. Blank titles derive from up to six lyric/style words. **Number of
Generations** defaults to two for fresh drafts, supports 1–32, and runs independent seeds
sequentially. Each song is separately cataloged; earlier successes remain if
another output fails or the request is canceled. Completed outputs are visible
while later outputs run. Model quality can repeat material or pronounce lyrics
imperfectly; this is documented rather than hidden by rewriting lyrics.

**More Options** is initially collapsed and contains only:

| Control         | Local mapping                                                                                                                                                                                                |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Vocal Gender    | Unset/Male/Female caption guidance for newly generated voices; a preference, not guaranteed classification or an effect on source recordings                                                                 |
| Duration        | Auto uses the optional local model planner before arranging samples and bounds its suggested length to 10–300 seconds; explicit lengths must be within that range |
| Weirdness       | 0–100 maps to schedule shift 1–5 with the supported ODE sampler throughout; independent of style guidance                                                                                                 |
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
Settings opens a Windows folder browser. If the current folder contains data,
choose to move it, use the selected folder without moving, or cancel. Moves use a
verified staging copy before switching locations and remove only unchanged managed
originals. Shared, changed and unrelated files remain; populated destinations are
not overwritten. Existing song playback links follow a successful library move.

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
