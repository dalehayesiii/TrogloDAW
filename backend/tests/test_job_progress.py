import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app import create_app

HEADERS = {"X-TrogloDAW-Request": "1"}


def test_optional_hardware_history_write_failure_does_not_fail_processing(core, monkeypatch):
    api = create_app(core)
    service = api.state.service

    def read_only():
        raise OSError("Read-only timing preferences")

    monkeypatch.setattr(service.storage, "persist", read_only)

    def execute(_action, _values, progress, _canceled):
        progress("Working", stage="rendering", timing_profile={"backend": "cpu", "gpu": "none"})
        return service.result("Done")

    service.execute = execute
    with TestClient(api) as client:
        jid = client.post("/api/jobs", headers=HEADERS, json={"action": "folder"}).json()["id"]
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            state = client.get("/api/jobs/" + jid).json()
            if state["status"] in {"complete", "failed"}:
                break
            time.sleep(0.01)
        assert state["status"] == "complete"


def test_queue_estimate_excludes_later_jobs_and_cancel_reconnect_retains_terminal(core):
    entered, release = threading.Event(), threading.Event()
    api = create_app(core)
    service = api.state.service

    def execute(_action, values, progress, canceled):
        if values.get("name") == "first":
            entered.set()
            assert release.wait(5)
        progress("Saving", stage="saving", units_complete=0, units_total=1)
        progress("Saved", stage="saving", units_complete=1, units_total=1)
        return service.result("Done")

    service.execute = execute
    profile = service.timing_profile("folder", {"name": "first"})
    for elapsed in [10, 11, 12]:
        service.history.observe("request", profile, elapsed)
    with TestClient(api) as client:

        def submit(name):
            return client.post(
                "/api/jobs", headers=HEADERS, json={"action": "folder", "values": {"name": name}}
            ).json()["id"]

        first = submit("first")
        assert entered.wait(2)
        second, third = submit("second"), submit("third")
        before = client.get(f"/api/jobs/{second}").json()
        later = client.get(f"/api/jobs/{third}").json()
        assert before["status"] == "queued" and before["elapsed_seconds"] == 0
        assert before["queue_remaining"]["high"] < later["queue_remaining"]["low"]
        assert client.post(f"/api/jobs/{second}/cancel", headers=HEADERS).status_code == 200
        assert client.get(f"/api/jobs/{second}").json()["cancel_requested"]
        # A canceled queued request has no predicted DSP duration for following work.
        assert (
            client.get(f"/api/jobs/{third}").json()["queue_remaining"]["high"]
            <= before["queue_remaining"]["high"]
        )
        release.set()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            states = client.get("/api/jobs").json()["jobs"]
            if all(state["status"] in {"complete", "canceled"} for state in states):
                break
            time.sleep(0.01)
        by_id = {state["id"]: state for state in states}
        assert by_id[first]["status"] == by_id[third]["status"] == "complete"
        assert by_id[second]["status"] == "canceled"
        for state in states:
            assert state["request_remaining"] is None and state["stage_remaining"] is None
            assert state["estimate_state"] == "finished"


def test_cancellation_during_output_commit_retains_completed_song(core, monkeypatch):
    api = create_app(core)
    service = api.state.service
    service.songs.local_inference = False

    def invoke(action, values, _progress, _canceled):
        assert action == "generate"
        path = Path(values["output"]) / "generated.wav"
        core.save_wav(path, core.synth_voice(10))
        return {"audio": str(path)}

    service.songs.invoke = invoke
    original_export = core.to_mp3

    def export(path, *args, **kwargs):
        current = next(jid for jid, job in service.jobs.items() if job["status"] == "running")
        service.cancel_events[current].set()
        return original_export(path, *args, **kwargs)

    monkeypatch.setattr(core, "to_mp3", export)
    with TestClient(api) as client:
        submitted = client.post(
            "/api/jobs",
            headers=HEADERS,
            json={
                "action": "song_generate",
                "values": {"lyrics": "Keep these words", "options": {"duration": 10}, "count": 2},
            },
        ).json()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            job = client.get("/api/jobs/" + submitted["id"]).json()
            if job["status"] in {"canceled", "failed", "complete"}:
                break
            time.sleep(0.02)
        assert job["status"] == "canceled"
        outcomes = job["result"]["outcomes"]
        assert [output["status"] for output in outcomes] == ["complete", "canceled"]
        assert Path(core.get_item(outcomes[0]["song"]["id"])["path"]).is_file()
        assert job["request_remaining"] is None
