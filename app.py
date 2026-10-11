"""musicmaker web UI — run: .venv/bin/python app.py  (http://localhost:7860)"""
import argparse
import json
import os
import socket
import sys
import tempfile
import threading
import time
import webbrowser

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr

import mmcore as mm


def choices(types):
    return [(f"{i['name']}  [{i['type']}, {i['duration']:.1f}s]  ·{i['id']}", i["id"])
            for i in reversed(mm.list_items(types))]


def table():
    return [[i["id"], i["type"], i["name"], round(i["duration"], 2), ",".join(i.get("tags", [])),
             i["created"], i["source"]] for i in reversed(mm.list_items())]


VOICE_T, MUSIC_T, ANY_T = "voice", "music,generated,mix", "voice,music,generated,mix"


def refresh_all():
    return (table(), gr.update(choices=choices(ANY_T)), gr.update(choices=choices(VOICE_T)),
            gr.update(choices=choices(VOICE_T)), gr.update(choices=choices(MUSIC_T)),
            gr.update(choices=choices("mix")), gr.update(choices=choices(VOICE_T)))


def do_upload(files, type_, tags):
    if not files:
        return "No files.", *refresh_all()
    tags = [t.strip() for t in (tags or "").split(",") if t.strip()]
    msgs = []
    for f in files:
        path = f if isinstance(f, str) else f.name
        it = mm.import_file(path, type_, name=os.path.splitext(os.path.basename(path))[0], tags=tags)
        msgs.append(f"Imported {it['name']} ({it['id']}, {it['duration']:.1f}s)")
    return "\n".join(msgs), *refresh_all()


def do_import_inbox(type_):
    items = mm.import_paths([mm.INBOX], type_, move_from_inbox=True)
    return (f"Imported {len(items)} file(s) from {mm.INBOX}" if items else f"Inbox empty ({mm.INBOX})"), *refresh_all()


def preview(iid):
    if not iid:
        return None, ""
    it = mm.get_item(iid)
    return it["path"], json.dumps(it, indent=2)


def do_delete(iid):
    if not iid:
        return "Pick an item.", *refresh_all()
    it = mm.delete_item(iid)
    return f"Deleted {it['name']}", *refresh_all()


def do_tags(iid, tags, name):
    if not iid:
        return "Pick an item.", *refresh_all()
    f = {"tags": [t.strip() for t in tags.split(",") if t.strip()]}
    if name.strip():
        f["name"] = name.strip()
    mm.update_item(iid, **f)
    return "Updated.", *refresh_all()


FX_KEYS = ["trim", "pitch", "stretch", "gain", "low_cut", "high_cut", "compress", "comp_threshold", "comp_ratio",
           "chorus", "robot", "robot_hz", "delay", "delay_time", "delay_feedback", "reverb", "room_size", "normalize"]


def do_fx(vid, name, save, *vals):
    if not vid:
        return None, "Pick a voice.", *refresh_all()
    s = dict(zip(FX_KEYS, vals))
    if save:
        it = mm.voice_fx(vid, s, name=name or None)
        return it["path"], f"Saved new voice {it['name']} ({it['id']})", *refresh_all()
    audio = mm.apply_fx(mm.load_item(vid), s)
    p = os.path.join(tempfile.gettempdir(), "mm_fx_preview.wav")
    mm.save_wav(p, audio)
    return p, "Preview only (not saved)", *refresh_all()


def do_gen(bpm, style, key, prog, bars, swing, seed, drums, bass, pad, name):
    s = dict(bpm=bpm, style=style, key=key, progression=prog or None, bars=int(bars), swing=swing,
             seed=int(seed) if seed not in (None, "", -1) and int(seed) >= 0 else None,
             drums=drums, bass=bass, pad=pad)
    try:
        it = mm.generate(s, name=name or None)
    except ValueError as e:
        return None, str(e), *refresh_all()
    return it["path"], f"Generated {it['name']} ({it['id']}), seed={it['recipe']['settings']['seed']}, " \
                       f"progression={it['recipe']['settings']['progression']}", *refresh_all()


MIX_KEYS = ["voice_vol", "music_vol", "offset", "duck", "duck_db", "fade_in", "fade_out", "loop", "tail"]


def do_mix(vid, mid, name, fxjson, *vals):
    if not vid or not mid:
        return None, None, "Pick a voice and a music track.", *refresh_all()
    s = dict(zip(MIX_KEYS, vals))
    if fxjson and fxjson.strip():
        try:
            s["voice_fx"] = json.loads(fxjson)
        except Exception as e:
            return None, None, f"Bad voice FX JSON: {e}", *refresh_all()
    it = mm.mix(vid, mid, s, name=name or None)
    return it["path"], it["mp3"], f"Mixed {it['name']} ({it['id']})\nmp3: {it['mp3']}", *refresh_all()


def do_produce(vid, upload, style, mood, bpm, key, tune, seed, progress=gr.Progress()):
    if upload:
        path = upload if isinstance(upload, str) else upload.name
        progress(0.05, desc="Importing recording...")
        vid = mm.import_file(path, "voice", name=os.path.splitext(os.path.basename(path))[0])["id"]
    if not vid:
        return None, None, "Pick a voice or drop a recording first.", *refresh_all()
    steps = {"analyzing vocal...": 0.15, "generating beat...": 0.45, "mixing & mastering...": 0.75}
    def log(msg):
        progress(steps.get(msg, 0.5), desc=msg.capitalize() if msg in steps else msg)
    try:
        it = mm.produce(vid, style=None if style == "auto" else style, mood=None if mood == "auto" else mood,
                        bpm=float(bpm) if bpm else None, key=key.strip() or None, tune=tune,
                        seed=int(seed) if seed is not None and int(seed) >= 0 else None, log=log)
    except Exception as e:
        return None, None, f"Produce failed: {e}", *refresh_all()
    pr = it["recipe"]["produce"]; an, ch = pr["analysis"], pr["choices"]
    secs = " → ".join(f"{s['name']} ({s['bars']})" for s in pr["sections"])
    info = (f"**{it['name']}**: {it['duration']:.0f} s · {it['loudness_lufs']} LUFS · true peak {it['true_peak_db']} dBTP\n\n"
            f"| | |\n|---|---|\n| Style | **{ch['style']}** ({ch['style_source']}) |\n"
            f"| Tempo | **{ch['bpm']:g} BPM** ({ch['tempo_source']}) |\n| Key | **{ch['key']}** ({ch['key_source']}) |\n"
            f"| Chords | {ch['progression']} |\n| Vocal | {'sung' if an['sung'] else 'spoken / rap'}, {an['n_phrases']} phrases, "
            f"{an['active_seconds']} s active, {an['loudness_lufs']} LUFS raw |\n"
            f"| Pitch correction | {'on (' + str(len(pr['chain']['corrections_semitones'])) + ' notes nudged)' if pr['chain']['pitch_correction'] else 'off'} |\n"
            f"| Arrangement | {secs} |\n| Seed | {pr['params']['seed']} |\n\n"
            f"Saved to `{it['mp3']}`. To tweak levels or ducking, load it in the **Mixer / Remix** tab.")
    return it["path"], it["mp3"], info, *refresh_all()


def load_recipe(mix_id):
    if not mix_id:
        return [gr.update()] * (4 + len(MIX_KEYS))
    r = mm.get_item(mix_id)["recipe"]
    s = {**mm.MIX_DEFAULTS, **r["settings"]}
    fx = json.dumps(s["voice_fx"]) if s.get("voice_fx") else ""
    return [gr.update(value=r["voice_id"], choices=choices(VOICE_T)), gr.update(value=r["music_id"], choices=choices(MUSIC_T)),
            mm.get_item(mix_id)["name"] + "_remix", fx] + [s[k] for k in MIX_KEYS]


with gr.Blocks(title="musicmaker") as demo:
    gr.Markdown("# 🎛️ musicmaker\nImport voices & tracks · tweak vocals · generate beats · mix any voice over any track · remix saved recipes.")
    with gr.Tab("🎤 AI Producer"):
        gr.Markdown("### One vocal in, finished song out\nPick a recorded voice (or drop a file), hit **Produce**. "
                    "The producer analyzes tempo, key and phrasing, writes an original beat with intro, verses and outro, "
                    "cleans up and places your vocal on the beat, ducks the music under you and masters the song to about -14 LUFS. "
                    "Everything is offline and saved to your library as a remixable recipe.")
        with gr.Row():
            with gr.Column(scale=1):
                ap_voice = gr.Dropdown(choices=choices(VOICE_T), label="Voice from library")
                ap_upload = gr.File(label="...or drop a new recording (any format)", file_types=["audio", "video"])
                with gr.Accordion("Optional overrides", open=False):
                    ap_style = gr.Dropdown(["auto"] + list(mm.DRUM_STYLES), value="auto", label="Style")
                    ap_mood = gr.Dropdown(["auto", "chill", "sad", "dreamy", "classic", "groovy", "dark", "hype", "happy"],
                                          value="auto", label="Mood")
                    ap_bpm = gr.Number(0, label="BPM (0 = detect)", precision=1)
                    ap_key = gr.Textbox("", label="Key (blank = detect), e.g. A minor")
                    ap_tune = gr.Radio(["auto", "on", "off"], value="auto", label="Pitch correction")
                    ap_seed = gr.Number(-1, label="Seed (-1 = random; reuse a seed to reproduce)", precision=0)
                ap_btn = gr.Button("🎛️  PRODUCE MY SONG", variant="primary", size="lg")
            with gr.Column(scale=1):
                ap_audio = gr.Audio(type="filepath", label="Your song")
                ap_file = gr.File(label="Download MP3")
                ap_info = gr.Markdown()

        lib_tbl = gr.Dataframe(value=table(), headers=["id", "type", "name", "dur(s)", "tags", "created", "source"],
                               interactive=False, wrap=True)
        with gr.Row():
            with gr.Column():
                up_files = gr.File(file_count="multiple", label="Upload audio (any format)")
                up_type = gr.Radio(["voice", "music"], value="voice", label="Import as")
                up_tags = gr.Textbox(label="Tags (comma separated)")
                with gr.Row():
                    up_btn = gr.Button("Import uploads", variant="primary")
                    inbox_btn = gr.Button(f"Import everything in inbox/")
                up_msg = gr.Textbox(label="Status", lines=3)
            with gr.Column():
                lib_pick = gr.Dropdown(choices=choices(ANY_T), label="Select item")
                lib_audio = gr.Audio(type="filepath", label="Playback")
                with gr.Row():
                    lib_tags = gr.Textbox(label="Set tags"); lib_name = gr.Textbox(label="Rename")
                with gr.Row():
                    tag_btn = gr.Button("Save name/tags"); del_btn = gr.Button("Delete item", variant="stop")
                lib_json = gr.Code(language="json", label="Catalog entry / recipe")
        with gr.Row():
            refresh_btn = gr.Button("🔄 Refresh library")
            quit_btn = gr.Button("⏻ Quit Music Maker", variant="stop")
        gr.Markdown(f"Library folder: `{mm.LIB}`  ·  drop recordings into `{mm.INBOX}` and click *Import everything in inbox/*")

    with gr.Tab("Voice FX"):
        with gr.Row():
            with gr.Column():
                fx_voice = gr.Dropdown(choices=choices(VOICE_T), label="Voice")
                fx_src_audio = gr.Audio(type="filepath", label="Original")
                fx_trim = gr.Checkbox(label="Trim silence")
                fx_pitch = gr.Slider(-12, 12, 0, step=0.5, label="Pitch (semitones)")
                fx_stretch = gr.Slider(0.5, 2.0, 1.0, step=0.05, label="Time stretch (tempo factor, >1 faster)")
                fx_gain = gr.Slider(-24, 24, 0, step=0.5, label="Gain (dB)")
                with gr.Row():
                    fx_low = gr.Slider(0, 1000, 0, step=10, label="Low cut / high-pass Hz (0=off)")
                    fx_high = gr.Slider(0, 20000, 0, step=100, label="High cut / low-pass Hz (0=off)")
                with gr.Row():
                    fx_comp = gr.Checkbox(label="Compression")
                    fx_cthr = gr.Slider(-60, 0, -20, step=1, label="Comp threshold dB")
                    fx_crat = gr.Slider(1, 20, 4, step=0.5, label="Comp ratio")
            with gr.Column():
                fx_chorus = gr.Slider(0, 1, 0, step=0.05, label="Chorus mix")
                with gr.Row():
                    fx_robot = gr.Slider(0, 1, 0, step=0.05, label="Robot mix")
                    fx_rhz = gr.Slider(40, 400, 110, step=5, label="Robot pitch Hz")
                with gr.Row():
                    fx_delay = gr.Slider(0, 1, 0, step=0.05, label="Echo mix")
                    fx_dtime = gr.Slider(0.05, 1.5, 0.3, step=0.05, label="Echo time s")
                    fx_dfb = gr.Slider(0, 0.9, 0.35, step=0.05, label="Echo feedback")
                with gr.Row():
                    fx_rev = gr.Slider(0, 1, 0, step=0.05, label="Reverb wet")
                    fx_room = gr.Slider(0, 1, 0.6, step=0.05, label="Room size")
                fx_norm = gr.Checkbox(True, label="Normalize")
                fx_name = gr.Textbox(label="Name for saved voice (optional)")
                with gr.Row():
                    fx_prev = gr.Button("Preview"); fx_save = gr.Button("Apply & save as new voice", variant="primary")
                fx_out = gr.Audio(type="filepath", label="Result"); fx_msg = gr.Textbox(label="Status")

    with gr.Tab("Generator"):
        with gr.Row():
            with gr.Column():
                g_bpm = gr.Slider(60, 180, 90, step=1, label="BPM")
                g_style = gr.Dropdown(list(mm.DRUM_STYLES), value="boombap", label="Drum style")
                g_key = gr.Textbox("A minor", label="Key (e.g. A minor, C major, F#m, D dorian)")
                g_prog = gr.Textbox("", label="Progression (roman numerals, blank = default; e.g. i-VI-III-VII, I-V-vi-IV)")
                g_bars = gr.Slider(1, 64, 8, step=1, label="Length (bars)")
                g_swing = gr.Slider(0, 1, 0, step=0.05, label="Swing")
                g_seed = gr.Number(-1, label="Seed (-1 = random)", precision=0)
                with gr.Row():
                    g_drums = gr.Checkbox(True, label="Drums"); g_bass = gr.Checkbox(True, label="Bass"); g_pad = gr.Checkbox(True, label="Chord pad")
                g_name = gr.Textbox(label="Name (optional)")
                g_btn = gr.Button("Generate", variant="primary")
            with gr.Column():
                g_out = gr.Audio(type="filepath", label="Generated"); g_msg = gr.Textbox(label="Status")

    with gr.Tab("Mixer / Remix"):
        with gr.Row():
            with gr.Column():
                rm_pick = gr.Dropdown(choices=choices("mix"), label="Load a saved mix recipe to remix (optional)")
                m_voice = gr.Dropdown(choices=choices(VOICE_T), label="Voice")
                m_music = gr.Dropdown(choices=choices(MUSIC_T), label="Music (imported, generated, or a previous mix)")
                m_vv = gr.Slider(-30, 12, 0, step=0.5, label="Voice volume dB")
                m_mv = gr.Slider(-30, 12, -4, step=0.5, label="Music volume dB")
                m_off = gr.Slider(0, 60, 2, step=0.25, label="Voice offset (s)")
                with gr.Row():
                    m_duck = gr.Checkbox(True, label="Duck music under vocals")
                    m_dd = gr.Slider(0, 24, 8, step=0.5, label="Duck amount dB")
                with gr.Row():
                    m_fi = gr.Slider(0, 10, 1, step=0.25, label="Fade in s"); m_fo = gr.Slider(0, 10, 2, step=0.25, label="Fade out s")
                with gr.Row():
                    m_loop = gr.Checkbox(True, label="Loop music to fit"); m_tail = gr.Slider(0, 20, 2, step=0.5, label="Music tail after voice (s)")
                m_fx = gr.Textbox(label='Render-time voice FX JSON (optional), e.g. {"pitch": -2, "reverb": 0.3}')
                m_name = gr.Textbox(label="Mix name (optional)")
                m_btn = gr.Button("Render mix", variant="primary")
            with gr.Column():
                m_out = gr.Audio(type="filepath", label="Mix (wav)")
                m_mp3 = gr.File(label="MP3 download"); m_msg = gr.Textbox(label="Status", lines=3)

    refresh_outs = [lib_tbl, lib_pick, fx_voice, m_voice, m_music, rm_pick, ap_voice]
    up_btn.click(do_upload, [up_files, up_type, up_tags], [up_msg] + refresh_outs)
    inbox_btn.click(do_import_inbox, [up_type], [up_msg] + refresh_outs)
    refresh_btn.click(refresh_all, None, refresh_outs)

    def _quit():
        threading.Timer(0.8, lambda: os._exit(0)).start()
        return "Music Maker has stopped. You can close this browser tab."
    quit_btn.click(_quit, None, up_msg)
    lib_pick.change(preview, lib_pick, [lib_audio, lib_json])
    del_btn.click(do_delete, lib_pick, [up_msg] + refresh_outs)
    tag_btn.click(do_tags, [lib_pick, lib_tags, lib_name], [up_msg] + refresh_outs)
    fx_voice.change(lambda i: mm.get_item(i)["path"] if i else None, fx_voice, fx_src_audio)
    fx_inputs = [fx_trim, fx_pitch, fx_stretch, fx_gain, fx_low, fx_high, fx_comp, fx_cthr, fx_crat, fx_chorus,
                 fx_robot, fx_rhz, fx_delay, fx_dtime, fx_dfb, fx_rev, fx_room, fx_norm]
    fx_prev.click(lambda v, n, *a: do_fx(v, n, False, *a), [fx_voice, fx_name] + fx_inputs, [fx_out, fx_msg] + refresh_outs)
    fx_save.click(lambda v, n, *a: do_fx(v, n, True, *a), [fx_voice, fx_name] + fx_inputs, [fx_out, fx_msg] + refresh_outs)
    g_btn.click(do_gen, [g_bpm, g_style, g_key, g_prog, g_bars, g_swing, g_seed, g_drums, g_bass, g_pad, g_name],
                [g_out, g_msg] + refresh_outs)
    mix_inputs = [m_vv, m_mv, m_off, m_duck, m_dd, m_fi, m_fo, m_loop, m_tail]
    m_btn.click(do_mix, [m_voice, m_music, m_name, m_fx] + mix_inputs, [m_out, m_mp3, m_msg] + refresh_outs)
    ap_btn.click(do_produce, [ap_voice, ap_upload, ap_style, ap_mood, ap_bpm, ap_key, ap_tune, ap_seed],
                 [ap_audio, ap_file, ap_info] + refresh_outs)
    rm_pick.change(load_recipe, rm_pick, [m_voice, m_music, m_name, m_fx] + mix_inputs)

def _port_in_use(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sk:
        sk.settimeout(0.5)
        return sk.connect_ex((host, port)) == 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="musicmaker web UI")
    ap.add_argument("--host", default=str(mm.setting("host")),
                    help="default from MM_HOST / config.local.json / config.json, else 127.0.0.1")
    ap.add_argument("--port", type=int, default=int(mm.setting("port") or 0) or None,
                    help="default from MM_PORT / config files, else 7860 (or the next free port)")
    ap.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    a = ap.parse_args()
    if sys.stdout is None or sys.stderr is None:  # windowless launch (pythonw): log to a file
        log = open(mm.LIB / "musicmaker.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log
    # single instance: if Music Maker is already running on the default port, just open it
    if a.port is None and _port_in_use("127.0.0.1", 7860):
        try:
            import urllib.request
            body = urllib.request.urlopen("http://127.0.0.1:7860/", timeout=3).read(200000).decode("utf-8", "ignore")
            if "musicmaker" in body:
                print("Music Maker is already running; opening it.")
                if not a.no_browser:
                    webbrowser.open("http://127.0.0.1:7860/")
                sys.exit(0)
        except Exception:
            pass
    print(f"musicmaker {time.strftime('%Y-%m-%d %H:%M:%S')} library: {mm.LIB}")
    demo.queue().launch(server_name=a.host, server_port=a.port, inbrowser=not a.no_browser,
                        allowed_paths=[str(mm.LIB), tempfile.gettempdir()], show_error=True)
