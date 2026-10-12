import json
import subprocess
import sys

import pytest

from storage import Storage, atomic_json, copy_verified, remove_owned_models, safe_file
from storage import writable_root
from types import SimpleNamespace
import storage as storage_module


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
