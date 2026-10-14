import copy
import time
import shutil

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import create_app

from songs import generation_mode


def recording(core, seconds=7, *, prior=False):
    t = np.arange(round(core.SR * seconds)) / core.SR
    audio = np.column_stack((0.9 * np.sin(2 * np.pi * 173 * t), 0.3 * np.cos(2 * np.pi * 257 * t)))
    return core._new_entry(
        "generated" if prior else "voice",
        "Synthetic source",
        audio.astype(np.float32),
        "synthetic",
        extra={"source_type": "upload"},
    )


def draft(item):
    return {
        "workflow": "recording-style",
        "styles": "warm acoustic folk",
        "count": 1,
        "clips": [
            {
                "id": item["id"],
                "settings": {"pitch": 123, "stretch": -5, "gain": "inactive", "samples": 0},
            }
        ],
        "options": {"duration": "auto", "gender": "Male", "variety": 90},
    }


@pytest.mark.parametrize("seconds", [63 + 18 / 44100, 63 + 30 / 44100])
def test_direct_batch_uses_exact_source_duration_despite_catalog_rounding(core, songs, seconds):
    service, calls = songs
    item = recording(core, seconds=seconds)
    source = core.load_item(item["id"])
    exact_duration = len(source) / core.SR
    assert item["duration"] != exact_duration
    request = {**draft(item), "count": 2}
    result = service.generate(request, lambda *_args, **_kwargs: None, lambda: False)
    assert calls == ["generate", "generate"]
    assert len(result["outcomes"]) == 2
    for output in result["outcomes"]:
        song = output["song"]
        recipe = song["recipe"]
        assert recipe["parameters"]["duration"] == exact_duration
        assert recipe["sources"][0]["duration"] == exact_duration
        assert len(core.load_item(song["id"])) == len(source)
        np.testing.assert_array_equal(core.load(service.asset(recipe["conditioning_file"])), source)
    np.testing.assert_array_equal(core.load_item(item["id"]), source)


def test_intact_source_bypasses_sampling_enhancement_and_second_overlay(
    core, songs, monkeypatch, tmp_path
):
    service, calls = songs
    service.models.manifest["models"]["base"]["conditioning"] = ["cover"]
    item = recording(core)
    original = core.load_item(item["id"]).copy()
    request = draft(item)
    snapshot = copy.deepcopy(request)
    received = []
    invoke = service.invoke

    def model(action, values, progress, canceled):
        received.append(copy.deepcopy(values))
        return invoke(action, values, progress, canceled)

    service.invoke = model

    def unexpected(*_args):
        raise AssertionError("The intact source must bypass sampling and enhancement")

    monkeypatch.setattr(service, "arrange", unexpected)
    monkeypatch.setattr(service, "enhance_guide", unexpected)
    result = service.generate(request, lambda *_args, **_kwargs: None, lambda: False)
    assert calls == ["generate"]
    params = received[0]["parameters"]
    assert params["duration"] == pytest.approx(7)
    assert params["lyrics"] == "" and params["instrumental"] is False
    assert params["caption"] == request["styles"]
    np.testing.assert_array_equal(core.load(received[0]["conditioning_audio"]), original)
    output = result["outcomes"][0]["song"]
    recipe = output["recipe"]
    assert recipe["workflow"] == "recording-style"
    assert recipe["render_mode"] == "conditioned"
    assert recipe["samples"] == recipe["placements"] == []
    expected = core.master(core.load(service.asset(recipe["musical_file"])))
    np.testing.assert_allclose(core.load_item(output["id"]), expected, atol=4e-5)
    np.testing.assert_array_equal(core.load_item(item["id"]), original)
    assert request == snapshot
    moved = tmp_path / "relocated-recording-library"
    shutil.copytree(core.LIB, moved)
    monkeypatch.setattr(core, "LIB", moved)
    replay = service.rerender(output["id"])
    np.testing.assert_allclose(core.load_item(replay["id"]), expected, atol=4e-5)
    assert calls == ["generate"]


@pytest.mark.parametrize(
    "extra",
    [
        {"lyrics": "hidden words"},
        {"lyric_idea": "write hidden words"},
        {"backing_song_id": "a-prior"},
        {"arrangement": {"samples": []}},
        {"audio_mode": "postmix"},
        {"clips": []},
    ],
)
def test_direct_mode_rejects_incompatible_payload_without_cataloging(core, songs, extra):
    service, calls = songs
    service.models.manifest["models"]["base"]["conditioning"] = ["cover"]
    item = recording(core)
    request = {**draft(item), **extra}
    with pytest.raises(ValueError):
        service.generate(request, lambda *_args, **_kwargs: None, lambda: False)
    assert calls == [] and len(core.list_items()) == 1


def test_direct_mode_rejects_multiple_clips_priors_and_unsupported_models(core, songs):
    service, calls = songs
    service.models.manifest["models"]["base"]["conditioning"] = ["cover"]
    first, second = recording(core), recording(core, prior=True)
    request = draft(first)
    request["clips"].append({"id": second["id"]})
    with pytest.raises(ValueError, match="exactly one"):
        service.generate(request, lambda *_args, **_kwargs: None, lambda: False)
    with pytest.raises(ValueError, match="prior song"):
        service.generate(draft(second), lambda *_args, **_kwargs: None, lambda: False)
    service.models.manifest["models"]["base"]["conditioning"] = []
    service.models.manifest["models"]["base"].pop("recording_conditioning")
    with pytest.raises(ValueError, match="direct recording conditioning"):
        service.generate(draft(first), lambda *_args, **_kwargs: None, lambda: False)
    assert calls == []


def test_fresh_conditioning_and_explicit_saved_postmix_are_distinct(core, songs):
    service, _calls = songs
    service.models.manifest["models"]["base"]["conditioning"] = ["cover"]
    assert generation_mode({}, service.models, True)["effective_mode"] == "conditioned"
    assert (
        generation_mode({"audio_mode": "postmix"}, service.models, True)["effective_mode"]
        == "postmix"
    )
    assert generation_mode({}, service.models, False)["effective_mode"] == "text"


def test_recording_workflow_api_preserves_source_and_rejects_hidden_words(core, songs):
    service, _calls = songs
    service.models.manifest["models"]["base"]["conditioning"] = ["cover"]
    source = recording(core, seconds=2)
    app = create_app(core)
    service.media = app.state.service.file
    app.state.service.songs = service
    with TestClient(app) as client:

        def run(values):
            response = client.post(
                "/api/jobs",
                json={"action": "song_generate", "values": values},
                headers={"X-TrogloDAW-Request": "1"},
            )
            assert response.status_code == 200
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                job = client.get("/api/jobs/" + response.json()["id"]).json()
                if job["status"] in {"complete", "failed"}:
                    return job
                time.sleep(0.02)
            raise AssertionError("API recording job did not finish")

        success = run(draft(source))
        assert success["status"] == "complete"
        outcome = success["result"]["outcomes"][0]
        assert outcome["song"]["recipe"]["workflow"] == "recording-style"
        media = client.get(outcome["recording_audio"]["url"])
        assert media.status_code == 200 and media.content[:4] == b"RIFF"
        rejected = run({**draft(source), "lyrics": "hidden replacement words"})
        assert rejected["status"] == "failed"
        assert "does not accept lyrics" in rejected["message"]
        assert len(core.list_items()) == 2
