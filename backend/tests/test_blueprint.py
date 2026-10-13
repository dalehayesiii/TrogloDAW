import copy
import json
import shutil

import numpy as np
import pytest

from inference_runner import generate
from models import Canceled
from planning import validated_blueprint


def parameters():
    return {
        "duration": 10,
        "caption": "dry spoken voice, no music",
        "lyrics": "Fuck their lies.",
        "seed": 42,
    }


@pytest.mark.parametrize(
    "result",
    [
        {"audio_codes": ""},
        {"audio_codes": "NO USER INPUT"},
        {"audio_codes": "<|audio_code_1|>"},
        {"audio_codes": "<|audio_code_64000|>" * 50},
        {"audio_codes": "<|audio_code_1|>" * 500},
        {"audio_codes": "<|audio_code_1|>" * 50, "metadata": {"bpm": float("nan")}},
    ],
)
def test_invalid_blueprints_cannot_reach_rendering(result):
    with pytest.raises(ValueError):
        validated_blueprint(result, parameters())


def test_renderer_rejects_blueprint_that_would_preempt_source_before_loading_models():
    with pytest.raises(ValueError, match="cannot replace an active source"):
        generate(
            {
                "parameters": {"effective_mode": "conditioned"},
                "conditioning_audio": "source.wav",
                "blueprint_codes": "<|audio_code_1|>",
            }
        )


def test_literal_music_constraints_override_planner_without_rewriting_any_text():
    params = {**parameters(), "caption": "dry voice, 80 BPM, F# minor, 3/4, no instruments"}
    result = {
        "metadata": {
            "bpm": 160,
            "keyscale": "C major",
            "timesignature": "4",
            "duration": 200,
            "lyrics": "bad rewrite",
        }
    }
    artifact = validated_blueprint(result, params)
    assert artifact["constraints"] == {"bpm": 80, "keyscale": "F# minor", "timesignature": "3"}
    assert artifact["lyrics"] == params["lyrics"] and artifact["caption"] == params["caption"]
    assert artifact["duration"] == 10


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"bpm": True},
        {"bpm": float("nan")},
        {"bpm": 301, "keyscale": "C major", "timesignature": "4"},
        {"bpm": 80, "keyscale": "unknown", "timesignature": "4"},
        {"bpm": 80, "keyscale": "C major", "timesignature": "7"},
    ],
)
def test_malformed_musical_metadata_cannot_reach_rendering(metadata):
    with pytest.raises(ValueError):
        validated_blueprint({"metadata": metadata}, parameters())


def enable(service):
    service.models.manifest["models"]["base"]["planning"] = ["musical_metadata"]
    service.models.manifest["models"]["base"]["conditioning"] = ["cover"]
    service.models.planner_ready = lambda: True


def test_blueprint_precedes_each_output_and_keeps_originals_and_portable_assets(
    core, songs, tmp_path, monkeypatch
):
    service, _ = songs
    enable(service)
    original = service.invoke
    requests = []
    source = {
        "styles": "dry spoken voice, no music",
        "lyrics": "Fuck their lies.\n私たちは黙りません。",
        "options": {"duration": 10},
        "count": 2,
    }
    snapshot = copy.deepcopy(source)

    def invoke(action, values, progress, canceled):
        requests.append((action, copy.deepcopy(values)))
        assert values["parameters"]["lyrics"] == source["lyrics"]
        assert values["parameters"]["caption"] == source["styles"]
        if action == "plan_blueprint":
            return {
                "planner": "fixture-lm",
                "metadata": {
                    "bpm": 80,
                    "keyscale": "C major",
                    "timesignature": "4",
                    "caption": "unwanted rewrite",
                    "lyrics": "unwanted words",
                },
            }
        assert values["conditioning_audio"] is None
        assert values["blueprint_metadata"] == {
            "bpm": 80,
            "keyscale": "C major",
            "timesignature": "4",
        }
        return original(action, values, progress, canceled)

    service.invoke = invoke
    result = service.generate(source, lambda *_args, **_kwargs: None, lambda: False)
    assert [action for action, _values in requests] == [
        "plan_blueprint",
        "generate",
        "plan_blueprint",
        "generate",
    ]
    assert source == snapshot
    first = result["outcomes"][0]["song"]
    planning = first["recipe"]["planning"]
    assert planning["status"] == "applied"
    artifact = json.loads(service.asset(planning["file"]).read_text())
    assert artifact["lyrics"] == source["lyrics"] and artifact["caption"] == source["styles"]
    assert artifact["constraints"] == {"bpm": 80, "keyscale": "C major", "timesignature": "4"}
    assert "audio_codes" not in artifact
    saved = core.load_item(first["id"]).copy()
    moved = tmp_path / "relocated-planned-library"
    shutil.copytree(core.LIB, moved)
    monkeypatch.setattr(core, "LIB", moved)
    replay = service.rerender(first["id"])
    np.testing.assert_allclose(core.load_item(replay["id"]), saved, atol=4e-5)
    assert service.asset(planning["file"]).exists()
    assert len(requests) == 4


def test_conditioned_source_skips_competing_blueprint_even_when_installed(core, songs):
    service, calls = songs
    enable(service)
    source = core._new_entry("voice", "Fixture", core.synth_voice(2), "fixture")
    result = service.generate(
        {
            "clips": [{"id": source["id"]}],
            "lyrics": "exact words",
            "styles": "folk",
            "options": {"duration": 10},
            "count": 1,
        },
        lambda *_args, **_kwargs: None,
        lambda: False,
    )
    assert calls == ["generate"]
    assert result["outcomes"][0]["song"]["recipe"]["planning"] == {
        "status": "bypassed",
        "reason": "source_audio_supplies_structure",
    }


@pytest.mark.parametrize("failure", [RuntimeError("planner ran out of memory"), Canceled("cancel")])
def test_planner_failure_falls_back_visibly_but_cancellation_stops(core, songs, failure):
    service, calls = songs
    enable(service)
    original = service.invoke
    events = []

    def invoke(action, values, progress, canceled):
        if action == "plan_blueprint":
            raise failure
        assert (
            values["blueprint_metadata"] is None and values["parameters"]["lyrics"] == "exact words"
        )
        return original(action, values, progress, canceled)

    service.invoke = invoke
    request = {"lyrics": "exact words", "styles": "folk", "count": 1, "options": {"duration": 10}}
    progress = lambda message, *_args, **details: events.append((message, details))
    if isinstance(failure, Canceled):
        with pytest.raises(Canceled):
            service.generate(request, progress, lambda: False)
        assert core.list_items() == [] and calls == []
    else:
        result = service.generate(request, progress, lambda: False)
        assert result["outcomes"][0]["planning"]["status"] == "failed"
        assert any(details.get("stage") == "planning_fallback" for _message, details in events)
        assert calls == ["generate"]


def test_missing_planner_is_reported_without_invocation(core, songs):
    service, calls = songs
    enable(service)
    service.models.planner_ready = lambda: False
    result = service.generate(
        {"styles": "folk", "count": 1, "options": {"duration": 10}},
        lambda *_args, **_kwargs: None,
        lambda: False,
    )
    assert result["outcomes"][0]["planning"]["status"] == "unavailable"
    assert calls == ["generate"]
