import shutil
from contextlib import contextmanager

import numpy as np
import pytest
import soundfile as sf

import library_actions
from models import Canceled
from storage import digest, safe_file


def upload(tmp_path):
    path = tmp_path / "external song.wav"
    t = np.arange(8000 * 2) / 8000
    sf.write(path, 0.08 * np.sin(2 * np.pi * 220 * t), 8000, subtype="FLOAT")
    return {"path": path, "name": path.name}


def test_wav_import_preserves_original_and_relocated_prior_metadata(
    core, songs, tmp_path, monkeypatch
):
    source = upload(tmp_path)
    checksum = digest(source["path"])
    with core._locked_catalog(write=True) as catalog:
        catalog["folders"] = ["Imported songs"]
    result = library_actions.import_song(
        core,
        source,
        {"title": "My imported song", "folder": "Imported songs"},
        lambda *_a, **_k: None,
        lambda: False,
    )
    song = core.get_item(result["song"]["id"])
    assert song["name"] == "My imported song" and song["folder"] == "Imported songs"
    assert song["duration"] == 2 and song["is_song"]
    assert digest(source["path"]) == checksum
    assert digest(safe_file(core.LIB, song["recipe"]["original_file"])) == checksum
    assert song["recipe"]["op"] == "song_import" and "draft" not in song["recipe"]
    assert sf.info(song["path"]).samplerate == core.SR and sf.info(song["path"]).channels == 2
    moved = tmp_path / "relocated library"
    shutil.copytree(core.LIB, moved)
    monkeypatch.setattr(core, "LIB", moved)
    monkeypatch.setattr(core, "CATALOG", moved / "catalog.json")
    monkeypatch.setattr(core, "INBOX", moved / "inbox")
    assert len(core.load_item(song["id"])) == core.SR * 2
    service, _ = songs
    assert (
        service.collect_sources({"clips": [{"id": song["id"]}]})[0]["source_type"] == "prior-song"
    )


@pytest.mark.parametrize("kind", ["corrupt", "nonfinite", "wrong-format"])
def test_invalid_import_does_not_register_or_overwrite(core, tmp_path, kind):
    source = upload(tmp_path)
    if kind == "corrupt":
        source["path"].write_bytes(b"not a WAV")
    elif kind == "nonfinite":
        sf.write(source["path"], np.full(8000, np.nan), 8000, subtype="FLOAT")
    else:
        sf.write(source["path"], np.ones(8000) * 0.03, 8000, format="FLAC")
    checksum = digest(source["path"])
    with pytest.raises(ValueError):
        library_actions.import_song(
            core, source, {"title": "Invalid"}, lambda *_a, **_k: None, lambda: False
        )
    assert core.list_items() == [] and digest(source["path"]) == checksum


def test_encode_failure_and_cancel_clean_owned_files(core, tmp_path, monkeypatch):
    source = upload(tmp_path)

    def fail(*_a, **_k):
        raise OSError("Synthetic encoding failure")

    monkeypatch.setattr(core, "to_mp3", fail)
    with pytest.raises(OSError, match="Synthetic"):
        library_actions.import_song(
            core, source, {"title": "Failed"}, lambda *_a, **_k: None, lambda: False
        )
    assert core.list_items() == []
    assert not list((core.LIB / "mixes").glob("*.wav"))
    assert not list((core.LIB / "assets/imports").rglob("original.wav"))
    with pytest.raises(Canceled):
        library_actions.import_song(
            core, source, {"title": "Canceled"}, lambda *_a, **_k: None, lambda: True
        )
    assert core.list_items() == [] and source["path"].is_file()


def test_catalog_commit_failure_rolls_back_and_retry_succeeds(core, tmp_path, monkeypatch):
    source = upload(tmp_path)
    original_lock = core._locked_catalog

    @contextmanager
    def failing_lock(write=False):
        with original_lock(write=write) as catalog:
            yield catalog
            if write:
                raise OSError("Synthetic catalog commit failure")

    monkeypatch.setattr(core, "_locked_catalog", failing_lock)
    with pytest.raises(OSError, match="catalog"):
        library_actions.import_song(
            core, source, {"title": "Retry me"}, lambda *_a, **_k: None, lambda: False
        )
    assert core.list_items() == [] and not list((core.LIB / "mixes").glob("*"))
    monkeypatch.setattr(core, "_locked_catalog", original_lock)
    result = library_actions.import_song(
        core, source, {"title": "Retry me"}, lambda *_a, **_k: None, lambda: False
    )
    assert result["song"]["name"] == "Retry me" and len(core.list_items()) == 1


def test_float_stereo_import_reduces_hot_peaks_without_boosting_quiet_audio(core, tmp_path):
    source = upload(tmp_path)
    sf.write(source["path"], np.full((8000, 2), [1.3, -1.2]), 8000, subtype="FLOAT")
    result = library_actions.import_song(
        core, source, {"title": "Hot stereo"}, lambda *_a, **_k: None, lambda: False
    )
    assert result["song"]["recipe"]["playable_format"]["headroom_gain"] < 1
    assert np.max(np.abs(core.load_item(result["song"]["id"]))) <= 0.951
    sf.write(source["path"], np.full((8000, 2), 0.01), 8000, subtype="FLOAT")
    result = library_actions.import_song(
        core, source, {"title": "Quiet stereo"}, lambda *_a, **_k: None, lambda: False
    )
    assert result["song"]["recipe"]["playable_format"]["headroom_gain"] == 1
