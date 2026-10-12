"""Development browser fixture: real app/API with injected release/installer boundaries."""

import argparse
import hashlib
import io
import json
import os
import sys
import threading
import time
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import uvicorn

repository = Path(__file__).resolve().parents[1]
backend = Path(os.environ.get("TROGLODAW_TEST_APP", repository / "backend/app.py")).parent
sys.path.insert(0, str(backend))
import app  # noqa: E402
from storage import atomic_json  # noqa: E402
from updates import INSTALLER, Updates  # noqa: E402
from models import Canceled  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, required=True)
args = parser.parse_args()
state: dict[str, bool | float] = {
    "failed_download": False,
    "failed_launch": False,
    "check_delay": 0,
}
artifact = b"MZ" + b"synthetic installer" * 4096
checksum = hashlib.sha256(artifact).hexdigest()
source = "a" * 40
manifest = {"version": "2.0.0", "sha": source, "sha256": checksum, "installer": INSTALLER}
release = {
    "tag_name": "v2.0.0",
    "draft": False,
    "prerelease": False,
    "assets": [
        {"name": INSTALLER, "id": 1, "state": "uploaded", "size": len(artifact)},
        {"name": "release.json", "id": 2, "state": "uploaded", "size": 200},
        {"name": "SHA256SUMS", "id": 3, "state": "uploaded", "size": 87},
    ],
}


class Transfer(io.BytesIO):
    def read(self, size=-1):
        time.sleep(0.005)
        return super().read(min(size, 512) if size > 0 else size)


class Transport:
    def open(self, request, timeout):
        url = request.full_url
        if url.endswith("/latest"):
            time.sleep(state["check_delay"])
            return io.BytesIO(json.dumps(release).encode())
        if "/git/ref/tags/" in url:
            return io.BytesIO(json.dumps({"object": {"type": "commit", "sha": source}}).encode())
        if url.endswith("/assets/2"):
            return io.BytesIO(json.dumps(manifest).encode())
        if url.endswith("/assets/3"):
            return io.BytesIO((checksum + "  " + INSTALLER + "\n").encode())
        if url.endswith("/assets/1"):
            if not state["failed_download"]:
                state["failed_download"] = True
                raise urllib.error.URLError("Synthetic interrupted transfer")
            return Transfer(artifact)
        raise ValueError("Unexpected fixture endpoint")


def make_updates(storage):
    root = storage.core.CONFIG_DIR / "update-fixture/app"
    root.mkdir(parents=True, exist_ok=True)
    atomic_json(
        root / "version.json",
        {"version": "1.0.0", "sha": "b" * 40, "repository": "dalehayesiii/music-maker"},
    )
    (root.parent / "python").mkdir(exist_ok=True)
    (root.parent / "python/python.exe").write_bytes(b"Synthetic runtime boundary")
    helper = root / "scripts/windows/app_update.ps1"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text("# Fixture launcher is injected")
    manager = Updates(
        storage, root=root, opener=Transport(), token_source=lambda: [("", "Fixture")]
    )
    manager.supported = True
    manager.state["supported"] = True

    def launch(command, **_kwargs):
        if not state["failed_launch"]:
            state["failed_launch"] = True
            raise OSError("Synthetic installer helper launch failed; retry.")
        plan = json.loads(Path(command[-1]).read_text())
        atomic_json(Path(plan["status"]), {"phase": "waiting"})

        def restart():
            api.state.service.handoff = False
            manager.identity.update(version="2.0.0", sha=source)
            manager.set_state(
                phase="current",
                version="2.0.0",
                available_version=None,
                message="TrogloDAW is up to date.",
            )

        threading.Timer(1.5, restart).start()
        return SimpleNamespace(poll=lambda: None)

    manager.launcher = launch
    return manager


def fixture_model_install(_model, progress, canceled):
    # External model acquisition/inference tooling is replaced; service job lifecycle is real.
    for unit in range(300):
        if canceled():
            raise Canceled("Synthetic setup canceled; partial downloads can resume")
        progress(
            "Downloading synthetic model fixture",
            unit / 300,
            stage="downloading",
            units_complete=unit,
            units_total=300,
            downloaded=unit,
            total_bytes=300,
            download_bytes_complete=unit,
            download_bytes_total=300,
            destination="Synthetic selected-drive model storage",
        )
        time.sleep(0.1)
    return {"message": "Synthetic fixture complete"}


api = app.create_app(updates_factory=make_updates, quit_callback=lambda: None)


@api.post("/api/fixture/busy")
def busy(values: dict):
    service = api.state.service
    if values.get("active"):
        service.jobs["fixture"] = {"status": "running", "action": "fixture"}
    else:
        service.jobs.pop("fixture", None)
    return {"message": "Fixture processing state changed"}


@api.post("/api/fixture/setup")
def setup_fixture():
    api.state.service.models.install = fixture_model_install
    return {"message": "External model acquisition fixture enabled"}


@api.post("/api/fixture/check-delay")
def check_delay(values: dict):
    state["check_delay"] = min(3, max(0, float(values.get("seconds", 0))))
    return {"message": "Synthetic release delay configured"}


@api.post("/api/fixture/stop")
def stop():
    threading.Timer(0.2, lambda: os._exit(0)).start()
    return {"message": "Fixture stopping"}


# create_app mounts the UI last. Newly added fixture routes must precede that mount.
api.router.routes.sort(key=lambda route: getattr(route, "name", None) == "frontend")
uvicorn.run(api, host="127.0.0.1", port=args.port, log_config=None)
