"""Real service/browser fixture; only external planner/music inference is synthetic."""

import argparse
import os
import sys
import threading
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import uvicorn

repository = Path(__file__).resolve().parents[1]
backend = Path(os.environ.get("TROGLODAW_TEST_APP", repository / "backend/app.py")).parent
sys.path.insert(0, str(backend))
import app  # noqa: E402
from models import Canceled  # noqa: E402
from prompt_enrichment import CODEC, PROMPT_VERSION, asset_identity, provenance  # noqa: E402

api = app.create_app(quit_callback=lambda: None)
service = api.state.service
service.models.ready = lambda: {"fixture": True}
service.models.planner_ready = lambda: {"fixture": True}
service.storage.preferences["setup_seen"] = True
service.storage.persist()
calls = []
enrichment_profile = None
support_present = True


def inference(action, values, progress, canceled):
    calls.append({"action": action, "values": values})
    for step in range(16):
        if canceled():
            raise Canceled("Synthetic inference canceled")
        progress(
            "Synthetic local planning" if action != "generate" else "Synthetic music inference",
            step / 16,
            stage="enriching_prompt"
            if action == "enrich_prompt"
            else "planning_song"
            if action != "generate"
            else "generating",
            units_complete=step,
            units_total=16,
        )
        time.sleep(0.03)
    if action == "enrich_prompt":
        if values["caption"] == "fail enrichment":
            raise RuntimeError("Synthetic writer failure")
        return provenance(
            values["caption"],
            profile=enrichment_profile,
            additions="warm rhythmic guitar accents",
            verdict="ACCEPT",
        )
    if action == "write_lyrics":
        if values["prompt"] == "fail":
            raise RuntimeError("Synthetic lyric failure")
        return {
            "lyrics": "[Verse]\nPurple cave lights shine\nThese words are mine",
            "duration": 18,
            "planner": "synthetic-boundary",
        }
    if action == "plan_song":
        return {"duration": 18, "planner": "synthetic-boundary"}
    if action == "plan_blueprint":
        return {
            "metadata": {"bpm": 120, "keyscale": "C major", "timesignature": "4"},
            "planner": "synthetic-boundary",
        }
    folder = Path(values["output"])
    folder.mkdir(parents=True, exist_ok=True)
    samples = round(values["parameters"]["duration"] * service.core.SR)
    timeline = np.arange(samples) / service.core.SR
    audio = np.repeat((0.05 * np.sin(2 * np.pi * 180 * timeline))[:, None], 2, axis=1).astype(
        np.float32
    )
    path = folder / "synthetic-music.wav"
    sf.write(path, audio, service.core.SR, subtype="FLOAT")
    return {"audio": str(path), "sample_rate": service.core.SR, "parameters": values["parameters"]}


service.songs.invoke = inference
service.songs.local_inference = False


@api.post("/api/fixture/stop")
def stop():
    threading.Timer(0.2, lambda: os._exit(0)).start()
    return {"message": "Synthetic fixture stopping"}


api.router.routes.sort(key=lambda route: getattr(route, "path", "") == "")
parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, required=True)
parser.add_argument("--enrichment", action="store_true")
arguments = parser.parse_args()
if arguments.enrichment:
    music = service.models.manifest["models"][service.models.selected]
    music["enrichment_profile"] = "fixture"
    enrichment_profile = {
        "id": "fixture",
        "qualified": True,
        "codec": CODEC,
        "prompt_version": PROMPT_VERSION,
        "music_runtime_revision": service.models.manifest["runtime_revision"],
        "music_asset_identity": asset_identity(music),
        "max_characters": 120,
        "writer": "synthetic-boundary",
        "writer_revision": "fixture",
        "assets": [],
    }
    service.models.manifest["enrichment_profiles"] = {"fixture": enrichment_profile}
    service.models.enrichment_ready = lambda: {"fixture": True} if support_present else None

    @api.get("/api/fixture/calls")
    def recorded_calls():
        return calls

    @api.post("/api/fixture/missing-support")
    def missing_support():
        global support_present
        support_present = False
        return {"ready": False}

    api.router.routes.sort(key=lambda route: getattr(route, "path", "") == "")
uvicorn.run(api, host="127.0.0.1", port=arguments.port, log_level="warning")
