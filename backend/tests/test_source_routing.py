import copy
import random
from collections import Counter

import numpy as np
import pytest

from arrangement import plan_events, route_sources, sample_transform, select_regions
from songs import CLIP_DEFAULTS


CASES = [
    (1, 0, "one-prior"),
    (0, 1, "one-recording"),
    (2, 0, "multiple-priors"),
    (0, 2, "multiple-recordings"),
    (1, 1, "one-prior+one-recording"),
    (1, 2, "one-prior+multiple-recordings"),
    (2, 1, "multiple-priors+one-recording"),
    (2, 2, "multiple-priors+multiple-recordings"),
]


def mixed_audio(sr=8000, seconds=12):
    t = np.arange(sr * seconds) / sr
    harmony = 0.04 * sum(np.sin(2 * np.pi * frequency * t) for frequency in (220, 277, 330))
    pulse = np.zeros_like(t)
    rng = np.random.default_rng(4)
    for onset in (0.5, 1, 2, 3.5, 5, 6.5, 8, 9.5, 11):
        position = round(onset * sr)
        size = min(round(sr * 0.1), len(t) - position)
        pulse[position : position + size] += (
            0.1 * rng.standard_normal(size) * np.exp(-np.arange(size) / (sr * 0.02))
        )
    return np.repeat((harmony + pulse)[:, None], 2, axis=1).astype(np.float32)


def sources(priors, recordings):
    return [
        {"id": str(index), "source_type": kind, "settings": {**CLIP_DEFAULTS}}
        for index, kind in enumerate(["prior-song"] * priors + ["upload"] * recordings)
    ]


@pytest.mark.parametrize("priors,recordings,collection", CASES)
def test_all_collections_have_independent_roles_coverage_and_bounded_returns(
    priors, recordings, collection
):
    original = sources(priors, recordings)
    before = copy.deepcopy(original)
    routed = route_sources(original)
    assert original == before
    audio = mixed_audio()
    samples = []
    for index, source in enumerate(routed):
        policy = source["routing"]
        assert policy["collection"] == collection
        assert policy["classification"] == ("finished-mix" if index < priors else "recording")
        regions, info = select_regions(
            audio,
            8000,
            source["settings"],
            {"tempo_raw": 120, "tempo_confidence": 3},
            random.Random(42),
            120 / len(routed),
            policy,
        )
        if index < priors:
            assert not info["whole_clip_included"]
            assert info["measured_anchors"] > 0
            assert all(region["end"] - region["start"] <= 8000 for region in regions)
            assert info["effective_budget"] <= policy["sample_cap"]
        for family, region in enumerate(regions):
            for variant in range(3):
                samples.append(
                    {
                        "id": f"{index}-{family}-{variant}",
                        "family_id": f"{index}-{family}",
                        "source_index": index,
                        "source_type": source["source_type"],
                        "variant": variant,
                        "kind": region["kind"],
                        "role": ("statement", "response", "fill")[variant],
                        "length_samples": region["end"] - region["start"],
                    }
                )
    events, plan = plan_events(
        samples, 120 * 8000, 8000, 120, random.Random(42), routed[0]["routing"]
    )
    assert (
        events
        == plan_events(samples, 120 * 8000, 8000, 120, random.Random(42), routed[0]["routing"])[0]
    )
    assert {event["motif"] for event in events} == {
        f"source-{index}" for index in range(len(routed))
    }
    assert plan["rest_seconds"] > 36
    families = Counter(event["family_id"] for event in events)
    for sample in samples:
        if sample["source_type"] == "prior-song":
            assert families[sample["family_id"]] <= (2 if recordings else 3)


def test_finished_mix_octaves_and_user_offsets_do_not_change_pitch_classes():
    settings = {**CLIP_DEFAULTS, "pitch": -1, "stretch": 1.05, "gain": -3}
    policy = route_sources(sources(1, 1))[0]["routing"]
    values = [
        sample_transform(
            settings, {"kind": "phrase", "rms": 0.08}, 0, random.Random(5), variant, policy=policy
        )
        for variant in range(3)
    ]
    assert values[0]["pitch"] == -1 and values[0]["stretch"] == 1.05
    # An octave outside the supported range returns to the requested register.
    assert values[1]["pitch"] == 11 and values[2]["pitch"] == -1
    assert values[0]["gain"] == -3


def test_unreliable_tempo_uses_explicit_fallback_and_originals_stay_unchanged():
    audio = mixed_audio()
    before = audio.copy()
    policy = route_sources(sources(1, 0))[0]["routing"]
    _, info = select_regions(
        audio,
        8000,
        CLIP_DEFAULTS,
        {"tempo_raw": 180, "tempo_confidence": 0.5},
        random.Random(9),
        120,
        policy,
    )
    assert info["tempo_policy"] == "fallback" and info["effective_sample_seconds"] == 1.25
    np.testing.assert_array_equal(audio, before)


def test_catalog_authority_wins_over_client_source_label_and_filename(core, songs):
    service, _ = songs
    voice = core._new_entry("voice", "prior song mix.wav", core.synth_voice(3), "fixture")
    prior = core._new_entry("generated", "plain recording", core.synth_voice(3), "fixture")
    draft = {
        "clips": [
            {"id": voice["id"], "source_type": "prior-song"},
            {"id": prior["id"], "source_type": "upload", "settings": {"pitch": -2}},
        ],
        "styles": "spoken, no music",
        "lyrics": "Keep these words.",
    }
    before = copy.deepcopy(draft)
    routed = service.collect_sources(draft)
    assert [source["source_type"] for source in routed] == ["upload", "prior-song"]
    assert routed[1]["settings"]["pitch"] == -2
    assert draft == before
