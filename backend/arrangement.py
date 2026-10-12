"""Content-aware, seeded sample selection and rhythmic arrangement heuristics."""

from __future__ import annotations

import math

import numpy as np


def phase_safe_audio(audio):
    """Avoid losing audible stereo material through an out-of-phase mono fold."""
    mono = audio.mean(axis=1)
    channels = np.sqrt(np.mean(audio**2, axis=0))
    if float(np.sqrt(np.mean(mono**2))) < float(channels.max()) * 0.25:
        dominant = audio[:, int(np.argmax(channels))]
        return np.repeat(dominant[:, None], 2, axis=1), "dominant-channel-stereo"
    return audio, "preserved-stereo"


PLANNER_VERSION = "phrase-motifs-v2"
VARIANTS_PER_REGION = 3


def _activity(audio, sr):
    hop = max(1, round(sr * 0.02))
    mono = phase_safe_audio(audio)[0].mean(axis=1)
    mono = mono - np.median(mono)
    padded = np.pad(mono, (0, (-len(mono)) % hop))
    energy = np.sqrt(np.mean(padded.reshape(-1, hop) ** 2, axis=1))
    reference = float(np.percentile(energy, 95))
    if reference < 1e-8 and np.max(energy, initial=0) >= 1e-8:
        reference = float(np.max(energy))
    if reference < 1e-8:
        raise ValueError("Input clip has no audible changing signal")
    floor = float(np.percentile(energy, 10))
    threshold = max(1e-8, min(reference * 0.3, max(reference * 0.08, floor * 2)))
    active = energy >= threshold
    # Bridge articulation gaps rather than reducing every cut to one energy run.
    indices = np.flatnonzero(active)
    if not len(indices):
        raise ValueError("Input clip has no audible samples")
    runs = np.split(indices, np.flatnonzero(np.diff(indices) > 1) + 1)
    phrases = []
    for run in runs:
        begin, end = int(run[0] * hop), min(len(audio), int((run[-1] + 1) * hop))
        if phrases and begin - phrases[-1][1] <= sr * 0.22:
            phrases[-1][1] = end
        else:
            phrases.append([begin, end])
    return mono, energy, active, threshold, hop, phrases, reference


def select_regions(audio, sr, settings, analysis, rng=None, guide_seconds=None):
    """Select mixed source phrases/accents; the budget counts distinct cut families."""
    import random

    rng = rng or random.Random(0)
    mono, energy, active, threshold, hop, detected, reference = _activity(audio, sr)
    preferred = float(settings["sample_seconds"])
    cap = int(settings["samples"])
    active_seconds = float(active.sum() * hop / sr)
    budget = min(cap, max(1, math.ceil(math.sqrt(active_seconds) * 2)))
    if guide_seconds:
        budget = min(budget, max(1, int(guide_seconds / max(0.4, preferred * 0.8))))
    # Preset length remains a short-cut policy; other inputs can retain phrases.
    preset = bool(settings.get("version"))
    phrase_limit = preferred if preset else preferred * 2
    phrases = detected
    candidates: list[dict] = []
    seen = set()

    def add(begin, end, kind):
        begin, end = max(0, int(begin)), min(len(audio), int(end))
        if end - begin < min(len(audio), round(0.16 * sr)) or (begin, end) in seen:
            return
        part = mono[begin:end]
        first, last = begin // hop, max(begin // hop + 1, math.ceil(end / hop))
        audible = float(np.mean(active[first:last]))
        rms = float(np.sqrt(np.mean(part**2)))
        if audible < 0.2 or rms < threshold * 0.5:
            return
        # Representative energy, not a leading silence or isolated loud pop.
        frames = energy[first:last]
        representative = first + int(np.argmin(np.abs(frames - np.percentile(frames, 70))))
        fft_start = max(begin, min(end - min(4096, len(part)), representative * hop))
        spectral = mono[fft_start : min(end, fft_start + 4096)]
        spectrum = np.abs(np.fft.rfft(spectral * np.hanning(len(spectral))))
        frequencies = np.fft.rfftfreq(len(spectral), 1 / sr)
        centroid = float(np.dot(spectrum, frequencies) / max(1e-12, spectrum.sum()))
        candidates.append(
            {
                "start": begin,
                "end": end,
                "rms": rms,
                "centroid_hz": centroid,
                "audible_fraction": audible,
                "kind": kind,
            }
        )
        seen.add((begin, end))

    for begin, end in phrases:
        span = end - begin
        if span / sr <= phrase_limit:
            add(begin, end, "phrase" if span / sr >= 0.9 else "accent")
        else:
            for start in np.linspace(
                begin,
                max(begin, end - preferred * sr),
                min(8, math.ceil(span / (preferred * sr))),
                dtype=int,
            ):
                add(start, start + min(phrase_limit * sr, end - start), "phrase")
        # Actual onsets and phrase subdivisions offer smaller, different gestures.
        anchors = sorted(set([begin, begin + span // 3, begin + span * 2 // 3]))
        for index, start in enumerate(anchors):
            fraction = (0.4, 0.65, 1.0)[index]
            width = min(end - start, max(0.24, preferred * fraction) * sr)
            add(start, start + width, "accent" if fraction < 0.7 else "motif")
    # Additional active-region motifs cover material missed by a coarse phrase pass.
    for start in np.flatnonzero(active)[:: max(1, round(0.35 * sr / hop))][:192]:
        begin = int(start * hop)
        add(begin, begin + preferred * sr, "motif")
    if not candidates:
        for begin, end in detected:
            add(begin, min(end, begin + preferred * sr), "accent")
    if not candidates:
        raise ValueError("Input clip has no usable audible region")
    selected: list[dict] = []
    duration = len(audio) / sr
    whole_eligible = (
        not preset
        and 0.5 <= duration <= 8
        and (guide_seconds is None or guide_seconds >= duration * 3)
        and budget > 1
    )
    if whole_eligible and rng.random() < 0.45:
        add(0, len(audio), "whole-clip")
        whole = next((c for c in candidates if c["start"] == 0 and c["end"] == len(audio)), None)
        if whole:
            whole = {**whole, "kind": "whole-clip"}
            selected.append(whole)

    def redundant(candidate):
        for old in selected:
            intersection = max(
                0, min(old["end"], candidate["end"]) - max(old["start"], candidate["start"])
            )
            union = max(old["end"], candidate["end"]) - min(old["start"], candidate["start"])
            if intersection / max(1, union) > 0.65:
                return True
        return False

    while len(selected) < budget:
        available = [c for c in candidates if not redundant(c)]
        if not available:
            break
        used_kinds = {c["kind"] for c in selected}

        def score(candidate):
            priority = {"phrase": 1.3, "motif": 0.6, "accent": 0.8, "whole-clip": 0}[
                candidate["kind"]
            ]
            new_kind = 0.8 if candidate["kind"] not in used_kinds else 0
            spectral = min(
                (
                    abs(math.log2((candidate["centroid_hz"] + 80) / (s["centroid_hz"] + 80)))
                    for s in selected
                ),
                default=0,
            )
            coverage = min(
                (abs(candidate["start"] - s["start"]) / max(1, len(audio)) for s in selected),
                default=0,
            )
            return (
                priority
                + new_kind
                + candidate["audible_fraction"] * 0.3
                + min(1.5, spectral)
                + coverage
            )

        # Seed affects close alternatives, while level scaling cannot affect ordering.
        priorities = [(score(c) + rng.uniform(0, 0.08), c) for c in available]
        selected.append(max(priorities, key=lambda pair: pair[0])[1])
    if guide_seconds:
        available = guide_seconds * 0.7
        fitting = []
        for candidate in selected:
            width = (candidate["end"] - candidate["start"]) / sr / float(settings["stretch"])
            if width + 0.5 <= available:
                fitting.append(candidate)
                available -= width + 0.5
        if not fitting:
            candidates.sort(key=lambda c: c["end"] - c["start"])
            for candidate in candidates:
                width = (candidate["end"] - candidate["start"]) / sr / float(settings["stretch"])
                if width + 0.3 <= guide_seconds:
                    fitting = [candidate]
                    break
        if not fitting:
            raise ValueError("Input material needs a longer song duration or fewer selected clips")
        selected = fitting
    return sorted(selected, key=lambda c: (c["start"], c["end"])), {
        "method": PLANNER_VERSION,
        "active_seconds": active_seconds,
        "requested_cap": cap,
        "effective_budget": len(selected),
        "candidate_count": len(candidates),
        "threshold_relative": threshold / reference,
        "whole_clip_included": any(c["kind"] == "whole-clip" for c in selected),
    }


def sample_transform(settings, region, index, rng, variant=0, bpm=90, analysis=None):
    """Recognizable phrase, pitched response and shorter filtered fill variants."""
    analysis = analysis or {}
    phrase = region["kind"] in {"phrase", "whole-clip"}
    intervals = (
        (0, 3, 5, 7, 10)
        if analysis.get("key_reliable") and "minor" in analysis.get("key_detected", "")
        else (0, 2, 4, 7, 9)
    )
    interval = 0 if phrase and variant == 0 else rng.choice(intervals[1:])
    if variant == 2:
        interval -= 12
    pitch = min(12, max(-12, float(settings["pitch"]) + interval))
    speed = (1.0, rng.uniform(0.9, 1.1), rng.uniform(1.12, 1.3))[variant]
    balancing = min(6, max(-6, 20 * math.log10(0.08 / max(region["rms"], 1e-6))))
    return {
        "pitch": pitch,
        "stretch": min(2, max(0.5, float(settings["stretch"]) * speed)),
        "gain": min(12, max(-30, float(settings["gain"]) + balancing)),
        "low_cut": 80 if phrase else 120,
        "high_cut": (12000, 9000, 6000)[variant],
        "delay": (0, 0.055, 0.08)[variant],
        "delay_time": min(0.4, 30 / bpm),
        "delay_feedback": 0.18,
        "normalize": False,
        "trim": False,
    }


def _free_gaps(events, length, rest):
    cursor = 0
    result = []
    for event in sorted(events, key=lambda e: e["offset_samples"]):
        end = max(0, event["offset_samples"] - rest)
        if end > cursor:
            result.append((cursor, end))
        cursor = max(cursor, event["offset_samples"] + event["length_samples"] + rest)
    if cursor < length:
        result.append((cursor, length))
    return result


def plan_events(samples, length, sr, bpm, rng):
    """Plan source-derived gestures with sections, pauses and capped motif returns."""
    if not samples:
        return [], {"method": PLANNER_VERSION, "sections": [], "rest_seconds": length / sr}
    beat = sr * 60 / bpm
    grid = max(1, round(beat / 2))
    rest = max(round(0.16 * sr), round(beat * 0.5))
    section_count = max(3, min(16, math.ceil(length / (32 * beat))))
    boundaries = [round(i * length / section_count) for i in range(section_count + 1)]
    sections: list[dict] = []
    for index in range(section_count):
        name = (
            "intro"
            if index == 0
            else "outro"
            if index == section_count - 1
            else "bridge"
            if section_count >= 5 and index == section_count // 2
            else "refrain"
            if index % 2 == 0
            else "verse"
        )
        sections.append(
            {
                "index": index,
                "name": name,
                "start": boundaries[index],
                "end": boundaries[index + 1],
                "target_density": {
                    "intro": 0.18,
                    "verse": 0.28,
                    "refrain": 0.42,
                    "bridge": 0.14,
                    "outro": 0.18,
                }[name],
            }
        )
    families = {}
    for sample in samples:
        families.setdefault(sample["family_id"], []).append(sample)
    keys = list(families)
    rng.shuffle(keys)
    # Largest gestures first so complete clips cannot be crowded out by fills.
    keys.sort(key=lambda key: -families[key][0]["length_samples"])
    events: list[dict] = []
    family_uses = {key: 0 for key in keys}
    sample_uses = {sample["id"]: 0 for sample in samples}

    def add(sample, preferred, section, mandatory=False):
        width = sample["length_samples"]
        options = []
        for begin, end in _free_gaps(events, length, rest):
            if end - begin < width:
                continue
            position = max(begin, min(end - width, preferred))
            snapped = max(begin, min(end - width, round(position / grid) * grid))
            if not mandatory and not section["start"] <= snapped < section["end"]:
                continue
            # A return needs musical distance from every earlier member of its family.
            if not mandatory:
                family_gap = max(8 * beat, width * 2)
                if any(
                    e["family_id"] == sample["family_id"]
                    and abs(snapped - e["offset_samples"]) < family_gap
                    for e in events
                ):
                    continue
                ordered = sorted(
                    [*events, {"offset_samples": snapped, "family_id": sample["family_id"]}],
                    key=lambda e: e["offset_samples"],
                )
                at = next(i for i, e in enumerate(ordered) if e["offset_samples"] == snapped)
                if len(families) > 1 and any(
                    0 <= neighbor < len(ordered)
                    and ordered[neighbor]["family_id"] == sample["family_id"]
                    for neighbor in [at - 1, at + 1]
                ):
                    continue
            options.append((abs(snapped - preferred), snapped))
        if not options:
            return False
        _, position = min(options)
        actual_section = next(s for s in sections if s["start"] <= position < s["end"])
        gain = {"intro": 0.75, "verse": 0.9, "refrain": 1, "bridge": 0.65, "outro": 0.7}[
            actual_section["name"]
        ]
        events.append(
            {
                "sample_id": sample["id"],
                "family_id": sample["family_id"],
                "offset_samples": position,
                "length_samples": width,
                "gain": gain,
                "section": actual_section["name"],
                "section_index": actual_section["index"],
                "variant": sample["variant"],
                "motif": "source-" + str(sample["source_index"]),
                "role": sample["role"],
            }
        )
        family_uses[sample["family_id"]] += 1
        sample_uses[sample["id"]] += 1
        return True

    for index, key in enumerate(keys):
        sample = families[key][0]
        preferred = round((index + 0.15 + rng.uniform(0, 0.5)) * length / max(1, len(keys)))
        if not add(
            sample,
            preferred,
            sections[min(section_count - 1, int(preferred / length * section_count))],
            True,
        ):
            raise ValueError(
                "The selected sample material cannot fit with meaningful rests. Choose a longer song duration or fewer inputs."
            )
    family_cap = min(6, max(2, math.ceil(section_count / 2)))
    for section in sections:
        candidates = samples.copy()
        rng.shuffle(candidates)
        # Bounded loops and assets: no duration-proportional modulo cycling.
        for sample in candidates:
            used = sum(
                max(
                    0,
                    min(section["end"], e["offset_samples"] + e["length_samples"])
                    - max(section["start"], e["offset_samples"]),
                )
                for e in events
            )
            if used >= (section["end"] - section["start"]) * section["target_density"]:
                break
            cap = 2 if sample["kind"] == "whole-clip" else family_cap
            if family_uses[sample["family_id"]] >= cap or sample_uses[sample["id"]] >= 2:
                continue
            if section["name"] == "bridge" and sample["variant"] == 0:
                continue
            preferred = (
                section["start"]
                + round(rng.uniform(0.05, 0.8) * (section["end"] - section["start"]) / grid) * grid
            )
            add(sample, preferred, section)
    events.sort(key=lambda event: event["offset_samples"])
    occupied = sum(event["length_samples"] for event in events)
    return events, {
        "method": PLANNER_VERSION,
        "bpm": bpm,
        "sections": sections,
        "placements": len(events),
        "families": len(families),
        "family_repeat_cap": family_cap,
        "exact_variant_repeat_cap": 2,
        "rest_seconds": (length - occupied) / sr,
        "occupied_fraction": occupied / length,
    }
