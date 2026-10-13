"""Quality regressions use invented signals, never private input audio."""

import random
from collections import Counter

import numpy as np
import pytest

from arrangement import plan_events, sample_transform, select_regions
from songs import CLIP_DEFAULTS


def articulated_source(sr=8000):
    """Seven seconds with three changing phrases and brief articulation gaps."""
    time = np.arange(sr * 7) / sr
    audio = np.zeros(len(time))
    for start, end, hz in ((0.2, 1.8, 180), (2.1, 4.6, 330), (5.0, 6.8, 520)):
        mask = (time >= start) & (time < end)
        envelope = 0.2 + 0.8 * np.sin(np.pi * (time[mask] - start) / (end - start)) ** 2
        audio[mask] = (
            0.18
            * envelope
            * (np.sin(2 * np.pi * hz * time[mask]) + 0.2 * np.sin(4 * np.pi * hz * time[mask]))
        )
    for start in (0.9, 2.9, 3.7, 5.7):
        audio[round(start * sr) : round((start + 0.1) * sr)] = 0
    return np.repeat(audio[:, None], 2, axis=1).astype(np.float32)


def descriptors(regions, sr=8000, sources=1):
    result = []
    for source in range(sources):
        for index, region in enumerate(regions):
            for variant, factor in enumerate((1, 0.93, 0.8)):
                result.append(
                    {
                        "id": f"s{source}-{index}-v{variant}",
                        "family_id": f"s{source}-{index}",
                        "source_index": source,
                        "variant": variant,
                        "length_samples": round((region["end"] - region["start"]) * factor),
                        "role": ("statement", "response", "fill")[variant],
                        "kind": region["kind"],
                    }
                )
    return result


def test_phrase_diversity_survives_articulation_transient_and_level_changes():
    sr = 8000
    audio = articulated_source(sr)
    audio[round(0.04 * sr)] = 0.9  # a brief pop must not set the whole-source threshold
    settings = {**CLIP_DEFAULTS, "sample_seconds": 2}
    choices = []
    for scale in (1, 0.03, 0.003):
        regions, budget = select_regions(audio * scale, sr, settings, {}, random.Random(42), 120)
        choices.append([(r["start"], r["end"], r["kind"]) for r in regions])
        assert 3 <= len(regions) <= settings["samples"]
        lengths = [(r["end"] - r["start"]) / sr for r in regions]
        assert max(lengths) >= 1.6 and min(lengths) <= 1.3
        assert len({r["kind"] for r in regions}) >= 2
        assert any(r["start"] < sr * 2 and r["end"] >= sr * 1.7 for r in regions)
        assert any(sr * 2 <= r["start"] < sr * 4.7 for r in regions)
        assert any(r["start"] >= sr * 5 for r in regions)
        assert budget["active_seconds"] > 4
    assert choices[0] == choices[1] == choices[2]
    with pytest.raises(ValueError, match="audible"):
        select_regions(np.ones((sr, 2), np.float32) * 0.1, sr, settings, {})


def test_whole_short_clip_is_seeded_optional_and_prior_preset_stays_short():
    sr = 8000
    audio = articulated_source(sr)
    included = []
    for seed in range(12):
        regions, budget = select_regions(audio, sr, CLIP_DEFAULTS, {}, random.Random(seed), 120)
        whole = [r for r in regions if r["kind"] == "whole-clip"]
        included.append(bool(whole))
        if whole:
            assert whole[0]["start"] == 0 and whole[0]["end"] == len(audio)
            assert any(r["kind"] != "whole-clip" for r in regions)
        assert bool(whole) == budget["whole_clip_included"]
    assert any(included) and not all(included)
    prior = {**CLIP_DEFAULTS, "version": "prior-song-v1", "sample_seconds": 1}
    regions, _ = select_regions(audio, sr, prior, {}, random.Random(1), 120)
    assert all(r["kind"] != "whole-clip" and r["end"] - r["start"] <= sr for r in regions)


@pytest.mark.parametrize("seconds", [10, 120, 300])
def test_sections_rests_spaced_bounded_motifs_and_repeatability(seconds):
    sr = 8000
    regions, _ = select_regions(
        articulated_source(sr), sr, CLIP_DEFAULTS, {}, random.Random(42), seconds
    )
    samples = descriptors(regions, sr)
    events, plan = plan_events(samples, seconds * sr, sr, 100, random.Random(7))
    assert events == plan_events(samples, seconds * sr, sr, 100, random.Random(7))[0]
    assert events != plan_events(samples, seconds * sr, sr, 100, random.Random(8))[0]
    assert {e["family_id"] for e in events} == {s["family_id"] for s in samples}
    counts = Counter(e["sample_id"] for e in events)
    families = Counter(e["family_id"] for e in events)
    assert max(counts.values()) <= 2
    assert max(families.values()) <= plan["family_repeat_cap"] <= 6
    assert plan["rest_seconds"] > seconds * 0.3
    assert all(
        0 <= e["offset_samples"] and e["offset_samples"] + e["length_samples"] <= seconds * sr
        for e in events
    )
    for first, second in zip(events, events[1:]):
        assert (
            second["offset_samples"] - (first["offset_samples"] + first["length_samples"])
            >= sr * 0.16
        )
        assert first["family_id"] != second["family_id"]
    if seconds >= 120:
        assert len({e["variant"] for e in events}) > 1
        assert len({s["target_density"] for s in plan["sections"]}) >= 3
        assert len(set(np.diff([e["offset_samples"] for e in events]))) >= 3
        assert len(events) < 40


def test_single_family_returns_change_variant_and_leave_musical_space():
    sr = 8000
    samples = descriptors([{"start": 0, "end": sr, "kind": "phrase"}], sr)
    events, _ = plan_events(samples, sr * 120, sr, 120, random.Random(2))
    assert len(events) > 1 and len({e["variant"] for e in events}) > 1
    assert all(
        b["offset_samples"] - a["offset_samples"] >= sr * 4 for a, b in zip(events, events[1:])
    )


def test_transforms_preserve_statement_and_evolve_responses():
    region = {"kind": "phrase", "rms": 0.1}
    variants = [sample_transform(CLIP_DEFAULTS, region, 0, random.Random(8), v) for v in range(3)]
    assert variants[0]["pitch"] == 0 and variants[0]["stretch"] == 1
    assert variants[1]["pitch"] > 0 and variants[2]["pitch"] < 0
    assert len({v["high_cut"] for v in variants}) == 3
    assert all(-12 <= v["pitch"] <= 12 and 0.5 <= v["stretch"] <= 2 for v in variants)
    quiet = sample_transform(CLIP_DEFAULTS, {"kind": "phrase", "rms": 1e-7}, 0, random.Random(1))
    assert quiet["gain"] <= CLIP_DEFAULTS["gain"] + 6


def test_saved_variants_have_headroom_reproducible_guide_and_unchanged_source(core, songs):
    service, _ = songs
    audio = articulated_source(core.SR) * 4
    item = core._new_entry("voice", "synthetic articulation", audio, "fixture")
    source = service.collect_sources({"clips": [{"id": item["id"], "settings": {"gain": 12}}]})
    original = core.load_item(item["id"])
    plans = []
    for index in range(2):
        directory = core.LIB / "assets" / f"synthetic-quality-{index}"
        directory.mkdir(parents=True)
        progress = []
        layer, samples, events, analysis = service.arrange(
            source,
            directory,
            {"duration": 120, "seed": 42},
            lambda *a, **k: progress.append(k),
        )
        assert np.max(np.abs(layer)) <= 0.80001
        assert any(s["headroom_gain"] < 1 for s in samples)
        assert all(np.max(np.abs(core.load(service.asset(s["file"])))) <= 0.80001 for s in samples)
        assert all(s["length_samples"] > 0 for s in samples)
        np.testing.assert_array_equal(core.load(service.asset(source[0]["file"])), original)
        assert any(
            p.get("timing_stage_profile", {}).get("planner") == "phrase-motifs-v3" for p in progress
        )
        assert analysis[0]["arrangement"]["rest_seconds"] > 60
        plans.append((layer, events))
    np.testing.assert_array_equal(plans[0][0], plans[1][0])
    assert plans[0][1] == plans[1][1]


def test_budget_one_keeps_one_distinct_cut_with_bounded_useful_variants():
    sr = 8000
    settings = {**CLIP_DEFAULTS, "samples": 1}
    regions, budget = select_regions(
        articulated_source(sr), sr, settings, {}, random.Random(7), 120
    )
    assert len(regions) == budget["effective_budget"] == budget["requested_cap"] == 1
    assert regions[0]["kind"] != "whole-clip"
    events, _ = plan_events(descriptors(regions), sr * 120, sr, 100, random.Random(7))
    assert 1 <= len(events) <= 6 and len({e["family_id"] for e in events}) == 1
    assert len({e["variant"] for e in events}) > 1


def test_short_guide_budgets_slower_material_for_every_source(core, songs):
    service, _ = songs
    inputs = [
        core._new_entry("voice", f"short-guide-{i}", articulated_source(core.SR), "fixture")
        for i in range(2)
    ]
    sources = service.collect_sources(
        {"clips": [{"id": i["id"], "settings": {"stretch": 0.5}} for i in inputs]}
    )
    directory = core.LIB / "assets" / "short-guide"
    directory.mkdir(parents=True)
    _, samples, placements, _ = service.arrange(
        sources, directory, {"duration": 10, "seed": 7}, lambda *a, **k: None
    )
    placed = {p["sample_id"] for p in placements}
    assert {s["source_id"] for s in samples if s["id"] in placed} == {i["id"] for i in inputs}
    assert all(p["offset_samples"] + p["length_samples"] <= 10 * core.SR for p in placements)


def test_cancellation_between_saved_variants_stops_before_inference(core, songs):
    from models import Canceled

    service, calls = songs
    item = core._new_entry("voice", "cancel synthetic", articulated_source(core.SR), "fixture")
    sources = service.collect_sources({"clips": [{"id": item["id"]}]})
    directory = core.LIB / "assets" / "canceled-quality"
    directory.mkdir(parents=True)
    stopped = False

    def progress(*args, **details):
        nonlocal stopped
        if details.get("stage") == "sampling" and details.get("units_complete") == 1:
            stopped = True

    with pytest.raises(Canceled, match="transformation"):
        service.arrange(
            sources, directory, {"duration": 120, "seed": 42}, progress, lambda: stopped
        )
    assert len(list((directory / "samples").glob("*.wav"))) == 1 and not calls


def test_explicit_saved_arrangement_reuse_does_not_resample_or_claim_new_plan(
    core, songs, monkeypatch
):
    service, _ = songs
    item = core._new_entry("voice", "reused synthetic", core.synth_voice(1), "fixture")
    draft = {
        "clips": [{"id": item["id"]}],
        "styles": "folk",
        "audio_mode": "postmix",
        "options": {"duration": 10},
    }
    result = service.generate(draft, lambda *a, **k: None, lambda: False)["outcomes"][0]["song"]
    fields = service.ingredients(result["id"])["available"]

    def unexpected(*args, **kwargs):
        raise AssertionError("Saved layout was unnecessarily resampled")

    monkeypatch.setattr("songs.select_regions", unexpected)
    outcome = service.generate(
        {**draft, "clips": fields["clips"], "arrangement": fields["arrangement"]},
        lambda *a, **k: None,
        lambda: False,
    )["outcomes"][0]
    assert outcome["status"] == "complete"
    recipe = outcome["song"]["recipe"]
    assert all(a["arrangement"]["method"] == "saved-arrangement" for a in recipe["analysis"])
    assert [(p["offset_samples"], p["length_samples"]) for p in recipe["placements"]] == [
        (p["offset_samples"], p["length_samples"]) for p in result["recipe"]["placements"]
    ]
