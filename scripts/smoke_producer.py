"""Exercise the actual producer with synthetic audio, never personal recordings."""

from pathlib import Path
import sys

import numpy as np

if not sys.flags.isolated:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import mmcore as mm

voice = mm._new_entry("voice", "producer_smoke", mm.synth_voice(seconds=2), "synthetic-test")
song = mm.produce(voice["id"], seed=42, bpm=120, style="lofi", tune="off")
assert song["recipe"]["produce"]["params"]["seed"] == 42
assert Path(song["mp3"]).stat().st_size > 100
assert np.isfinite(mm.load(song["path"])).all()
assert song["true_peak_db"] <= -0.9
print("Producer smoke test passed")
