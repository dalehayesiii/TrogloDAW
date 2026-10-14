import subprocess
import sys
import time

import pytest

import songs as song_module
from models import Canceled, Models
from songs import stop_inference
from storage import Storage


def test_stopping_owned_worker_releases_its_process(tmp_path):
    marker = tmp_path / "started"
    code = "from pathlib import Path;import sys,time;Path(sys.argv[1]).write_text('ready');time.sleep(60)"
    worker = subprocess.Popen([sys.executable, "-c", code, str(marker)])
    try:
        deadline = time.monotonic() + 10
        while not marker.is_file() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert marker.is_file()
        stop_inference(worker)
        assert worker.poll() is not None
        stop_inference(worker)  # Finished handles do not target another PID.
    finally:
        if worker.poll() is None:
            stop_inference(worker)


@pytest.mark.parametrize("interruption", ["cancel", "deadline", "progress-error"])
def test_enrichment_interruption_stops_live_worker_and_removes_request(
    core, songs, tmp_path, monkeypatch, interruption
):
    service, _ = songs
    service.models = Models(Storage(core))
    service.models.storage.preferences["music_model"] = "base"
    service.models.manifest = {"runtime_revision": "fixture", "models": {"base": {"assets": []}}}
    root = tmp_path / "synthetic-worker"
    (root / "backend").mkdir(parents=True)
    (root / "backend/inference_runner.py").write_text(
        "import time\n"
        'print(\'TROGLO_EVENT {"stage":"enriching_prompt","fraction":0}\',flush=True)\n'
        "time.sleep(60)\n"
    )
    monkeypatch.setattr(song_module, "ROOT", root)
    monkeypatch.setattr(
        service.models,
        "ready",
        lambda: {
            "model": "base",
            "runtime_revision": "fixture",
            "packages": "runtime-packages/fixture",
            "code": "inference-code/fixture",
        },
    )
    monkeypatch.setattr(service.models, "enrichment_ready", lambda: {"packages": "addon"})
    monkeypatch.setattr(
        service.models, "enrichment_profile", lambda: {"writer_path": "checkpoints/writer"}
    )
    spawned = []
    popen = subprocess.Popen

    def spawn(*args, **kwargs):
        worker = popen(*args, **kwargs)
        spawned.append(worker)
        return worker

    monkeypatch.setattr(song_module.subprocess, "Popen", spawn)
    clock = [0.0]
    canceled = [False]
    monkeypatch.setattr(song_module.time, "monotonic", lambda: clock[0])

    def progress(_message, _fraction=0, **details):
        if details.get("stage") == "enriching_prompt":
            if interruption == "deadline":
                clock[0] = 151
            elif interruption == "progress-error":
                raise Canceled("Synthetic progress cancellation")
            else:
                canceled[0] = True

    expected = TimeoutError if interruption == "deadline" else Canceled
    with pytest.raises(expected):
        service._invoke("enrich_prompt", {"caption": "fixture"}, progress, lambda: canceled[0])
    assert spawned and all(worker.poll() is not None for worker in spawned)
    assert not list((service.models.storage.models / "cache").glob("*.json"))
