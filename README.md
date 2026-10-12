# musicmaker v1

Developer workflow, CI, OpenSpec and automated Windows releases:
[Development guide](docs/development.md). Repository owners should complete
[merge enforcement setup](docs/repository-settings.md).

A personal music maker: import voice recordings, tweak vocals, generate original beats,
mix any voice over any track, and remix saved mixes later. Everything is stored on disk
in a library folder with a catalog of "recipes", so any mix can be re-rendered or remixed.

## Easiest: Windows installer

Run **`MusicMaker-Setup.exe`**. Python is included and no admin rights are needed. It installs to
`%LOCALAPPDATA%\MusicMaker`, adds **Music Maker** to the Desktop and Start Menu, and keeps your files in
`Documents\MusicMaker\library` (set in `%LOCALAPPDATA%\MusicMaker\app\config.json`). The app opens in your browser
and has no console window. Use the **Quit Music Maker** button in Library inside AI Producer to stop it. Uninstall from
Settings > Apps or the Start Menu. Your library is kept. Command line: `%LOCALAPPDATA%\MusicMaker\mm.bat <command>`.
Windows SmartScreen may warn because the installer isn't code-signed. Click *More info > Run anyway*.

## Run from source

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Node.js
24.15 or newer. Source development targets Python 3.12, matching the embedded runtime;
uv can install that Python version automatically.

Windows: run **`scripts\launchers\start.bat`**. macOS/Linux: run
`bash scripts/launchers/start.sh` (or double-click `scripts/launchers/start.command`
on macOS). The launcher runs `uv sync --locked`, builds the Angular frontend if
missing, then starts FastAPI and opens **http://127.0.0.1:7860** (or the next free port).
The first setup needs internet. Leave the terminal open or use **Quit Music Maker**.
After frontend source changes, run `npm run build` before relaunching.
The Windows installer includes the compiled UI and Python; it needs neither uv nor Node.

You don't need to install ffmpeg separately. A copy comes with the `imageio-ffmpeg` package.

## Where your files live

By default everything goes in a `library` folder next to the app:

```
library/
  voices/      imported voice recordings + FX'd versions (wav)
  music/       imported music tracks (wav)
  generated/   beats made by the generator (wav)
  mixes/       mixes and remixes (wav + mp3)
  inbox/       drop recordings here, then click "Import everything in inbox/" (or `mm import --inbox`)
  catalog.json id, name, type, duration, source, created, tags, recipe (paths relative to library/)
```

### Configuration

Settings are looked up in this order: **environment variables > `config.local.json` > `config.json` > built-in defaults**.

| Setting | Env var | Default |
|---|---|---|
| `library_dir` | `MM_LIBRARY` | `library` (next to the app) |
| `host` | `MM_HOST` | `127.0.0.1` |
| `port` | `MM_PORT` | 7860, or the next free port |
| `ffmpeg` | `MM_FFMPEG` | bundled `imageio-ffmpeg`, else `ffmpeg` on PATH |

`config.local.json` is for machine-specific values (library location, port, build paths) and is gitignored.
Copy `config/config.local.example.json` to root `config.local.json`. `MM_CONFIG_DIR` changes where both config files are read from.
When you update the app, keep your library folder (or point `library_dir` at it).

## AI Producer (one vocal in, finished song out)

Open the **AI Producer** tab, pick a voice (or drop a recording) and click **PRODUCE MY SONG**, or on the command line:

```
mm produce user_vocal_1                      # everything automatic
mm produce my_take.m4a --mood chill          # import a file and produce it in one step
mm produce user_vocal_1 --style trap --bpm 92 --key "C minor" --seed 42 --tune off
mm analyze user_vocal_1                      # see what the producer hears
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
choices and seed. `mm remix <song> --music-vol -8` changes the balance and keeps the mastering.
`mm rerender <song>` re-runs the whole producer with the same seed and gives the same song.

## The web UI

- **Library (inside AI Producer)**: upload any audio (mp3, m4a, wav, ogg, opus, flac, webm, video files...), play items,
  tag/rename/delete, and view each item's catalog entry and recipe.
- **Voice FX**: pitch (semitones), time stretch, gain, low/high cut EQ, compression, chorus, robot,
  echo, reverb, trim silence, normalize. Use Preview, or save the result as a new voice.
- **Generator**: drums (boombap, hiphop, trap, house, rock, lofi), bassline and chord pad. Set the key
  (`A minor`, `C major`, `F#m`, `D dorian`), a roman-numeral progression (`i-VI-III-VII`), BPM, bars, swing and seed.
- **Mixer / Remix**: pick any voice and any music (imported, generated, or a previous mix). Set voice and music volume,
  offset, ducking, fades, looping, and optional render-time voice FX. Load a saved mix to change it and render a remix.

## Command line

Source: `uv run --locked python backend/cli.py <command>` or the wrappers in
`scripts/launchers/`. Installed Windows: `%LOCALAPPDATA%\MusicMaker\mm.bat <command>`.
You can refer to items by id, a unique id prefix, or exact name.

```
mm where                                   # show library + ffmpeg location
mm demo                                    # end-to-end self test
mm import rec1.m4a rec2.mp3 --type voice --tags take1
mm import mybeat.mp3 --type music --name "my beat"
mm import --inbox                          # import everything in library/inbox
mm list [--type voice|music|generated|mix] [--tag X] [--json]
mm show <id>                               # full catalog entry incl. recipe
mm voice-fx <voice> --pitch -2 --reverb 0.3 --low-cut 100 --compress --name myvoice_fx
    # also: --stretch 0.9 --gain 3 --high-cut 8000 --chorus 0.4 --robot 0.6 --robot-hz 110
    #       --delay 0.3 --delay-time 0.35 --delay-feedback 0.4 --room-size 0.7 --trim --no-normalize
mm generate --bpm 90 --key "A minor" --bars 8 --style boombap [--progression i-VI-III-VII] [--seed 42] [--swing 0.2]
mm mix <voice> <music> --voice-vol 0 --music-vol -3 --offset 4 --duck --duck-db 8 \
       --fade-in 1 --fade-out 2 --loop [--voice-fx '{"pitch":-2,"reverb":0.3}'] --name mymix
mm remix <mix> --music-vol -1 --offset 1.5 --duck-db 14 --voice-fx '{"robot":0.5}' [--voice <id>] [--music <id>]
mm rerender <id>                           # rebuild any generated/fx/mix item from its recipe
mm export <id> [--out DIR] [--formats mp3,wav] [--bitrate 256k]
mm tag <id> a,b   |  mm rename <id> "new name"  |  mm delete <id>
mm tts "some words"                        # test voice (espeak-ng if installed, otherwise a synthesized sung phrase)
```

Any setting can also be passed as `--set key=value` (for example `--set duck_threshold=-40`).
On Windows cmd, write JSON with escaped quotes: `--voice-fx "{\"pitch\":-2}"`.

## How recipes work

Each mix stores `voice_id`, `music_id`, and every setting. `remix` loads that recipe, applies your overrides
(you can even swap the voice or the music), renders a new mix, and records the `parent`. Generated beats store
their seed, so `rerender` reproduces them exactly.

## Building the Windows installer (from Linux)

Run `uv sync --locked`, `npm ci --ignore-scripts`, and `npm run build` first.
`scripts/windows/build.sh` makes a self-contained `MusicMaker-Setup.exe` with embedded
Python, locked Windows wheels, bundled ffmpeg and the compiled Angular UI. It needs
Linux `makensis` (`apt install nsis`), `curl` and `unzip`. No Windows machine is needed to build;
CI installs and functionally tests the result on Windows before any release.
Paths come from the `build` section of `config.local.json` (or `MM_BUILD_*` env vars):
`venv`, `work_dir`, `cache_dir`, `output`, `parts_dir` (optional 15 MB split), `python_embed_version`.
Installer target paths are in the `windows` section (`install_dir`, `library_dir`, as NSIS variables).
`scripts/windows/wine_test.sh` provides the original optional Wine smoke test.
Packaging assets are under `cicd/windows/`; installer versions come from semantic-release.

## Limitations (v1)

- The generator is simple pattern-based synthesis (no MIDI export, no melody line, no separate stems).
- The "robot" effect is a zero-phase robotizer, not a true carrier/modulator vocoder.
- There is no automatic tempo/key matching between a vocal and a track. Use offset, stretch and pitch by hand.
- One voice + one music track per mix. To stack more, mix a mix with another voice.
- AI Producer: it can't tell where words or beats fall, so phrases are placed by silence gaps. Free-tempo speech is placed line by line,
  not re-timed to the groove. Key detection on speech is unreliable, so spoken vocals get a beat rooted on the speaker's median pitch.
  Pitch correction is a gentle per-note nudge, not hard autotune. Style choice is a heuristic on energy and tempo.
- Pitch shift and time stretch quality is good for moderate amounts (about ±5 semitones, 0.75-1.3x).
