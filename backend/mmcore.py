"""musicmaker core: library/catalog, import, voice FX, generator, mixer, remix, export.

Internal audio format: float32 numpy array shaped (samples, 2), 44.1 kHz stereo.
"""
from __future__ import annotations

import copy
import importlib
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from scipy import signal

SR = 44100
APP_DIR = Path(__file__).resolve().parents[1]


CONFIG_DIR = Path(os.environ.get("MM_CONFIG_DIR") or APP_DIR)


def _read_json(path: Path) -> dict:
    """Read a JSON config file; tolerant of UTF-8/UTF-16 (the Windows installer writes UTF-16) and ANSI."""
    if not path.exists():
        return {}
    raw = path.read_bytes()
    for enc in (("utf-16",) if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else ("utf-8-sig", "mbcs", "latin-1")):
        try:
            data = json.loads(raw.decode(enc))
            return data if isinstance(data, dict) else {}
        except Exception:
            continue
    return {}


def _load_config() -> dict:
    """Settings precedence: environment variables > config.local.json > config.json > built-in defaults.
    config.local.json is for machine-specific values and is never committed (see .gitignore)."""
    cfg = {}
    for name in ("config.json", "config.local.json"):
        for k, v in _read_json(CONFIG_DIR / name).items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k] = {**cfg[k], **v}
            else:
                cfg[k] = v
    return cfg


CONFIG = _load_config()
ENV_VARS = {"library_dir": "MM_LIBRARY", "ffmpeg": "MM_FFMPEG", "host": "MM_HOST", "port": "MM_PORT"}
DEFAULTS = {"library_dir": "library", "ffmpeg": None, "host": "127.0.0.1", "port": None}


def setting(name: str, default=None):
    """Look up a runtime setting: env var > config.local.json > config.json > DEFAULTS/default."""
    env = ENV_VARS.get(name)
    if env and os.environ.get(env):
        return os.environ[env]
    if CONFIG.get(name) not in (None, ""):
        return CONFIG[name]
    return DEFAULTS.get(name, default) if default is None else default


_lib = Path(os.path.expandvars(os.path.expanduser(str(setting("library_dir")))))
LIB = (_lib if _lib.is_absolute() else APP_DIR / _lib).resolve()
INBOX = LIB / "inbox"
CATALOG = LIB / "catalog.json"


def ffmpeg_exe() -> str:
    """Bundled ffmpeg (imageio-ffmpeg, has Windows/macOS/Linux binaries) or one on PATH."""
    if setting("ffmpeg"):
        return str(setting("ffmpeg"))
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        exe = shutil.which("ffmpeg")
        if exe:
            return exe
        raise RuntimeError("ffmpeg not found: run 'pip install imageio-ffmpeg' or install ffmpeg")


_CREATIONFLAGS = 0x08000000 if os.name == "nt" else 0  # no console flash on Windows


def _run_ffmpeg(args):
    r = subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", *map(str, args)],
                       capture_output=True, text=True, creationflags=_CREATIONFLAGS)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr.strip()}")
    return r
TYPE_DIRS = {"voice": "voices", "music": "music", "generated": "generated", "mix": "mixes"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".flac", ".webm",
              ".wma", ".aiff", ".aif", ".amr", ".3gp", ".mp4", ".mov", ".mkv", ".caf"}

for d in list(TYPE_DIRS.values()):
    (LIB / d).mkdir(parents=True, exist_ok=True)
INBOX.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------------------------- catalog
import threading
_TLOCK = threading.RLock()


@contextmanager
def _file_lock():
    """Cross-process lock: fcntl on macOS/Linux, msvcrt on Windows."""
    f = open(str(CATALOG) + ".lock", "a+")
    try:
        if os.name == "nt":
            import msvcrt, time
            f.seek(0)
            for _ in range(200):
                try:
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1); break
                except OSError:
                    time.sleep(0.05)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt
                f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_UN)
        except OSError:
            pass
        f.close()


def _abs(item: dict) -> dict:
    """Catalog stores paths relative to the library so it can be moved/copied between machines."""
    it = dict(item)
    if it.get("file"):
        it["path"] = str(LIB / Path(it["file"]))
    if it.get("mp3_file"):
        it["mp3"] = str(LIB / Path(it["mp3_file"]))
    return it


def _rel(item: dict) -> dict:
    it = dict(item)
    for absk, relk in (("path", "file"), ("mp3", "mp3_file")):
        if it.get(absk):
            try:
                it[relk] = Path(it[absk]).resolve().relative_to(LIB).as_posix()
            except ValueError:
                it[relk] = it[absk]
            it.pop(absk)
    return it


@contextmanager
def _locked_catalog(write=False):
    with _TLOCK, _file_lock():
        data = json.loads(CATALOG.read_text(encoding="utf-8")) if CATALOG.exists() else {"items": []}
        data["items"] = [_abs(i) for i in data["items"]]
        yield data
        if write:
            out = {"version": 1, "items": [_rel(i) for i in data["items"]]}
            tmp = str(CATALOG) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2)
            os.replace(tmp, CATALOG)


def list_items(type_: str | None = None, tag: str | None = None) -> list[dict]:
    with _locked_catalog() as data:
        items = data["items"]
    if type_:
        types = {t.strip() for t in type_.split(",")}
        items = [i for i in items if i["type"] in types]
    if tag:
        items = [i for i in items if tag in i.get("tags", [])]
    return items


def get_item(ref: str) -> dict:
    """Look up by full id, id prefix, or exact name (latest wins)."""
    items = list_items()
    for i in items:
        if i["id"] == ref:
            return i
    pref = [i for i in items if i["id"].startswith(ref)]
    if len(pref) == 1:
        return pref[0]
    named = [i for i in items if i["name"] == ref]
    if named:
        return named[-1]
    if len(pref) > 1:
        raise KeyError(f"ambiguous id prefix '{ref}'")
    raise KeyError(f"no library item '{ref}'")


def _add_item(item: dict) -> dict:
    with _locked_catalog(write=True) as data:
        data["items"].append(item)
    return item


def update_item(ref: str, **fields) -> dict:
    it = get_item(ref)
    with _locked_catalog(write=True) as data:
        for i in data["items"]:
            if i["id"] == it["id"]:
                i.update(fields)
                it = i
    return it


def delete_item(ref: str, remove_file=True) -> dict:
    it = get_item(ref)
    with _locked_catalog(write=True) as data:
        data["items"] = [i for i in data["items"] if i["id"] != it["id"]]
    if remove_file:
        for p in [it.get("path"), it.get("mp3")]:
            if p and Path(p).exists():
                Path(p).unlink()
    return it


def _slug(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")
    return s[:60] or "audio"


def _new_entry(type_, name, audio, source, tags=None, recipe=None, extra=None) -> dict:
    iid = uuid.uuid4().hex[:10]
    path = LIB / TYPE_DIRS[type_] / f"{_slug(name)}_{iid}.wav"
    save_wav(path, audio)
    item = {
        "id": iid, "name": name, "type": type_, "path": str(path),
        "duration": round(len(audio) / SR, 3), "source": source,
        "created": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "tags": list(tags or []), "recipe": recipe,
    }
    if extra:
        item.update(extra)
    return _add_item(item)


# ----------------------------------------------------------------------------- audio io
def load(path) -> np.ndarray:
    a, sr = sf.read(str(path), dtype="float32", always_2d=True)
    if a.shape[1] == 1:
        a = np.repeat(a, 2, axis=1)
    elif a.shape[1] > 2:
        a = a[:, :2]
    if sr != SR:
        from math import gcd
        g = gcd(int(sr), SR)
        a = signal.resample_poly(a, SR // g, int(sr) // g, axis=0).astype(np.float32)
    return np.ascontiguousarray(a)


def load_item(ref) -> np.ndarray:
    return load(get_item(ref)["path"])


def save_wav(path, audio):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.clip(audio, -1, 1), SR, subtype="PCM_16")


def to_mp3(wav_path, mp3_path=None, bitrate="192k") -> str:
    mp3_path = str(mp3_path or Path(wav_path).with_suffix(".mp3"))
    _run_ffmpeg(["-i", wav_path, "-codec:a", "libmp3lame", "-b:a", bitrate, mp3_path])
    return mp3_path


def decode_any(path) -> np.ndarray:
    """Decode any ffmpeg-readable file (audio or video w/ audio) to our format."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "x.wav"
        try:
            _run_ffmpeg(["-i", path, "-vn", "-ac", "2", "-ar", SR, "-c:a", "pcm_f32le", out])
        except RuntimeError as e:
            raise RuntimeError(f"could not decode {path}: {e}")
        return load(out)


def db(x):
    return 10 ** (x / 20.0)


def normalize(a, peak_db=-1.0):
    m = float(np.max(np.abs(a))) if a.size else 0.0
    return a if m < 1e-9 else (a * (db(peak_db) / m)).astype(np.float32)


def trim_silence(a, top_db=40.0, pad=0.05):
    """Trim leading/trailing audio quieter than (peak - top_db), using 20 ms RMS frames."""
    mono = a.mean(axis=1)
    hop = int(0.02 * SR)
    n = len(mono) // hop
    if n < 2:
        return a
    rms = np.sqrt((mono[: n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12)
    rdb = 20 * np.log10(rms / rms.max())
    idx = np.where(rdb > -top_db)[0]
    if not len(idx):
        return a
    p = int(pad * SR)
    return a[max(0, idx[0] * hop - p): min(len(a), (idx[-1] + 1) * hop + p)]


def fade(a, fade_in=0.0, fade_out=0.0):
    a = a.copy()
    n_in, n_out = int(fade_in * SR), int(fade_out * SR)
    if n_in > 0:
        n_in = min(n_in, len(a))
        a[:n_in] *= np.linspace(0, 1, n_in, dtype=np.float32)[:, None]
    if n_out > 0:
        n_out = min(n_out, len(a))
        a[len(a) - n_out:] *= np.linspace(1, 0, n_out, dtype=np.float32)[:, None]
    return a


# ----------------------------------------------------------------------------- import
def import_file(path, type_="voice", name=None, tags=None, norm=True) -> dict:
    path = Path(path)
    if type_ not in TYPE_DIRS:
        raise ValueError(f"type must be one of {list(TYPE_DIRS)}")
    audio = decode_any(path)
    if norm:
        audio = normalize(audio, -1.0)
    return _new_entry(type_, name or path.stem, audio, source=f"import:{path.resolve()}",
                      tags=tags, recipe={"op": "import", "original": str(path.resolve()),
                                         "normalized": norm})


def import_paths(paths, type_="voice", tags=None, move_from_inbox=False) -> list[dict]:
    out = []
    for p in paths:
        p = Path(p)
        files = sorted(f for f in p.rglob("*") if f.suffix.lower() in AUDIO_EXTS) if p.is_dir() else [p]
        for f in files:
            if "imported" in f.parts:
                continue
            out.append(import_file(f, type_, tags=tags))
            if move_from_inbox:
                dest = INBOX / "imported"
                dest.mkdir(exist_ok=True)
                shutil.move(str(f), dest / f.name)
    return out


# ----------------------------------------------------------------------------- voice fx
FX_DEFAULTS = {
    "trim": False, "trim_db": 40.0,
    "pitch": 0.0,            # semitones
    "stretch": 1.0,          # >1 = faster/shorter, <1 = slower/longer (tempo factor)
    "low_cut": 0.0,          # Hz high-pass (0=off)
    "high_cut": 0.0,         # Hz low-pass (0=off)
    "compress": False, "comp_threshold": -20.0, "comp_ratio": 4.0,
    "chorus": 0.0,           # mix 0..1
    "robot": 0.0,            # mix 0..1
    "robot_hz": 110.0,       # robot buzz pitch
    "delay": 0.0,            # mix 0..1
    "delay_time": 0.3, "delay_feedback": 0.35,
    "reverb": 0.0,           # wet 0..1
    "room_size": 0.6,
    "gain": 0.0,             # dB
    "normalize": True,
}


def _robotize(a, mix, hz):
    """Phase-vocoder robotization (zero phase, hop sets buzz pitch) + light ring mod."""
    hop = max(64, int(SR / max(hz, 20)))
    nfft = 1024 if hop < 512 else 2048
    out = np.zeros_like(a)
    for ch in range(a.shape[1]):
        _, _, Z = signal.stft(a[:, ch], SR, nperseg=nfft, noverlap=nfft - hop)
        _, y = signal.istft(np.abs(Z), SR, nperseg=nfft, noverlap=nfft - hop)
        y = y[:len(a)]
        out[:len(y), ch] = y
    t = np.arange(len(a)) / SR
    ring = out * (0.6 + 0.4 * np.sin(2 * np.pi * hz * 0.5 * t))[:, None]
    ring = normalize(ring, -1.0) * (np.max(np.abs(a)) + 1e-9)
    return ((1 - mix) * a + mix * ring).astype(np.float32)


def apply_fx(audio: np.ndarray, settings: dict) -> np.ndarray:
    import pedalboard as pb
    s = {**FX_DEFAULTS, **(settings or {})}
    a = audio.astype(np.float32)
    if s["trim"]:
        a = trim_silence(a, s["trim_db"])
    if abs(s["stretch"] - 1.0) > 1e-3:
        try:
            a = pb.time_stretch(a.T.copy(), SR, stretch_factor=float(s["stretch"])).T
        except Exception:  # optional fallback if pedalboard's stretcher is unavailable
            librosa = importlib.import_module("librosa")  # optional fallback, not a required dependency
            a = np.stack([librosa.effects.time_stretch(a[:, c], rate=s["stretch"]) for c in range(2)], 1)
        a = np.ascontiguousarray(a, dtype=np.float32)
    if abs(s["pitch"]) > 1e-3:
        a = pb.Pedalboard([pb.PitchShift(semitones=float(s["pitch"]))])(a.T.copy(), SR).T
    chain: list[pb.Plugin] = []
    if s["low_cut"] and s["low_cut"] > 0:
        chain.append(pb.HighpassFilter(cutoff_frequency_hz=float(s["low_cut"])))
    if s["high_cut"] and s["high_cut"] > 0:
        chain.append(pb.LowpassFilter(cutoff_frequency_hz=float(s["high_cut"])))
    if s["compress"]:
        chain.append(pb.Compressor(threshold_db=float(s["comp_threshold"]), ratio=float(s["comp_ratio"]),
                                   attack_ms=5, release_ms=120))
    if chain:
        a = pb.Pedalboard(chain)(np.ascontiguousarray(a.T), SR).T
    a = np.ascontiguousarray(a, dtype=np.float32)
    if s["robot"] > 0:
        a = _robotize(a, float(s["robot"]), float(s["robot_hz"]))
    tail: list[pb.Plugin] = []
    if s["chorus"] > 0:
        tail.append(pb.Chorus(rate_hz=1.2, depth=0.3, centre_delay_ms=8, feedback=0.1, mix=float(s["chorus"])))
    if s["delay"] > 0:
        tail.append(pb.Delay(delay_seconds=float(s["delay_time"]), feedback=float(s["delay_feedback"]),
                             mix=float(s["delay"])))
    if s["reverb"] > 0:
        tail.append(pb.Reverb(room_size=float(s["room_size"]), wet_level=float(s["reverb"]),
                              dry_level=1.0 - 0.4 * float(s["reverb"]), width=1.0))
    if tail:
        # pad so delay/reverb tails aren't cut off
        pad = np.zeros((int(SR * (1.5 + 3 * s["delay_time"] * (s["delay"] > 0))), 2), np.float32)
        a = pb.Pedalboard(tail)(np.ascontiguousarray(np.vstack([a, pad]).T), SR).T
        a = trim_end_silence(np.ascontiguousarray(a, dtype=np.float32))
    if s["gain"]:
        a = a * db(float(s["gain"]))
    if s["normalize"]:
        a = normalize(a, -1.0)
    return np.ascontiguousarray(a, dtype=np.float32)


def trim_end_silence(a, thresh_db=-60.0):
    mag = np.max(np.abs(a), axis=1)
    idx = np.where(mag > db(thresh_db))[0]
    return a[: idx[-1] + 1] if len(idx) else a


def voice_fx(ref, settings: dict, name=None, tags=None) -> dict:
    src = get_item(ref)
    out = apply_fx(load(src["path"]), settings)
    return _new_entry("voice", name or f"{src['name']}_fx", out, source=f"fx:{src['id']}",
                      tags=(tags or []) + ["fx"],
                      recipe={"op": "voice-fx", "source_id": src["id"],
                              "settings": {**FX_DEFAULTS, **settings}})


# ----------------------------------------------------------------------------- generator
NOTE_IDX = {"C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4, "F": 5, "F#": 6, "GB": 6,
            "G": 7, "G#": 8, "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11}
SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10],
          "dorian": [0, 2, 3, 5, 7, 9, 10], "mixolydian": [0, 2, 4, 5, 7, 9, 10]}
ROMAN = {"I": 0, "II": 1, "III": 2, "IV": 3, "V": 4, "VI": 5, "VII": 6}
DEFAULT_PROG = {"major": "I-V-vi-IV", "minor": "i-VI-III-VII", "dorian": "i-IV-i-VII",
                "mixolydian": "I-VII-IV-I"}
DRUM_STYLES = {
    # 16 steps per bar: K kick, S snare, H closed hat, O open hat (velocity via case not used)
    "boombap": {"K": "x.....x...x.....", "S": "....x.......x...", "H": "x.x.x.x.x.x.x.x.", "O": "................"},
    "hiphop":  {"K": "x......x..x.....", "S": "....x.......x...", "H": "x.x.x.x.x.x.x.x.", "O": "..............x."},
    "trap":    {"K": "x......x..x...x.", "S": "........x.......", "H": "xxxxxxxxxxxxxxxx", "O": "................"},
    "house":   {"K": "x...x...x...x...", "S": "....x.......x...", "H": "..x...x...x...x.", "O": "..x...x...x...x."},
    "rock":    {"K": "x.....x.x.......", "S": "....x.......x...", "H": "x.x.x.x.x.x.x.x.", "O": "................"},
    "lofi":    {"K": "x.......x.x.....", "S": "....x.......x..x", "H": "x.xxx.x.x.xxx.x.", "O": "................"},
}


def parse_key(key: str):
    k = key.strip().replace("_", " ")
    m = re.match(r"^([A-Ga-g])([#b]?)\s*(m(?:in(?:or)?)?|maj(?:or)?|dorian|mixolydian)?$", k, re.I)
    if not m:
        raise ValueError(f"can't parse key '{key}' (try 'A minor', 'Am', 'C major', 'F#m')")
    root = NOTE_IDX[(m.group(1) + m.group(2)).upper()]
    q = (m.group(3) or "major").lower()
    mode = "minor" if q.startswith("m") and not q.startswith("maj") and q != "mixolydian" else \
        ("dorian" if q == "dorian" else "mixolydian" if q == "mixolydian" else "major")
    return root, mode


def chord_notes(root, mode, numeral):
    """Diatonic triad (plus optional '7') for a roman numeral; returns MIDI notes around C3/C4."""
    n = numeral.strip()
    seventh = n.endswith("7")
    n = n.rstrip("7").replace("°", "").replace("o", "")
    flat = n.startswith("b")
    n = n.lstrip("b#")
    deg = ROMAN[n.upper()]
    scale = SCALES[mode]
    tones = []
    for step in ([0, 2, 4, 6] if seventh else [0, 2, 4]):
        d = deg + step
        tones.append(scale[d % 7] + 12 * (d // 7))
    base = 48 + root  # C3-ish
    notes = [base + t - (1 if flat else 0) for t in tones]
    return notes


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _env(n, a=0.005, d=0.1, s=0.7, r=0.1):
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    ns = max(0, n - na - nd - nr)
    e = np.concatenate([np.linspace(0, 1, na, endpoint=False), np.linspace(1, s, nd, endpoint=False),
                        np.full(ns, s), np.linspace(s, 0, nr)])
    return np.pad(e, (0, max(0, n - len(e))))[:n].astype(np.float32)


def _kick(rng):
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 7) + 0.3 * np.exp(-t * 300) * rng.standard_normal(n) * 0.2
    return np.tanh(1.6 * x).astype(np.float32)


def _snare(rng):
    n = int(0.3 * SR); t = np.arange(n) / SR
    coefficients = signal.butter(2, [1500, 9000], "bandpass", fs=SR, output="ba")
    noise = signal.lfilter(coefficients[0], coefficients[1], rng.standard_normal(n))
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 25)
    return (0.75 * noise * np.exp(-t * 16) + 0.5 * tone).astype(np.float32) * 0.8


def _hat(rng, open_=False):
    n = int((0.35 if open_ else 0.06) * SR); t = np.arange(n) / SR
    coefficients = signal.butter(4, 7000, "highpass", fs=SR, output="ba")
    noise = signal.lfilter(coefficients[0], coefficients[1], rng.standard_normal(n))
    return (noise * np.exp(-t * (9 if open_ else 70))).astype(np.float32) * (0.35 if open_ else 0.3)


def _saw(freq, n, detune_cents=(0,)):
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for c in detune_cents:
        f = freq * 2 ** (c / 1200)
        out += (2 * ((t * f + np.random.rand()) % 1.0) - 1).astype(np.float32)
    return out / len(detune_cents)


def _place(buf, x, start, gain=1.0, pan=0.0):
    if start >= len(buf):
        return
    end = min(len(buf), start + len(x))
    seg = x[: end - start] * gain
    buf[start:end, 0] += seg * np.sqrt(0.5 * (1 - pan))
    buf[start:end, 1] += seg * np.sqrt(0.5 * (1 + pan))


GEN_DEFAULTS: dict[str, Any] = {"bpm": 90, "style": "boombap", "key": "A minor", "progression": None, "bars": 8,
                "drums": True, "bass": True, "pad": True, "swing": 0.0, "seed": None,
                "drum_vol": 0.0, "bass_vol": 0.0, "pad_vol": 0.0, "sections": None, "texture": None}

DRUM_STYLES["ambient"] = {"K": "x.........x.....", "S": "................", "H": "....x.......x...", "O": "................"}
# per-style "B" variations used by arrangements (extra kicks / hats)
DRUM_VARIANTS = {
    "boombap": {"K": "x.....x...x..x..", "O": "..............x."},
    "hiphop":  {"K": "x......x..x..x..", "O": "......x.......x."},
    "trap":    {"K": "x......x.xx...x.", "H": "xxxxxxxxxxxxx.xx"},
    "house":   {"O": "..x...x...x...xx"},
    "rock":    {"K": "x.....x.x.x.....", "O": "..............x."},
    "lofi":    {"K": "x.......x.x...x.", "O": "..............x."},
    "ambient": {"K": "x.......x.......", "H": "..x...x...x...x."},
}


def _crash(rng):
    n = int(1.6 * SR); t = np.arange(n) / SR
    coefficients = signal.butter(2, 4500, "highpass", fs=SR, output="ba")
    noise = signal.lfilter(coefficients[0], coefficients[1], rng.standard_normal(n))
    return (noise * np.exp(-t * 2.6)).astype(np.float32) * 0.22


def _expand_sections(sections, bars):
    """Return one dict per bar: drums ('full'|'half'|'hats'|'none'), bass, pad, fill, crash, variant."""
    if not sections:
        return [{"drums": "full", "bass": True, "pad": True, "fill": b % 4 == 3, "crash": False, "variant": 0,
                 "section": "main"} for b in range(bars)]
    plan = []
    for sec in sections:
        nb = int(sec["bars"])
        for j in range(nb):
            last = j == nb - 1
            plan.append({"drums": sec.get("drums", "full"), "bass": sec.get("bass", True), "pad": sec.get("pad", True),
                         "fill": last and sec.get("fill", True) and sec.get("drums", "full") in ("full", "half"),
                         "crash": j == 0 and sec.get("crash", False), "variant": int(sec.get("variant", 0)),
                         "section": sec.get("name", "")})
    return plan


def render_generated(settings: dict) -> np.ndarray:
    s = {**GEN_DEFAULTS, **settings}
    rng = np.random.default_rng(s["seed"])
    np.random.seed(int(rng.integers(0, 2**31)))
    bpm = float(s["bpm"])
    plan = _expand_sections(s.get("sections"), int(s["bars"]))
    bars = len(plan)
    root, mode = parse_key(s["key"])
    prog = [p for p in re.split(r"[-\s,|]+", s["progression"] or DEFAULT_PROG[mode]) if p]
    step = 60.0 / bpm / 4  # 16th note
    bar_len = int(round(16 * step * SR))
    total = bar_len * bars + int(2.0 * SR)
    drums = np.zeros((total, 2), np.float32)
    bass = np.zeros((total, 2), np.float32)
    pad = np.zeros((total, 2), np.float32)
    base_pat = DRUM_STYLES.get(s["style"], DRUM_STYLES["boombap"])
    var_pat = {**base_pat, **DRUM_VARIANTS.get(s["style"], {})}

    def step_start(bar, i):
        sw = s["swing"] * step * 0.5 if i % 2 == 1 else 0.0
        return int(round((bar * 16 + i) * step * SR + sw * SR))

    if s["drums"]:
        kick, snare, hat, ohat = _kick(rng), _snare(rng), _hat(rng), _hat(rng, True)
        crash = _crash(rng) if s.get("sections") else None
        for b in range(bars):
            pb_ = plan[b]
            mode_d = pb_["drums"]
            if mode_d == "none":
                continue
            pat = var_pat if pb_["variant"] else base_pat
            fill = pb_["fill"]
            if pb_["crash"] and crash is not None:
                _place(drums, crash, step_start(b, 0), 1.0, -0.2)
            for i in range(16):
                st = step_start(b, i)
                if mode_d in ("full", "half"):
                    if pat["K"][i] == "x" and (mode_d == "full" or i in (0, 8, 10)): _place(drums, kick, st, 1.0)
                    if mode_d == "full" and pat["S"][i] == "x" and not (fill and i >= 12 and s.get("sections")):
                        _place(drums, snare, st, 0.9, 0.05)
                    if mode_d == "half" and i == 8 and "x" in pat["S"]: _place(drums, snare, st, 0.8, 0.05)
                    if fill and i in (14, 15) and s["style"] != "house" and not s.get("sections"):
                        _place(drums, snare, st, 0.5, 0.05)
                    if fill and s.get("sections") and i >= 12 and s["style"] not in ("house", "ambient"):
                        _place(drums, snare, st, 0.35 + 0.12 * (i - 12), 0.05)  # 4-step snare build
                if pat["H"][i] == "x": _place(drums, hat, st, (0.7 + 0.3 * rng.random()) * (0.6 if mode_d == "hats" else 1.0), 0.3)
                if pat["O"][i] == "x" and mode_d != "hats": _place(drums, ohat, st, 0.6, 0.3)
    chords = [chord_notes(root, mode, prog[b % len(prog)]) for b in range(bars)]
    if s["bass"]:
        bass_rhythm = [(0, 3), (3, 3), (6, 2), (8, 4), (12, 2), (14, 2)]  # (step, len)
        if s["style"] in ("ambient",):
            bass_rhythm = [(0, 15)]
        elif s["style"] == "lofi":
            bass_rhythm = [(0, 6), (6, 2), (8, 6), (14, 2)]
        bfilt = signal.butter(2, 600, "lowpass", fs=SR, output="ba")
        for b, ch in enumerate(chords):
            if not plan[b]["bass"]:
                continue
            r = ch[0] - 12  # bass octave
            for k, (i, ln) in enumerate(bass_rhythm):
                note = r + (12 if (k == 4 and b % 2) else 0) + (7 if k == 3 and b % 2 == 0 else 0)
                n = int(ln * step * SR * 0.95)
                f = midi_hz(note)
                t = np.arange(n) / SR
                x = 0.6 * _saw(f, n) + 0.6 * np.sin(2 * np.pi * f * t)
                x = signal.lfilter(bfilt[0], bfilt[1], x).astype(np.float32) * _env(n, 0.004, 0.08, 0.6, 0.03)
                _place(bass, np.tanh(1.5 * x), step_start(b, i), 0.7)
    if s["pad"]:
        pfilt = signal.butter(2, 1800 if s["style"] != "lofi" else 1200, "lowpass", fs=SR, output="ba")
        for b, ch in enumerate(chords):
            if not plan[b]["pad"]:
                continue
            n = bar_len + int(0.3 * SR)
            x = np.zeros(n, np.float32)
            for j, note in enumerate(ch):
                x += _saw(midi_hz(note + 12), n, (-9, 0, 8))
            x = signal.lfilter(pfilt[0], pfilt[1], x).astype(np.float32) * _env(n, 0.25, 0.3, 0.75, 0.35)
            st = step_start(b, 0)
            end = min(total, st + n)
            # slow stereo spread
            pad[st:end, 0] += x[: end - st] * 0.17
            pad[st:end, 1] += np.roll(x, 300)[: end - st] * 0.17
    mix = drums * db(s["drum_vol"]) + bass * db(s["bass_vol"]) + pad * db(s["pad_vol"])
    if s.get("texture") == "vinyl":  # lofi crackle + hiss
        n = len(mix)
        crackle = (rng.random(n) > 0.9993).astype(np.float32) * rng.uniform(-0.25, 0.25, n).astype(np.float32)
        coefficients = signal.butter(1, 6000, "lowpass", fs=SR, output="ba")
        hiss = signal.lfilter(coefficients[0], coefficients[1], rng.standard_normal(n)).astype(np.float32) * 0.004
        mix += (crackle + hiss)[:, None]
    mix = mix[: bar_len * bars + int((1.5 if s.get("sections") else 0.5) * SR)]
    import pedalboard as pb
    mix = pb.Pedalboard([pb.Compressor(threshold_db=-14, ratio=2.5, attack_ms=10, release_ms=150),
                         pb.Limiter(threshold_db=-1.5)])(np.ascontiguousarray(mix.T), SR).T
    mix = fade(np.ascontiguousarray(mix, np.float32), 0.0, 0.4 if not s.get("sections") else 1.2)
    return normalize(mix, -1.0)


def generate(settings: dict, name=None, tags=None) -> dict:
    s = {**GEN_DEFAULTS, **settings}
    if s["seed"] is None:
        s["seed"] = int(np.random.default_rng().integers(0, 2**31))
    root, mode = parse_key(s["key"])
    s["progression"] = s["progression"] or DEFAULT_PROG[mode]
    if s.get("sections"):
        s["bars"] = sum(int(x["bars"]) for x in s["sections"])
    audio = render_generated(s)
    nm = name or f"{s['style']}_{int(s['bpm'])}bpm_{_slug(s['key'])}_{s['bars']}bars"
    return _new_entry("generated", nm, audio, source="generate",
                      tags=(tags or []) + [s["style"], s["key"]],
                      recipe={"op": "generate", "settings": s})


# ----------------------------------------------------------------------------- mixer
MIX_DEFAULTS: dict[str, Any] = {
    "voice_vol": 0.0,      # dB applied to voice
    "music_vol": -4.0,     # dB applied to music
    "offset": 2.0,         # seconds into the music where the voice starts
    "duck": True, "duck_db": 8.0, "duck_attack": 0.05, "duck_release": 0.4, "duck_threshold": -35.0,
    "fade_in": 1.0, "fade_out": 2.0,
    "loop": True,          # loop music to fit voice + offset + tail
    "tail": 2.0,           # seconds of music after the voice ends (when looping)
    "length": None,        # force total length in seconds (None = auto)
    "voice_fx": None,      # optional dict of FX applied to the voice at render time
    "master": None,        # optional {"lufs": -14, "ceiling_db": -1}: bus comp + limiter to target loudness
}


def _envelope(mono, attack, release):
    """Peak follower with separate attack/release (vectorised in blocks for speed)."""
    hop = 256
    n = int(np.ceil(len(mono) / hop))
    pad = np.pad(np.abs(mono), (0, n * hop - len(mono)))
    blocks = pad.reshape(n, hop).max(axis=1)
    a_c = np.exp(-hop / (SR * max(attack, 1e-3)))
    r_c = np.exp(-hop / (SR * max(release, 1e-3)))
    env = np.zeros(n, np.float32); e = 0.0
    for i, x in enumerate(blocks):
        c = a_c if x > e else r_c
        e = c * e + (1 - c) * x
        env[i] = e
    return np.interp(np.arange(len(mono)), np.arange(n) * hop + hop / 2, env).astype(np.float32)


def render_mix(voice_ref, music_ref, settings: dict) -> np.ndarray:
    s = {**MIX_DEFAULTS, **(settings or {})}
    voice = load_item(voice_ref)
    if s.get("voice_fx"):
        voice = apply_fx(voice, s["voice_fx"])
    music = load_item(music_ref)
    voice = voice * db(s["voice_vol"])
    music = music * db(s["music_vol"])
    off = max(0, int(s["offset"] * SR))
    need = off + len(voice)
    if s.get("length"):
        total = int(s["length"] * SR)
    elif s["loop"]:
        total = max(need + int(s["tail"] * SR), len(music))  # never cut the track short; loop to fit voice
    else:
        total = max(need, len(music))
    if s["loop"] and len(music) < total and len(music) > 0:
        reps = int(np.ceil(total / len(music)))
        # tiny crossfade at loop seams to avoid clicks
        xf = min(int(0.01 * SR), len(music) // 4)
        seg = music.copy()
        if xf > 0:
            seg[:xf] *= np.linspace(0, 1, xf)[:, None]
            seg[-xf:] *= np.linspace(1, 0, xf)[:, None]
        music = np.tile(seg, (reps, 1))
    out = np.zeros((total, 2), np.float32)
    m = music[:total]
    out[: len(m)] += m
    vtrack = np.zeros((total, 2), np.float32)
    vlen = max(0, min(len(voice), total - off))
    vtrack[off: off + vlen] = voice[:vlen]
    if s["duck"]:
        env = _envelope(vtrack.mean(axis=1), s["duck_attack"], s["duck_release"])
        thr = db(s["duck_threshold"])
        amt = np.clip(env / thr, 0, 1)  # 0 below threshold..1 at/above
        gain = db(-s["duck_db"] * amt)
        out *= gain[:, None]
    out += vtrack
    out = fade(out, s["fade_in"], s["fade_out"])
    if s.get("master"):
        m = s["master"]
        return master(out, m.get("lufs", -14.0), m.get("ceiling_db", -1.0)).astype(np.float32)
    peak = float(np.max(np.abs(out)))
    if peak > db(-1.0):
        out = out * (db(-1.0) / peak)
    return out.astype(np.float32)


def mix(voice_ref, music_ref, settings: dict | None = None, name=None, tags=None, parent=None,
        mp3=True, extra_recipe=None) -> dict:
    v, mu = get_item(voice_ref), get_item(music_ref)
    s = {**MIX_DEFAULTS, **(settings or {})}
    audio = render_mix(v["id"], mu["id"], s)
    item = _new_entry("mix", name or f"{v['name']}+{mu['name']}", audio,
                      source=("remix:" + parent) if parent else "mix", tags=tags,
                      recipe={"op": "mix", "voice_id": v["id"], "music_id": mu["id"], "settings": s,
                              "parent": parent, **(extra_recipe or {})})
    if mp3:
        item = update_item(item["id"], mp3=to_mp3(item["path"]))
    return item


def remix(mix_ref, overrides: dict | None = None, voice_ref=None, music_ref=None, name=None,
          tags=None) -> dict:
    base = get_item(mix_ref)
    rec = base.get("recipe") or {}
    if rec.get("op") != "mix":
        raise ValueError(f"{base['id']} is not a mix (no mix recipe)")
    s = copy.deepcopy(rec["settings"])
    for k, v in (overrides or {}).items():
        if k == "voice_fx" and isinstance(v, dict):
            s["voice_fx"] = {**(s.get("voice_fx") or {}), **v}
        else:
            s[k] = v
    return mix(voice_ref or rec["voice_id"], music_ref or rec["music_id"], s,
               name=name or f"{base['name']}_remix", tags=tags or base.get("tags"), parent=base["id"])


def rerender(ref) -> dict:
    """Re-create an item from its recipe as a new catalog entry."""
    it = get_item(ref)
    rec = it.get("recipe") or {}
    op = rec.get("op")
    if op == "mix" and rec.get("produce"):
        return produce(**rec["produce"]["params"], name=f"{it['name']}_rerender")
    if op == "mix":
        return remix(it["id"], {}, name=f"{it['name']}_rerender")
    if op == "generate":
        return generate(rec["settings"], name=f"{it['name']}_rerender")
    if op == "voice-fx":
        return voice_fx(rec["source_id"], rec["settings"], name=f"{it['name']}_rerender")
    raise ValueError(f"item {it['id']} (op={op}) has no re-renderable recipe")


def export(ref, out_dir=None, formats=("mp3", "wav"), bitrate="192k") -> list[str]:
    it = get_item(ref)
    out_dir = Path(out_dir) if out_dir else Path(it["path"]).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(it["path"]).stem
    paths = []
    for f in formats:
        dst = out_dir / f"{stem}.{f}"
        if f == "wav":
            if Path(it["path"]).resolve() != dst.resolve():
                shutil.copy(it["path"], dst)
        elif f == "mp3":
            to_mp3(it["path"], dst, bitrate)
            if out_dir.resolve() == Path(it["path"]).parent.resolve():
                update_item(it["id"], mp3=str(dst))
        else:
            _run_ffmpeg(["-i", it["path"], dst])
        paths.append(str(dst))
    return paths


def synth_voice(seconds=8.0, root_hz=165.0, seed=1) -> np.ndarray:
    """A synthetic 'sung' test phrase: glottal pulse train through vowel formants, with phrasing/gaps."""
    rng = np.random.default_rng(seed)
    vowels = {"a": (800, 1150, 2900), "e": (400, 2000, 2550), "i": (300, 2300, 3000),
              "o": (450, 800, 2830), "u": (325, 700, 2530)}
    melody = [0, 3, 5, 7, 5, 3, 0, -2, 0, 3, 7, 10, 7, 5, 3, 0]
    out = []
    note_len = seconds / len(melody)
    for k, semi in enumerate(melody):
        n = int(note_len * SR * (0.75 if k % 4 != 3 else 0.5))
        t = np.arange(n) / SR
        f0 = root_hz * 2 ** (semi / 12) * (1 + 0.012 * np.sin(2 * np.pi * 5.5 * t))
        ph = np.cumsum(f0) / SR
        src = (2 * (ph % 1.0) - 1) + 0.03 * rng.standard_normal(n)
        y = np.zeros(n)
        for j, fc in enumerate(vowels["aeiou"[rng.integers(0, 5)]]):
            bw = 80 + 40 * j
            b, a_ = signal.iirpeak(fc, fc / bw, fs=SR)
            y += signal.lfilter(b, a_, src) / (j + 1)
        y *= _env(n, 0.03, 0.05, 0.85, 0.08)
        out += [y, np.zeros(int(note_len * SR) - n)]
    mono = np.concatenate(out).astype(np.float32)
    return normalize(np.stack([mono, mono], 1), -1.0)


def tts(text, name="tts_voice", voice="en-us", speed=150, pitch=50, tags=None) -> dict:
    """Make a test voice clip: espeak-ng if installed (optional), otherwise a synthesized vocal phrase."""
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if exe:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "tts.wav"
            subprocess.run([exe, "-v", voice, "-s", str(speed), "-p", str(pitch), "-w", str(p), text],
                           check=True, creationflags=_CREATIONFLAGS)
            audio = normalize(load(p), -1.0)
        return _new_entry("voice", name, audio, source="tts:espeak-ng", tags=(tags or []) + ["tts"],
                          recipe={"op": "tts", "text": text, "voice": voice, "speed": speed, "pitch": pitch})
    audio = synth_voice()
    return _new_entry("voice", name, audio, source="synth-voice", tags=(tags or []) + ["synth"],
                      recipe={"op": "synth-voice"})


def run_demo(log=print) -> dict:
    """End-to-end self test: voice -> FX -> 8-bar 90 BPM A-minor beat -> ducked mix -> remix."""
    v = tts("Yeah. This is my first track. Voice on the beat, remix it any time. Let's go.", name="demo_voice",
            tags=["demo"]); log(f"voice    {v['id']}  {v['name']}  ({v['source']})")
    fx = voice_fx(v["id"], {"pitch": -2, "reverb": 0.3, "low_cut": 100, "compress": True}, name="demo_voice_fx")
    log(f"voice-fx {fx['id']}  {fx['name']}")
    beat = generate({"bpm": 90, "key": "A minor", "bars": 8, "style": "boombap", "seed": 42}, name="demo_beat_90_Am")
    log(f"beat     {beat['id']}  {beat['name']}")
    m = mix(fx["id"], beat["id"], {"music_vol": -3, "offset": 4, "duck": True, "duck_db": 8}, name="demo_mix")
    export(m["id"]); m = get_item(m["id"]); log(f"mix      {m['id']}  {m['mp3']}")
    r = remix(m["id"], {"music_vol": -1, "offset": 1.5, "duck_db": 14, "voice_fx": {"robot": 0.5, "delay": 0.3}},
              name="demo_remix")
    export(r["id"]); r = get_item(r["id"]); log(f"remix    {r['id']}  {r['mp3']}")
    return {"voice": v, "fx": fx, "beat": beat, "mix": m, "remix": r}


# ============================================================================= AI Producer
# Offline "producer": analyze a vocal, pick style/tempo/key, build an arranged beat, process & place
# the vocal on bar boundaries, duck, master to ~-14 LUFS. numpy/scipy/pedalboard only.

KRUMHANSL_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KRUMHANSL_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
PC_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def _biquad(kind, fc, q, gain_db=0.0, fs=SR):
    A = 10 ** (gain_db / 40); w0 = 2 * np.pi * fc / fs; c = np.cos(w0); al = np.sin(w0) / (2 * q)
    if kind == "high_shelf":
        sA = np.sqrt(A)
        b = [A * ((A + 1) + (A - 1) * c + 2 * sA * al), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - 2 * sA * al)]
        a = [(A + 1) - (A - 1) * c + 2 * sA * al, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - 2 * sA * al]
    else:  # high_pass
        b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]; a = [1 + al, -2 * c, 1 - al]
    return np.array(b) / a[0], np.array(a) / a[0]


def lufs(a: np.ndarray) -> float:
    """Integrated loudness (ITU-R BS.1770-4 K-weighting, 400 ms blocks, abs -70 / rel -10 LU gating)."""
    x = a if a.ndim == 2 else a[:, None]
    for kind, fc, q, g in (("high_shelf", 1500.0, 1 / np.sqrt(2), 4.0), ("high_pass", 38.0, 0.5, 0.0)):
        b, a_ = _biquad(kind, fc, q, g)
        x = signal.lfilter(b, a_, x, axis=0)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    if len(x) < blk:
        return -70.0
    n = 1 + (len(x) - blk) // hop
    cs = np.vstack([np.zeros((1, x.shape[1])), np.cumsum(x ** 2, axis=0)])
    idx = np.arange(n) * hop
    z = (cs[idx + blk] - cs[idx]) / blk                       # (n, ch) mean squares
    lk = -0.691 + 10 * np.log10(z.sum(axis=1) + 1e-12)
    g = lk > -70
    if not g.any():
        return -70.0
    rel = -0.691 + 10 * np.log10(z[g].sum(axis=1).mean() + 1e-12) - 10
    g2 = g & (lk > rel)
    return float(-0.691 + 10 * np.log10(z[g2].sum(axis=1).mean() + 1e-12))


def true_peak_db(a: np.ndarray) -> float:
    up = signal.resample_poly(a, 4, 1, axis=0)
    return float(20 * np.log10(np.max(np.abs(up)) + 1e-12))


def master(audio: np.ndarray, target_lufs=-14.0, ceiling_db=-1.0) -> np.ndarray:
    """Bus glue compression + loudness to target + limiter, true-peak safe (4x oversampled check)."""
    import pedalboard as pb
    x = pb.Pedalboard([pb.HighpassFilter(30),
                       pb.Compressor(threshold_db=-18, ratio=2.0, attack_ms=25, release_ms=200)])(
        np.ascontiguousarray(audio.T, dtype=np.float32), SR).T
    x = np.ascontiguousarray(x, np.float32)
    # NB: pedalboard/JUCE Limiter applies makeup gain of -threshold and limits at 0 dBFS, so we use
    # threshold 0 (pure brickwall at 0 dBFS) and place the true-peak ceiling with a Gain stage after it.
    out_gain = ceiling_db - 0.6           # headroom for inter-sample peaks
    gain = target_lufs - lufs(x) - out_gain
    y = x
    for _outer in range(3):
        for _ in range(6):
            y = pb.Pedalboard([pb.Gain(gain), pb.Limiter(threshold_db=0.0, release_ms=120), pb.Gain(out_gain)])(
                np.ascontiguousarray(x.T), SR).T
            y = np.ascontiguousarray(y, np.float32)
            err = target_lufs - lufs(y)
            if abs(err) < 0.2:
                break
            gain += err
        tp = true_peak_db(y)
        if tp <= ceiling_db:
            break
        # inter-sample overs: lower the limiter ceiling, push more into it, and re-converge on loudness
        d = tp - ceiling_db + 0.1
        out_gain -= d
        gain += d
    tp = true_peak_db(y)
    if tp > ceiling_db:
        y = y * db(ceiling_db - tp - 0.05)
    return y


def _frames(x, n, hop):
    nf = 1 + max(0, len(x) - n) // hop
    idx = np.arange(n)[None, :] + hop * np.arange(nf)[:, None]
    return x[idx]


def _pitch_track(mono, sr_in=SR):
    """Autocorrelation f0 tracker on 16 kHz audio, 10 ms hop. Returns times, f0 (0=unvoiced), clarity, rms."""
    x = signal.resample_poly(mono, 160, 441).astype(np.float32)  # 44.1k -> 16k
    fs, n, hop = 16000, 640, 160
    if len(x) < n:
        return np.zeros(0), np.zeros(0), np.zeros(0), np.zeros(0)
    F = _frames(x, n, hop) * np.hanning(n)[None, :].astype(np.float32)
    rms = np.sqrt((F ** 2).mean(axis=1) + 1e-12)
    spec = np.fft.rfft(F, 2 * n, axis=1)
    ac = np.fft.irfft(np.abs(spec) ** 2, axis=1)[:, :n]
    ac /= (ac[:, :1] + 1e-12)
    # compensate the window's triangular taper
    ac /= np.maximum(1 - np.arange(n) / n, 0.2)[None, :]
    lo, hi = int(fs / 900), int(fs / 65)
    seg = ac[:, lo:hi]
    peak = seg.max(axis=1)
    # first lag reaching 92% of max (avoids octave-down errors)
    cand = seg >= (0.92 * peak[:, None])
    lag = lo + np.argmax(cand, axis=1)
    # climb to the local maximum just after the threshold crossing (removes sharp bias at low f0)
    win = np.maximum(3, (lag * 0.2).astype(int))
    for k in range(len(lag)):
        l0 = lag[k]
        lag[k] = l0 + int(np.argmax(ac[k, l0:min(n - 1, l0 + win[k])]))
    # parabolic refinement
    l = np.clip(lag, 1, n - 2)
    y0, y1, y2 = ac[np.arange(len(l)), l - 1], ac[np.arange(len(l)), l], ac[np.arange(len(l)), l + 1]
    den = (y0 - 2 * y1 + y2); off = 0.5 * (y0 - y2) / np.where(np.abs(den) > 1e-9, den, np.inf)
    f0 = fs / (l + np.clip(off, -0.5, 0.5))
    rdb = 20 * np.log10(rms / (rms.max() + 1e-12))
    voiced = (peak > 0.55) & (rdb > -40)
    f0 = np.where(voiced, f0, 0.0)
    # median-smooth to kill single-frame octave jumps
    f0s = signal.medfilt(f0, 5)
    f0 = np.where(voiced & (f0s > 0), f0s, 0.0)
    times = (np.arange(len(f0)) * hop + n / 2) / fs
    return times, f0, peak, rms


def _onset_env(mono):
    n, hop = 2048, 512
    F = _frames(mono, n, hop) * np.hanning(n)[None, :]
    mag = np.log1p(100 * np.abs(np.fft.rfft(F, axis=1)))
    flux = np.maximum(np.diff(mag, axis=0), 0).sum(axis=1)
    flux = np.concatenate([[0], flux])
    flux -= signal.medfilt(flux, 15) if len(flux) > 15 else flux.mean()
    return np.maximum(flux, 0), SR / hop


def _estimate_tempo(mono):
    env, fps = _onset_env(mono)
    if len(env) < fps * 4:
        return 90.0, 0.0, 0.0
    env = env - env.mean()
    ac = np.correlate(env, env, "full")[len(env) - 1:]
    ac /= ac[0] + 1e-12
    bpms = np.arange(60, 181, 0.5)
    lags = 60 * fps / bpms
    def acv(l):
        return np.interp(l, np.arange(len(ac)), ac)
    score = acv(lags) + 0.5 * acv(2 * lags) + 0.25 * acv(4 * lags) + 0.25 * acv(lags / 2)
    prior = np.exp(-0.5 * (np.log2(bpms / 95.0) / 0.6) ** 2)
    w = score * prior
    i = int(np.argmax(w))
    conf = float((w[i] - np.median(w)) / (np.std(w) + 1e-9))
    # onsets per second (syllable-ish rate)
    pk, _ = signal.find_peaks(env, height=np.percentile(env, 75), distance=int(0.08 * fps))
    rate = len(pk) / (len(env) / fps)
    return float(bpms[i]), conf, float(rate)


def _phrases(mono, top_db=32.0, min_gap=0.28, min_len=0.25):
    hop = int(0.01 * SR)
    n = len(mono) // hop
    if n < 3:
        return [], -90.0
    r = np.sqrt((mono[: n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12)
    rdb = 20 * np.log10(r)
    floor, peak = np.percentile(rdb, 10), np.percentile(rdb, 99)
    thr = max(peak - top_db, floor + 8)
    act = signal.medfilt((rdb > thr).astype(float), 5) > 0.5
    segs, i = [], 0
    while i < n:
        if act[i]:
            j = i
            while j < n and act[j]:
                j += 1
            segs.append([i * hop / SR, j * hop / SR]); i = j
        else:
            i += 1
    merged = []
    for s_, e in segs:
        if merged and s_ - merged[-1][1] < min_gap:
            merged[-1][1] = e
        else:
            merged.append([s_, e])
    return [(round(a, 3), round(b, 3)) for a, b in merged if b - a >= min_len], float(floor)


def analyze_vocal(audio: np.ndarray) -> dict:
    mono = audio.mean(axis=1).astype(np.float32)
    dur = len(mono) / SR
    phrases, floor_db = _phrases(mono)
    active = sum(b - a for a, b in phrases)
    times, f0, clar, rms = _pitch_track(mono)
    v = f0 > 0
    midi = np.where(v, 69 + 12 * np.log2(np.maximum(f0, 1) / 440.0), np.nan)
    voiced_ratio = float(v.mean()) if len(v) else 0.0
    # pitch stability: frame-to-frame change inside voiced runs + stable "note" fraction
    dm = np.abs(np.diff(midi)); dm = dm[np.isfinite(dm)]
    jitter = float(np.median(dm)) if len(dm) else 9.0
    stable = 0; run = []
    for k in range(len(midi)):
        if np.isfinite(midi[k]) and (not run or abs(midi[k] - np.median(run)) < 0.6):
            run.append(midi[k])
        else:
            if len(run) >= 12: stable += len(run)
            run = [midi[k]] if np.isfinite(midi[k]) else []
    if len(run) >= 12: stable += len(run)
    note_frac = stable / max(1, int(v.sum()))
    sung = bool(voiced_ratio > 0.35 and note_frac > 0.6 and jitter < 0.35)
    # tuning offset + key (Krumhansl-Schmuckler) from energy-weighted pitch-class histogram
    mv = midi[v]; wv = (rms[v] / (rms[v].max() + 1e-12)) if v.any() else np.zeros(0)
    tuning = 0.0
    if len(mv) > 20:
        ang = 2 * np.pi * (mv - np.round(mv))
        tuning = float(np.angle(np.sum(wv * np.exp(1j * ang))) / (2 * np.pi))
    hist = np.zeros(12)
    if len(mv):
        pcs = np.mod(np.round(mv - tuning), 12).astype(int)
        np.add.at(hist, pcs, wv)
    corr = []
    for mode_name, prof in (("major", KRUMHANSL_MAJOR), ("minor", KRUMHANSL_MINOR)):
        for r in range(12):
            corr.append((float(np.corrcoef(hist, np.roll(prof, r))[0, 1]) if hist.sum() > 0 else 0.0, r, mode_name))
    corr.sort(reverse=True)
    best, second = corr[0], corr[1]
    # relative major/minor share notes: margin vs the best *non-relative* key is a fairer confidence
    key_conf = float(best[0] - second[0])
    key_reliable = bool(best[0] > 0.55 and key_conf > 0.04 and len(mv) > 200 and sung)
    bpm, tconf, rate = _estimate_tempo(mono)
    # loudness / energy
    act_audio = np.concatenate([audio[int(a * SR):int(b * SR)] for a, b in phrases]) if phrases else audio
    loud = lufs(act_audio)
    F = _frames(mono, 2048, 1024) * np.hanning(2048)[None, :]
    mag = np.abs(np.fft.rfft(F, axis=1)); freqs = np.fft.rfftfreq(2048, 1 / SR)
    fr = (mag ** 2).sum(axis=1)
    cen = float(np.median(((mag ** 2) @ freqs / (fr + 1e-12))[fr > np.percentile(fr, 50)])) if len(fr) else 0.0
    return {
        "duration": round(dur, 2), "active_seconds": round(active, 2), "phrases": phrases,
        "n_phrases": len(phrases), "noise_floor_db": round(floor_db, 1),
        "tempo_raw": bpm, "tempo_confidence": round(tconf, 2), "onset_rate": round(rate, 2),
        "voiced_ratio": round(voiced_ratio, 3), "pitch_jitter_semitones": round(jitter, 3),
        "note_fraction": round(note_frac, 3), "sung": sung,
        "median_pitch_hz": round(float(np.nanmedian(f0[v])), 1) if v.any() else None,
        "tuning_offset_semitones": round(tuning, 3),
        "key_detected": f"{PC_NAMES[best[1]]} {best[2]}", "key_correlation": round(best[0], 3),
        "key_confidence": round(key_conf, 3), "key_reliable": key_reliable,
        "key_candidates": [f"{PC_NAMES[r]} {m} ({c:.2f})" for c, r, m in corr[:4]],
        "pitch_class_histogram": [round(float(h), 2) for h in hist / (hist.max() + 1e-12)],
        "loudness_lufs": round(loud, 1), "spectral_centroid_hz": round(cen, 0),
    }


def _fold_tempo(t, lo, hi):
    for f in (1, 0.5, 2, 2 / 3, 1.5, 0.25, 4, 1 / 3, 3):
        if lo <= t * f <= hi:
            return round(t * f)
    return None


MOOD_STYLE = {"chill": "lofi", "calm": "lofi", "sad": "lofi", "dreamy": "ambient", "ambient": "ambient",
              "dark": "trap", "hype": "trap", "aggressive": "trap", "energetic": "trap",
              "happy": "house", "upbeat": "house", "classic": "boombap", "groovy": "hiphop"}
MOOD_MODE = {"sad": "minor", "dark": "minor", "chill": "minor", "dreamy": "major", "happy": "major", "upbeat": "major"}
STYLE_PROGS = {
    ("lofi", "minor"): ["i7-iv7-VII7-III7", "i7-VI7-III7-VII7", "ii7-v7-i7-i7"],
    ("lofi", "major"): ["IV7-iii7-ii7-I7", "I7-vi7-ii7-V7", "ii7-V7-I7-vi7"],
    ("ambient", "minor"): ["i7-VI7-III7-VII7", "i-iv-i-VI"], ("ambient", "major"): ["I7-IV7-vi7-IV7", "I-V-vi-IV"],
    ("trap", "minor"): ["i-VI-VII-i", "i-i-VI-VII", "i-iv-VI-V"], ("trap", "major"): ["vi-IV-I-V"],
    ("boombap", "minor"): ["i-VI-III-VII", "i7-iv7-i7-v7", "i-VII-VI-VII"], ("boombap", "major"): ["I-vi-IV-V", "ii7-V7-I7-I7"],
    ("hiphop", "minor"): ["i-VI-III-VII", "i-iv-VII-III"], ("hiphop", "major"): ["I-V-vi-IV"],
    ("house", "minor"): ["i-VI-III-VII"], ("house", "major"): ["I-V-vi-IV", "vi-IV-I-V"],
}


def choose_production(an: dict, style=None, bpm=None, key=None, mood=None, rng=None) -> dict:
    rng = rng or np.random.default_rng()
    mood = (mood or "").lower().strip() or None
    sung = an["sung"]
    # tempo: spoken/rap -> fold into 80-100; sung -> 70-140 (folded), else default 90
    if bpm:
        tempo, tempo_src = float(bpm), "override"
    else:
        lo, hi = (70, 140) if sung else (80, 100)
        f = _fold_tempo(an["tempo_raw"], lo, hi) if an["tempo_confidence"] > 2.0 else None
        if f:
            tempo, tempo_src = float(f), f"detected {an['tempo_raw']:.1f} -> {lo}-{hi} range"
        else:
            tempo = 90.0
            tempo_src = ("default 90 (low tempo confidence)" if an["tempo_confidence"] <= 2.0 else
                         f"default 90 (detected {an['tempo_raw']:.1f} doesn't fold into {lo}-{hi})")
    # energy score 0..1
    e_rate = np.clip((an["onset_rate"] - 1.5) / 4.5, 0, 1)
    e_tempo = np.clip((tempo - 70) / 70, 0, 1)
    e_bright = np.clip((an["spectral_centroid_hz"] - 900) / 2200, 0, 1)
    e_loud = np.clip((an["loudness_lufs"] + 30) / 18, 0, 1)
    energy = float(0.35 * e_rate + 0.25 * e_tempo + 0.2 * e_bright + 0.2 * e_loud)
    if style and style != "auto":
        st, st_src = style, "override"
    elif mood in MOOD_STYLE:
        st, st_src = MOOD_STYLE[mood], f"mood '{mood}'"
    else:
        st = "ambient" if (energy < 0.2 and sung) else "lofi" if energy < 0.38 else "boombap" if energy < 0.62 else "trap"
        st_src = f"energy {energy:.2f}"
    # key
    if key:
        k, k_src = key, "override"
    elif an["key_reliable"]:
        k, k_src = an["key_detected"], "detected"
    elif an["key_correlation"] > 0.5 and an["key_confidence"] > 0.15:
        k, k_src = an["key_detected"], "detected from speech pitch (moderate confidence)"
    else:
        mode_ = MOOD_MODE.get(mood, "minor")
        if an["voiced_ratio"] > 0.15 and an.get("median_pitch_hz"):
            # keep the beat centred on the speaker's voice: root = pitch class of the median voice pitch
            pc = int(round(69 + 12 * np.log2(an["median_pitch_hz"] / 440))) % 12
            k, k_src = f"{PC_NAMES[pc]} {mode_}", "voice median pitch (key detection unreliable)"
        else:
            k, k_src = ("A minor" if mode_ == "minor" else "C major"), "default"
    root, mode_ = parse_key(k)
    progs = STYLE_PROGS.get((st, mode_), [DEFAULT_PROG[mode_]])
    prog = progs[int(rng.integers(0, len(progs)))]
    swing = {"lofi": 0.35, "boombap": 0.2, "hiphop": 0.15}.get(st, 0.0)
    return {"style": st, "style_source": st_src, "energy": round(energy, 3), "bpm": float(tempo),
            "tempo_source": tempo_src, "key": k, "key_source": k_src, "progression": prog, "swing": swing,
            "texture": "vinyl" if st == "lofi" else None, "mood": mood}


def _pitch_correct(audio, key, strength=0.7):
    """Gentle per-note pitch correction toward the scale of `key` (pitch-shifts stable note segments)."""
    import pedalboard as pb
    root, mode_ = parse_key(key)
    scale = [(root + i) % 12 for i in SCALES[mode_]]
    mono = audio.mean(axis=1)
    times, f0, _, _ = _pitch_track(mono)
    midi = np.where(f0 > 0, 69 + 12 * np.log2(np.maximum(f0, 1) / 440), np.nan)
    segs, run = [], []
    for k in range(len(midi)):
        if np.isfinite(midi[k]) and (not run or abs(midi[k] - np.median([midi[j] for j in run])) < 0.5):
            run.append(k)
        else:
            if len(run) >= 8: segs.append(run)
            run = [k] if np.isfinite(midi[k]) else []
    if len(run) >= 8: segs.append(run)
    out = audio.copy(); applied = []
    xf = int(0.012 * SR)
    for run in segs:
        m = float(np.median(midi[run]))
        targets = [n for n in range(int(m) - 2, int(m) + 3) if n % 12 in scale]
        tgt = min(targets, key=lambda n: abs(n - m))
        shift = (tgt - m) * strength
        if abs(shift) < 0.12 or abs(shift) > 1.2:
            continue
        a0 = max(0, int((times[run[0]] - 0.02) * SR)); a1 = min(len(audio), int((times[run[-1]] + 0.02) * SR))
        pad = int(0.08 * SR)
        p0, p1 = max(0, a0 - pad), min(len(audio), a1 + pad)
        seg = pb.Pedalboard([pb.PitchShift(semitones=float(shift))])(np.ascontiguousarray(audio[p0:p1].T), SR).T
        seg = seg[a0 - p0: a0 - p0 + (a1 - a0)]
        if len(seg) < 2 * xf + 2:
            continue
        w = np.ones(len(seg), np.float32); w[:xf] = np.linspace(0, 1, xf); w[-xf:] = np.linspace(1, 0, xf)
        out[a0:a0 + len(seg)] = out[a0:a0 + len(seg)] * (1 - w[:, None]) + seg * w[:, None]
        applied.append(round(shift, 2))
    return out, applied


def vocal_chain(audio, an, tune=False, key=None):
    import pedalboard as pb
    gate_thr = float(np.clip(an["noise_floor_db"] + 8, -60, -38))
    pre = pb.Pedalboard([
        pb.HighpassFilter(cutoff_frequency_hz=90),
        pb.NoiseGate(threshold_db=gate_thr, ratio=4.0, attack_ms=2, release_ms=120),
        pb.LowShelfFilter(cutoff_frequency_hz=250, gain_db=-1.5),     # de-mud
        pb.PeakFilter(cutoff_frequency_hz=3500, gain_db=2.0, q=0.8),  # presence
        pb.Compressor(threshold_db=-22, ratio=3.5, attack_ms=6, release_ms=110),
        pb.Compressor(threshold_db=-10, ratio=6.0, attack_ms=1, release_ms=60),  # peak catcher
    ])
    x = np.ascontiguousarray(pre(np.ascontiguousarray(normalize(audio, -3).T), SR).T, np.float32)
    corrections = []
    if tune and key:
        x, corrections = _pitch_correct(x, key)
    return normalize(x, -1.0), {"gate_threshold_db": gate_thr, "pitch_correction": bool(tune and key),
                                "corrections_semitones": corrections}


def _lines(phrases, bar_s=2.667, max_gap=1.0, max_bars=3):
    """Group phrases into lines (each will start on a downbeat). Lines keep natural internal timing.
    Dynamic programming picks groupings that minimise dead air (unused bar time) - lines may span
    1..max_bars bars and only join phrases separated by less than max_gap seconds."""
    P = list(phrases)
    n = len(P)
    if n == 0:
        return []
    INF = 1e18
    best = [INF] * (n + 1); best[0] = 0.0; back = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(j - 1, -1, -1):
            if i < j - 1 and P[i + 1][0] - P[i][1] >= max_gap:
                break                                   # can't join across a long pause
            length = P[j - 1][1] - P[i][0] + 0.06
            bars = int(np.ceil((length + 0.15) / bar_s - 0.05))
            if bars > max_bars and i < j - 1:
                break
            waste = bars * bar_s - length
            cost = best[i] + waste + 0.3                # small per-line cost favours fewer, fuller lines
            if cost < best[j]:
                best[j], back[j] = cost, i
    out, j = [], n
    while j > 0:
        i = back[j]; out.append((P[i][0], P[j - 1][1])); j = i
    return out[::-1]


def _arrange(an, bpm, voice_len_s, rng):
    bar_s = 240.0 / bpm
    lines = _lines(an["phrases"], bar_s) or [(0.0, voice_len_s)]
    intro = 4 if voice_len_s > 25 else 2
    placements, t_bar = [], intro
    for a, b in lines:
        a0 = max(0.0, a - 0.06)            # keep a breath of pre-roll
        start = t_bar * bar_s - (a - a0)
        placements.append({"src_start": round(a0, 3), "src_end": round(min(voice_len_s, b + 0.12), 3),
                           "bar": int(t_bar), "dst_start": round(start, 3)})
        end_t = start + (b - a0)
        t_bar = int(np.ceil((end_t + 0.05) / bar_s - 0.02))  # next downbeat after this line ends
    body_end_bar = int(np.ceil((placements[-1]["dst_start"] + (placements[-1]["src_end"] - placements[-1]["src_start"])) / bar_s))
    body = max(4, body_end_bar - intro)
    body += (-body) % 4                   # whole 4-bar phrases
    outro = 4
    sections = [{"name": "intro", "bars": intro, "drums": "hats" if intro >= 4 else "none", "bass": False, "pad": True,
                 "fill": False}]
    k, var = 0, 0
    while k < body:
        nb = min(8, body - k)
        sections.append({"name": f"verse{'AB'[var % 2]}", "bars": nb, "drums": "full", "bass": True, "pad": True,
                         "variant": var % 2, "crash": True, "fill": True})
        k += nb; var += 1
    sections.append({"name": "outro", "bars": outro, "drums": "half", "bass": True, "pad": True, "crash": True,
                     "fill": False})
    return sections, placements, bar_s


def produce(voice_id, style=None, bpm=None, key=None, mood=None, seed=None, tune="auto", name=None,
            target_lufs=-14.0, log=None) -> dict:
    """Make a finished, mastered song from one vocal. Returns the new mix catalog item."""
    log = log or (lambda *a: None)
    src = get_item(voice_id)
    if seed is None:
        seed = int(np.random.default_rng().integers(0, 2**31))
    rng = np.random.default_rng(seed)
    raw = load(src["path"])
    log("analyzing vocal...")
    an = analyze_vocal(raw)
    ch = choose_production(an, style, bpm, key, mood, rng)
    do_tune = tune == "on" or (tune == "auto" and an["sung"] and (an["key_reliable"] or bool(key)))
    log(f"style={ch['style']} bpm={ch['bpm']} key={ch['key']}")
    voc, chain_info = vocal_chain(raw, an, tune=do_tune, key=ch["key"])
    sections, placements, bar_s = _arrange(an, ch["bpm"], len(raw) / SR, rng)
    gen = {"bpm": ch["bpm"], "style": ch["style"], "key": ch["key"], "progression": ch["progression"],
           "swing": ch["swing"], "seed": int(rng.integers(0, 2**31)), "sections": sections, "texture": ch["texture"],
           "pad_vol": {"ambient": 3.0, "lofi": 1.0}.get(ch["style"], 0.0)}
    base = _slug(src["name"])
    log("generating beat...")
    beat = generate(gen, name=f"{base}_beat_{ch['style']}_{int(ch['bpm'])}bpm", tags=["produced"])
    # arranged vocal on the beat timeline
    total = int(round(sum(s_["bars"] for s_ in sections) * bar_s * SR))
    track = np.zeros((total + int(3 * SR), 2), np.float32)
    for p in placements:
        seg = voc[int(p["src_start"] * SR):int(p["src_end"] * SR)].copy()
        seg = fade(seg, 0.01, 0.06)
        d0 = max(0, int(p["dst_start"] * SR))
        n = min(len(seg), len(track) - d0)
        track[d0:d0 + n] += seg[:n]
    import pedalboard as pb
    rev = {"ambient": 0.28, "lofi": 0.18}.get(ch["style"], 0.14)
    track = pb.Pedalboard([pb.Reverb(room_size=0.45, damping=0.6, wet_level=rev, dry_level=1.0, width=0.9),
                           pb.Delay(delay_seconds=60 / ch["bpm"] * 0.75, feedback=0.15, mix=0.07)])(
        np.ascontiguousarray(track.T), SR).T
    track = normalize(trim_end_silence(np.ascontiguousarray(track, np.float32)), -1.0)
    vitem = _new_entry("voice", f"{base}_produced_vocal", track, source=f"produce:{src['id']}", tags=["produced"],
                       recipe={"op": "produce-vocal", "source_id": src["id"], "chain": chain_info,
                               "placements": placements, "reverb": rev})
    # balance: music sits ~5 LU under the vocal before ducking
    act = np.concatenate([track[int(p["dst_start"] * SR):int((p["dst_start"] + p["src_end"] - p["src_start"]) * SR)]
                          for p in placements])
    beat_audio = load(beat["path"])
    music_vol = float(np.clip((lufs(act) - lufs(beat_audio)) - {"ambient": 3.5, "lofi": 2.5}.get(ch["style"], 1.5), -18, 6))
    mix_settings = {"voice_vol": 0.0, "music_vol": round(music_vol, 2), "offset": 0.0, "duck": True, "duck_db": 4.0,
                    "duck_attack": 0.08, "duck_release": 0.5, "duck_threshold": -32.0, "fade_in": 0.0,
                    "fade_out": 1.5, "loop": False, "tail": 0.0, "length": None, "voice_fx": None,
                    "master": {"lufs": target_lufs, "ceiling_db": -1.0}}
    params = {"voice_id": src["id"], "style": style, "bpm": bpm, "key": key, "mood": mood, "seed": seed,
              "tune": tune, "target_lufs": target_lufs}
    log("mixing & mastering...")
    item = mix(vitem["id"], beat["id"], mix_settings, name=name or f"{base}_song_{ch['style']}",
               tags=["produced", ch["style"]],
               extra_recipe={"produce": {"params": params, "analysis": an, "choices": ch, "sections": sections,
                                         "beat_id": beat["id"], "vocal_id": vitem["id"], "chain": chain_info}})
    a = load(item["path"])
    item = update_item(item["id"], loudness_lufs=round(lufs(a), 1), true_peak_db=round(true_peak_db(a), 2))
    return item
