import copy

import numpy as np
import pytest
import soundfile as sf

from songs import sample_loudness


def tone(core, seconds, amplitude, hz=220):
    return np.repeat(
        (amplitude * np.sin(2 * np.pi * hz * np.arange(round(seconds * core.SR)) / core.SR))[
            :, None
        ],
        2,
        axis=1,
    ).astype(np.float32)


@pytest.mark.parametrize(
    "lyrics,stem_gain,reference",
    [("", 0, "song"), ("words", 0.25, "vocals"), ("words", 0, "song"), ("words", 0.0001, "song")],
)
def test_matches_each_gesture_and_preserves_manual_offsets(
    core, songs, lyrics, stem_gain, reference
):
    service, calls = songs
    directory = core.LIB / "assets" / "matching"
    directory.mkdir(parents=True)
    generated = tone(core, 15, 0.2)
    sf.write(directory / "musical-parts.wav", generated, core.SR, subtype="FLOAT")
    original = service.invoke

    def invoke(action, values, progress, canceled):
        assert action == "separate" and values["reference_only"] is True
        result = original(action, values, progress, canceled)
        sf.write(
            directory / "loudness-reference" / "vocals.wav",
            generated * stem_gain,
            core.SR,
            subtype="FLOAT",
        )
        return result

    service.invoke = invoke
    samples, placements, sources = [], [], []
    for index, (amplitude, seconds, offset) in enumerate(
        [(0.008, 0.15, 0), (0.03, 1, -6), (0.05, 2, 3)]
    ):
        audio = tone(core, seconds, amplitude)
        file = directory / f"sample{index}.wav"
        sf.write(file, audio, core.SR, subtype="FLOAT")
        samples.append({"id": str(index), "source_id": str(index), "file": service.relative(file)})
        placements.append(
            {
                "sample_id": str(index),
                "offset_samples": index * 3 * core.SR,
                "length_samples": len(audio),
                "gain": 0.4,
            }
        )
        sources.append({"id": str(index), "settings": {"gain": offset}})
    layer, metadata = service.match_samples(
        generated,
        directory,
        samples,
        placements,
        sources,
        {"lyrics": lyrics},
        lambda *_a, **_k: None,
        lambda: False,
    )
    assert metadata["reference"] == reference
    assert calls == (["separate"] if lyrics else [])
    target = sample_loudness(core, generated * stem_gain if reference == "vocals" else generated)
    for placement, source in zip(placements, sources, strict=True):
        start, length = placement["offset_samples"], placement["length_samples"]
        assert sample_loudness(core, layer[start : start + length]) == pytest.approx(
            target + source["settings"]["gain"], abs=0.01
        )
        assert placement["pre_match_gain"] == 0.4
    assert metadata["reference_file"] is None or not metadata["reference_file"].startswith(
        str(core.LIB)
    )


def test_new_postmix_recipe_replays_matched_gains_without_inference(core, songs):
    service, calls = songs
    service.models.manifest["models"]["base"]["conditioning"] = ["cover"]
    clip = core._new_entry("voice", "quiet input", tone(core, 2, 0.008), "synthetic")
    outcome = service.generate(
        {
            "clips": [{"id": clip["id"]}],
            "lyrics": "words",
            "styles": "folk",
            "count": 1,
            "options": {"duration": 10},
        },
        lambda *_a, **_k: None,
        lambda: False,
    )["outcomes"][0]
    assert outcome["status"] == "complete", outcome
    song = outcome["song"]
    assert song["recipe"]["render_mode"] == "postmix"
    assert song["recipe"]["sample_loudness_match"]["reference"] == "vocals"
    before = copy.deepcopy(calls)
    replay = service.rerender(song["id"])
    assert calls == before
    np.testing.assert_allclose(
        core.load_item(replay["id"]), core.load_item(song["id"]), atol=1 / 32768
    )


def test_silence_and_extremely_quiet_samples_have_bounded_gain(core, songs):
    service, _ = songs
    directory = core.LIB / "assets" / "quiet"
    directory.mkdir(parents=True)
    for amplitude in (0, 1e-6, 1e-3):
        file = directory / "sample.wav"
        sf.write(file, tone(core, 1, amplitude), core.SR, subtype="FLOAT")
        placements: list[dict] = [
            {"sample_id": "a", "offset_samples": 0, "length_samples": core.SR}
        ]
        layer, _ = service.match_samples(
            tone(core, 2, 0.5),
            directory,
            [{"id": "a", "source_id": "a", "file": service.relative(file)}],
            placements,
            [{"id": "a", "settings": {"gain": 0}}],
            {},
            lambda *_a, **_k: None,
            lambda: False,
        )
        assert np.isfinite(layer).all() and placements[0]["gain"] <= 10 ** (30 / 20)
        if amplitude == 1e-3:
            assert placements[0]["gain"] == pytest.approx(10 ** (30 / 20))
    with pytest.raises(ValueError, match="non-finite"):
        sample_loudness(core, np.full((core.SR, 2), np.nan))
