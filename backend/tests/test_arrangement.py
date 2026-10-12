import copy
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from arrangement import select_regions
from models import Canceled
from songs import CLIP_DEFAULTS, generation_mode
from test_songs import songs as song_service_fixture


@pytest.fixture(name="songs")
def arrangement_song_service(core):
    return song_service_fixture.__wrapped__(core)


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
    assert len(short) == 1
    with pytest.raises(ValueError, match="audible"):
        select_regions(np.zeros((sr, 2), np.float32), sr, CLIP_DEFAULTS, {})


@pytest.mark.parametrize("mode", ["conditioned", "postmix"])
def test_real_arrangement_request_and_no_double_overlay(core, songs, mode):
    service, _ = songs
    service.models.manifest["models"]["base"]["conditioning"] = ["cover"]
    clip = core._new_entry("voice", "phrases", core.synth_voice(4), "fixture")
    original = service.invoke
    requests = []

    def invoke(action, values, progress, canceled):
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
    music = core.load(service.asset(recipe["musical_file"]))
    layer = core.load(service.asset(recipe["conditioning_file"]))
    expected = core.master(music + layer if mode == "postmix" else music)
    np.testing.assert_allclose(core.load_item(output["song"]["id"]), expected, atol=1 / 32768)
    rerender = service.rerender(output["song"]["id"])
    np.testing.assert_allclose(core.load_item(rerender["id"]), expected, atol=1 / 32768)
    assert len({tuple(s["transformation"].values()) for s in recipe["samples"]}) > 1
    assert service.ingredients(output["song"]["id"])["available"]["audio_mode"] == mode
    assert all(not Path(s["file"]).is_absolute() for s in recipe["samples"])


def test_modes_fallback_and_input_validation(songs):
    service, _ = songs
    fallback = generation_mode({}, service.models, True)
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
