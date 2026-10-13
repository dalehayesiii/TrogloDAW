import copy
import shutil

import numpy as np

import pytest

from models import Canceled
from prompt_enrichment import CODEC, PROMPT_VERSION, asset_identity, provenance


def profile(service):
    music = service.models.manifest["models"]["base"]
    music["enrichment_profile"] = "fixture"
    value = {
        "id": "fixture",
        "qualified": True,
        "codec": CODEC,
        "prompt_version": PROMPT_VERSION,
        "music_runtime_revision": service.models.manifest["runtime_revision"],
        "music_asset_identity": asset_identity(music),
        "max_characters": 300,
        "writer": "fixture",
        "writer_revision": "r",
    }
    service.models.manifest["enrichment_profiles"] = {"fixture": value}
    service.models.enrichment_ready = lambda: {"profile": "fixture"}
    return value


def test_one_checked_addition_precedes_two_outputs_without_rewriting_editor_or_lyrics(
    core, songs, tmp_path, monkeypatch
):
    service, _ = songs
    configured = profile(service)
    invoke = service.invoke
    calls = []
    music = []
    values = {
        "styles": "industrial punk, no orchestra",
        "lyrics": "Fuck their promises. Every word stays.",
        "count": 2,
        "options": {"duration": 10, "variety": 100},
    }
    before = copy.deepcopy(values)

    def worker(action, request, progress, canceled):
        calls.append(action)
        if action == "enrich_prompt":
            assert "lyrics" not in request and not core.list_items()
            return provenance(
                request["caption"],
                profile=configured,
                additions="precise mechanical drum accents",
                verdict="ACCEPT",
            )
        assert calls.count("enrich_prompt") == 1
        music.append(copy.deepcopy(request["parameters"]))
        return invoke(action, request, progress, canceled)

    service.invoke = worker
    outputs = service.generate(values, lambda *_a, **_k: None, lambda: False)["outcomes"]
    assert calls == ["enrich_prompt", "generate", "generate"] and values == before
    assert [output["status"] for output in outputs] == ["complete", "complete"]
    assert all(request["lyrics"] == before["lyrics"] for request in music)
    assert all(request["caption"].endswith("precise mechanical drum accents") for request in music)
    for output in outputs:
        recipe = output["song"]["recipe"]
        assert recipe["draft"]["styles"] == values["styles"]
        assert recipe["prompt_enrichment"]["applied"]
        assert service.ingredients(output["song"]["id"])["available"]["styles"] == values["styles"]
    calls.clear()
    saved = core.load_item(outputs[0]["song"]["id"]).copy()
    moved = tmp_path / "relocated-enriched-library"
    shutil.copytree(core.LIB, moved)
    monkeypatch.setattr(core, "LIB", moved)
    replay = service.rerender(outputs[0]["song"]["id"])
    np.testing.assert_allclose(core.load_item(replay["id"]), saved, atol=4e-5)
    assert calls == []


def test_off_skips_support_lookup_and_writer(songs):
    service, calls = songs
    profile(service)
    service.models.enrichment_ready = lambda: (_ for _ in ()).throw(AssertionError("off bypass"))
    info = service.enrich_request(
        {"prompt_enrichment": False}, "dry voice only", lambda *_a, **_k: None, lambda: False
    )
    assert info["effective_caption"] == "dry voice only" and not info["applied"] and not calls


@pytest.mark.parametrize(
    "case", ["unavailable", "failure", "wrong-original", "oversized", "rejected"]
)
def test_optional_enrichment_issues_keep_original_caption(songs, case):
    service, _ = songs
    configured = profile(service)
    caption = "political speech, no music, no instruments"
    if case == "unavailable":
        service.models.enrichment_ready = lambda: None

    def invoke(*_a):
        if case == "failure":
            raise RuntimeError("Synthetic missing codec")
        return provenance(
            "wrong" if case == "wrong-original" else caption,
            profile=configured,
            additions="x" * 301 if case == "oversized" else "piano accompaniment",
            verdict="REJECT" if case == "rejected" else "ACCEPT",
        )

    service.invoke = invoke
    info = service.enrich_request({}, caption, lambda *_a, **_k: None, lambda: False)
    assert info["effective_caption"] == caption and not info["applied"]


def test_canceled_enrichment_never_starts_music_and_reports_all_requested_outputs(core, songs):
    service, _ = songs
    profile(service)

    def invoke(action, *_args):
        assert action == "enrich_prompt"
        raise Canceled("Stopped")

    service.invoke = invoke
    with pytest.raises(Canceled) as failure:
        service.generate(
            {"styles": "salsa", "count": 2, "options": {"duration": 10}},
            lambda *_a, **_k: None,
            lambda: False,
        )
    assert failure.value.result is not None
    assert [output["status"] for output in failure.value.result["outcomes"]] == [
        "canceled",
        "canceled",
    ]
    assert core.list_items() == []


def test_enrichment_cannot_rewrite_duration_or_musical_blueprint_inputs(core, songs):
    service, _ = songs
    configured = profile(service)
    service.models.manifest["models"]["base"]["planning"] = ["musical_metadata"]
    service.models.planner_ready = lambda: True
    invoke = service.invoke
    received = []

    def worker(action, request, progress, canceled):
        received.append((action, copy.deepcopy(request)))
        if action == "enrich_prompt":
            return provenance(
                request["caption"],
                profile=configured,
                additions="rhythmic guitar",
                verdict="ACCEPT",
            )
        if action == "plan_song":
            assert request["parameters"]["caption"] == "folk, 80 BPM, D minor"
            return {"duration": 12}
        if action == "plan_blueprint":
            assert request["parameters"]["caption"] == "folk, 80 BPM, D minor"
            return {"metadata": {"bpm": 120, "keyscale": "C major", "timesignature": "4"}}
        assert request["parameters"]["caption"].endswith("; rhythmic guitar")
        assert request["blueprint_metadata"]["bpm"] == 80
        assert request["blueprint_metadata"]["keyscale"] == "D minor"
        return invoke(action, request, progress, canceled)

    service.invoke = worker
    result = service.generate(
        {"styles": "folk, 80 BPM, D minor", "lyrics": "Keep every word", "count": 1},
        lambda *_a, **_k: None,
        lambda: False,
    )
    song = result["outcomes"][0]["song"]
    assert [action for action, _ in received] == [
        "enrich_prompt",
        "plan_song",
        "plan_blueprint",
        "generate",
    ]
    assert song["recipe"]["parameters"]["duration"] == 12
    assert song["recipe"]["draft"]["styles"] == "folk, 80 BPM, D minor"
    assert core.list_items()


def test_direct_recording_enrichment_retains_source_and_skips_competing_blueprints(core, songs):
    service, _ = songs
    configured = profile(service)
    music = service.models.manifest["models"]["base"]
    music.update(
        conditioning=["cover"], planning=["musical_metadata"], recording_conditioning="cover-nofsq"
    )
    service.models.planner_ready = lambda: True
    source = core._new_entry("voice", "Synthetic intact source", core.synth_voice(2), "synthetic")
    original = core.load_item(source["id"]).copy()
    invoke = service.invoke
    actions = []

    def worker(action, request, progress, canceled):
        actions.append(action)
        if action == "enrich_prompt":
            assert request["source_authoritative"] and not request["instrumental"]
            assert "lyrics" not in request
            return provenance(
                request["caption"],
                profile=configured,
                additions="warm guitar tone",
                verdict="ACCEPT",
            )
        assert action == "generate"
        assert request["parameters"]["duration"] == len(original) / core.SR
        assert not request["parameters"]["instrumental"]
        np.testing.assert_allclose(core.load(request["conditioning_audio"]), original)
        return invoke(action, request, progress, canceled)

    service.invoke = worker
    result = service.generate(
        {
            "workflow": "recording-style",
            "styles": "folk",
            "clips": [{"id": source["id"]}],
            "count": 1,
        },
        lambda *_a, **_k: None,
        lambda: False,
    )
    assert actions == ["enrich_prompt", "generate"]
    assert result["outcomes"][0]["status"] == "complete", result
    assert result["outcomes"][0]["song"]["recipe"]["planning"]["status"] == "bypassed"
