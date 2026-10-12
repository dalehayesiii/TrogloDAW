import json
import subprocess
import sys
from pathlib import Path

import pytest

from storage import Storage, atomic_json, copy_verified, remove_owned_models, safe_file
from storage import writable_root
from types import SimpleNamespace
import storage as storage_module


def test_parallel_setup_and_audio_cache_ownership_retains_both_records(core, tmp_path, monkeypatch):
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    storage = Storage(core)
    root = tmp_path / "shared-model-cache"
    root.mkdir()
    first, second = root / "setup.bin", root / "audio.bin"
    first.write_bytes(b"synthetic setup")
    second.write_bytes(b"synthetic audio cache")
    entered, released = threading.Event(), threading.Event()
    original = storage_module.digest

    def digest(path):
        if path == first:
            entered.set()
            assert released.wait(3)
        return original(path)

    monkeypatch.setattr(storage_module, "digest", digest)
    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(storage.owned, root, [first])
        assert entered.wait(2)
        two = pool.submit(storage.owned, root, [second])
        time.sleep(0.05)
        released.set()
        one.result(timeout=3)
        two.result(timeout=3)
    marker = root / ".troglodaw" / (storage.preferences["installation_id"] + ".json")
    assert set(json.loads(marker.read_text())["files"]) == {"setup.bin", "audio.bin"}


def test_setup_history_belongs_to_installation_preferences_not_retained_assets(core):
    storage = Storage(core)
    assert storage.describe()["setup_seen"] is False
    assert Storage(core).describe()["setup_seen"] is False
    storage.preferences["setup_seen"] = True
    storage.persist()
    assert Storage(core).describe()["setup_seen"] is True
    # Upgrades of pre-flag installations retain their established setup history.
    storage.preferences.pop("setup_seen")
    storage.persist()
    assert Storage(core).describe()["setup_seen"] is True
    # Uninstall removes preferences, even when asset folders remain.
    storage.config_path.unlink()
    assert Storage(core).describe()["setup_seen"] is False


def test_reserved_program_paths_are_rejected_and_legacy_data_is_preserved(tmp_path):
    app_root = tmp_path / "installed/app"
    library = app_root / "personal library"
    library.mkdir(parents=True)
    audio = library / "song.wav"
    audio.write_bytes(b"synthetic personal data")
    config = app_root / "config.local.json"
    atomic_json(config, {"library_dir": str(library)})
    with pytest.raises(ValueError, match="program folders"):
        storage_module.guard_uninstall(config, app_root)
    assert audio.read_bytes() == b"synthetic personal data"
    with pytest.raises(ValueError, match="program folders"):
        storage_module.protect_location(app_root.parent / "python/models", app_root)
    storage_module.protect_location(app_root.parent / "models", app_root)


def test_uninstall_cli_reports_bounded_counts(core, tmp_path):
    storage = Storage(core)
    root = tmp_path / "models"
    root.mkdir()
    assets = []
    for index in range(1000):
        asset = root / f"canceled-setup-cache-fragment-{index:04}.bin"
        asset.write_bytes(b"synthetic cache")
        assets.append(asset)
    shared = root / "shared.bin"
    shared.write_bytes(b"shared")
    unrelated = root / "personal.txt"
    unrelated.write_bytes(b"unrelated")
    storage.owned(root, [*assets, shared])
    atomic_json(root / ".troglodaw" / "otherowner.json", {"files": {"shared.bin": "other"}})
    process = subprocess.run(
        [sys.executable, storage_module.__file__, str(storage.config_path)],
        capture_output=True,
        check=True,
    )
    assert json.loads(process.stdout) == {"removed": 1000, "retained": 1}
    assert len(process.stdout) < 100
    assert not process.stderr
    assert all(not asset.exists() for asset in assets)
    assert shared.exists() and unrelated.exists()


def test_uninstall_cli_preserves_actual_failure_status(core, tmp_path):
    storage = Storage(core)
    root = tmp_path / "models"
    root.mkdir()
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"preserve")
    storage.preferences["model_roots"] = [str(root)]
    storage.persist()
    atomic_json(
        root / ".troglodaw" / f"{storage.preferences['installation_id']}.json",
        {"files": {"../outside.bin": "unsafe"}},
    )
    process = subprocess.run(
        [sys.executable, storage_module.__file__, str(storage.config_path)],
        capture_output=True,
    )
    assert process.returncode != 0
    assert not process.stdout
    assert b"Unsafe managed asset path" in process.stderr
    assert outside.read_bytes() == b"preserve"


def test_relocation_verifies_and_preserves_source(tmp_path):
    source, destination = tmp_path / "original", tmp_path / "new location"
    source.mkdir()
    (source / "catalog.json").write_text('{"items": []}')
    (source / "nested").mkdir()
    (source / "nested" / "asset.bin").write_bytes(b"asset")
    copy_verified(source, destination, lambda *_, **__: None)
    assert (destination / "nested" / "asset.bin").read_bytes() == b"asset"
    assert (source / "nested" / "asset.bin").read_bytes() == b"asset"
    with pytest.raises(ValueError, match="not empty"):
        copy_verified(source, destination, lambda *_, **__: None)
    with pytest.raises(ValueError, match="contain each other"):
        copy_verified(source, source / "child", lambda *_, **__: None)


def test_interrupted_relocation_keeps_original(tmp_path):
    source = tmp_path / "original"
    source.mkdir()
    (source / "asset.bin").write_bytes(b"asset")

    def interrupt(*_, **__):
        raise OSError("drive disappeared")

    with pytest.raises(OSError, match="disappeared"):
        copy_verified(source, tmp_path / "destination", interrupt)
    assert (source / "asset.bin").read_bytes() == b"asset"
    assert not (tmp_path / "destination").exists()
    assert list(tmp_path.glob(".troglodaw-relocate-*/.relocation.json"))


def test_storage_preferences_survive_restart(core, tmp_path, monkeypatch):
    storage = Storage(core)
    with pytest.raises(ValueError, match="TROGLODAW_LIBRARY"):
        storage.change("library", str(tmp_path / "elsewhere"), "open", lambda *_, **__: None)
    monkeypatch.delenv("TROGLODAW_LIBRARY")
    new = tmp_path / "new library"
    storage.change("library", str(new), "relocate", lambda *_, **__: None)
    models = tmp_path / "model folder"
    storage.change("model", str(models), "open", lambda *_, **__: None)
    restarted = Storage(core)
    assert restarted.describe()["library_dir"] == str(new)
    assert restarted.models == models
    assert json.loads(storage.config_path.read_text())["library_dir"] == str(new)


def test_model_uninstall_preserves_shared_changed_and_unrelated_files(core, tmp_path):
    storage = Storage(core)
    root = tmp_path / "models"
    root.mkdir()
    owned, changed, shared, unrelated = [
        root / name for name in ("owned", "changed", "shared", "notes")
    ]
    for path in (owned, changed, shared, unrelated):
        path.write_bytes(b"original")
    storage.owned(root, [owned, changed, shared])
    atomic_json(root / ".troglodaw" / "otherowner.json", {"files": {"shared": "other"}})
    changed.write_bytes(b"user replacement")
    result = remove_owned_models(storage.config_path)
    assert str(owned) in result["removed"]
    assert not owned.exists()
    assert changed.read_bytes() == b"user replacement"
    assert shared.exists() and unrelated.exists()
    assert len(result["retained"]) == 2


@pytest.mark.parametrize("relative", ["../outside", "nested/../../outside"])
def test_managed_paths_cannot_escape(tmp_path, relative):
    with pytest.raises(ValueError):
        safe_file(tmp_path, relative)


def test_uninstall_rejects_tampered_paths(core, tmp_path):
    storage = Storage(core)
    root = tmp_path / "models"
    root.mkdir()
    outside = tmp_path / "personal.txt"
    outside.write_text("keep")
    storage.owned(root, [])
    manifest = root / ".troglodaw" / (storage.preferences["installation_id"] + ".json")
    atomic_json(manifest, {"files": {"../personal.txt": "irrelevant"}})
    with pytest.raises(ValueError):
        remove_owned_models(storage.config_path)
    assert outside.read_text() == "keep"


def test_storage_rejects_insufficient_space_and_unwritable_destination(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_module.shutil, "disk_usage", lambda _: SimpleNamespace(free=0))
    with pytest.raises(ValueError, match="free space"):
        writable_root(str(tmp_path / "no space"), 1)

    def denied(_self, _data):
        raise PermissionError("destination is read-only")

    monkeypatch.setattr(storage_module.Path, "write_bytes", denied)
    with pytest.raises(PermissionError, match="read-only"):
        writable_root(str(tmp_path / "denied"))


def test_relocated_model_copy_does_not_inherit_other_installation_references(core, tmp_path):
    manager = Storage(core)
    old = tmp_path / "models"
    old.mkdir()
    owned = old / "weight.bin"
    owned.write_bytes(b"synthetic")
    manager.preferences["model_dir"] = str(old)
    manager.owned(old, [owned])
    atomic_json(old / ".troglodaw/other.json", {"files": {"weight.bin": "other"}})
    new = tmp_path / "relocated"
    manager.change("model", str(new), "relocate", lambda *_, **__: None)
    assert (old / ".troglodaw/other.json").exists()
    assert not (new / ".troglodaw/other.json").exists()
    remove_owned_models(manager.config_path)
    assert owned.exists() and not (new / "weight.bin").exists()


def test_model_reuse_preserves_original_ownership_checksum_and_external_files(core, tmp_path):
    first = Storage(core)
    root = tmp_path / "models"
    root.mkdir()
    managed = root / "managed.bin"
    external = root / "external.bin"
    managed.write_bytes(b"original")
    external.write_bytes(b"external")
    first.owned(root, [managed])
    checksum = first.core._read_json(
        root / ".troglodaw" / (first.preferences["installation_id"] + ".json")
    )["files"]["managed.bin"]
    managed.write_bytes(b"user replacement")
    second = Storage(core)
    second.preferences["installation_id"] = "second"
    second.reference(root, [managed, external])
    manifest = json.loads((root / ".troglodaw/second.json").read_text())
    assert manifest["files"] == {"managed.bin": checksum}
    remove_owned_models(second.config_path)
    assert managed.read_bytes() == b"user replacement" and external.read_bytes() == b"external"


def test_move_models_removes_only_verified_unshared_unchanged_managed_originals(core, tmp_path):
    manager = Storage(core)
    old = tmp_path / "models"
    old.mkdir()
    manager.preferences["model_dir"] = str(old)
    paths = {name: old / name for name in ["own.bin", "shared.bin", "changed.bin", "personal.txt"]}
    for path in paths.values():
        path.write_bytes(b"original")
    manager.owned(old, [paths["own.bin"], paths["shared.bin"], paths["changed.bin"]])
    paths["changed.bin"].write_bytes(b"user replacement")
    atomic_json(old / ".troglodaw/other.json", {"files": {"shared.bin": "other"}})
    new = tmp_path / "new models"
    state = manager.change("model", str(new), "move", lambda *_, **__: None)
    assert state["model_dir"] == str(new) and state["retained_files"] == 2
    assert (
        not paths["own.bin"].exists()
        and paths["shared.bin"].exists()
        and paths["changed.bin"].exists()
    )
    assert paths["personal.txt"].exists() and not (new / "personal.txt").exists()
    assert (old / ".troglodaw/other.json").exists() and not (new / ".troglodaw/other.json").exists()
    assert (new / "own.bin").read_bytes() == b"original"
    remove_owned_models(manager.config_path)
    assert not (new / "own.bin").exists() and not (new / "shared.bin").exists()
    assert (new / "changed.bin").read_bytes() == b"user replacement"
    assert paths["shared.bin"].exists() and paths["changed.bin"].exists()


def test_move_failure_and_preference_commit_failure_keep_original_active(
    core, tmp_path, monkeypatch
):
    monkeypatch.delenv("TROGLODAW_LIBRARY")
    item = core._new_entry("voice", "Synthetic", core.synth_voice(1), "fixture")
    manager = Storage(core)
    old = core.LIB

    def failed_commit():
        raise OSError("Cannot save preferences")

    monkeypatch.setattr(manager, "persist", failed_commit)
    with pytest.raises(OSError, match="preferences"):
        manager.change(
            "library", str(tmp_path / "failed destination"), "move", lambda *_, **__: None
        )
    assert core.LIB == old and Path(item["path"]).is_file()
    assert manager.preferences.get("library_dir") is None


def test_move_retains_a_library_file_changed_after_verification(core, tmp_path, monkeypatch):
    monkeypatch.delenv("TROGLODAW_LIBRARY")
    item = core._new_entry("voice", "Synthetic", core.synth_voice(1), "fixture")
    original = Path(item["path"])
    manager = Storage(core)
    new = tmp_path / "moved library"

    def externally_changed(_old, _new, _copied):
        original.write_bytes(b"external change after copying")

    state = manager.change("library", str(new), "move", lambda *_, **__: None, externally_changed)
    assert state["retained_files"] == 1 and core.LIB == new
    assert original.read_bytes() == b"external change after copying"
    assert Path(core.get_item(item["id"])["path"]).read_bytes().startswith(b"RIFF")


def test_custom_replacement_of_a_known_unowned_model_is_preserved(core, tmp_path):
    manager = Storage(core)
    old = tmp_path / "original models"
    old.mkdir()
    asset = old / "weights.bin"
    asset.write_bytes(b"custom replacement")
    manager.preferences["model_dir"] = str(old)
    manager.model_manifest = {
        "models": {
            "base": {"assets": [{"path": "weights.bin", "sha256": "original pinned checksum"}]}
        }
    }
    new = tmp_path / "new models"
    state = manager.change("model", str(new), "move", lambda *_, **__: None)
    assert state["retained_files"] == 1 and asset.read_bytes() == b"custom replacement"
    remove_owned_models(manager.config_path)
    assert (new / "weights.bin").read_bytes() == b"custom replacement"


def test_unreadable_coowner_metadata_preserves_original_models_after_verified_move(core, tmp_path):
    manager = Storage(core)
    old = tmp_path / "models"
    old.mkdir()
    asset = old / "weights.bin"
    asset.write_bytes(b"shared perhaps")
    manager.preferences["model_dir"] = str(old)
    manager.owned(old, [asset])
    (old / ".troglodaw/other.json").write_text("corrupted external ownership record")
    new = tmp_path / "new models"
    state = manager.change("model", str(new), "move", lambda *_, **__: None)
    assert manager.models == new and state["retained_files"] > 0
    assert asset.read_bytes() == (new / "weights.bin").read_bytes() == b"shared perhaps"


def test_move_reuses_pinned_runtime_without_this_owners_ready_record(core, tmp_path, monkeypatch):
    import models

    monkeypatch.setattr(models, "runtime_signature", lambda: "fixturelock000000000")
    manager = Storage(core)
    old = tmp_path / "default models"
    old.mkdir()
    manager.preferences["model_dir"] = str(old)
    manager.model_manifest = {"runtime_revision": "pinnedrevision"}
    code = old / "inference-code/pinnedrevision/engine.py"
    package = old / "runtime-packages/fixturelock00000/torch.dll"
    for path in [code, package]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"shared pinned runtime")
    manager.owned(old, [code, package])
    own = old / ".troglodaw" / (manager.preferences["installation_id"] + ".json")
    own.rename(old / ".troglodaw/previousinstallation.json")
    unrelated = old / "runtime-packages/unrelated-version/custom.dll"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_bytes(b"leave unrelated version")
    new = tmp_path / "new models"
    manager.change("model", str(new), "move", lambda *_, **__: None)
    assert code.exists() and package.exists()  # The other installation still owns them.
    assert (new / code.relative_to(old)).read_bytes() == b"shared pinned runtime"
    assert (new / package.relative_to(old)).read_bytes() == b"shared pinned runtime"
    assert unrelated.exists() and not (new / unrelated.relative_to(old)).exists()
    remove_owned_models(manager.config_path)
    assert not (new / code.relative_to(old)).exists()
    assert code.exists()
