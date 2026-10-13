import copy
import shutil

import numpy as np
import pytest

from arrangement import align_recording, backing_context, plan_events
from models import Canceled
from songs import CLIP_DEFAULTS


def draft(core, seconds=12):
    backing = core._new_entry("mix", "Backing", core.synth_voice(seconds) * 0.1, "fixture")
    voice = core._new_entry("voice", "Recording", core.synth_voice(3) * 0.01, "fixture")
    return {
        "workflow": "arrange-over-song",
        "backing_song_id": backing["id"],
        "clips": [{"id": voice["id"]}],
        "count": 1,
        "styles": "do not use",
        "lyrics": "do not use",
        "options": {"duration": "invalid", "weirdness": -500},
        "audio_mode": "invalid",
        "guide_enhancement": "invalid",
    }


def test_fixed_backing_ignores_models_and_stale_controls_replays_after_move(
    core, songs, tmp_path, monkeypatch
):
    service, calls = songs
    values = draft(core)
    before = copy.deepcopy(values)
    backing_before = core.load_item(values["backing_song_id"])
    service.local_inference = True
    service.models.ready = lambda: False
    result = service.generate(values, lambda *_a, **_k: None, lambda: False)
    assert result["outcomes"][0]["status"] == "complete", result
    assert not calls and values == before
    item = result["outcomes"][0]["song"]
    recipe = item["recipe"]
    assert recipe["workflow"] == "arrange-over-song" and recipe["model"] is None
    assert recipe["parameters"]["duration"] == 12
    np.testing.assert_array_equal(core.load_item(values["backing_song_id"]), backing_before)
    np.testing.assert_array_equal(core.load(service.asset(recipe["musical_file"])), backing_before)
    expected = core.load_item(item["id"])
    assert len(expected) == len(backing_before) and np.isfinite(expected).all()
    assert np.max(np.abs(expected)) <= 1
    ingredients = service.ingredients(item["id"])["available"]
    assert (
        ingredients["workflow"] == "arrange-over-song"
        and "lyrics" not in ingredients
        and "styles" not in ingredients
    )
    moved = tmp_path / "moved"
    shutil.copytree(core.LIB, moved)
    monkeypatch.setattr(core, "LIB", moved)
    monkeypatch.setattr(core, "CATALOG", moved / "catalog.json")
    monkeypatch.setattr(core, "INBOX", moved / "inbox")
    replay = service.rerender(item["id"])
    np.testing.assert_allclose(core.load_item(replay["id"]), expected, atol=1 / 32768)


@pytest.mark.parametrize(
    "case",
    ["missing-backing", "voice-backing", "no-recordings", "duplicate-backing", "unknown-workflow"],
)
def test_invalid_collections_fail_before_changing_backing(core, songs, case):
    service, calls = songs
    values = draft(core)
    if case == "missing-backing":
        values["backing_song_id"] = ""
    if case == "voice-backing":
        values["backing_song_id"] = values["clips"][0]["id"]
    if case == "no-recordings":
        values["clips"] = []
    if case == "duplicate-backing":
        values["clips"] = [{"id": values["backing_song_id"]}]
    if case == "unknown-workflow":
        values["workflow"] = "future-unsupported"
    with pytest.raises(ValueError):
        service.generate(values, lambda *_a, **_k: None, lambda: False)
    assert not calls and len(core.list_items()) == 2


def test_sequential_two_arrangements_and_cancel_keep_first(core, songs):
    service, calls = songs
    values = draft(core)
    values["count"] = 2
    cancel = [False]

    def progress(_message, _fraction=0, **details):
        if details.get("stage") == "output_complete":
            cancel[0] = True

    with pytest.raises(Canceled) as failure:
        service.generate(values, progress, lambda: cancel[0])
    assert failure.value.result is not None
    assert [output["status"] for output in failure.value.result["outcomes"]] == [
        "complete",
        "canceled",
    ]
    assert len(core.list_items()) == 3 and not calls


def test_energy_gaps_and_phase_guide_placements_without_losing_sources():
    sr = 8000
    context = {
        "energy": [1] * 20 + [0] * 20 + [1] * 20,
        "energy_hop": sr // 4,
        "beat_phase_seconds": 0.125,
    }
    samples = [
        {
            "id": "s0",
            "family_id": "f0",
            "source_index": 0,
            "variant": 0,
            "kind": "phrase",
            "role": "statement",
            "length_samples": sr,
        }
    ]
    import random

    events, _ = plan_events(samples, sr * 15, sr, 120, random.Random(42), backing_context=context)
    assert any(5 <= event["offset_samples"] / sr < 9 for event in events)
    assert all((event["offset_samples"] - round(sr * 0.125)) % (sr // 4) == 0 for event in events)


def test_tonal_alignment_is_confidence_gated_and_preserves_manual_offset():
    source = {"sung": True, "key_reliable": True, "key_detected": "A minor"}
    target = {"key_reliable": True, "key_detected": "C minor"}
    settings = {**CLIP_DEFAULTS, "pitch": -1}
    result, info = align_recording(settings, source, target)
    assert result["pitch"] == 2 and settings["pitch"] == -1 and info["semitones"] == 3
    unchanged, info = align_recording(settings, source, {**target, "key_reliable": False})
    assert unchanged == settings and not info["applied"]


def test_silent_backing_has_recorded_fallback_without_analyzer_claims():
    def no_analysis(_audio):
        raise AssertionError("Silent backing must not invent analysis")

    context = backing_context(np.zeros((8000, 2), np.float32), 8000, no_analysis)
    assert context["tempo_source"] == "fallback" and context["bpm"] == 90
    assert not context["key_reliable"] and context["analysis_windows"] == []


def test_two_outputs_finish_in_sequence_and_keep_independent_recipes(core, songs):
    service, calls = songs
    values = draft(core)
    values["count"] = 2
    finished = []

    def progress(_message, _fraction=0, **details):
        if details.get("stage") == "output_complete":
            finished.append(details["item"])
            assert len(core.list_items()) == 2 + len(finished)

    outputs = service.generate(values, progress, lambda: False)["outcomes"]
    assert finished == [1, 2] and [o["status"] for o in outputs] == ["complete", "complete"]
    recipes = [o["song"]["recipe"] for o in outputs]
    assert recipes[0]["musical_file"] != recipes[1]["musical_file"] and not calls


def test_partial_wav_failure_cleans_only_new_output_assets(core, songs, monkeypatch):
    service, _ = songs
    values = draft(core)
    before = {item["id"] for item in core.list_items()}

    def fail(path, _audio):
        path.write_bytes(b"partial output")
        raise OSError("Synthetic WAV storage failure")

    monkeypatch.setattr(core, "save_wav", fail)
    result = service.generate(values, lambda *_a, **_k: None, lambda: False)
    assert result["outcomes"][0]["status"] == "failed"
    assert "Synthetic WAV storage failure" in result["problems"][0]
    assert {item["id"] for item in core.list_items()} == before
    assert not list((core.LIB / "assets/songs").glob("*"))
    assert all(
        path.read_bytes() != b"partial output" for path in (core.LIB / "mixes").glob("*.wav")
    )
