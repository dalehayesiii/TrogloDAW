import copy
import shutil
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from arrangement import select_regions
from models import Canceled
from songs import CLIP_DEFAULTS, generation_mode


def test_content_selection_avoids_silence_and_covers_different_material():
    sr = 8000
    audio = np.zeros((sr * 10, 2), np.float32)
    for start, hz in ((1, 220), (4, 880), (7, 2200)):
        phrase = 0.2 * np.sin(2 * np.pi * hz * np.arange(sr) / sr)
        audio[start * sr : (start + 1) * sr] = phrase[:, None]
    regions, budget = select_regions(
        audio, sr, {**CLIP_DEFAULTS, "sample_seconds": 0.5}, {"phrases": [(1, 2), (4, 5), (7, 8)]}
    )
    assert 3 <= len(regions) <= 8
    assert all(r["rms"] > 0.08 and r["audible_fraction"] > 0.4 for r in regions)
    assert {int(r["start"] / sr) for r in regions} >= {1, 4, 7}
    assert budget["active_seconds"] == 3
    assert max(r["centroid_hz"] for r in regions) - min(r["centroid_hz"] for r in regions) > 1000
    short, _ = select_regions(audio[sr : sr * 2], sr, CLIP_DEFAULTS, {})
    assert 1 <= len(short) <= 2
    assert any(r["end"] - r["start"] == sr for r in short)
    with pytest.raises(ValueError, match="audible"):
        select_regions(np.zeros((sr, 2), np.float32), sr, CLIP_DEFAULTS, {})


@pytest.mark.parametrize("mode", ["conditioned", "postmix"])
def test_real_arrangement_request_and_no_double_overlay(core, songs, mode, tmp_path, monkeypatch):
    service, _ = songs
    service.models.manifest["models"]["base"]["conditioning"] = ["cover"]
    clip = core._new_entry("voice", "phrases", core.synth_voice(4), "fixture")
    original = service.invoke
    requests = []

    def invoke(action, values, progress, canceled):
        if action != "generate":
            return original(action, values, progress, canceled)
        requests.append(copy.deepcopy(values))
        if mode == "conditioned":
            audio, sr = sf.read(values["conditioning_audio"], always_2d=True)
            assert sr == core.SR and len(audio) == core.SR * 10
            assert np.max(np.abs(audio)) > 0
        else:
            assert values["conditioning_audio"] is None
        return original(action, values, progress, canceled)

    service.invoke = invoke
    draft = {
        "clips": [{"id": clip["id"]}],
        "lyrics": "Every word unchanged",
        "styles": "folk",
        "audio_mode": mode,
        "audio_adherence": 64,
        "options": {"duration": 10},
    }
    output = service.generate(draft, lambda *_a, **_k: None, lambda: False)["outcomes"][0]
    assert output["status"] == "complete"
    recipe = output["song"]["recipe"]
    assert recipe["parameters"]["effective_mode"] == mode
    assert requests[0]["parameters"]["lyrics"] == draft["lyrics"]
    assert requests[0]["parameters"]["guidance"] == 8
    if mode == "conditioned":
        assert requests[0]["parameters"]["audio_cover_steps"] == 20
        assert requests[0]["parameters"]["effective_audio_adherence"] == 20 / 32
    music = core.load(service.asset(recipe["musical_file"]))
    layer = core.load(service.asset(recipe["conditioning_file"]))
    expected = core.master(music + layer if mode == "postmix" else music)
    np.testing.assert_allclose(core.load_item(output["song"]["id"]), expected, atol=1 / 32768)
    rerender = service.rerender(output["song"]["id"])
    np.testing.assert_allclose(core.load_item(rerender["id"]), expected, atol=1 / 32768)
    assert len({tuple(s["transformation"].values()) for s in recipe["samples"]}) > 1
    assert service.ingredients(output["song"]["id"])["available"]["audio_mode"] == mode
    assert all(not Path(s["file"]).is_absolute() for s in recipe["samples"])
    moved = tmp_path / "relocated-library"
    shutil.copytree(core.LIB, moved)
    monkeypatch.setattr(core, "LIB", moved)
    monkeypatch.setattr(core, "CATALOG", moved / "catalog.json")
    monkeypatch.setattr(core, "INBOX", moved / "inbox")
    relocated = service.rerender(output["song"]["id"])
    np.testing.assert_allclose(core.load_item(relocated["id"]), expected, atol=1 / 32768)


def test_original_recipe_retains_postmix_replay_semantics(core, songs):
    service, _ = songs
    clip = core._new_entry("voice", "legacy-source", core.synth_voice(2), "fixture")
    result = service.generate(
        {
            "clips": [{"id": clip["id"]}],
            "styles": "folk",
            "audio_mode": "postmix",
            "options": {"duration": 10},
        },
        lambda *_a, **_k: None,
        lambda: False,
    )["outcomes"][0]["song"]
    recipe = copy.deepcopy(result["recipe"])
    recipe["version"] = 1
    recipe.pop("render_mode")
    recipe.pop("conditioning_file")
    audio = core.load(service.asset(recipe["musical_file"]))
    samples = {sample["id"]: sample for sample in recipe["samples"]}
    for placement in recipe["placements"]:
        placement.pop("gain")
        start, length = placement["offset_samples"], placement["length_samples"]
        fragment = core.load(service.asset(samples[placement["sample_id"]]["file"]))
        audio[start : start + length] += fragment[:length]
    core.update_item(result["id"], recipe=recipe)
    replay = service.rerender(result["id"])
    np.testing.assert_allclose(core.load_item(replay["id"]), core.master(audio), atol=1 / 32768)


def test_modes_fallback_and_input_validation(songs):
    service, _ = songs
    assert generation_mode({}, service.models, True)["requested_mode"] == "postmix"
    fallback = generation_mode({"audio_mode": "conditioned"}, service.models, True)
    assert fallback["requested_mode"] == "conditioned" and fallback["effective_mode"] == "postmix"
    assert fallback["fallback_reason"] and fallback["effective_audio_adherence"] is None
    assert generation_mode({}, service.models, False)["effective_mode"] == "text"
    with pytest.raises(ValueError, match="adherence"):
        generation_mode({"audio_adherence": float("nan")}, service.models, True)
    with pytest.raises(ValueError, match="Choose"):
        generation_mode({"audio_mode": "other"}, service.models, True)


def test_sample_work_cancels_without_an_inference_call(core, songs, tmp_path):
    service, calls = songs
    clip = core._new_entry("voice", "source", core.synth_voice(2), "fixture")
    sources = service.collect_sources({"clips": [{"id": clip["id"]}]})
    with pytest.raises(Canceled):
        service.arrange(
            sources, tmp_path, {"duration": 10, "seed": 42}, lambda *_a, **_k: None, lambda: True
        )
    assert not calls


def test_audible_antiphase_stereo_is_selected_and_conditioning_remains_audible(
    core, songs, tmp_path
):
    service, _ = songs
    left = core.synth_voice(2)[:, 0]
    audio = np.stack([left, -left], axis=1)
    item = core._new_entry("voice", "out of phase", audio, "fixture")
    sources = service.collect_sources({"clips": [{"id": item["id"]}]})
    directory = core.LIB / "assets" / "phase-fixture"
    directory.mkdir(parents=True)
    layer, samples, _, analyses = service.arrange(
        sources, directory, {"duration": 10, "seed": 42}, lambda *_a, **_k: None
    )
    assert samples and np.max(np.abs(layer.mean(axis=1))) > 0.01
    assert analyses[0]["channel_strategy"] == "dominant-channel-stereo"
    preserved = core.load(service.asset(sources[0]["file"]))
    np.testing.assert_allclose(preserved[:, 0], -preserved[:, 1], atol=1 / 32768)
