import json
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app
import pytest
from storage import atomic_json
from test_updates import complete, make_update_manager

HEADERS = {"X-TrogloDAW-Request": "1"}


def test_setup_acknowledgment_survives_restart_without_claiming_model_readiness(core):
    with TestClient(app.create_app(core)) as client:
        assert client.get("/api/library").json()["storage"]["setup_seen"] is False
        assert client.post("/api/setup/acknowledge").status_code == 403
        assert client.post("/api/setup/acknowledge", headers=HEADERS).status_code == 200
        assert not client.get("/api/library").json()["models"]["ready"]
    with TestClient(app.create_app(core)) as client:
        assert client.get("/api/library").json()["storage"]["setup_seen"] is True


@pytest.fixture
def update_manager(core, tmp_path):
    return make_update_manager(core, tmp_path)


def client_for(core, manager, callback):
    manager.storage.persist()

    def factory(storage):
        manager.storage = storage
        return manager

    return TestClient(
        app.create_app(core, quit_callback=callback, updates_factory=factory),
        base_url="http://127.0.0.1:9876",
    )


def prepare(manager):
    complete(manager, "check")
    complete(manager, "download")
    helper = manager.root / "scripts/windows/app_update.ps1"
    helper.parent.mkdir(parents=True)
    helper.write_text("# Synthetic helper; launcher is injected")


def test_update_mutations_and_preferences_use_the_local_boundary(core, update_manager):
    manager, _ = update_manager
    manager.storage.preferences["check_updates"] = False
    with client_for(core, manager, lambda: None) as client:
        assert client.get("/api/updates").json()["version"] == "1.0.0"
        assert (
            client.post("/api/updates/preferences", json={"check_on_startup": False}).status_code
            == 403
        )
        response = client.post(
            "/api/updates/preferences", headers=HEADERS, json={"check_on_startup": False}
        )
        assert response.status_code == 200 and response.json()["check_on_startup"] is False
        assert json.loads(manager.storage.config_path.read_text())["check_updates"] is False
        assert client.get("/api/health").json()["sha"] == "b" * 40


def test_private_access_never_echoes_the_request_secret(core, update_manager, monkeypatch):
    manager, _ = update_manager
    saved = []
    monkeypatch.setattr(app.credentials, "save", lambda token, _target: saved.append(token))
    manager.storage.preferences["check_updates"] = False
    with client_for(core, manager, lambda: None) as client:
        response = client.post(
            "/api/updates/access", headers=HEADERS, json={"token": "synthetic_private_secret"}
        )
        assert response.status_code == 200 and response.json()["saved_access"]
        assert "synthetic_private_secret" not in response.text
        assert "synthetic_private_secret" not in manager.storage.config_path.read_text()
        assert saved == ["synthetic_private_secret"]
        response = client.post(
            "/api/updates/access", headers=HEADERS, json={"token": ["synthetic_private_secret"]}
        )
        assert response.status_code == 400 and "synthetic_private_secret" not in response.text


def test_processing_uploads_and_recording_leases_block_handoff(core, update_manager):
    manager, _ = update_manager
    prepare(manager)
    manager.storage.preferences["check_updates"] = False
    with client_for(core, manager, lambda: None) as client:
        service = client.app.state.service
        service.jobs["fixture"] = {"status": "running", "action": "fixture"}
        assert client.post("/api/updates/apply", headers=HEADERS).status_code == 409
        service.jobs.clear()
        service.active_uploads = 1
        assert client.post("/api/updates/apply", headers=HEADERS).status_code == 409
        service.active_uploads = 0
        sessions = [uuid.uuid4().hex, uuid.uuid4().hex]
        for session in sessions:
            assert (
                client.post(
                    "/api/updates/capture",
                    headers=HEADERS,
                    json={"client_id": session, "active": True},
                ).status_code
                == 200
            )
        assert client.post("/api/updates/apply", headers=HEADERS).status_code == 409
        client.post(
            "/api/updates/capture",
            headers=HEADERS,
            json={"client_id": sessions[0], "active": False},
        )
        assert client.post("/api/updates/apply", headers=HEADERS).status_code == 409
        service.recording_leases[sessions[1]] = time.monotonic() - 1
        assert not service.handoff


def test_failed_helper_launch_keeps_service_and_admission_available(core, update_manager):
    manager, _ = update_manager
    prepare(manager)
    manager.storage.preferences["check_updates"] = False
    callbacks = []

    def fail_launch(*_args, **_kwargs):
        raise OSError("Synthetic helper launch failed")

    manager.launcher = fail_launch
    with client_for(core, manager, lambda: callbacks.append(True)) as client:
        assert client.post("/api/updates/apply", headers=HEADERS).status_code == 409
        assert not client.app.state.service.handoff and not callbacks
        assert client.get("/api/health").status_code == 200
        assert (
            client.post("/api/jobs", headers=HEADERS, json={"action": "unknown"}).status_code == 422
        )
        assert manager.snapshot()["phase"] == "ready"


def test_acknowledged_handoff_reserves_new_work_and_has_no_credentials(core, update_manager):
    manager, _ = update_manager
    prepare(manager)
    manager.storage.preferences["check_updates"] = False
    launched = []
    callbacks = []

    def acknowledge(command, **options):
        plan = json.loads(Path(command[-1]).read_text())
        assert "synthetic_token" not in json.dumps(plan)
        assert options["creationflags"] == 0x08000000
        assert not Path(command[-3]).is_relative_to(manager.root.parent)
        atomic_json(Path(plan["status"]), {"phase": "waiting"})
        launched.append(command)
        return SimpleNamespace(poll=lambda: None)

    manager.launcher = acknowledge
    with client_for(core, manager, lambda: callbacks.append(True)) as client:
        response = client.post("/api/updates/apply", headers=HEADERS)
        assert response.status_code == 200 and response.json()["phase"] == "handoff"
        assert launched and client.app.state.service.handoff
        assert (
            client.post("/api/jobs", headers=HEADERS, json={"action": "unknown"}).status_code == 409
        )
        assert (
            client.post(
                "/api/updates/capture",
                headers=HEADERS,
                json={"client_id": uuid.uuid4().hex, "active": True},
            ).status_code
            == 409
        )
        assert client.get("/api/updates").json()["phase"] == "handoff"
        time.sleep(0.9)
        assert callbacks == [True]
