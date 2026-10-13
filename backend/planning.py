"""Portable musical metadata blueprints; no setup or text rewriting."""

from __future__ import annotations

import math
import re
import json


def explicit_music_metadata(parameters):
    """Respect literal tempo/key/meter in styles before asking the music planner."""
    caption = parameters["caption"]
    values = {"duration": parameters["duration"]}
    tempo = re.search(r"\b([0-9]{2,3})\s*bpm\b|\bbpm\s*[:=]?\s*([0-9]{2,3})\b", caption, re.I)
    if tempo:
        values["bpm"] = int(tempo[1] or tempo[2])
    key = re.search(r"\b([A-G][#b]?)\s+(major|minor)\b", caption, re.I)
    if key:
        values["keyscale"] = key[1][0].upper() + key[1][1:] + " " + key[2].lower()
    meter = re.search(r"\b([2346])\s*/\s*[48]\b", caption)
    if meter:
        values["timesignature"] = meter[1]
    return values


def validated_blueprint(result, parameters):
    if result.get("audio_codes"):
        raise ValueError("Semantic-code blueprints are not qualified for this runtime")
    metadata = result.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("The music planner returned invalid blueprint metadata")
    json.dumps(metadata, allow_nan=False)
    effective = {**metadata, **explicit_music_metadata(parameters)}
    bpm = effective.get("bpm")
    if isinstance(bpm, bool) or not isinstance(bpm, (int, float)) or not math.isfinite(bpm):
        raise ValueError("The music blueprint needs a finite tempo")
    if not 30 <= bpm <= 300 or bpm != int(bpm):
        raise ValueError("The music blueprint tempo must be an integer from 30–300 BPM")
    key = effective.get("keyscale", "")
    if not isinstance(key, str) or not re.fullmatch(r"[A-G][#b]? (?:major|minor)", key):
        raise ValueError("The music blueprint needs a supported major or minor key")
    meter = str(effective.get("timesignature", ""))
    if meter not in {"2", "3", "4", "6"}:
        raise ValueError("The music blueprint needs a supported time signature")
    constraints = {"bpm": int(bpm), "keyscale": key, "timesignature": meter}
    # Never forward suggested text/language/duration or unrecognized model fields.
    return {
        "version": 2,
        "strategy": "musical_metadata",
        "planner": result.get("planner"),
        "runtime_revision": result.get("runtime_revision"),
        "seed": parameters["seed"],
        "duration": parameters["duration"],
        "caption": parameters["caption"],
        "lyrics": parameters["lyrics"],
        "metadata": metadata,
        "constraints": constraints,
        "seconds": result.get("seconds"),
        "peak_vram": result.get("peak_vram"),
    }
