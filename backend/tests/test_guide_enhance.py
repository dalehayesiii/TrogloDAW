import copy
import shutil

import numpy as np
import pytest
import soundfile as sf
from scipy import signal

import guide_enhance
from guide_enhance import enhance_guide, loudness, settings

SR = 44100


def harsh_guide(seconds=6, level=0.01, seed=3):
    """Synthetic quiet vocal-like guide: harsh 3.5 kHz partials, noisy gaps and a click."""
    rng = np.random.default_rng(seed)
    t = np.arange(SR * seconds) / SR
    voice = sum(np.sin(2 * np.pi * f * t) / (i + 1) for i, f in enumerate((220, 440, 660)))
    voice += 1.5 * np.sin(2 * np.pi * 3500 * t)
    phrases = ((t % 1.5) < 0.9).astype(float)
    audio = level * voice * phrases + 0.0004 * rng.standard_normal(len(t))
    audio[SR * 2 + 100] += 0.4
    return np.repeat(audio[:, None], 2, axis=1).astype(np.float32)


def band_share(audio, low, high):
    f, p = signal.welch(audio.mean(1), SR, nperseg=4096)
    return p[(f >= low) & (f < high)].sum() / p.sum()


def gap_rms(audio):
    t = np.arange(len(audio)) / SR
    return float(np.sqrt(np.mean(audio[(t % 1.5) > 1.0] ** 2)))


def test_light_improves_quiet_harsh_noisy_guide_without_mutating_input():
    raw = harsh_guide()
    before = raw.copy()
    out, info = enhance_guide(raw, SR, "light", 50)
    np.testing.assert_array_equal(raw, before)
    assert info["applied"] and info["effective"] == "light" and info["version"] == 1
    assert info["metrics"]["discontinuities_repaired"] >= 1
    assert loudness(out, SR) > loudness(raw, SR) + 3
    assert loudness(out, SR) < guide_enhance.TARGET_LUFS + 1.5
    assert np.max(np.abs(out)) <= guide_enhance.PEAK + 1e-6
    assert band_share(out, 3000, 4000) < band_share(raw, 3000, 4000)
    level = 10 ** ((loudness(out, SR) - loudness(raw, SR)) / 20)
    assert gap_rms(out) < gap_rms(raw) * level * 0.7


def test_quiet_input_lift_is_bounded():
    raw = harsh_guide(level=0.0005)
    out, info = enhance_guide(raw, SR, "light", 100)
    assert info["metrics"]["lift_db"] <= guide_enhance.MAX_LIFT_DB
    assert loudness(out, SR) - loudness(raw, SR) <= guide_enhance.MAX_LIFT_DB + 1


def test_off_and_zero_strength_preserve_guide():
    raw = harsh_guide()
    out, info = enhance_guide(raw, SR, "off", 50)
    assert out is raw and not info["applied"]
    gentle, info = enhance_guide(raw, SR, "light", 0)
    assert info["metrics"]["lift_db"] == 0
    assert info["metrics"]["spectral_distance_db"] < 1


def test_ai_clean_resolves_to_light_with_reason():
    out, info = enhance_guide(harsh_guide(), SR, "ai_clean", 50)
    assert info["requested"] == "ai_clean" and info["effective"] == "light"
    assert "unavailable" in info["fallback_reason"] and info["applied"]


@pytest.mark.parametrize(
    "broken, reason",
    [
        (lambda a: a * np.nan, "invalid"),
        (lambda a: a * 0, "silent"),
        (
            lambda a: np.random.default_rng(1).standard_normal(a.shape).astype(np.float32),
            "too much",
        ),
    ],
)
def test_unsafe_results_fall_back_to_raw(monkeypatch, broken, reason):
    raw = harsh_guide()
    monkeypatch.setattr(guide_enhance, "light", lambda a, sr, s: (broken(a), {}))
    out, info = enhance_guide(raw, SR, "light", 50)
    assert out is raw and not info["applied"] and reason in info["fallback_reason"]


def test_silent_guide_and_settings_validation():
    silent = np.zeros((SR, 2), np.float32)
    out, info = enhance_guide(silent, SR, "light", 50)
    assert out is silent and not info["applied"]
    assert settings({}) == {"tier": "light", "strength": 50}
    for bad in (
        {"guide_enhancement": "strong"},
        {"guide_enhancement_strength": 101},
        {"guide_enhancement_strength": True},
    ):
        with pytest.raises(ValueError):
            settings(bad)


@pytest.mark.parametrize("measurement", ["spectral_distance", "loudness"])
def test_measurement_failure_preserves_raw_and_explains_fallback(monkeypatch, measurement):
    raw = harsh_guide()
    monkeypatch.setattr(guide_enhance, "light", lambda a, sr, s: (a.copy(), {}))

    def fail(*args):
        raise RuntimeError("synthetic measurement failure")

    monkeypatch.setattr(guide_enhance, measurement, fail)
    out, info = enhance_guide(raw, SR, "ai_clean", 50)
    assert out is raw and not info["applied"]
    assert "unavailable" in info["fallback_reason"]
    assert "synthetic measurement failure" in info["fallback_reason"]


def test_opposite_phase_stereo_cannot_hide_large_spectral_changes(monkeypatch):
    t = np.arange(SR * 2) / SR
    tone = np.sin(2 * np.pi * 220 * t).astype(np.float32) * 0.1
    raw = np.column_stack((tone, -tone))
    replacement = np.sin(2 * np.pi * 3500 * t).astype(np.float32) * 0.1
    changed = np.column_stack((replacement, -replacement))
    monkeypatch.setattr(guide_enhance, "light", lambda a, sr, s: (changed, {}))
    out, info = enhance_guide(raw, SR, "light", 50)
    assert out is raw and not info["applied"]
    assert "too much" in info["fallback_reason"]


def test_shape_change_and_invalid_safety_measurement_fall_back(monkeypatch):
    raw = harsh_guide()
    monkeypatch.setattr(guide_enhance, "light", lambda a, sr, s: (a[:-1], {}))
    out, info = enhance_guide(raw, SR, "light", 50)
    assert out is raw and "shape" in info["fallback_reason"]
    monkeypatch.setattr(guide_enhance, "light", lambda a, sr, s: (a.copy(), {}))
    monkeypatch.setattr(guide_enhance, "spectral_distance", lambda *args: float("nan"))
    out, info = enhance_guide(raw, SR, "light", 50)
    assert out is raw and "invalid" in info["fallback_reason"]


def generate(service, core, clip, **draft):
    return service.generate(
        {
            "clips": [{"id": clip["id"]}],
            "styles": "folk",
            "options": {"duration": 10},
            "audio_mode": "conditioned",
            **draft,
        },
        lambda *_a, **_k: None,
        lambda: False,
    )["outcomes"][0]


def test_conditioned_generation_receives_enhanced_guide_and_keeps_raw(
    core, songs, tmp_path, monkeypatch
):
    service, _ = songs
    service.models.manifest["models"]["base"]["conditioning"] = ["cover"]
    clip = core._new_entry("voice", "phrases", core.synth_voice(4), "fixture")
    received, messages = [], []
    original = service.invoke

    def invoke(action, values, progress, canceled):
        if action == "generate":
            received.append(sf.read(values["conditioning_audio"], always_2d=True)[0])
            assert values["parameters"]["guide_enhancement"]["effective"] == "light"
        return original(action, values, progress, canceled)

    service.invoke = invoke
    output = service.generate(
        {
            "clips": [{"id": clip["id"]}],
            "styles": "folk",
            "options": {"duration": 10},
            "audio_mode": "conditioned",
        },
        lambda message, *_a, **_k: messages.append(message),
        lambda: False,
    )["outcomes"][0]
    recipe = output["song"]["recipe"]
    assert recipe["guide_enhancement"]["applied"]
    assert recipe["draft"]["guide_enhancement"] == "light"
    assert recipe["draft"]["guide_enhancement_strength"] == 50
    assert not recipe["conditioning_raw_file"].startswith("/")
    enhanced = core.load(service.asset(recipe["conditioning_file"]))
    raw = core.load(service.asset(recipe["conditioning_raw_file"]))
    np.testing.assert_allclose(enhanced, received[0], atol=1e-6)
    assert not np.allclose(enhanced, raw)
    assert output["arrangement_raw_audio"] and output["guide_enhancement"]["applied"]
    assert "Arrangement guide enhanced" in messages
    ingredients = service.ingredients(output["song"]["id"])["available"]
    assert ingredients["guide_enhancement"] == "light"
    expected = core.load_item(output["song"]["id"])
    moved = tmp_path / "relocated-library"
    shutil.copytree(core.LIB, moved)
    monkeypatch.setattr(core, "LIB", moved)
    monkeypatch.setattr(core, "CATALOG", moved / "catalog.json")
    monkeypatch.setattr(core, "INBOX", moved / "inbox")
    assert service.asset(recipe["conditioning_raw_file"]).is_file()
    relocated = service.rerender(output["song"]["id"])
    np.testing.assert_allclose(core.load_item(relocated["id"]), expected, atol=1 / 32768)


def test_off_postmix_and_saved_arrangement_reuse(core, songs):
    service, _ = songs
    service.models.manifest["models"]["base"]["conditioning"] = ["cover"]
    clip = core._new_entry("voice", "phrases", core.synth_voice(4), "fixture")
    off = generate(service, core, clip, guide_enhancement="off")["song"]["recipe"]
    assert not off["guide_enhancement"]["applied"] and "conditioning_raw_file" not in off
    postmix = generate(service, core, clip, audio_mode="postmix")["song"]["recipe"]
    assert "guide_enhancement" not in postmix and "conditioning_raw_file" not in postmix
    first = generate(service, core, clip)["song"]
    reused = service.ingredients(first["id"])["available"]
    draft = copy.deepcopy(
        {
            "clips": reused["clips"],
            "arrangement": reused["arrangement"],
            "styles": "folk",
            "options": {"duration": 10},
            "guide_enhancement": "ai_clean",
            "guide_enhancement_strength": 80,
            "audio_mode": "conditioned",
        }
    )
    messages = []
    again = service.generate(draft, lambda m, *_a, **_k: messages.append(m), lambda: False)
    recipe = again["outcomes"][0]["song"]["recipe"]
    assert recipe["guide_enhancement"]["requested"] == "ai_clean"
    assert recipe["guide_enhancement"]["effective"] == "light"
    assert recipe["guide_enhancement"]["strength"] == 80
    assert any("unavailable" in m for m in messages)
    assert service.asset(recipe["conditioning_raw_file"]).is_file()
