import threading
import time

import numpy as np
from fastapi.testclient import TestClient

from app import create_app

HEADERS = {"X-TrogloDAW-Request": "1"}


def job(client, action, values):
    response = client.post("/api/jobs", json={"action": action, "values": values}, headers=HEADERS)
    assert response.status_code == 200
    jid = response.json()["id"]
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        state = client.get(f"/api/jobs/{jid}").json()
        if state["status"] in {"complete", "failed"}:
            return state
        time.sleep(0.02)
    raise AssertionError("Worker did not complete")


def test_upload_import_media_and_catalog(core, tmp_path):
    source = tmp_path / "test.wav"
    core.save_wav(source, core.synth_voice(seconds=1))
    with TestClient(create_app(core)) as client:
        uploaded = client.post(
            "/api/uploads",
            files={"file": ("../take.wav", source.read_bytes(), "audio/wav")},
            headers=HEADERS,
        ).json()
        assert uploaded["name"] == "take.wav"
        result = job(
            client, "import", {"uploads": [uploaded["id"]], "type": "voice", "tags": "test, demo"}
        )
        assert result["status"] == "complete"
        assert "Imported take" in result["result"]["message"]
        items = client.get("/api/library").json()["items"]
        assert items[0]["tags"] == ["test", "demo"]
        preview = client.get(f"/api/items/{items[0]['id']}").json()
        audio = client.get(preview["audio"]["url"])
        assert audio.content[:4] == b"RIFF"
        assert "inline" in audio.headers["content-disposition"]
        assert (
            "attachment"
            in client.get(preview["audio"]["url"] + "?download=true").headers["content-disposition"]
        )
        assert client.get("/api/media/unknown").status_code == 404
        assert client.get("/api/items/unknown").status_code == 404
        assert client.get("/api/jobs/unknown").status_code == 404


def test_jobs_retain_engine_behavior_and_mix_recipe(core):
    voice = core._new_entry("voice", "test voice", core.synth_voice(seconds=1), "test")
    settings = {"bpm": 120, "bars": 1, "seed": 42, "key": "A minor", "style": "boombap"}
    expected = core.render_generated(settings)
    with TestClient(create_app(core)) as client:
        result = job(client, "generate", {"settings": settings, "name": "test beat"})
        assert result["status"] == "complete"
        beat = core.get_item("test beat")
        # WAV is PCM16; compare to the same original core renderer after quantization.
        np.testing.assert_allclose(core.load(beat["path"]), expected, atol=1 / 32768)
        preview = job(
            client, "fx", {"voice": voice["id"], "settings": {"pitch": -2}, "save": False}
        )
        assert preview["result"]["message"] == "Preview only (not saved)"
        assert len(core.list_items("voice")) == 1
        saved = job(client, "fx", {"voice": voice["id"], "settings": {"pitch": -2}, "save": True})
        assert "Saved new voice" in saved["result"]["message"]
        mixed = job(
            client,
            "mix",
            {
                "voice": voice["id"],
                "music": beat["id"],
                "settings": {"music_vol": -4},
                "name": "api mix",
            },
        )
        assert mixed["result"]["download"]
        entry = core.get_item("api mix")
        recipe = client.get(f"/api/recipes/{entry['id']}").json()
        assert recipe["voice"] == voice["id"] and recipe["music"] == beat["id"]
        assert recipe["name"] == "api mix_remix"
        assert recipe["settings"]["music_vol"] == -4
        bad_json = job(
            client, "mix", {"voice": voice["id"], "music": beat["id"], "settings": {}, "fx": "bad"}
        )
        assert bad_json["result"]["message"].startswith("Bad voice FX JSON:")


def test_validation_messages_and_production(core, monkeypatch):
    voice = core._new_entry("voice", "test voice", core.synth_voice(seconds=2), "test")
    with TestClient(create_app(core)) as client:
        assert job(client, "fx", {})["result"]["message"] == "Pick a voice."
        assert job(client, "mix", {})["result"]["message"] == "Pick a voice and a music track."
        assert (
            job(client, "produce", {})["result"]["message"]
            == "Pick a voice or drop a recording first."
        )
        produced = job(
            client,
            "produce",
            {"voice": voice["id"], "style": "lofi", "seed": 42, "bpm": 120, "tune": "off"},
        )
        assert produced["status"] == "complete"
        assert produced["result"]["production"]["params"]["seed"] == 42
        assert produced["result"]["song"]["true_peak_db"] <= -0.9

        def fail(*args, **kwargs):
            raise ValueError("example failure")

        monkeypatch.setattr(core, "produce", fail)
        assert (
            job(client, "produce", {"voice": voice["id"]})["result"]["message"]
            == "Produce failed: example failure"
        )


def test_static_service_and_mutation_boundary(core, tmp_path):
    (tmp_path / "index.html").write_text("<title>TrogloDAW</title>")
    stopped = threading.Event()
    with TestClient(create_app(core, tmp_path, stopped.set)) as client:
        assert client.get("/").text == "<title>TrogloDAW</title>"
        assert client.get("/api/health").json()["frontend"] is True
        assert client.get("/api/health").json()["product"] == "TrogloDAW"
        assert client.post("/api/shutdown").status_code == 403
        assert (
            client.post("/api/jobs", json={"action": "unknown"}, headers=HEADERS).status_code == 422
        )
        assert (
            client.post("/api/shutdown", headers=HEADERS).json()["message"]
            == "TrogloDAW has stopped. You can close this browser tab."
        )
        assert stopped.wait(2)
