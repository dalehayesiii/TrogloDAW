from pathlib import Path

import pytest

from library_actions import delete, move
from models import Canceled
from test_api import job
from app import create_app
from fastapi.testclient import TestClient


def songs(core):
    return [
        core._new_entry(
            "generated", name, core.synth_voice(seconds=0.2), "synthetic", recipe={"seed": seed}
        )
        for seed, name in enumerate(["Bulk Alpha", "Bulk Beta", "Keep Gamma"])
    ]


def test_move_is_atomic_persistent_and_preserves_paths_recipes(core):
    items = songs(core)
    before = core.CATALOG.read_bytes()
    with pytest.raises(ValueError, match="no longer available"):
        move(
            core,
            {"ids": [items[0]["id"], "missing"], "folder": "New", "create_folder": True},
            lambda: False,
        )
    assert core.CATALOG.read_bytes() == before
    with pytest.raises(ValueError, match="existing folder"):
        move(core, {"ids": [items[0]["id"]], "folder": "New"}, lambda: False)
    result = move(
        core,
        {"ids": [i["id"] for i in items[:2]], "folder": "New", "create_folder": True},
        lambda: False,
    )
    assert result["completed_ids"] == [i["id"] for i in items[:2]]
    for original in items[:2]:
        current = core.get_item(original["id"])
        assert current["folder"] == "New"
        assert current["path"] == original["path"] and current["recipe"] == original["recipe"]
        assert Path(current["path"]).exists()
    assert not core.get_item(items[2]["id"]).get("folder")
    move(core, {"ids": [items[0]["id"]], "folder": ""}, lambda: False)
    assert core.get_item(items[0]["id"])["folder"] == ""


@pytest.mark.parametrize("ids", [[], "song", [None], ["missing"], ["duplicate", "duplicate"]])
def test_invalid_selection_has_no_side_effects(core, ids):
    songs(core)
    before = core.CATALOG.read_bytes()
    with pytest.raises(ValueError):
        delete(core, {"ids": ids}, lambda *_args, **_kwargs: None, lambda: False)
    assert core.CATALOG.read_bytes() == before


def test_partial_file_failure_restores_staged_audio_and_keeps_entry(core, monkeypatch):
    items = songs(core)
    mp3 = Path(items[0]["path"]).with_suffix(".mp3")
    mp3.write_bytes(b"synthetic")
    core.update_item(items[0]["id"], mp3=str(mp3))
    original_rename = Path.rename
    staged = []

    def locked(path, destination):
        if path.name.startswith("Bulk_Alpha"):
            staged.append(path)
            if len(staged) == 2:
                raise PermissionError("Synthetic locked file")
        return original_rename(path, destination)

    monkeypatch.setattr(Path, "rename", locked)
    result = delete(
        core, {"ids": [i["id"] for i in items[:2]]}, lambda *_args, **_kwargs: None, lambda: False
    )
    assert result["completed_ids"] == [items[1]["id"]]
    assert result["outcomes"][0]["status"] == "failed"
    assert "Synthetic locked file" in result["problems"][0]
    assert core.get_item(items[0]["id"])["id"] == items[0]["id"]
    assert Path(items[0]["path"]).exists() and mp3.exists()
    assert not list(core.LIB.rglob(".troglodaw-delete-*"))


def test_catalog_failure_rolls_back_staged_files(core, monkeypatch):
    items = songs(core)
    import troglocore

    original_replace = troglocore.os.replace

    def reject_catalog(source, destination):
        if Path(destination) == core.CATALOG:
            raise PermissionError("Synthetic catalog lock")
        return original_replace(source, destination)

    monkeypatch.setattr(troglocore.os, "replace", reject_catalog)
    result = delete(core, {"ids": [items[0]["id"]]}, lambda *_args, **_kwargs: None, lambda: False)
    assert not result["completed_ids"]
    assert core.get_item(items[0]["id"])
    assert Path(items[0]["path"]).exists()


def test_cleanup_failure_reports_retained_file_after_catalog_commit(core, monkeypatch):
    item = songs(core)[0]
    original_unlink = Path.unlink

    def locked_cleanup(path, *args, **kwargs):
        if path.name.startswith(".troglodaw-delete-"):
            raise PermissionError("Synthetic cleanup lock")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", locked_cleanup)
    result = delete(core, {"ids": [item["id"]]}, lambda *_args, **_kwargs: None, lambda: False)
    assert result["completed_ids"] == [item["id"]]
    assert "cleanup retained" in result["problems"][0]
    with pytest.raises(KeyError):
        core.get_item(item["id"])
    assert len(list(core.LIB.rglob(".troglodaw-delete-*"))) == 1


def test_external_audio_and_shared_files_are_protected(core, tmp_path):
    items = songs(core)
    external = tmp_path / "outside.wav"
    external.write_bytes(b"keep")
    core.update_item(items[0]["id"], path=str(external))
    core.update_item(items[2]["id"], path=items[1]["path"])
    result = delete(
        core, {"ids": [i["id"] for i in items[:2]]}, lambda *_args, **_kwargs: None, lambda: False
    )
    assert result["outcomes"][0]["status"] == "failed"
    assert external.read_bytes() == b"keep"
    assert Path(core.get_item(items[2]["id"])["path"]).exists()


def test_cancel_reports_completed_deletions_and_preserves_remainder(core):
    items = songs(core)
    with pytest.raises(Canceled) as failure:
        delete(
            core,
            {"ids": [i["id"] for i in items]},
            lambda *_args, **_kwargs: None,
            lambda: len(core.list_items()) < 3,
        )
    assert failure.value.result is not None
    assert failure.value.result["completed_ids"] == [items[0]["id"]]
    assert [i["id"] for i in core.list_items()] == [i["id"] for i in items[1:]]
    before = core.CATALOG.read_bytes()
    with pytest.raises(Canceled):
        move(
            core,
            {"ids": [items[1]["id"]], "folder": "Canceled", "create_folder": True},
            lambda: True,
        )
    assert core.CATALOG.read_bytes() == before


def test_queued_bulk_api_moves_then_deletes_without_touching_other_songs(core):
    items = songs(core)
    with TestClient(create_app(core)) as client:
        result = job(
            client,
            "library_move",
            {"ids": [i["id"] for i in items[:2]], "folder": "Queue", "create_folder": True},
        )
        assert result["status"] == "complete"
        assert "Moved 2 songs" in result["result"]["message"]
        result = job(client, "library_delete", {"ids": [i["id"] for i in items[:2]]})
        assert result["status"] == "complete" and not result["result"]["problems"]
        assert [i["id"] for i in core.list_items()] == [items[2]["id"]]
