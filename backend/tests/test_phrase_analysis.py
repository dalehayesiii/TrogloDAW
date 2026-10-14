"""Invented voice activity and waveforms prove safe boundaries, cache and replay."""

import copy
import json
import random
import shutil
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

from arrangement import route_sources, select_regions
from models import Canceled
from phrase_analysis import probability_spans, validate_evidence
from songs import CLIP_DEFAULTS
from test_arrangement_quality import articulated_source
from test_source_routing import CASES


def evidence(samples, sr, intervals=()):
    scores = np.zeros(((samples * 16000 + sr - 1) // sr + 511) // 512)
    for begin, end in intervals:
        scores[int(begin / 0.032) : int(end / 0.032)] = 0.9
    return probability_spans(scores, samples, sr)


def test_hysteresis_keeps_articulation_and_short_words_without_forced_duration_cut():
    scores = np.zeros(625)  # 20 seconds
    scores[5:450] = 0.9
    scores[100:106] = 0  # a 192 ms articulation gap, not a new phrase
    scores[475:477] = 0.9  # a brief word must not disappear
    result = probability_spans(scores, 20 * 16000, 16000)
    assert len(result["spans"]) == 2
    first, last = result["spans"]
    assert first["start"] == 0 and first["end"] >= round(450 * 512 + 0.24 * 16000)
    assert last["start"] <= 475 * 512 and last["end"] >= 477 * 512
    assert validate_evidence(result, 20 * 16000, 16000) == result


@pytest.mark.parametrize("bad", [np.nan, -0.1, 1.1])
def test_invalid_probabilities_cannot_authorize_cuts(bad):
    with pytest.raises(ValueError, match="evidence"):
        probability_spans([bad], 512, 16000)
    with pytest.raises(ValueError, match="evidence"):
        probability_spans([[0]], 512, 16000)


def test_near_threshold_sustained_activity_abstains_and_cache_bounds_are_checked():
    result = probability_spans(np.full(100, 0.3), 51200, 16000)
    assert result["status"] == "uncertain" and not result["instrumental_confident"]
    speech = evidence(7 * 8000, 8000, [(0.2, 1.8), (2.1, 4.6), (5, 6.8)])
    for corrupt in (
        {**speech, "samples": 1},
        {**speech, "spans": [{"start": -1, "end": 100}]},
        {**speech, "spans": [{"start": 10, "end": 90000}]},
        {**speech, "spans": [{"start": 0.5, "end": 100}]},
        {**speech, "spans": list(reversed(speech["spans"]))},
        {**speech, "peak_probability": float("inf")},
        {**speech, "status": "instrumental", "spans": [], "instrumental_confident": True},
    ):
        with pytest.raises(ValueError, match="cached"):
            validate_evidence(corrupt, 7 * 8000, 8000)


@pytest.mark.parametrize("scale", [1, 0.003])
@pytest.mark.parametrize("bed", [0, 0.02])
def test_protected_voice_over_continuous_bed_is_whole_even_with_one_second_preset(scale, bed):
    sr = 8000
    audio = articulated_source(sr)
    audio += bed * np.sin(2 * np.pi * 220 * np.arange(len(audio)) / sr)[:, None]
    audio *= scale
    before = audio.copy()
    speech = evidence(len(audio), sr, [(0.2, 1.8), (2.1, 4.6), (5, 6.8)])
    settings = {**CLIP_DEFAULTS, "sample_seconds": 1, "version": "prior-song-v1"}
    regions, info = select_regions(audio, sr, settings, {"speech": speech}, random.Random(5), 120)
    for begin, end in ((0.2, 1.8), (2.1, 4.6), (5, 6.8)):
        assert any(r["start"] <= begin * sr and r["end"] >= end * sr for r in regions)
    for region in regions:
        for span in speech["spans"]:
            if region["start"] < span["end"] and region["end"] > span["start"]:
                assert region["start"] <= span["start"] and region["end"] >= span["end"]
    assert info["boundary_policy"] == "speech-pauses"
    assert info["longest_selected_seconds"] > 2
    np.testing.assert_array_equal(audio, before)


def test_no_fit_and_unknown_continuous_prior_do_not_chop_words_to_fill_budget():
    sr = 8000
    audio = np.repeat((0.1 * np.sin(2 * np.pi * 220 * np.arange(20 * sr) / sr))[:, None], 2, 1)
    analysis = {"speech": evidence(len(audio), sr, [(0, 20)])}
    with pytest.raises(ValueError, match="longer song duration"):
        select_regions(audio, sr, CLIP_DEFAULTS, analysis, guide_seconds=10)
    prior = route_sources([{"source_type": "prior-song", "settings": CLIP_DEFAULTS}])[0]
    with pytest.raises(ValueError, match="complete safe phrase"):
        select_regions(audio, sr, CLIP_DEFAULTS, {}, policy=prior["routing"])
    # Qualified instrumental material still supports bounded short motifs.
    regions, info = select_regions(
        audio, sr, CLIP_DEFAULTS, {"speech": evidence(len(audio), sr)}, policy=prior["routing"]
    )
    assert len(regions) > 1 and info["boundary_policy"] == "instrumental-best-effort"
    assert all(r["end"] - r["start"] <= 1.25 * sr for r in regions)


@pytest.mark.parametrize("priors,recordings,collection", CASES)
def test_all_collections_protect_detected_vocals(priors, recordings, collection):
    sr = 8000
    audio = articulated_source(sr)
    speech = evidence(len(audio), sr, [(0.2, 1.8), (2.1, 4.6), (5, 6.8)])
    sources = route_sources(
        [
            {"source_type": kind, "settings": CLIP_DEFAULTS}
            for kind in ["prior-song"] * priors + ["upload"] * recordings
        ]
    )
    for source in sources:
        regions, info = select_regions(
            audio,
            sr,
            source["settings"],
            {"speech": speech},
            random.Random(7),
            120 / len(sources),
            source["routing"],
        )
        assert source["routing"]["collection"] == collection
        assert 1 <= len(regions) <= source["routing"]["sample_cap"]
        assert all(r["protected_vocals"] for r in regions)
        assert info["boundary_policy"] == "speech-pauses"


def detector_fixture(service, core, monkeypatch):
    root = core.LIB.parent / "synthetic-models"
    root.mkdir()
    model = {"id": "fixture-vad", "path": "detector.jit", "sha256": "fixture", "revision": "v1"}
    monkeypatch.setattr(service.models, "source_analysis_ready", lambda: model, raising=False)
    monkeypatch.setattr(service.models, "storage", SimpleNamespace(models=root), raising=False)
    audio = articulated_source(core.SR)
    path = core.LIB / "fixture.wav"
    sf.write(path, audio, core.SR, subtype="FLOAT")
    calls = []

    def invoke(action, values, progress, canceled):
        assert action == "analyze_phrases" and values["speech_model"] == str(root / "detector.jit")
        calls.append(action)
        return evidence(len(audio), core.SR, [(0.2, 1.8), (2.1, 4.6), (5, 6.8)])

    monkeypatch.setattr(service, "invoke", invoke)
    return path, audio, calls, model


def test_cpu_cache_reuse_corruption_model_change_and_library_relocation(core, songs, monkeypatch):
    service, _ = songs
    path, audio, calls, model = detector_fixture(service, core, monkeypatch)
    before = path.read_bytes()
    first = service.source_phrases(path, audio, lambda *a, **k: None, lambda: False)
    second = service.source_phrases(path, audio, lambda *a, **k: None, lambda: False)
    assert len(calls) == 1 and second["reused"] and not first["reused"]
    assert first["cache_file"].startswith("assets/source-analysis/")
    assert first["detector"]["model"] == model["id"]
    cache = service.asset(first["cache_file"])
    saved = json.loads(cache.read_text())
    saved["evidence"]["spans"][0]["end"] = len(audio) + 1
    cache.write_text(json.dumps(saved))
    service.source_phrases(path, audio, lambda *a, **k: None, lambda: False)
    assert len(calls) == 2  # invalid evidence recomputed
    relocated = core.LIB.parent / "relocated-library"
    shutil.copytree(core.LIB, relocated)
    monkeypatch.setattr(core, "LIB", relocated)
    moved = service.source_phrases(
        relocated / path.name, audio, lambda *a, **k: None, lambda: False
    )
    assert moved["reused"] and len(calls) == 2
    model["sha256"] = "new-revision"
    changed = service.source_phrases(
        relocated / path.name, audio, lambda *a, **k: None, lambda: False
    )
    assert not changed["reused"] and len(calls) == 3
    assert (relocated / path.name).read_bytes() == before


def test_analysis_failure_and_cancel_have_distinct_recovery(core, songs, monkeypatch):
    service, _ = songs
    path, audio, _, _ = detector_fixture(service, core, monkeypatch)

    def unavailable(*args, **kwargs):
        raise RuntimeError("Synthetic detector failure")

    monkeypatch.setattr(service, "invoke", unavailable)
    fallback = service.source_phrases(path, audio, lambda *a, **k: None, lambda: False)
    assert fallback["status"] == "fallback"
    regions, info = select_regions(audio, core.SR, CLIP_DEFAULTS, {"speech": fallback})
    assert regions and info["boundary_policy"] == "conservative-acoustic-pauses"
    with pytest.raises(Canceled, match="analysis"):
        service.source_phrases(path, audio, lambda *a, **k: None, lambda: True)
    assert not list((core.LIB / "assets/source-analysis").glob("*.json"))


def test_replay_skips_new_phrase_analysis(core, songs, monkeypatch):
    service, _ = songs
    item = core._new_entry("voice", "invented phrase", articulated_source(core.SR), "fixture")
    draft = {"clips": [{"id": item["id"]}], "styles": "folk", "options": {"duration": 30}}
    outcome = service.generate(draft, lambda *a, **k: None, lambda: False)["outcomes"][0]
    assert outcome["status"] == "complete"
    ingredients = service.ingredients(outcome["song"]["id"])["available"]

    def unexpected(*args, **kwargs):
        raise AssertionError("Explicit saved arrangement must bypass fresh analysis")

    monkeypatch.setattr(service, "source_phrases", unexpected)
    result = service.generate(
        {
            **draft,
            "clips": ingredients["clips"],
            "arrangement": copy.deepcopy(ingredients["arrangement"]),
        },
        lambda *a, **k: None,
        lambda: False,
    )["outcomes"][0]
    assert result["status"] == "complete"
    assert [
        (p["offset_samples"], p["length_samples"], p["gain"])
        for p in result["song"]["recipe"]["placements"]
    ] == [
        (p["offset_samples"], p["length_samples"], p["gain"])
        for p in outcome["song"]["recipe"]["placements"]
    ]


@pytest.mark.parametrize("backing", [False, True])
def test_sequential_outputs_reuse_cpu_evidence_and_keep_original_assets(
    core, songs, monkeypatch, backing
):
    service, _ = songs
    original_invoke = service.invoke
    _, audio, _, _ = detector_fixture(service, core, monkeypatch)
    # Restore synthetic music generation while keeping actual parent-side cache management.
    calls = []

    def invoke(action, values, progress, canceled):
        if action == "analyze_phrases":
            calls.append(action)
            return evidence(len(audio), core.SR, [(0.2, 1.8), (2.1, 4.6), (5, 6.8)])
        return original_invoke(action, values, progress, canceled)

    monkeypatch.setattr(service, "invoke", invoke)
    item = core._new_entry("voice", "invented words", audio, "fixture")
    original = core.load_item(item["id"])
    draft = {
        "clips": [{"id": item["id"]}],
        "styles": "folk",
        "options": {"duration": 30},
        "count": 2,
    }
    if backing:
        song = core._new_entry("mix", "invented backing", core.synth_voice(30) * 0.1, "fixture")
        draft.update(workflow="arrange-over-song", backing_song_id=song["id"])
    outputs = service.generate(draft, lambda *a, **k: None, lambda: False)["outcomes"]
    assert [outcome["status"] for outcome in outputs] == ["complete", "complete"]
    assert calls == ["analyze_phrases"]
    recipes = [outcome["song"]["recipe"] for outcome in outputs]
    assert [recipe["analysis"][0]["analysis"]["speech"]["reused"] for recipe in recipes] == [
        False,
        True,
    ]
    for recipe in recipes:
        np.testing.assert_array_equal(
            core.load(service.asset(recipe["sources"][0]["file"])), original
        )
        assert all(
            sample["selection"]["boundary_policy"] == "speech-pauses"
            for sample in recipe["samples"]
        )
    assert not list((core.LIB / "assets").rglob("*-phrase-analysis.wav"))


def test_cancel_during_second_phrase_analysis_preserves_first_output(core, songs, monkeypatch):
    service, _ = songs
    item = core._new_entry("voice", "invented voice", articulated_source(core.SR), "fixture")
    analysis_calls = 0
    original = service.source_phrases

    def cancel_second(*args):
        nonlocal analysis_calls
        analysis_calls += 1
        if analysis_calls == 2:
            raise Canceled("Phrase analysis canceled")
        return original(*args)

    monkeypatch.setattr(service, "source_phrases", cancel_second)
    with pytest.raises(Canceled) as failure:
        service.generate(
            {
                "clips": [{"id": item["id"]}],
                "styles": "folk",
                "options": {"duration": 30},
                "count": 2,
            },
            lambda *a, **k: None,
            lambda: False,
        )
    assert failure.value.result is not None
    outcomes = failure.value.result["outcomes"]
    assert [outcome["status"] for outcome in outcomes] == ["complete", "canceled"]
    assert core.get_item(outcomes[0]["song"]["id"])
    assert not list((core.LIB / "assets").rglob("*-phrase-analysis.wav"))
