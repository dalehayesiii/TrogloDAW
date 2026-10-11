"""mm — musicmaker command line."""
import argparse
import json
import sys

import mmcore as mm


def _val(v):
    try:
        return json.loads(v)
    except Exception:
        low = v.lower()
        if low in ("true", "yes", "on"): return True
        if low in ("false", "no", "off"): return False
        if low in ("none", "null"): return None
        return v


def _sets(pairs):
    out = {}
    for p in pairs or []:
        if "=" not in p:
            sys.exit(f"--set expects key=value, got '{p}'")
        k, v = p.split("=", 1)
        out[k.strip().replace("-", "_")] = _val(v)
    return out


def _flags(ns, keys):
    return {k: getattr(ns, k) for k in keys if getattr(ns, k, None) is not None}


def _show(item):
    print(f"{item['id']}  [{item['type']}]  {item['name']}  {item['duration']:.2f}s")
    print(f"  wav: {item['path']}")
    if item.get("mp3"):
        print(f"  mp3: {item['mp3']}")


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):  # Windows consoles: never crash on non-ASCII names
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(prog="mm", description="Personal music maker")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("import", help="import audio files/dirs (any format) into the library")
    p.add_argument("paths", nargs="*")
    p.add_argument("--type", default="voice", choices=list(mm.TYPE_DIRS))
    p.add_argument("--name"); p.add_argument("--tags", default="")
    p.add_argument("--inbox", action="store_true", help=f"import everything in {mm.INBOX} and move originals to inbox/imported")

    p = sub.add_parser("list", help="list library"); p.add_argument("--type"); p.add_argument("--tag")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("show", help="show an item incl. recipe"); p.add_argument("id")

    p = sub.add_parser("voice-fx", help="apply vocal effects -> new voice item")
    p.add_argument("id")
    p.add_argument("--pitch", type=float, help="semitones"); p.add_argument("--stretch", type=float, help="tempo factor (>1 faster)")
    p.add_argument("--gain", type=float, help="dB"); p.add_argument("--reverb", type=float, help="wet 0..1")
    p.add_argument("--room-size", dest="room_size", type=float)
    p.add_argument("--delay", type=float, help="echo mix 0..1"); p.add_argument("--delay-time", dest="delay_time", type=float)
    p.add_argument("--delay-feedback", dest="delay_feedback", type=float)
    p.add_argument("--low-cut", dest="low_cut", type=float, help="high-pass Hz"); p.add_argument("--high-cut", dest="high_cut", type=float, help="low-pass Hz")
    p.add_argument("--compress", action="store_true", default=None); p.add_argument("--comp-threshold", dest="comp_threshold", type=float)
    p.add_argument("--comp-ratio", dest="comp_ratio", type=float)
    p.add_argument("--chorus", type=float, help="mix 0..1"); p.add_argument("--robot", type=float, help="mix 0..1")
    p.add_argument("--robot-hz", dest="robot_hz", type=float)
    p.add_argument("--trim", action="store_true", default=None, help="trim leading/trailing silence")
    p.add_argument("--no-normalize", dest="normalize", action="store_false", default=None)
    p.add_argument("--set", action="append", metavar="KEY=VAL"); p.add_argument("--name")

    p = sub.add_parser("generate", help="generate original beat/bass/pad")
    p.add_argument("--bpm", type=float, default=90); p.add_argument("--style", default="boombap", choices=list(mm.DRUM_STYLES))
    p.add_argument("--key", default="A minor"); p.add_argument("--progression", help="e.g. i-VI-III-VII")
    p.add_argument("--bars", type=int, default=8); p.add_argument("--swing", type=float, default=0.0)
    p.add_argument("--seed", type=int); p.add_argument("--no-drums", dest="drums", action="store_false")
    p.add_argument("--no-bass", dest="bass", action="store_false"); p.add_argument("--no-pad", dest="pad", action="store_false")
    p.add_argument("--name"); p.add_argument("--set", action="append", metavar="KEY=VAL")

    mixkeys = ["voice_vol", "music_vol", "offset", "duck", "duck_db", "fade_in", "fade_out", "loop", "tail", "length"]

    def add_mix_flags(p):
        p.add_argument("--voice-vol", dest="voice_vol", type=float, help="dB")
        p.add_argument("--music-vol", dest="music_vol", type=float, help="dB")
        p.add_argument("--offset", type=float, help="seconds before voice starts")
        p.add_argument("--duck", dest="duck", action="store_true", default=None)
        p.add_argument("--no-duck", dest="duck", action="store_false")
        p.add_argument("--duck-db", dest="duck_db", type=float)
        p.add_argument("--fade-in", dest="fade_in", type=float); p.add_argument("--fade-out", dest="fade_out", type=float)
        p.add_argument("--loop", dest="loop", action="store_true", default=None)
        p.add_argument("--no-loop", dest="loop", action="store_false")
        p.add_argument("--tail", type=float); p.add_argument("--length", type=float)
        p.add_argument("--voice-fx", dest="voice_fx_json", help='JSON FX applied at render, e.g. \'{"pitch":-2,"reverb":0.3}\'')
        p.add_argument("--set", action="append", metavar="KEY=VAL"); p.add_argument("--name")

    p = sub.add_parser("mix", help="mix a voice over a music track"); p.add_argument("voice"); p.add_argument("music")
    add_mix_flags(p)
    p = sub.add_parser("remix", help="re-render a saved mix recipe with overrides"); p.add_argument("mix_id")
    p.add_argument("--voice", help="swap in a different voice id"); p.add_argument("--music", help="swap in a different music id")
    add_mix_flags(p)

    p = sub.add_parser("rerender", help="re-create any item from its recipe"); p.add_argument("id")
    p = sub.add_parser("export", help="export item to mp3+wav"); p.add_argument("id")
    p.add_argument("--out", help="output dir (default: item's library folder)"); p.add_argument("--formats", default="mp3,wav")
    p.add_argument("--bitrate", default="192k")
    p = sub.add_parser("produce", help="AI Producer: make a finished, mastered song from one voice (id or audio file)")
    p.add_argument("voice", help="voice id/name, or a path to an audio file to import first")
    p.add_argument("--style", choices=["auto"] + list(mm.DRUM_STYLES), default="auto")
    p.add_argument("--bpm", type=float); p.add_argument("--key", help="e.g. 'A minor' (default: detect)")
    p.add_argument("--mood", help="chill, sad, dark, hype, happy, dreamy, classic, groovy ...")
    p.add_argument("--seed", type=int); p.add_argument("--tune", choices=["auto", "on", "off"], default="auto",
                   help="gentle pitch correction (auto = only for sung vocals with a reliable key)")
    p.add_argument("--lufs", type=float, default=-14.0, help="master loudness target"); p.add_argument("--name")
    p = sub.add_parser("analyze", help="analyze a voice: tempo, key, phrases, loudness, sung/spoken")
    p.add_argument("voice"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("demo", help="run the end-to-end self test (voice, FX, 90 BPM A-minor beat, ducked mix, remix)")
    p = sub.add_parser("where", help="show library location and ffmpeg in use")
    p = sub.add_parser("tts", help="make a test voice (espeak-ng if installed, else synthesized)"); p.add_argument("text"); p.add_argument("--name", default="tts_voice")
    p.add_argument("--voice", default="en-us"); p.add_argument("--speed", type=int, default=150); p.add_argument("--pitch", type=int, default=50)
    p = sub.add_parser("tag", help="set tags"); p.add_argument("id"); p.add_argument("tags", help="comma separated")
    p = sub.add_parser("rename", help="rename"); p.add_argument("id"); p.add_argument("name")
    p = sub.add_parser("delete", help="remove item and its files"); p.add_argument("id")

    a = ap.parse_args(argv)
    try:
        if a.cmd == "import":
            tags = [t for t in a.tags.split(",") if t]
            if a.inbox:
                items = mm.import_paths([mm.INBOX], a.type, tags, move_from_inbox=True)
            elif a.name and len(a.paths) == 1:
                items = [mm.import_file(a.paths[0], a.type, a.name, tags)]
            else:
                items = mm.import_paths(a.paths, a.type, tags)
            if not items:
                print("nothing imported")
            for it in items: _show(it)
        elif a.cmd == "list":
            items = mm.list_items(a.type, a.tag)
            if a.json:
                print(json.dumps(items, indent=2)); return
            for it in items:
                print(f"{it['id']}  {it['type']:<9} {it['duration']:7.2f}s  {it['name']:<40} {','.join(it.get('tags', []))}")
            print(f"({len(items)} items)")
        elif a.cmd == "show":
            print(json.dumps(mm.get_item(a.id), indent=2))
        elif a.cmd == "voice-fx":
            s = _flags(a, list(mm.FX_DEFAULTS)); s.update(_sets(a.set))
            _show(mm.voice_fx(a.id, s, name=a.name))
        elif a.cmd == "generate":
            s = {k: getattr(a, k) for k in ["bpm", "style", "key", "progression", "bars", "swing", "seed", "drums", "bass", "pad"]}
            s.update(_sets(a.set)); _show(mm.generate(s, name=a.name))
        elif a.cmd in ("mix", "remix"):
            s = _flags(a, mixkeys)
            if a.voice_fx_json: s["voice_fx"] = json.loads(a.voice_fx_json)
            s.update(_sets(a.set))
            if a.cmd == "mix":
                _show(mm.mix(a.voice, a.music, s, name=a.name))
            else:
                _show(mm.remix(a.mix_id, s, voice_ref=a.voice, music_ref=a.music, name=a.name))
        elif a.cmd == "rerender":
            _show(mm.rerender(a.id))
        elif a.cmd == "export":
            for pth in mm.export(a.id, a.out, a.formats.split(","), a.bitrate): print(pth)
        elif a.cmd == "produce":
            import os
            ref = a.voice
            if os.path.isfile(ref):
                ref = mm.import_file(ref, "voice")["id"]
            it = mm.produce(ref, style=None if a.style == "auto" else a.style, bpm=a.bpm, key=a.key, mood=a.mood,
                            seed=a.seed, tune=a.tune, name=a.name, target_lufs=a.lufs, log=lambda s: print("..", s))
            ch = it["recipe"]["produce"]["choices"]
            print(f"style {ch['style']} ({ch['style_source']}), {ch['bpm']:g} BPM ({ch['tempo_source']}), "
                  f"key {ch['key']} ({ch['key_source']}), progression {ch['progression']}")
            print(f"loudness {it['loudness_lufs']} LUFS, true peak {it['true_peak_db']} dBTP, seed "
                  f"{it['recipe']['produce']['params']['seed']}")
            _show(it)
        elif a.cmd == "analyze":
            an = mm.analyze_vocal(mm.load_item(a.voice))
            if a.json:
                print(json.dumps(an, indent=2))
            else:
                ch = mm.choose_production(an)
                for k in ["duration", "active_seconds", "n_phrases", "sung", "voiced_ratio", "median_pitch_hz",
                          "tempo_raw", "tempo_confidence", "onset_rate", "key_detected", "key_confidence",
                          "key_reliable", "key_candidates", "tuning_offset_semitones", "loudness_lufs",
                          "spectral_centroid_hz"]:
                    print(f"{k:24} {an[k]}")
                print(f"{'-> would choose':24} {ch['style']} @ {ch['bpm']:g} BPM in {ch['key']} ({ch['style_source']}; "
                      f"{ch['tempo_source']}; {ch['key_source']})")
        elif a.cmd == "demo":
            mm.run_demo()
        elif a.cmd == "where":
            print(f"app:     {mm.APP_DIR}\nlibrary: {mm.LIB}\ninbox:   {mm.INBOX}\nffmpeg:  {mm.ffmpeg_exe()}")
        elif a.cmd == "tts":
            _show(mm.tts(a.text, a.name, a.voice, a.speed, a.pitch))
        elif a.cmd == "tag":
            _show(mm.update_item(a.id, tags=[t for t in a.tags.split(",") if t]))
        elif a.cmd == "rename":
            _show(mm.update_item(a.id, name=a.name))
        elif a.cmd == "delete":
            it = mm.delete_item(a.id); print(f"deleted {it['id']} {it['name']}")
    except (KeyError, ValueError, RuntimeError) as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
