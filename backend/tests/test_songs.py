import copy
import threading
from pathlib import Path

import numpy as np
import pytest

from songs import fixed_effect, generation_parameters


@pytest.mark.parametrize("weirdness", [0, 50, 51, 66, 90, 100])
def test_exposed_weirdness_range_keeps_supported_sampler(weirdness):
    parameters = generation_parameters(
        {
            "styles": "80s city pop",
            "options": {"duration": 120, "weirdness": weirdness, "influence": 75},
        },
        [],
        733969040,
    )
    assert parameters["method"] == "ode"
    assert parameters["shift"] == pytest.approx(1 + weirdness * 0.04)
    assert parameters["guidance"] == pytest.approx(11.5)


def test_two_outputs_finish_and_catalog_before_next_inference(core, songs):
    service, _ = songs
    invoke = service.invoke
    worker = threading.get_ident()
    requests = []

    def sequential(action, values, progress, canceled):
        assert threading.get_ident() == worker
        assert len([item for item in core.list_items() if item["type"] == "generated"]) == len(
            requests
        )
        requests.append(copy.deepcopy(values))
        return invoke(action, values, progress, canceled)

    service.invoke = sequential
    result = service.generate(
        {
            "styles": "80s city pop",
            "count": 2,
            "options": {"duration": 10, "weirdness": 66, "influence": 75},
        },
        lambda *_args, **_kwargs: None,
        lambda: False,
    )
    assert [outcome["status"] for outcome in result["outcomes"]] == ["complete", "complete"]
    assert len({request["parameters"]["seed"] for request in requests}) == 2
    assert len({request["output"] for request in requests}) == 2
    assert all(request["parameters"]["method"] == "ode" for request in requests)


def test_controls_preserve_lyrics_and_have_independent_mappings():
    draft = {
        "lyrics": "Keep every word exactly.\nAnd this line.",
        "styles": "folk, guitar",
        "options": {"duration": 30},
    }
    original = generation_parameters(draft, [], 42)
    assert original["lyrics"] == draft["lyrics"]
    assert original["effective_styles"] == draft["styles"]
    weird = generation_parameters({**draft, "options": {"duration": 30, "weirdness": 90}}, [], 42)
    influence = generation_parameters(
        {**draft, "options": {"duration": 30, "influence": 90}}, [], 42
    )
    assert weird["shift"] != original["shift"] and weird["guidance"] == original["guidance"]
    assert influence["guidance"] != original["guidance"] and influence["shift"] == original["shift"]
    variety = generation_parameters({**draft, "options": {"duration": 30, "variety": 90}}, [], 42)
    assert variety["lyrics"] == draft["lyrics"] and variety["effective_styles"].startswith(
        draft["styles"]
    )
    assert variety["effective_styles"] != draft["styles"]
    auto = generation_parameters({"lyrics": "word " * 100}, [], 42)
    assert auto["duration"] > 30 and auto["duration_derivation"]["lyric_words"] == 100
    with pytest.raises(ValueError, match="10–300"):
        generation_parameters({**draft, "options": {"duration": 900}}, [], 42)


def test_five_minute_duration_and_default_two_independent_outputs(core, songs):
    assert (
        generation_parameters({"styles": "folk", "options": {"duration": 300}}, [], 1)["duration"]
        == 300
    )
    for duration in [9, 301, float("inf"), float("nan")]:
        with pytest.raises(ValueError, match="10–300"):
            generation_parameters({"styles": "folk", "options": {"duration": duration}}, [], 1)
    service, _ = songs
    result = service.generate(
        {"styles": "folk", "options": {"duration": 10}},
        lambda *_args, **_kwargs: None,
        lambda: False,
    )
    assert len(result["outcomes"]) == 2
    one = service.generate(
        {"styles": "folk", "count": 1, "options": {"duration": 10}},
        lambda *_args, **_kwargs: None,
        lambda: False,
    )
    assert len(one["outcomes"]) == 1


def test_native_auto_duration_precedes_arrangement_and_keeps_manual_words(core, songs):
    service, _ = songs
    original = service.invoke
    sequence = []

    def planned(action, values, progress, canceled):
        sequence.append(action)
        if action == "plan_song":
            assert values["parameters"]["lyrics"] == "[Verse]\nMy unchanged words"
            return {
                "duration": 18,
                "planner": "synthetic-native-planner",
                "suggested_caption": "DO NOT replace styles",
            }
        assert values["parameters"]["duration"] == 18
        assert values["parameters"]["caption"] == "folk"
        return original(action, values, progress, canceled)

    service.invoke = planned
    result = service.generate(
        {"styles": "folk", "lyrics": "[Verse]\nMy unchanged words", "count": 1},
        lambda *_args, **_kwargs: None,
        lambda: False,
    )
    assert sequence == ["plan_song", "generate"]
    recipe = result["outcomes"][0]["song"]["recipe"]
    assert recipe["parameters"]["lyrics"] == "[Verse]\nMy unchanged words"
    assert recipe["parameters"]["duration_derivation"]["suggested_seconds"] == 18
    assert core.load(service.asset(recipe["conditioning_file"])).shape[0] == 18 * core.SR


@pytest.mark.parametrize("suggested,effective", [(1, 10), (320, 300)])
def test_auto_duration_bounds_are_recorded(songs, suggested, effective):
    service, _ = songs
    original = service.invoke

    def planned(action, values, progress, canceled):
        if action == "plan_song":
            return {"duration": suggested, "planner": "synthetic"}
        return original(action, values, progress, canceled)

    service.invoke = planned
    result = service.generate(
        {"styles": "folk", "count": 1}, lambda *_args, **_kwargs: None, lambda: False
    )
    params = result["outcomes"][0]["song"]["recipe"]["parameters"]
    assert params["duration"] == effective
    assert params["duration_derivation"]["suggested_seconds"] == suggested


def test_lyrics_are_local_editable_results_and_invalid_results_fail(songs):
    service, _ = songs
    result = service.lyrics(
        {"prompt": "A song about cave lights"}, lambda *_args, **_kwargs: None, lambda: False
    )
    assert result["lyrics"].startswith("[Verse]")
    for values in [{"prompt": ""}, {"prompt": "idea", "language": "invalid"}]:
        with pytest.raises(ValueError):
            service.lyrics(values, lambda *_args, **_kwargs: None, lambda: False)
    service.invoke = lambda *args: {"lyrics": ""}
    with pytest.raises(ValueError, match="usable lyrics"):
        service.lyrics({"prompt": "idea"}, lambda *_args, **_kwargs: None, lambda: False)


def test_every_input_has_transformed_assets_and_rerenders_portably(core, songs):
    service, _ = songs
    a = core._new_entry(
        "voice", "one", core.synth_voice(1), "fixture", extra={"source_type": "microphone"}
    )
    b = core._new_entry("voice", "two", core.synth_voice(1, root_hz=220), "fixture")
    draft = {
        "clips": [{"id": a["id"], "settings": {"pitch": 2}}, {"id": b["id"]}],
        "lyrics": "Keep these words",
        "styles": "folk",
        "options": {"duration": 10},
        "count": 2,
    }
    outcome = service.generate(draft, lambda *_args, **_kwargs: None, lambda: False)
    assert len(outcome["outcomes"]) == 2
    items = [entry["song"] for entry in outcome["outcomes"]]
    assert len({item["recipe"]["parameters"]["seed"] for item in items}) == 2
    recipe = items[0]["recipe"]
    assert {sample["source_id"] for sample in recipe["samples"]} == {a["id"], b["id"]}
    assert len(recipe["placements"]) >= len({s["family_id"] for s in recipe["samples"]}) >= 2
    placed = {p["sample_id"] for p in recipe["placements"]}
    assert {s["source_id"] for s in recipe["samples"] if s["id"] in placed} == {a["id"], b["id"]}
    assert all(
        1 <= analysis["selection"]["effective_budget"] <= 8 for analysis in recipe["analysis"]
    )
    assert all(not Path(sample["file"]).is_absolute() for sample in recipe["samples"])
    assert recipe["sources"][0]["source_type"] == "microphone"
    rerender = service.rerender(items[0]["id"])
    np.testing.assert_allclose(
        core.load_item(rerender["id"]), core.load_item(items[0]["id"]), atol=1 / 32768
    )
    fields = service.ingredients(items[0]["id"])["available"]
    assert fields["lyrics"] == draft["lyrics"] and "arrangement" in fields
    core.delete_item(a["id"])
    reused = service.generate(
        {**draft, "count": 1, "clips": fields["clips"], "arrangement": fields["arrangement"]},
        lambda *_args, **_kwargs: None,
        lambda: False,
    )
    assert reused["outcomes"][0]["status"] == "complete"
    assert all(
        sample["id"].startswith("reused-")
        for sample in reused["outcomes"][0]["song"]["recipe"]["samples"]
    )


def test_prior_song_requires_explicit_preset_and_records_choice(core, songs):
    service, _ = songs
    item = core._new_entry("generated", "prior", core.synth_voice(1), "fixture")
    with pytest.raises(ValueError, match="prior-song defaults"):
        service.collect_sources({"clips": [{"id": item["id"]}]})
    applied = service.collect_sources({"clips": [{"id": item["id"], "preset": "apply"}]})[0]
    kept = service.collect_sources(
        {"clips": [{"id": item["id"], "preset": "keep", "settings": {"pitch": -1}}]}
    )[0]
    assert applied["settings"]["sample_seconds"] == 1 and applied["settings"]["samples"] == 8
    assert kept["settings"]["pitch"] == -1 and kept["preset"] == "keep"
    assert kept["preset_version"] == applied["preset_version"]


def test_partial_generation_failure_keeps_completed_output(core, songs):
    service, _ = songs
    original = service.invoke
    calls = 0

    def sometimes_fails(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("Synthetic failure")
        return original(*args)

    service.invoke = sometimes_fails
    result = service.generate(
        {"styles": "folk", "options": {"duration": 10}, "count": 2},
        lambda *_args, **_kwargs: None,
        lambda: False,
    )
    assert [item["status"] for item in result["outcomes"]] == ["complete", "failed"]
    assert core.get_item(result["outcomes"][0]["song"]["id"])


def test_fx_identity_repeated_saves_correction_and_invalidation(core, songs):
    service, calls = songs
    original = core._new_entry("generated", "original", core.synth_voice(1), "fixture")
    progress = lambda *_args, **_kwargs: None
    prepared = service.prepare_fx(original["id"], progress, lambda: False)
    assert calls == ["separate"] and not prepared["cache_hit"]
    first = service.render_fx(
        {"song_id": original["id"], "group_settings": {}, "save": True}, progress, lambda: False
    )["song"]
    np.testing.assert_allclose(
        core.load_item(first["id"]), core.load_item(original["id"]), atol=1 / 32768
    )
    reopened = service.prepare_fx(first["id"], progress, lambda: False)
    assert reopened["cache_hit"] and calls == ["separate"]
    corrected = copy.deepcopy(reopened["segments"])
    corrected[1]["group"] = "g1"
    groups = service.prepare_fx(first["id"], progress, lambda: False, corrected)
    assert len(groups["groups"]) == 1
    changed = service.render_fx(
        {
            "song_id": first["id"],
            "segments": corrected,
            "group_settings": {"g1": {"gain": -6}},
            "mode": "update",
        },
        progress,
        lambda: False,
    )["song"]
    repeated = service.render_fx(
        {
            "song_id": first["id"],
            "segments": corrected,
            "group_settings": {"g1": {"gain": -6}},
            "mode": "update",
        },
        progress,
        lambda: False,
    )["song"]
    assert changed["id"] == repeated["id"] == first["id"]
    np.testing.assert_array_equal(core.load(changed["path"]), core.load(repeated["path"]))
    assert core.get_item(original["id"])["name"] == "original"
    with pytest.raises(ValueError, match="cannot be overwritten"):
        service.render_fx({"song_id": original["id"], "mode": "update"}, progress, lambda: False)
    core.save_wav(original["path"], core.synth_voice(1, root_hz=220))
    assert not service.prepare_fx(original["id"], progress, lambda: False)["cache_hit"]
    assert calls == ["separate", "separate"]


@pytest.mark.parametrize(
    "settings",
    [
        {"pitch": 3},
        {"stretch": 0.7},
        {"stretch": 1.5},
        {"trim": True},
        {"reverb": 0.6},
        {"delay": 0.4},
        {"low_cut": 200},
        {"high_cut": 1000},
        {"compress": True},
        {"chorus": 0.3},
        {"robot": 0.2},
        {"normalize": True},
    ],
)
def test_group_effects_keep_exact_slot_duration(core, settings):
    audio = core.synth_voice(0.5)
    result = fixed_effect(core, audio, settings)
    assert result.shape == audio.shape
    assert np.isfinite(result).all()
