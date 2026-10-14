import hashlib
import io
import os
import sys

import pytest

import models
from models import Canceled, cache_environment, download


def test_runtime_installation_reports_safe_package_activity_without_guessing_totals():
    events = []
    command = [
        sys.executable,
        "-c",
        "print('Downloading torch (2.5 GiB)'); print('https://example.invalid/private-secret'); print('Downloaded torch'); print('Installed 3 packages in 1s')",
    ]
    models.run_setup(
        command,
        dict(os.environ),
        lambda message, fraction=0, **details: events.append({"message": message, **details}),
        lambda: False,
    )
    assert any("Downloading torch (2.5 GiB)" in event["message"] for event in events)
    assert any("Installed 3 packages" in event["message"] for event in events)
    assert all("private-secret" not in event["message"] for event in events)
    assert any(event.get("runtime_running") for event in events)
    assert events[-1]["runtime_running"] is False
    assert all("units_total" not in event for event in events)


def asset(data):
    return {
        "path": "checkpoints/weights.bin",
        "url": "https://example.invalid/weights",
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def partial_file(root, data):
    return root / "cache" / "downloads" / (asset(data)["sha256"] + ".partial")


class Response(io.BytesIO):
    def __init__(self, data, status=200):
        super().__init__(data)
        self.status = status


def test_verified_asset_reused_without_network(tmp_path, monkeypatch):
    data = b"verified weights"
    path = tmp_path / "checkpoints" / "weights.bin"
    path.parent.mkdir()
    path.write_bytes(data)

    def no_network(*_args, **_kwargs):
        raise AssertionError("Network called for a verified asset")

    monkeypatch.setattr(models.urllib.request, "urlopen", no_network)
    result, owned = download(asset(data), tmp_path, lambda *_args, **_kwargs: None, lambda: False)
    assert result == path and not owned


def test_resume_range_and_checksum(tmp_path, monkeypatch):
    data = b"verified weights"
    partial = partial_file(tmp_path, data)
    partial.parent.mkdir(parents=True)
    partial.write_bytes(data[:5])

    def response(request, **_):
        assert request.headers["Range"] == "bytes=5-"
        return Response(data[5:], 206)

    monkeypatch.setattr(models.urllib.request, "urlopen", response)
    path, owned = download(asset(data), tmp_path, lambda *_args, **_kwargs: None, lambda: False)
    assert owned and path.read_bytes() == data and not partial.exists()


def test_range_ignored_restarts_safely(tmp_path, monkeypatch):
    data = b"verified weights"
    partial = partial_file(tmp_path, data)
    partial.parent.mkdir(parents=True)
    partial.write_bytes(data[:5])
    monkeypatch.setattr(models.urllib.request, "urlopen", lambda *_args, **_kwargs: Response(data))
    path, _ = download(asset(data), tmp_path, lambda *_args, **_kwargs: None, lambda: False)
    assert path.read_bytes() == data


def test_invalid_download_never_activates(tmp_path, monkeypatch):
    monkeypatch.setattr(
        models.urllib.request, "urlopen", lambda *_args, **_kwargs: Response(b"bad")
    )
    with pytest.raises(ValueError, match="verification"):
        download(asset(b"good"), tmp_path, lambda *_args, **_kwargs: None, lambda: False)
    assert not (tmp_path / "checkpoints" / "weights.bin").exists()


def test_canceled_download_keeps_partial_for_resume(tmp_path, monkeypatch):
    data = b"x" * (1024 * 1024 + 1)
    monkeypatch.setattr(models.urllib.request, "urlopen", lambda *_args, **_kwargs: Response(data))
    count = 0

    def canceled():
        nonlocal count
        count += 1
        return count > 1

    with pytest.raises(Canceled):
        download(asset(data), tmp_path, lambda *_args, **_kwargs: None, canceled)
    assert partial_file(tmp_path, data).stat().st_size == 1024 * 1024
    assert not (tmp_path / "checkpoints" / "weights.bin").exists()


def test_cache_environment_keeps_assets_in_selected_folder(tmp_path):
    env = cache_environment(tmp_path)
    for key in [
        "HF_HOME",
        "TORCH_HOME",
        "UV_CACHE_DIR",
        "TEMP",
        "TMP",
        "TRITON_CACHE_DIR",
        "TORCHINDUCTOR_CACHE_DIR",
    ]:
        assert env[key].startswith(str(tmp_path))


def test_canceled_partial_is_owned_for_uninstall_while_legacy_partial_is_preserved(
    core, monkeypatch
):
    from storage import Storage, remove_owned_models

    storage = Storage(core)
    root = storage.models
    owner = storage.preferences["installation_id"]
    legacy = root / "checkpoints" / "weights.bin.partial"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"external legacy transfer")
    data = b"x" * (1024 * 1024 + 1)
    monkeypatch.setattr(models.urllib.request, "urlopen", lambda *_args, **_kwargs: Response(data))
    calls = 0

    def canceled():
        nonlocal calls
        calls += 1
        return calls > 1

    with pytest.raises(Canceled):
        download(
            asset(data),
            root,
            lambda *_args, **_kwargs: None,
            canceled,
            owner=owner,
            record=lambda path: storage.owned(root, [path]),
        )
    partial = root / "cache" / owner / "downloads" / (asset(data)["sha256"] + ".partial")
    assert partial.stat().st_size == 1024 * 1024
    removed = remove_owned_models(storage.config_path)
    assert str(partial) in removed["removed"] and not partial.exists()
    assert legacy.read_bytes() == b"external legacy transfer"


def test_existing_different_file_is_preserved(tmp_path):
    path = tmp_path / "checkpoints/weights.bin"
    path.parent.mkdir()
    path.write_bytes(b"someone else's asset")
    with pytest.raises(ValueError, match="different contents"):
        download(asset(b"good"), tmp_path, lambda *_args, **_kwargs: None, lambda: False)
    assert path.read_bytes() == b"someone else's asset"


def test_runtime_fingerprint_ignores_unrelated_packages_but_tracks_transitive_pins(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="app"\n[project.optional-dependencies]\ninference=["model==1"]\n'
    )
    prefix = '[[package]]\nname="app"\nversion="0"\n[package.optional-dependencies]\ninference=[{name="model"}]\n[[package]]\nname="model"\nversion="1"\ndependencies=[{name="engine"}]\n[[package]]\nname="engine"\nversion="1"\n'
    lock = tmp_path / "uv.lock"
    lock.write_text(prefix)
    first = models.runtime_signature(tmp_path)
    lock.write_text(prefix + '[[package]]\nname="unrelated"\nversion="2"\n')
    assert models.runtime_signature(tmp_path) == first
    lock.write_text(prefix.replace('name="engine"\nversion="1"', 'name="engine"\nversion="2"'))
    assert models.runtime_signature(tmp_path) != first


def test_complete_partial_can_finish_offline_with_measured_verification(tmp_path, monkeypatch):
    data = b"verified weights"
    partial = partial_file(tmp_path, data)
    partial.parent.mkdir(parents=True)
    partial.write_bytes(data)
    events, owned = [], []

    def no_network(*_, **__):
        raise AssertionError("A complete verified partial does not need a new download")

    monkeypatch.setattr(models.urllib.request, "urlopen", no_network)
    path, acquired = download(
        asset(data),
        tmp_path,
        lambda message, fraction=0, **event: events.append(event),
        lambda: False,
        record=owned.append,
    )
    assert acquired and path.read_bytes() == data and not partial.exists()
    assert path in owned
    assert events[0]["units_complete"] == 0
    assert events[-1]["units_complete"] == len(data)
    assert all(event["stage"] == "verifying" for event in events)


def test_cancel_cached_verification_preserves_existing_asset(tmp_path):
    data = b"verified weights"
    path = tmp_path / asset(data)["path"]
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    events = []
    with pytest.raises(Canceled, match="verification"):
        download(
            asset(data),
            tmp_path,
            lambda message, fraction=0, **event: events.append(event),
            lambda: True,
        )
    assert path.read_bytes() == data
    assert events[0]["stage"] == "verifying" and events[0]["units_complete"] == 0


def test_fresh_install_reuses_retained_assets_and_reports_real_installation_checkpoints(
    core, monkeypatch
):
    import io
    import zipfile
    from storage import Storage

    storage = Storage(core)
    manager = models.Models(storage)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("revision/acestep/__init__.py", "# Synthetic pinned inference code")
    code_asset = {**asset(archive.getvalue()), "path": "archives/code.zip"}
    weight_asset = asset(b"synthetic pinned weights")
    manager.manifest = {
        "runtime": code_asset,
        "runtime_revision": "synthetic-revision",
        "models": {"fixture": {"name": "Fixture", "assets": [weight_asset]}},
    }
    monkeypatch.setattr(models, "runtime_signature", lambda: "synthetic-lock")
    from types import SimpleNamespace

    monkeypatch.setattr(models.shutil, "disk_usage", lambda _path: SimpleNamespace(free=1024**3))
    monkeypatch.setattr(models, "run_setup", lambda *args, **kwargs: None)

    def no_network(*args, **kwargs):
        raise AssertionError("Retained complete pinned files require no network")

    monkeypatch.setattr(models.urllib.request, "urlopen", no_network)
    for entry, content in [
        (code_asset, archive.getvalue()),
        (weight_asset, b"synthetic pinned weights"),
    ]:
        path = storage.models / entry["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    packages = storage.models / "runtime-packages/synthetic-lock"
    packages.mkdir(parents=True)
    (packages / ".complete").write_text("synthetic-lock")
    storage.preferences["music_model"] = "fixture"
    storage.persist()
    events = []
    result = manager.install(
        "fixture", lambda _message, _fraction=0, **event: events.append(event), lambda: False
    )
    assert result["ready"]
    checkpoints = [
        event["installation_steps_complete"]
        for event in events
        if "installation_steps_complete" in event
    ]
    assert checkpoints == sorted(checkpoints) and checkpoints[-1] == 8
    assert events[-1]["installation_steps_total"] == 8
    assert events[-1]["setup_phase"] == "installation"
    assert any(event.get("stage") == "verifying" and event.get("units_total") for event in events)
    # Upgrades keep the music model ready without the newly optional detector.
    phrase_asset = {
        **asset(b"synthetic phrase detector"),
        "path": "checkpoints/source-analysis/detector.jit",
    }
    manager.manifest["source_analysis"] = {
        "id": "fixture-vad",
        "name": "Synthetic VAD",
        "assets": [phrase_asset],
    }
    assert manager.ready() and manager.source_analysis_ready() is None
    assert "not installed" in manager.describe()["voice_models"][-1]["name"]
    phrase_path = storage.models / phrase_asset["path"]
    requests = []

    def phrase_download(request, **kwargs):
        requests.append(request.full_url)
        assert request.full_url == phrase_asset["url"]
        return Response(b"synthetic phrase detector")

    monkeypatch.setattr(models.urllib.request, "urlopen", phrase_download)
    manager.install("fixture", lambda *a, **k: None, lambda: False)
    assert requests == [phrase_asset["url"]]
    monkeypatch.setattr(models.urllib.request, "urlopen", no_network)
    manager.install("fixture", lambda *a, **k: None, lambda: False)
    assert manager.source_analysis_ready()["id"] == "fixture-vad"
    assert "ready" in manager.describe()["voice_models"][-1]["name"]
    phrase_path.write_bytes(b"changed!! phrase detector")
    assert manager.source_analysis_ready() is None and manager.ready()
    phrase_path.write_bytes(b"synthetic phrase detector")
    planner_asset = {**asset(b"synthetic song planner"), "path": "checkpoints/planner/weights.bin"}
    manager.manifest["models"]["fixture"]["planner"] = "fixture-planner"
    manager.manifest["planners"] = {
        "fixture-planner": {"name": "Synthetic planner", "assets": [planner_asset]}
    }
    assert manager.ready() and manager.planner_ready() is None
    assert manager.describe()["ready"] and not manager.describe()["planner"]["ready"]
    planner_path = storage.models / planner_asset["path"]
    planner_path.parent.mkdir(parents=True)
    planner_path.write_bytes(b"synthetic song planner")
    planned = manager.install("fixture", lambda *args, **kwargs: None, lambda: False, planner=True)
    assert planned["ready"] and planned["planner"]["ready"]
    assert manager.planner_ready()
    # Planner-only corruption cannot be hidden behind an unchanged size/ready flag.
    planner_path.write_bytes(b"changed!! song planner")
    assert manager.planner_ready() is None
    assert manager.ready(), "Optional planner damage must not invalidate music generation"
    planner_path.write_bytes(b"synthetic song planner")
    # Reinstallation has a new identity, requiring explicit verification rather than trusting the old ready marker.
    owner = storage.preferences["installation_id"]
    storage.config_path.unlink()
    fresh = Storage(core)
    assert fresh.preferences["installation_id"] != owner and not fresh.describe()["setup_seen"]
    fresh.preferences["music_model"] = "fixture"
    reused = models.Models(fresh)
    reused.manifest = manager.manifest
    assert reused.ready() is None
    assert reused.install("fixture", lambda *args, **kwargs: None, lambda: False)["ready"]
    assert not reused.describe()["planner"]["ready"]
    assert reused.source_analysis_ready()
