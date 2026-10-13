# Command line and procedural production

The CLI shares the local DSP and portable catalog with the browser. Its
`generate` and `produce` commands synthesize procedural music on CPU; they do
not invoke ACE-Step or the browser’s three generation choices. Use
[Generation](song-workflows.md#generation) for model-generated songs or the
preserved-backing workflow. No model installation is needed for CLI DSP.

## Running commands

Source: `uv run --locked python backend/cli.py <command>` or the wrappers in
`scripts/launchers/`. Installed Windows: `%LOCALAPPDATA%\TrogloDAW\troglodaw.bat <command>`.
You can refer to items by id, a unique id prefix, or exact name.
Replace `<id>`, `<voice>` and similar placeholders with your item references.
Square brackets below indicate optional arguments; omit the brackets themselves.
`troglodaw` represents the source/installed invocation described above.

```
troglodaw where                                   # show library + ffmpeg location
troglodaw demo                                    # end-to-end self test
troglodaw import rec1.m4a rec2.mp3 --type voice --tags take1
troglodaw import mybeat.mp3 --type music --name "my beat"
troglodaw import --inbox                          # import everything in library/inbox
troglodaw list [--type voice|music|generated|mix] [--tag X] [--json]
troglodaw show <id>                               # full catalog entry incl. recipe
troglodaw voice-fx <voice> --pitch -2 --reverb 0.3 --low-cut 100 --compress --name myvoice_fx
    # also: --stretch 0.9 --gain 3 --high-cut 8000 --chorus 0.4 --robot 0.6 --robot-hz 110
    #       --delay 0.3 --delay-time 0.35 --delay-feedback 0.4 --room-size 0.7 --trim --no-normalize
troglodaw generate --bpm 90 --key "A minor" --bars 8 --style boombap [--progression i-VI-III-VII] [--seed 42] [--swing 0.2]
troglodaw mix <voice> <music> --voice-vol 0 --music-vol -3 --offset 4 --duck --duck-db 8 --fade-in 1 --fade-out 2 --loop [--voice-fx '{"pitch":-2,"reverb":0.3}'] --name mymix
troglodaw remix <mix> --music-vol -1 --offset 1.5 --duck-db 14 --voice-fx '{"robot":0.5}' [--voice <id>] [--music <id>]
troglodaw rerender <id>                           # rebuild any generated/fx/mix item from its recipe
troglodaw export <id> [--out DIR] [--formats mp3,wav] [--bitrate 256k]
troglodaw tag <id> a,b
troglodaw rename <id> "new name"
troglodaw delete <id>
troglodaw tts "some words"                        # test voice (espeak-ng if installed, otherwise a synthesized sung phrase)
```

The `voice-fx`, `generate`, `mix` and `remix` commands also accept `--set key=value` (for example `--set duck_threshold=-40`).
On Windows cmd, write JSON with escaped quotes: `--voice-fx "{\"pitch\":-2}"`.

## How recipes work

Legacy mixes store `voice_id`, `music_id`, and every setting. `remix` loads that recipe, applies your overrides
(you can even swap the voice or the music), renders a new mix, and records the `parent`. Generated beats store
their seed, so `rerender` reproduces them exactly. Browser-generated songs instead
retain the actual generated WAV, original inputs, transformed samples, timeline
placements, options and model identity. Rerendering uses saved assets offline;
running model inference again with the same seed does not promise identical audio.
Vocal FX recipes retain their source and cached unprocessed vocals so edits do not
repeatedly bake previous effects into the audio.

## Procedural producer: one vocal in, finished song out

The retained procedural producer is available on the command line:

```
troglodaw produce user_vocal_1                      # everything automatic
troglodaw produce my_take.m4a --mood chill          # import a file and produce it in one step
troglodaw produce user_vocal_1 --style trap --bpm 92 --key "C minor" --seed 42 --tune off
troglodaw analyze user_vocal_1                      # see what the producer hears
```

What it does, all offline with no API key (numpy/scipy/pedalboard):

1. **Analysis**:
   - tempo from onset-strength autocorrelation (spoken/rap vocals fold into 80-100 BPM, default 90)
   - sung vs spoken detection, f0 tracking and key estimation (Krumhansl-Schmuckler), with a reliability flag
   - silence-based phrase detection, BS.1770 loudness and an energy score
2. **Style and beat**:
   - style comes from energy (calm → lofi/ambient, mid → boombap, high → trap) unless you set a mood or style
   - an original beat in the chosen tempo/key with an intro (pad and hats), alternating verse A/B sections with crashes and fills, and a half-time outro
3. **Vocal chain**:
   - high-pass, noise gate, EQ, two-stage compression, normalize, light reverb and delay
   - gentle per-note pitch correction toward the key, only when the vocal is sung and the key is reliable (or `--tune on`)
4. **Arrangement**: phrases are grouped into 1-3 bar lines (chosen to minimise dead air) and each line starts on a downbeat after the intro. The music ducks under the vocal.
5. **Mastering**: bus compression and limiting to -14 LUFS integrated, with a true-peak ceiling of -1 dBTP (4x oversampled check). Output is wav + mp3 in `library/mixes`.

Each song is saved as a normal mix recipe (processed vocal + generated beat + settings + mastering) plus the full analysis,
choices and seed. `troglodaw remix <song> --music-vol -8` changes the balance and keeps the mastering.
`troglodaw rerender <song>` re-runs the whole producer with the same seed and gives the same song.

## Limits

Style and placement use energy, tempo, key estimates and silence gaps. The
producer does not understand words or beat boundaries; free-tempo speech is
placed line by line rather than retimed to the groove. Speech key detection is
unreliable, and pitch correction is a gentle per-note nudge. Legacy mixes accept
one voice and one music track; another mix can add another voice. The robot
effect is a zero-phase robotizer. Moderate pitch/time changes work best
(roughly ±5 semitones and 0.75–1.3× speed).
