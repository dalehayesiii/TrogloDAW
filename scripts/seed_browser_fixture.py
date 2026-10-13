"""Seed synthetic cached-song data for browser/installed-app contract tests."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

backend = Path(os.environ.get("TROGLODAW_TEST_APP", "backend/app.py")).resolve().parent
sys.path.insert(0, str(backend))
import troglocore as core  # noqa: E402
from models import ROOT, runtime_signature  # noqa: E402
from storage import atomic_json, digest  # noqa: E402

voice = core._new_entry(
    "voice", "Synthetic browser recording", core.synth_voice(1), "synthetic-test"
)
late_vocals = os.environ.get("TROGLODAW_TEST_LATE_VOCALS") == "1"
if late_vocals:
    audio = np.repeat(
        (0.2 * np.sin(2 * np.pi * 220 * np.arange(15 * core.SR) / core.SR))[:, None], 2, axis=1
    ).astype(np.float32)
else:
    audio = core.synth_voice(2) * 0.4
item = core._new_entry(
    "generated",
    "Synthetic browser song",
    audio,
    "synthetic-test",
    recipe={
        "op": "generate",
        "settings": {"seed": 42, "bars": 1, "bpm": 120, "style": "boombap", "key": "A minor"},
    },
    extra={"is_song": True},
)
processor = {
    "alignment": 1,
    "model_manifest": digest(ROOT / "config/model-manifest.json"),
    "runtime_lock": runtime_signature(),
}
key = hashlib.sha256(
    json.dumps(
        {"source": digest(Path(item["path"])), "processor": processor}, sort_keys=True
    ).encode()
).hexdigest()[:24]
directory = core.LIB / "assets/vocals" / item["id"] / key
directory.mkdir(parents=True)
import shutil  # noqa: E402

shutil.copyfile(item["path"], directory / "source.wav")
source = core.load_item(item["id"])
vocal = source * (0.9 if late_vocals else 0.25)
sf.write(directory / "vocals.wav", vocal, core.SR, subtype="FLOAT")
sf.write(directory / "accompaniment.wav", source - vocal, core.SR, subtype="FLOAT")
groups, segments = [], []
ranges = (
    [(12 * core.SR, len(vocal)), (0, 12 * core.SR)]
    if late_vocals
    else [(0, len(vocal) // 2), (len(vocal) // 2, len(vocal))]
)
for index, (start, end) in enumerate(ranges):
    group = f"g{index}" if late_vocals else f"g{index + 1}"
    part = np.zeros_like(vocal)
    part[start:end] = vocal[start:end]
    path = directory / (group + ".wav")
    sf.write(path, part, core.SR, subtype="FLOAT")
    segments.append({"start": start, "end": end, "group": group, "uncertain": True})
    groups.append(
        {
            "id": group,
            "name": f"Synthetic candidate {index + 1}",
            "file": path.relative_to(core.LIB).as_posix(),
            "segments": [{"start": start, "end": end}],
            "uncertain": True,
        }
    )
relative = lambda path: path.relative_to(core.LIB).as_posix()
metadata = {
    "source_song_id": item["id"],
    "source_file": relative(directory / "source.wav"),
    "vocals_file": relative(directory / "vocals.wav"),
    "accompaniment_file": relative(directory / "accompaniment.wav"),
    "groups": groups,
    "segments": segments,
    "sample_rate": core.SR,
    "samples": len(source),
    "processor": processor,
    "cache_key": key,
    "creation_recipe": item["recipe"],
    "warning": "Synthetic cached test groups. Live candidate groups may require correction.",
    "files": {relative(p): digest(p) for p in directory.glob("*.wav")},
}
atomic_json(directory / "analysis.json", metadata)
print(json.dumps({"song": item, "voice": voice}))
