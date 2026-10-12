"""Content-aware, seeded sample selection and rhythmic arrangement heuristics."""

from __future__ import annotations

import math

import numpy as np


def select_regions(audio, sr, settings, analysis):
    """Choose distinct audible cuts; an explicit sample count is an upper bound."""
    hop = max(1, round(sr * 0.02))
    mono = audio.mean(axis=1)
    padded = np.pad(mono, (0, (-len(mono)) % hop))
    energy = np.sqrt(np.mean(padded.reshape(-1, hop) ** 2, axis=1))
    threshold = max(1e-5, float(energy.max()) * 0.08)
    active = np.flatnonzero(energy >= threshold)
    if not len(active):
        raise ValueError("Input clip has no audible samples")
    width = min(len(audio), round(float(settings["sample_seconds"]) * sr))
    runs = np.split(active, np.flatnonzero(np.diff(active) > 1) + 1)
    width = min(width, max(hop, max(len(run) for run in runs) * hop))
    active_seconds = len(active) * hop / sr
    cap = int(settings["samples"])
    budget = min(cap, max(1, math.ceil(math.sqrt(active_seconds) * 2)))
    # Phrase beginnings, energy onsets, and active interior points supply candidates.
    starts = {max(0, min(len(audio) - width, int(frame * hop))) for frame in active[::10]}
    for begin, _end in analysis.get("phrases", []):
        starts.add(max(0, min(len(audio) - width, round(begin * sr))))
    candidates = []
    for start in sorted(starts):
        part = mono[start : start + width]
        rms = float(np.sqrt(np.mean(part**2)))
        audible = float(np.mean(np.abs(part) >= threshold))
        if audible < 0.4 or rms < threshold:
            continue
        spectral_part = part[:4096]
        spectrum = np.abs(np.fft.rfft(spectral_part * np.hanning(len(spectral_part))))
        frequencies = np.fft.rfftfreq(len(spectral_part), 1 / sr)
        centroid = float(np.dot(spectrum, frequencies) / max(1e-12, spectrum.sum()))
        onset = max(
            0, float(energy[min(len(energy) - 1, start // hop)] - energy[max(0, start // hop - 1)])
        )
        candidates.append(
            {
                "start": start,
                "end": start + width,
                "rms": rms,
                "centroid_hz": centroid,
                "audible_fraction": audible,
                "onset": onset,
            }
        )
    if not candidates:
        # Very short or quiet audible clips still get one bounded contribution.
        start = max(0, min(len(audio) - width, int(active[0] * hop)))
        candidates = [
            {
                "start": start,
                "end": start + width,
                "rms": float(np.sqrt(np.mean(mono[start : start + width] ** 2))),
                "centroid_hz": 0.0,
                "audible_fraction": 1.0,
                "onset": 0.0,
            }
        ]
    selected = []
    peak = max(c["rms"] for c in candidates)
    for _ in range(budget):
        available = [
            c
            for c in candidates
            if all(abs(c["start"] - s["start"]) >= width * 0.5 for s in selected)
        ]
        if not available:
            break

        def score(candidate):
            if not selected:
                return candidate["rms"] / peak + candidate["onset"] / max(peak, 1e-12)
            diversity = min(
                abs(math.log2((candidate["centroid_hz"] + 80) / (s["centroid_hz"] + 80)))
                for s in selected
            )
            coverage = min(
                abs(candidate["start"] - s["start"]) / max(1, len(audio)) for s in selected
            )
            return candidate["rms"] / peak * 0.3 + min(2, diversity) + coverage

        selected.append(max(available, key=score))
    return sorted(selected, key=lambda c: c["start"]), {
        "method": "audible-phrase-energy-spectral-diversity-v1",
        "active_seconds": active_seconds,
        "requested_cap": cap,
        "effective_budget": len(selected),
        "candidate_count": len(candidates),
    }


def sample_transform(settings, region, index, rng):
    # Seeded individual variations around the chosen per-clip adjustments.
    pitch = float(settings["pitch"]) + (0, 2, -2, 0, 5)[index % 5]
    stretch = float(settings["stretch"]) * (1, 0.9, 1.1)[index % 3]
    balancing = min(3, max(-3, 20 * math.log10(0.12 / max(region["rms"], 1e-6))))
    return {
        "pitch": min(12, max(-12, pitch)),
        "stretch": min(2, max(0.5, stretch)),
        "gain": min(12, max(-30, float(settings["gain"]) + balancing + rng.uniform(-0.5, 0.5))),
        "normalize": False,
        "trim": False,
    }


def positions(sample_count, source_index, sources_total, length, sr, bpm):
    """Repeat a source motif on a shared grid across opening/body/closing sections."""
    beat = max(1, round(sr * 60 / bpm))
    events = max(sample_count, math.ceil(length / (4 * beat)))
    for event in range(events):
        ideal = event * length / events + (source_index % 2) * beat / 2
        position = min(length - 1, round(ideal / (beat / 2)) * round(beat / 2))
        section = position / max(1, length)
        gain = (0.75 if section < 0.16 else 0.9 if section > 0.84 else 1.0) / math.sqrt(
            sources_total
        )
        yield event % sample_count, position, gain
