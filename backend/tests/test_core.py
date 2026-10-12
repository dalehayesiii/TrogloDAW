import json
from pathlib import Path

import numpy as np
import pytest


def test_import_catalog_and_relocation(core, tmp_path, monkeypatch):
    source = tmp_path / "voice.wav"
    core.save_wav(source, core.synth_voice(seconds=1))
    item = core.import_file(source, name="take one", tags=["demo"])
    assert core.get_item(item["id"][:8])["id"] == item["id"]
    assert core.list_items(type_="voice", tag="demo")[0]["id"] == item["id"]
    raw = json.loads(core.CATALOG.read_text())["items"][0]
    assert "path" not in raw
    assert not Path(raw["file"]).is_absolute()
    monkeypatch.setattr(core, "LIB", tmp_path / "relocated")
    assert core._abs(raw)["path"] == str(core.LIB / raw["file"])


def test_config_precedence_and_windows_encoding(core, tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text('{"port": 9000, "host": "localhost"}', encoding="utf-16")
    (tmp_path / "config.local.json").write_text('{"port": 9001}', encoding="utf-8")
    monkeypatch.setattr(core, "CONFIG", core._load_config())
    assert core.setting("port") == 9001
    assert core.setting("host") == "localhost"
    monkeypatch.setenv("MM_PORT", "9002")
    assert core.setting("port") == "9002"


def test_seeded_generation_and_recipe_rerender(core):
    settings = {"bpm": 120, "bars": 1, "key": "A minor", "style": "boombap", "seed": 42}
    first = core.generate(settings, name="beat")
    second = core.rerender(first["id"])
    audio = core.load(first["path"])
    assert audio.dtype == np.float32 and audio.shape[1] == 2
    assert np.isfinite(audio).all()
    np.testing.assert_array_equal(audio, core.load(second["path"]))
    assert first["recipe"]["settings"]["seed"] == 42


def test_mix_remix_and_mp3_export(core, tmp_path):
    voice = core._new_entry("voice", "vocal", core.synth_voice(seconds=1), "test")
    beat = core.generate({"bpm": 120, "bars": 1, "seed": 3})
    mix = core.mix(voice["id"], beat["id"], {"duck": True})
    remix = core.remix(mix["id"], {"music_vol": -9})
    assert remix["recipe"]["parent"] == mix["id"]
    assert remix["recipe"]["settings"]["music_vol"] == -9
    assert mix["recipe"]["settings"]["music_vol"] != -9
    for path in core.export(remix["id"], tmp_path / "exports"):
        assert Path(path).stat().st_size > 100


def test_mastering_ceiling_and_analysis(core):
    audio = core.synth_voice(seconds=2)
    analysis = core.analyze_vocal(audio)
    assert analysis["phrases"]
    mastered = core.master(audio)
    assert np.isfinite(mastered).all()
    assert core.true_peak_db(mastered) <= -0.9


def test_catalog_mutation_and_missing_recipe(core):
    item = core._new_entry("voice", "vocal", core.synth_voice(seconds=1), "test")
    core.update_item(item["id"], name="renamed", tags=["take"])
    assert core.get_item("renamed")["tags"] == ["take"]
    with pytest.raises(ValueError, match="no re-renderable recipe"):
        core.rerender(item["id"])
    core.delete_item(item["id"])
    assert not Path(item["path"]).exists()
    assert core.list_items() == []
