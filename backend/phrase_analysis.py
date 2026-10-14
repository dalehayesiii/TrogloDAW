"""Conservative speech/pause evidence; model inference lives in its CPU subprocess."""

from __future__ import annotations

import math

import numpy as np

ANALYSIS_VERSION = "speech-pauses-v1"
WINDOW_SAMPLES = 512
ANALYSIS_RATE = 16000


def probability_spans(probabilities, samples, sr):
    """Merge articulation gaps; never force a split by utterance duration."""
    if type(samples) is not int or samples <= 0 or type(sr) is not int or sr <= 0:
        raise ValueError("Invalid speech activity dimensions")
    values = np.asarray(probabilities, dtype=np.float32)
    resampled = (samples * ANALYSIS_RATE + sr - 1) // sr
    expected = (resampled + WINDOW_SAMPLES - 1) // WINDOW_SAMPLES
    if (
        values.ndim != 1
        or len(values) != expected
        or not np.all(np.isfinite(values))
        or np.any((values < 0) | (values > 1))
    ):
        raise ValueError("Invalid speech activity evidence")
    ranges = []
    start = quiet = None
    for index, probability in enumerate(values):
        if start is None:
            if probability >= 0.45:
                start = index
        elif probability >= 0.25:
            quiet = None
        else:
            quiet = index if quiet is None else quiet
            if (index - quiet + 1) * WINDOW_SAMPLES / ANALYSIS_RATE >= 0.32:
                ranges.append([start, quiet])
                start = quiet = None
    if start is not None:
        end = len(values)
        ranges.append([start, end])
    # Endpoint context retains quiet consonants and VAD's delayed decisions.
    margin = round(0.24 * sr)
    spans = []
    for index, (begin, end) in enumerate(ranges):
        # Context can approach the midpoint of a confirmed pause but cannot
        # bridge it again after the hysteresis pass deliberately separated it.
        left = (
            round((ranges[index - 1][1] + begin) * WINDOW_SAMPLES / ANALYSIS_RATE * sr / 2)
            if index
            else 0
        )
        right = (
            round((end + ranges[index + 1][0]) * WINDOW_SAMPLES / ANALYSIS_RATE * sr / 2)
            if index + 1 < len(ranges)
            else samples
        )
        begin = max(0, round(begin * WINDOW_SAMPLES / ANALYSIS_RATE * sr) - margin)
        end = min(samples, round(end * WINDOW_SAMPLES / ANALYSIS_RATE * sr) + margin)
        spans.append({"start": max(left, begin), "end": min(right, end)})
    peak = float(np.max(values, initial=0))
    # Abstain for sustained near-threshold vocal evidence instead of claiming music.
    uncertain = float(np.mean(values >= 0.15)) if len(values) else 0
    return {
        "version": ANALYSIS_VERSION,
        "samples": samples,
        "sample_rate": sr,
        "spans": spans,
        "peak_probability": peak,
        "uncertain_fraction": uncertain,
        "endpoint_context_seconds": 0.24,
        "pause_join_seconds": 0.32,
        "instrumental_confident": not spans and peak < 0.35 and uncertain < 0.05,
        "status": "speech"
        if spans
        else "instrumental"
        if peak < 0.35 and uncertain < 0.05
        else "uncertain",
    }


def validate_evidence(evidence, samples, sr):
    """Reject invalid cached timestamps rather than trusting them as cut positions."""
    if (
        not isinstance(evidence, dict)
        or evidence.get("version") != ANALYSIS_VERSION
        or evidence.get("samples") != samples
        or evidence.get("sample_rate") != sr
        or type(evidence.get("samples")) is not int
        or type(evidence.get("sample_rate")) is not int
        or type(evidence.get("instrumental_confident")) is not bool
        or evidence.get("status") not in {"speech", "instrumental", "uncertain"}
        or not isinstance(evidence.get("spans"), list)
    ):
        raise ValueError("Invalid cached phrase evidence")
    end = 0
    for span in evidence["spans"]:
        if (
            not isinstance(span, dict)
            or type(span.get("start")) is not int
            or type(span.get("end")) is not int
            or not end <= span["start"] < span["end"] <= samples
        ):
            raise ValueError("Invalid cached phrase boundaries")
        end = span["end"]
    if bool(evidence["spans"]) != (evidence["status"] == "speech"):
        raise ValueError("Inconsistent cached phrase evidence")
    if evidence.get("instrumental_confident") != (evidence["status"] == "instrumental"):
        raise ValueError("Inconsistent cached phrase confidence")
    for key in ("peak_probability", "uncertain_fraction"):
        value = evidence.get(key)
        if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Invalid cached phrase confidence")
    if evidence["instrumental_confident"] and (
        evidence["peak_probability"] >= 0.35 or evidence["uncertain_fraction"] >= 0.05
    ):
        raise ValueError("Invalid cached instrumental decision")
    return evidence
