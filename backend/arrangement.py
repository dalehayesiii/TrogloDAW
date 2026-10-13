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


PLANNER_VERSION = "phrase-motifs-v3"
VARIANTS_PER_REGION = 3
SOURCE_POLICY_VERSION = "source-roles-v1"


def route_sources(sources):
    """Classify trusted source records independently; never infer from filenames."""
    priors = sum(source["source_type"] == "prior-song" for source in sources)
    recordings = len(sources) - priors
    names = {
        (1, 0): "one-prior",
        (2, 0): "multiple-priors",
        (0, 1): "one-recording",
        (0, 2): "multiple-recordings",
        (1, 1): "one-prior+one-recording",
        (1, 2): "one-prior+multiple-recordings",
        (2, 1): "multiple-priors+one-recording",
        (2, 2): "multiple-priors+multiple-recordings",
    }
    collection = names.get((min(2, priors), min(2, recordings)), "text-only")
    result = []
    for source in sources:
        prior = source["source_type"] == "prior-song"
        role = (
            "mix-accent"
            if prior and recordings
            else "mix-hook"
            if prior
            else "recording-response"
            if recordings > 1
            else "recording-phrase"
        )
        cap = (
            (2 if recordings else 4 if priors > 1 else 6) if prior else (4 if recordings > 1 else 8)
        )
        result.append(
            {
                **source,
                "routing": {
                    "version": SOURCE_POLICY_VERSION,
                    "collection": collection,
                    "prior_count": priors,
                    "recording_count": recordings,
                    "classification": "finished-mix" if prior else "recording",
                    "role": role,
                    "sample_cap": cap,
                    "duration_weight": 0.55 if prior and recordings else 1.0,
                    "density_scale": 0.65 if priors else 0.9 if recordings > 1 else 1.0,
                },
            }
        )
    return result


def rhythmic_anchors(mono, sr):
    """Measured spectral-flux peaks at bounded analysis rate, not a semantic label."""
    from scipy import signal

    step = max(1, sr // 8000)
    audio = signal.resample_poly(mono, 1, step) if step > 1 else mono
    n, hop = 512, 160
    if len(audio) < n + hop:
        return []
    level = float(np.sqrt(np.mean(audio**2)))
    if level < 1e-8:
        return []
    frames = np.lib.stride_tricks.sliding_window_view(audio / level, n)[::hop]
    magnitude = np.log1p(np.abs(np.fft.rfft(frames * np.hanning(n), axis=1)))
    flux = np.maximum(np.diff(magnitude, axis=0), 0).sum(axis=1)
    peaks, _ = signal.find_peaks(
        flux,
        height=max(1e-8, float(np.percentile(flux, 70))),
        distance=max(1, round(0.12 * sr / step / hop)),
    )
    # Bound work while keeping peaks spread across the complete source.
    if len(peaks) > 96:
        groups = np.array_split(peaks, 96)
        peaks = np.array([group[np.argmax(flux[group])] for group in groups])
    return [max(0, round((int(index) + 1) * hop * step)) for index in peaks]


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


def select_regions(audio, sr, settings, analysis, rng=None, guide_seconds=None, policy=None):
    """Select mixed source phrases/accents; the budget counts distinct cut families."""
    import random

    rng = rng or random.Random(0)
    mono, energy, active, threshold, hop, detected, reference = _activity(audio, sr)
    preferred = float(settings["sample_seconds"])
    cap = int(settings["samples"])
    policy = policy or {}
    prior = policy.get("classification") == "finished-mix"
    confident = analysis.get("tempo_confidence", 0) > 2.0 and analysis.get("tempo_raw")
    beat_seconds = 60 / min(180, max(60, float(analysis["tempo_raw"]))) if confident else None
    if prior:
        preferred = min(preferred, max(0.5, 2 * beat_seconds) if beat_seconds else 1.25)
    cap = min(cap, policy.get("sample_cap", cap))
    active_seconds = float(active.sum() * hop / sr)
    budget = min(cap, max(1, math.ceil(math.sqrt(active_seconds) * 2)))
    if guide_seconds:
        budget = min(budget, max(1, int(guide_seconds / max(0.4, preferred * 0.8))))
    # Preset length remains a short-cut policy; other inputs can retain phrases.
    preset = bool(settings.get("version")) or prior
    phrase_limit = preferred if preset else preferred * 2
    phrases = detected
    candidates: list[dict] = []
    seen = set()

    def add(begin, end, kind, anchored=False):
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
                "onset_anchored": anchored,
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
    anchors = rhythmic_anchors(mono, sr) if prior else []
    for anchor in anchors:
        begin = max(0, anchor - round(0.025 * sr))
        add(begin, begin + preferred * sr, "phrase", True)
        add(begin, begin + min(preferred * 0.45, beat_seconds or 0.5) * sr, "accent", True)
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
                + (0.7 if prior and candidate["onset_anchored"] else 0)
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
        **(
            {
                "routing": policy,
                "requested_sample_seconds": float(settings["sample_seconds"]),
                "effective_sample_seconds": preferred,
                "requested_cap": int(settings["samples"]),
                "policy_cap": cap,
                "measured_anchors": len(anchors),
                "tempo_policy": "confident" if confident else "fallback",
            }
            if policy
            else {}
        ),
    }


def sample_transform(settings, region, index, rng, variant=0, bpm=90, analysis=None, policy=None):
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
    prior = (policy or {}).get("classification") == "finished-mix"
    if prior:
        interval = (0, 12, -12)[variant]
        if not -12 <= float(settings["pitch"]) + interval <= 12:
            interval = 0
    pitch = min(12, max(-12, float(settings["pitch"]) + interval))
    speed = (1.0, rng.uniform(0.9, 1.1), rng.uniform(1.12, 1.3))[variant]
    if prior:
        speed = (1.0, 1.0, rng.uniform(0.94, 1.06))[variant]
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


def plan_events(samples, length, sr, bpm, rng, policy=None, backing_context=None):
    """Plan source-derived gestures with sections, pauses and capped motif returns."""
    if not samples:
        return [], {"method": PLANNER_VERSION, "sections": [], "rest_seconds": length / sr}
    beat = sr * 60 / bpm
    density_scale = (policy or {}).get("density_scale", 1.0)
    grid = max(1, round(beat / 2))
    origin = round((backing_context or {}).get("beat_phase_seconds", 0) * sr)
    energy = (backing_context or {}).get("energy", [])
    energy_hop = (backing_context or {}).get("energy_hop", 1)
    energy_prefix = np.r_[0.0, np.cumsum(energy)]
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
                }[name]
                * density_scale,
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
            if backing_context:
                positions = np.arange(
                    math.ceil((begin - origin) / grid) * grid + origin,
                    end - width + 1,
                    grid,
                    dtype=int,
                )
                if not mandatory:
                    positions = positions[
                        (positions >= section["start"]) & (positions < section["end"])
                    ]
                if not len(positions):
                    continue
                if len(energy):
                    first = np.minimum(len(energy) - 1, positions // energy_hop)
                    last = np.minimum(
                        len(energy), np.maximum(first + 1, (positions + width) // energy_hop)
                    )
                    density = (energy_prefix[last] - energy_prefix[first]) / (last - first)
                    costs = np.abs(positions - preferred) / max(1, length) + density * 0.6
                else:
                    costs = np.abs(positions - preferred) / max(1, length)
                snapped = int(positions[int(np.argmin(costs))])
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
            if backing_context and len(energy):
                first = min(len(energy) - 1, snapped // energy_hop)
                last = min(len(energy), max(first + 1, (snapped + width) // energy_hop))
                density = (energy_prefix[last] - energy_prefix[first]) / (last - first)
                cost = abs(snapped - preferred) / max(1, length) + density * 0.6
            else:
                cost = abs(snapped - preferred)
            options.append((cost, snapped))
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
            if sample.get("source_type") == "prior-song":
                cap = min(cap, 2 if (policy or {}).get("recording_count") else 3)
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
        **(
            {"prior_family_repeat_cap": 2 if policy.get("recording_count") else 3}
            if policy and policy.get("prior_count")
            else {}
        ),
        "exact_variant_repeat_cap": 2,
        "rest_seconds": (length - occupied) / sr,
        "occupied_fraction": occupied / length,
        **(
            {
                "backing_context": {
                    key: value for key, value in backing_context.items() if key != "energy"
                }
            }
            if backing_context
            else {}
        ),
    }


def align_recording(settings, analysis, context):
    """Only transpose confidently sung recordings between matching key modes."""
    result = settings.copy()
    info = {"applied": False, "semitones": 0, "method": "same-mode-key-root"}
    if not (analysis.get("sung") and analysis.get("key_reliable") and context.get("key_reliable")):
        info["reason"] = "Uncertain source or backing key"
        return result, info
    source = str(analysis.get("key_detected", "")).split()
    target = str(context.get("key_detected", "")).split()
    notes = {
        name: index
        for index, name in enumerate(
            ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
        )
    }
    notes.update(Db=1, Eb=3, Gb=6, Ab=8, Bb=10)
    if (
        len(source) != 2
        or len(target) != 2
        or source[1] != target[1]
        or source[0] not in notes
        or target[0] not in notes
    ):
        info["reason"] = "Ambiguous or differing key modes"
        return result, info
    shift = (notes[target[0]] - notes[source[0]] + 6) % 12 - 6
    if not -12 <= float(settings["pitch"]) + shift <= 12:
        info["reason"] = "Alignment would exceed the requested pitch range"
        return result, info
    result["pitch"] = float(settings["pitch"]) + shift
    info.update(
        applied=True, semitones=shift, source_key=" ".join(source), target_key=" ".join(target)
    )
    return result, info


def backing_context(audio, sr, analyzer):
    """Bounded window analysis plus complete energy timeline; no semantic-gap claim."""
    safe = phase_safe_audio(audio)[0]
    seconds = len(safe) / sr
    width = min(len(safe), round(12 * sr))
    starts = sorted(set(int(position) for position in np.linspace(0, max(0, len(safe) - width), 3)))
    results = []
    for start in starts:
        part = safe[start : start + width]
        if np.max(np.abs(part), initial=0) > 1e-7:
            results.append((start, analyzer(part)))
    confident = [
        (start, result)
        for start, result in results
        if result.get("tempo_confidence", 0) > 2.0 and result.get("tempo_raw")
    ]
    bpm = 90.0
    phase = 0.0
    if confident:
        start, strongest = max(confident, key=lambda pair: pair[1]["tempo_confidence"])
        bpm = min(180, max(60, float(strongest["tempo_raw"])))
        anchors = rhythmic_anchors(safe[start : start + width].mean(axis=1), sr)
        if anchors:
            beat = sr * 60 / bpm
            counts, edges = np.histogram(
                [(start + anchor) % beat for anchor in anchors], bins=16, range=(0, beat)
            )
            at = int(np.argmax(counts))
            phase = (edges[at] + edges[at + 1]) / 2 / sr
    hop = max(1, round(sr * 0.25))
    mono = safe.mean(axis=1)
    padded = np.pad(mono, (0, (-len(mono)) % hop))
    energy = np.sqrt(np.mean(padded.reshape(-1, hop) ** 2, axis=1))
    reference = float(np.percentile(energy, 95))
    energy = np.minimum(1.0, energy / reference) if reference > 1e-8 else np.zeros_like(energy)
    keys = [result["key_detected"] for _, result in results if result.get("key_reliable")]
    reliable_key = bool(results) and len(keys) == len(results) and len(set(keys)) == 1
    return {
        "version": "backing-context-v1",
        "duration": seconds,
        "bpm": bpm,
        "tempo_source": "measured-window" if confident else "fallback",
        "beat_phase_seconds": phase,
        "energy_hop": hop,
        "energy": energy.tolist(),
        "key_reliable": reliable_key,
        "key_detected": keys[0] if reliable_key else None,
        "analysis_windows": [
            {"start_seconds": start / sr, "duration_seconds": width / sr} for start, _ in results
        ],
        "placement_policy": "phase-grid-and-energy-gaps",
    }
