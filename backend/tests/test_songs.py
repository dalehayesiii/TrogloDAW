import copy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

from songs import Songs, fixed_effect, generation_parameters


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
    with pytest.raises(ValueError, match="10–120"):
        generation_parameters({**draft, "options": {"duration": 900}}, [], 42)


@pytest.fixture
def songs(core):
    calls = []
    model = SimpleNamespace(
        selected="base",
        manifest={"runtime_revision": "fixture", "models": {"base": {"assets": []}}},
    )

    def invoke(action, values, progress, canceled):
        calls.append(action)
        directory = Path(values["output"])
        directory.mkdir(exist_ok=True, parents=True)
        if action == "generate":
            samples = round(values["parameters"]["duration"] * core.SR)
            timeline = np.arange(samples) / core.SR
            audio = np.repeat(
                (0.05 * np.sin(2 * np.pi * 100 * timeline))[:, None], 2, axis=1
            ).astype(np.float32)
            path = directory / "music.wav"
            sf.write(path, audio, core.SR, subtype="FLOAT")
            return {"audio": str(path), "sample_rate": core.SR, "parameters": values["parameters"]}
        audio = core.load(values["audio"])
        vocals = audio * 0.25
        sf.write(directory / "vocals.wav", vocals, core.SR, subtype="FLOAT")
        sf.write(directory / "accompaniment.wav", audio - vocals, core.SR, subtype="FLOAT")
        half = len(audio) // 2
        segments = [
            {"start": 0, "end": half, "group": "g1", "uncertain": True},
            {"start": half, "end": len(audio), "group": "g2", "uncertain": True},
        ]
        groups = []
        for segment in segments:
            group_audio = np.zeros_like(vocals)
            group_audio[segment["start"] : segment["end"]] = vocals[
                segment["start"] : segment["end"]
            ]
            filename = str(segment["group"]) + ".wav"
            sf.write(directory / filename, group_audio, core.SR, subtype="FLOAT")
            groups.append(
                {
                    "id": segment["group"],
                    "name": segment["group"],
                    "file": filename,
                    "uncertain": True,
                }
            )
        return {
            "groups": groups,
            "segments": segments,
            "samples": len(audio),
            "sample_rate": core.SR,
            "warning": "Synthetic fixture groups, not model inference",
        }

    service = Songs(core, model, lambda path: {"url": str(path)}, invoke)
    return service, calls


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
    assert len(recipe["placements"]) >= len(recipe["samples"]) >= 2
    assert all(analysis["selection"]["effective_budget"] == 1 for analysis in recipe["analysis"])
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
