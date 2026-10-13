"""Optional pre-conditioning enhancement for the arranged sample guide.

The guide is the full-duration arrangement handed to audio-conditioned inference.
Light uses only bundled numpy/scipy/pedalboard DSP. AI clean is reserved for a
verified add-on and currently resolves to Light (see docs/guide-enhancement.md).
"""

from __future__ import annotations

import math

import numpy as np
import pedalboard as pb
from scipy import ndimage, signal

VERSION = 1
TIERS = ("off", "light", "ai_clean")
DEFAULT_TIER = "light"
DEFAULT_STRENGTH = 50
TARGET_LUFS = -20.0
MAX_LIFT_DB = 12.0
PEAK = 0.8
MAX_SPECTRAL_DISTANCE_DB = 8.0
AI_CLEAN_UNAVAILABLE = (
    "AI clean add-on is unavailable in this version; Light guide enhancement was used."
)


def settings(draft: dict) -> dict:
    """Validate draft enhancement settings, defaulting to Light at strength 50."""
    tier = draft.get("guide_enhancement", DEFAULT_TIER)
    if tier not in TIERS:
        raise ValueError("Choose Off, Light or AI clean guide enhancement")
    strength = draft.get("guide_enhancement_strength", DEFAULT_STRENGTH)
    if (
        isinstance(strength, bool)
        or not isinstance(strength, (int, float))
        or not math.isfinite(strength)
        or not 0 <= strength <= 100
    ):
        raise ValueError("Guide enhancement strength must be between 0 and 100")
    return {"tier": tier, "strength": strength}


def ai_clean_available() -> bool:
    # No verified add-on is distributable for the embedded Python 3.12 runtime yet.
    return False


def loudness(audio: np.ndarray, sr: int) -> float:
    """Approximate ITU-R BS.1770 integrated loudness (K-weighting, gated 400 ms blocks)."""
    shelf = pb.Pedalboard([pb.HighShelfFilter(1500, 4.0, 0.71), pb.HighpassFilter(38)])
    weighted = shelf(np.ascontiguousarray(audio.T, np.float32), sr).T.astype(np.float64)
    block, hop = int(0.4 * sr), int(0.1 * sr)
    if len(weighted) < block:
        return -math.inf
    power = np.array(
        [
            np.mean(weighted[i : i + block] ** 2, axis=0).sum()
            for i in range(0, len(weighted) - block + 1, hop)
        ]
    )
    with np.errstate(divide="ignore"):
        levels = -0.691 + 10 * np.log10(power)
    gated = power[levels > -70]
    if not len(gated):
        return -math.inf
    relative = -0.691 + 10 * np.log10(gated.mean()) - 10
    with np.errstate(divide="ignore"):
        final = gated[-0.691 + 10 * np.log10(gated) > relative]
    return float(-0.691 + 10 * np.log10(final.mean())) if len(final) else -math.inf


def _envelope(audio: np.ndarray, width: int) -> np.ndarray:
    power = signal.fftconvolve(
        (audio.astype(np.float64) ** 2).mean(1), np.ones(width) / width, "same"
    )
    return np.sqrt(np.maximum(power, 0))


def repair_discontinuities(audio: np.ndarray, sr: int, limit: int = 256) -> tuple[np.ndarray, int]:
    """Bridge isolated sample-level jumps that stand far above the local signal level."""
    out = np.array(audio, np.float32, copy=True)
    if len(out) < 8:
        return out, 0
    curvature = np.abs(np.diff(out, 2, axis=0)).max(1)
    local = signal.fftconvolve(curvature, np.ones(256) / 256, "same")
    floor = np.percentile(curvature, 99) + 1e-6
    spikes = np.where((curvature > 12 * np.maximum(local, 1e-6)) & (curvature > 4 * floor))[0] + 1
    half = max(2, int(0.0005 * sr))
    repaired, last = 0, -half * 2
    for index in spikes:
        if repaired >= limit:
            break
        if index - last < half * 2:
            continue
        start, end = max(0, index - half), min(len(out) - 1, index + half)
        ramp = np.linspace(0, 1, end - start + 1)[:, None]
        out[start : end + 1] = out[start] * (1 - ramp) + out[end] * ramp
        repaired, last = repaired + 1, index
    return out, repaired


def spectral_distance(reference: np.ndarray, candidate: np.ndarray, sr: int) -> float:
    """Level-matched log-spectral distance (dB) over the reference's active frames."""
    # Combine channel power, not waveforms: opposite-phase stereo is still audible.
    _, _, x = signal.stft(reference.T, sr, nperseg=2048, axis=-1)
    _, _, y = signal.stft(candidate.T, sr, nperseg=2048, axis=-1)
    x = 10 * np.log10((np.abs(x) ** 2).mean(0) + 1e-14)
    y = 10 * np.log10((np.abs(y) ** 2).mean(0) + 1e-14)
    active = x.max(0) > x.max() - 50
    if not active.any():
        return 0.0
    difference = (x - y)[:, active]
    difference -= np.median(difference)
    return float(np.sqrt((difference**2).mean(0)).mean())


def _peak_limit(audio: np.ndarray, sr: int) -> np.ndarray:
    """Smooth gain-reduction limiter to PEAK without make-up gain."""
    needed = np.minimum(1.0, PEAK / np.maximum(np.abs(audio).max(1), 1e-9))
    window = max(3, int(0.005 * sr))
    held = ndimage.minimum_filter1d(needed, 2 * window + 1)
    gain = np.minimum(signal.fftconvolve(held, np.ones(window) / window, "same"), needed)
    return (audio * gain[:, None]).astype(np.float32)


def light(audio: np.ndarray, sr: int, strength: float) -> tuple[np.ndarray, dict]:
    amount = strength / 100
    out, clicks = repair_discontinuities(audio, sr)
    if amount > 0:
        chain = pb.Pedalboard(
            [
                pb.HighpassFilter(70),
                pb.PeakFilter(3500, -(1 + 3 * amount), 1.4),
                pb.Compressor(-20, 1.5 + 2 * amount, 10, 120),
            ]
        )
        out = chain(np.ascontiguousarray(out.T), sr).T.astype(np.float32)
        level = 20 * np.log10(_envelope(out, int(0.05 * sr)) + 1e-9)
        active = np.percentile(level, 95)
        # Gate relative to the guide's own level so quiet takes are not erased.
        gain = np.clip((level - (active - 32)) / 12, 0, 1)
        gain = 1 - min(0.9, 0.4 + amount) * (1 - gain)
        smooth = int(0.02 * sr)
        gain = np.clip(signal.fftconvolve(gain, np.ones(smooth) / smooth, "same"), 0, 1)
        out = out * gain[:, None].astype(np.float32)
        current = loudness(out, sr)
        lift = 0.0
        if math.isfinite(current):
            # Strength 50+ reaches the target; lower strengths lift proportionally less.
            lift = float(np.clip(TARGET_LUFS - current, 0, MAX_LIFT_DB)) * min(1.0, 2 * amount)
        out = out * np.float32(10 ** (lift / 20))
        out = _peak_limit(out, sr)
    else:
        lift = 0.0
    peak = float(np.max(np.abs(out), initial=0))
    if peak > PEAK:
        out *= np.float32(PEAK / peak)
    return out, {"discontinuities_repaired": clicks, "lift_db": round(lift, 2)}


def enhance_guide(
    layer: np.ndarray, sr: int, tier: str, strength: float
) -> tuple[np.ndarray, dict]:
    """Return (guide for the model, provenance). Never mutates ``layer``."""
    info: dict = {
        "version": VERSION,
        "requested": tier,
        "effective": tier,
        "strength": strength,
        "applied": False,
        "fallback_reason": None,
        "metrics": {},
    }
    if tier == "ai_clean" and not ai_clean_available():
        info["effective"] = "light"
        info["fallback_reason"] = AI_CLEAN_UNAVAILABLE
    if info["effective"] == "off":
        return layer, info
    raw = np.asarray(layer, np.float32)
    raw_peak = float(np.max(np.abs(raw), initial=0))
    if raw_peak < 1e-5:
        info["fallback_reason"] = "Guide is silent; enhancement skipped."
        return layer, info
    try:
        enhanced, metrics = light(raw, sr, strength)
        reason = None
        if enhanced.shape != raw.shape:
            reason = "Enhanced guide changed shape; original guide used."
        elif not np.isfinite(enhanced).all():
            reason = "Enhanced guide contained invalid samples; original guide used."
        elif float(np.max(np.abs(enhanced), initial=0)) < 1e-5:
            reason = "Enhanced guide was silent; original guide used."
        else:
            distance = spectral_distance(raw, enhanced, sr)
            if not math.isfinite(distance):
                reason = "Guide safety measurement was invalid; original guide used."
            else:
                metrics["spectral_distance_db"] = round(distance, 2)
                if distance > MAX_SPECTRAL_DISTANCE_DB:
                    reason = (
                        "Enhanced guide changed too much from the original; original guide used."
                    )
        before, after = loudness(raw, sr), loudness(enhanced, sr) if reason is None else None
        metrics["lufs_before"] = round(before, 2) if math.isfinite(before) else None
        if after is not None:
            metrics["lufs_after"] = round(after, 2) if math.isfinite(after) else None
        info["metrics"] = metrics
        if reason:
            info["fallback_reason"] = (
                info["fallback_reason"] + " " + reason if info["fallback_reason"] else reason
            )
            return layer, info
    except Exception as exc:  # DSP failures must never block generation.
        reason = f"Guide enhancement failed ({exc}); original guide used."
        info["fallback_reason"] = (
            info["fallback_reason"] + " " + reason if info["fallback_reason"] else reason
        )
        return layer, info
    info["applied"] = True
    return enhanced.astype(np.float32), info
