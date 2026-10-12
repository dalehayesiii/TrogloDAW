import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import folders
from app import create_app

HEADERS = {"X-TrogloDAW-Request": "1"}


@pytest.mark.skipif(not folders.available(), reason="Windows native dialog adapter")
def test_real_native_dialog_initializes_and_releases_without_showing_ui(tmp_path):
    assert folders.choose(str(tmp_path), "TrogloDAW test folder", probe=True) is None


@pytest.mark.parametrize("selection", [None, "selected"])
def test_native_selection_boundary_leaves_preferences_unchanged_until_confirmation(
    core, tmp_path, selection
):
    calls = []
    destination = str(tmp_path / "different folder") if selection else None

    def picker(initial, title):
        calls.append((initial, title))
        return destination

    api = create_app(core, folder_picker=picker)
    with TestClient(api) as client:
        old = client.get("/api/library").json()["storage"]
        response = client.post("/api/storage/pick", headers=HEADERS, json={"kind": "model"})
        assert response.status_code == 200 and response.json()["path"] == destination
        assert calls == [(old["model_dir"], "Choose model storage folder")]
        assert client.get("/api/library").json()["storage"]["model_dir"] == old["model_dir"]
        assert client.post("/api/storage/pick", json={"kind": "model"}).status_code == 403
        assert (
            client.post("/api/storage/pick", headers=HEADERS, json={"kind": "invalid"}).status_code
            == 422
        )


def test_picker_failure_is_recoverable_and_does_not_change_folder(core):
    def picker(*_):
        raise OSError("Folder dialog unavailable")

    api = create_app(core, folder_picker=picker)
    with TestClient(api) as client:
        before = client.get("/api/library").json()["storage"]
        response = client.post("/api/storage/pick", headers=HEADERS, json={"kind": "library"})
        assert response.status_code == 503 and "unavailable" in response.json()["detail"]
        assert client.get("/api/library").json()["storage"] == before


def test_library_move_preserves_registered_media_and_portable_recipe(core, monkeypatch, tmp_path):
    monkeypatch.delenv("TROGLODAW_LIBRARY")
    item = core._new_entry(
        "voice", "Synthetic source", core.synth_voice(1), "fixture", recipe={"op": "fixture"}
    )
    original = Path(item["path"])
    api = create_app(core)
    service = api.state.service
    media = service.file(original)
    old = core.LIB
    (old / "personal.txt").write_text("unrelated")
    new = tmp_path / "moved library"
    with TestClient(api) as client:
        assert client.get("/api/library").json()["storage"]["library_has_data"]
        jid = client.post(
            "/api/jobs",
            headers=HEADERS,
            json={
                "action": "storage",
                "values": {"kind": "library", "path": str(new), "mode": "move"},
            },
        ).json()["id"]
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            job = client.get("/api/jobs/" + jid).json()
            if job["status"] in {"complete", "failed"}:
                break
            time.sleep(0.01)
        assert job["status"] == "complete", job
        assert client.get(media["url"]).status_code == 200
        moved = core.get_item(item["id"])
        assert Path(moved["path"]).is_relative_to(new) and moved["recipe"] == {"op": "fixture"}
        assert not original.exists() and (old / "personal.txt").read_text() == "unrelated"
        assert (new / "catalog.json").is_file() and not (new / "personal.txt").exists()
