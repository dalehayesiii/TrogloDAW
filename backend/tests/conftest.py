import importlib
import sys

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import soundfile as sf
import pytest

from songs import Songs


@pytest.fixture
def core(tmp_path, monkeypatch):
    monkeypatch.setenv("TROGLODAW_LIBRARY", str(tmp_path / "library"))
    monkeypatch.setenv("TROGLODAW_CONFIG_DIR", str(tmp_path))
    for key in ("TROGLODAW_FFMPEG", "TROGLODAW_HOST", "TROGLODAW_PORT"):
        monkeypatch.delenv(key, raising=False)
    sys.modules.pop("troglocore", None)
    return importlib.import_module("troglocore")


@pytest.fixture
def songs(core):
    calls = []
    model = SimpleNamespace(
        selected="base",
        manifest={
            "runtime_revision": "fixture",
            "models": {"base": {"assets": [], "recording_conditioning": "cover-nofsq"}},
        },
    )

    def invoke(action, values, progress, canceled):
        calls.append(action)
        if action == "plan_song":
            return {"duration": values["parameters"]["duration"], "planner": "synthetic-fixture"}
        if action == "write_lyrics":
            return {
                "lyrics": "[Verse]\nCave lights shine\nThese words are mine",
                "duration": 30,
                "planner": "synthetic-fixture",
            }
        directory = Path(values["output"])
        directory.mkdir(exist_ok=True, parents=True)
        if action == "generate":
            samples = round(values["parameters"]["duration"] * core.SR)
            timeline = np.arange(samples) / core.SR
            audio = np.repeat(
                (0.05 * np.sin(2 * np.pi * 100 * timeline))[:, None], 2, axis=1
            ).astype(np.float32)
            path = directory / "music.wav"
            sf.write(path, audio, core.SR, subtype="FLOAT")
            return {"audio": str(path), "sample_rate": core.SR, "parameters": values["parameters"]}
        audio = core.load(values["audio"])
        vocals = audio * 0.25
        sf.write(directory / "vocals.wav", vocals, core.SR, subtype="FLOAT")
        sf.write(directory / "accompaniment.wav", audio - vocals, core.SR, subtype="FLOAT")
        half = len(audio) // 2
        segments = [
            {"start": 0, "end": half, "group": "g1", "uncertain": True},
            {"start": half, "end": len(audio), "group": "g2", "uncertain": True},
        ]
        groups = []
        for segment in segments:
            group_audio = np.zeros_like(vocals)
            group_audio[segment["start"] : segment["end"]] = vocals[
                segment["start"] : segment["end"]
            ]
            filename = str(segment["group"]) + ".wav"
            sf.write(directory / filename, group_audio, core.SR, subtype="FLOAT")
            groups.append(
                {
                    "id": segment["group"],
                    "name": segment["group"],
                    "file": filename,
                    "uncertain": True,
                }
            )
        return {
            "groups": groups,
            "segments": segments,
            "samples": len(audio),
            "sample_rate": core.SR,
            "warning": "Synthetic fixture groups, not model inference",
        }

    service = Songs(core, model, lambda path: {"url": str(path)}, invoke)
    return service, calls
