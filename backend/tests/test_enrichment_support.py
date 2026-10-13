import json
import re

import models
import pytest
from models import Canceled
from models import Models
from prompt_enrichment import CODEC, PROMPT_VERSION, asset_identity
from storage import Storage, atomic_json, digest


def fixture(core, monkeypatch):
    storage = Storage(core)
    storage.preferences["music_model"] = "fixture"
    manager = Models(storage)
    music = {"assets": [], "enrichment_profile": "p"}
    path = storage.models / "checkpoints/writer/weights.bin"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"fixture writer")
    asset = {
        "path": "checkpoints/writer/weights.bin",
        "bytes": path.stat().st_size,
        "sha256": digest(path),
    }
    profile = {
        "id": "p",
        "qualified": True,
        "music_runtime_revision": "r",
        "music_asset_identity": asset_identity(music),
        "prompt_version": PROMPT_VERSION,
        "codec": CODEC,
        "assets": [asset],
        "writer": "fixture",
        "writer_revision": "r",
    }
    manager.manifest = {
        "runtime_revision": "r",
        "models": {"fixture": music},
        "enrichment_profiles": {"p": profile},
    }
    monkeypatch.setattr(manager, "ready", lambda: {"model": "fixture"})
    monkeypatch.setattr(models, "enrichment_signature", lambda: "addon-lock")
    packages = storage.models / "enrichment-packages/addon-lock"
    packages.mkdir(parents=True)
    (packages / ".complete").write_text("addon-lock")
    (packages / "bitsandbytes").mkdir()
    (packages / "bitsandbytes/__init__.py").write_text("# synthetic codec")
    atomic_json(
        manager.enrichment_state_path(),
        {
            "profile": "p",
            "lock": "addon-lock",
            "packages": "enrichment-packages/addon-lock",
            "verified": [{**asset, "mtime": path.stat().st_mtime_ns}],
        },
    )
    return storage, manager, path, packages


def test_absent_corrupt_and_unknown_support_never_invalidates_music(core, monkeypatch):
    _storage, manager, path, packages = fixture(core, monkeypatch)
    assert manager.enrichment_ready()
    path.unlink()
    assert manager.enrichment_ready() is None and manager.ready()
    path.write_bytes(b"corrupt")
    assert manager.enrichment_ready() is None and manager.ready()
    manager.manifest["enrichment_profiles"]["p"]["qualified"] = False
    assert manager.enrichment_ready() is None and manager.ready()
    assert packages.is_dir()


def test_enrichment_support_relocates_with_relative_state_and_pinned_assets(
    core, tmp_path, monkeypatch
):
    storage, manager, _path, _packages = fixture(core, monkeypatch)
    storage.model_manifest = manager.manifest
    monkeypatch.setattr(models, "runtime_signature", lambda: "music-lock")
    before = storage.models
    state = json.loads(manager.enrichment_state_path().read_text())
    source = tmp_path / "moved models"
    storage.change("model", str(source), "relocate", lambda *_a, **_k: None)
    assert manager.enrichment_ready() and manager.ready()
    assert json.loads(manager.enrichment_state_path().read_text())["packages"] == state["packages"]
    assert storage.models != before and storage.models == source.resolve()


def test_locked_addon_contains_only_missing_codec_packages_without_changing_music(tmp_path):
    core = models.dependency_graph(include_base=True)
    addon = models.dependency_graph(extra="enrichment")
    assert {p["name"] for p in addon["packages"]} - {p["name"] for p in core["packages"]} == {
        "bitsandbytes"
    }
    # Compare the same host's music graph with a project/lock lacking the add-on.
    project = (models.ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project = re.sub(r"\nenrichment = \[\n.*?\n\]\n", "\n", project, flags=re.S)
    lock = (models.ROOT / "uv.lock").read_text(encoding="utf-8")
    lock = re.sub(
        r'\[\[package\]\]\nname = "bitsandbytes".*?(?=\n\[\[package\]\])', "", lock, flags=re.S
    )
    (tmp_path / "pyproject.toml").write_text(project, encoding="utf-8")
    (tmp_path / "uv.lock").write_text(lock, encoding="utf-8")
    assert models.runtime_signature(tmp_path) == models.runtime_signature()


def test_reused_addon_runs_probe_and_records_state_without_installing_again(core, monkeypatch):
    storage, manager, path, packages = fixture(core, monkeypatch)
    commands = []
    monkeypatch.setattr(models, "run_setup", lambda command, *_a, **_k: commands.append(command))
    asset = manager.enrichment_profile()["assets"][0]
    completed = []
    manager.install_enrichment_support(
        manager.enrichment_profile(),
        [{**asset, "mtime": path.stat().st_mtime_ns}],
        storage.models / "runtime-packages/music",
        {},
        lambda *_a, **_k: None,
        lambda: False,
        lambda count=1: completed.append(count),
    )
    assert len(commands) == 1 and sum(completed) == 4 and manager.enrichment_ready()
    assert manager.enrichment_ready()["packages"] == "enrichment-packages/addon-lock"
    assert packages.is_dir()


@pytest.mark.parametrize("interrupt", [False, True])
def test_fresh_addon_omits_music_dependencies_and_tracks_partial_install(
    core, monkeypatch, interrupt
):
    storage, manager, path, packages = fixture(core, monkeypatch)
    marker = packages / ".complete"
    marker.unlink()
    manager.enrichment_state_path().unlink()
    commands = []

    def setup(command, *_args, **_kwargs):
        commands.append(command)
        if "export" in command:
            destination = command[command.index("--output-file") + 1]
            from pathlib import Path

            Path(destination).write_text("# synthetic hashed export")
        elif "install" in command:
            (packages / "partial-codec-file").write_text("synthetic partial install")
            if interrupt:
                raise Canceled("Synthetic interrupted codec install")

    monkeypatch.setattr(models, "run_setup", setup)
    asset = manager.enrichment_profile()["assets"][0]

    def install():
        manager.install_enrichment_support(
            manager.enrichment_profile(),
            [{**asset, "mtime": path.stat().st_mtime_ns}],
            storage.models / "runtime-packages/music",
            {},
            lambda *_a, **_k: None,
            lambda: False,
            lambda *_a: None,
        )

    if interrupt:
        with pytest.raises(Canceled):
            install()
        assert not manager.enrichment_state_path().exists() and manager.enrichment_ready() is None
    else:
        install()
        assert manager.enrichment_ready() and len(commands) == 3
    assert manager.ready() and path.exists()
    assert "--extra" in commands[0] and "enrichment" in commands[0]
    assert "torch" in commands[0] and "transformers" in commands[0]
    assert "--no-deps" in commands[1] and "--require-hashes" in commands[1]
    owner = storage.models / ".troglodaw" / (storage.preferences["installation_id"] + ".json")
    owned = json.loads(owner.read_text())["files"]
    assert "enrichment-packages/addon-lock/partial-codec-file" in owned
    assert not list((storage.models / "cache").glob("enrichment-*.json"))
    assert not list((storage.models / "cache").glob("enrichment-*.txt"))
