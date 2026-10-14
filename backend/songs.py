"""Portable song arrangements and fixed-timeline vocal derivatives."""

from __future__ import annotations

import copy
import json
import math
import queue
import random
import re
import subprocess
import sys
import threading
import uuid
import shutil
import os
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf

import guide_enhance
from planning import validated_blueprint
import prompt_enrichment

from arrangement import (
    PLANNER_VERSION,
    VARIANTS_PER_REGION,
    align_recording,
    backing_context,
    phase_safe_audio,
    plan_events,
    route_sources,
    sample_transform,
    select_regions,
)
from models import CREATE_FLAGS, ROOT, Canceled, cache_environment, runtime_signature
from storage import atomic_json, digest, safe_file, writable_root

CLIP_DEFAULTS = {"sample_seconds": 2.0, "samples": 8, "pitch": 0.0, "stretch": 1.0, "gain": 0.0}
OPTIONS = {"gender": "", "duration": "auto", "weirdness": 50, "influence": 50, "variety": 0}


def song_item(item):
    return item.get("is_song", False) or item["type"] in {"generated", "mix"}


def sample_loudness(core, audio):
    """Measure short gestures without diluting them with padded silence."""
    if not np.isfinite(audio).all():
        raise ValueError("Cannot match loudness of audio containing non-finite samples")
    if not len(audio) or np.max(np.abs(audio)) < 1e-7:
        return -70.0
    minimum = round(0.4 * core.SR)
    if len(audio) < minimum:
        audio = np.tile(audio, (math.ceil(minimum / len(audio)), 1))[:minimum]
    return core.lufs(audio)


def generation_mode(draft, models, has_samples):
    recording = draft.get("workflow") == "recording-style"
    requested = "conditioned" if recording else draft.get("audio_mode", "conditioned")
    if requested not in {"conditioned", "postmix"}:
        raise ValueError("Choose audio-conditioned generation or post-generation sample mixing")
    adherence = 100 if recording else draft.get("audio_adherence", 75)
    if (
        isinstance(adherence, bool)
        or not isinstance(adherence, (int, float))
        or not math.isfinite(adherence)
        or not 0 <= adherence <= 100
    ):
        raise ValueError("Audio adherence must be between 0 and 100")
    supported = "cover" in models.manifest["models"][models.selected].get("conditioning", [])
    effective = requested if has_samples else "text"
    reason = None
    if has_samples and requested == "conditioned" and not supported:
        effective = "postmix"
        reason = "This model does not support audio conditioning; mixing samples after generation."
    return {
        "requested_mode": requested,
        "effective_mode": effective,
        "audio_adherence": adherence,
        "effective_audio_adherence": int(32 * adherence / 100) / 32
        if effective == "conditioned"
        else None,
        "audio_cover_steps": int(32 * adherence / 100) if effective == "conditioned" else 0,
        "fallback_reason": reason,
    }


def validate_recording_request(draft):
    """Direct recordings have no lyric, prior/reference, arrangement or postmix inputs."""
    if len(draft.get("clips", [])) != 1:
        raise ValueError("Recording + style requires exactly one uploaded or microphone recording")
    for key in ("lyrics", "lyric_idea", "backing_song_id", "arrangement"):
        if draft.get(key):
            raise ValueError(
                "Recording + style does not accept lyrics, prior songs or arrangements"
            )
    if draft.get("audio_mode", "conditioned") != "conditioned":
        raise ValueError("Recording + style requires direct audio conditioning, not postmix")
    if not str(draft.get("styles", "")).strip():
        raise ValueError("Add style instructions for the recording")


def generation_parameters(draft: dict, sources: list[dict], seed: int):
    options: dict = {**OPTIONS, **draft.get("options", {})}
    recording = draft.get("workflow") == "recording-style"
    if recording:
        validate_recording_request(draft)
        if len(sources) != 1 or sources[0]["source_type"] not in {"upload", "microphone"}:
            raise ValueError("Recording + style accepts an original recording, not a prior song")
        # Source structure and length are authoritative; hidden sampled-mode controls are inert.
        options.update(gender="", variety=0, duration="source")
    if options["duration"] in (None, "") or str(options["duration"]).lower() == "auto":
        options["duration"] = "auto"
    if options["gender"] not in {"", "Male", "Female"}:
        raise ValueError("Choose unset, Male or Female vocal character")
    for key in ("weirdness", "influence", "variety"):
        if (
            not isinstance(options[key], (int, float))
            or not math.isfinite(options[key])
            or not 0 <= options[key] <= 100
        ):
            raise ValueError("Generation controls must be between 0 and 100")
    lyrics, styles = str(draft.get("lyrics", "")), str(draft.get("styles", ""))
    if len(lyrics) > 4096 or len(styles) > 400:
        raise ValueError("Use at most 4096 lyric characters and 400 style characters")
    if not styles.strip() and not lyrics.strip() and not sources:
        raise ValueError("Add audio, lyrics or styles before generating")
    if recording:
        duration = float(sources[0]["duration"])
        if not math.isfinite(duration) or not 1 <= duration <= 300:
            raise ValueError("Recording + style supports intact recordings from 1–300 seconds")
        derivation = {"method": "source-recording", "source_seconds": duration}
    elif options["duration"] == "auto":
        words = len(re.findall(r"\w+", lyrics))
        source_duration = max(
            (
                min(
                    source["duration"],
                    source["settings"]["sample_seconds"] * source["settings"]["samples"],
                )
                for source in sources
            ),
            default=0,
        )
        duration = math.ceil(max(10, words / 2.2 + (12 if words else 0), source_duration * 1.25))
        derivation = {
            "lyric_words": words,
            "longest_sample_budget_seconds": source_duration,
            "seconds_per_word": 1 / 2.2,
            "structure_seconds": 12 if words else 0,
        }
    else:
        duration, derivation = float(options["duration"]), None
    if options["duration"] == "auto":
        duration = min(300, duration)
    if not recording and (not math.isfinite(duration) or not 10 <= duration <= 300):
        raise ValueError(
            "This configuration supports 10–300 seconds. Choose a duration in that range"
        )
    effective_styles = styles
    rng = random.Random(seed)
    if options["variety"]:
        variations = [
            "vary dynamics, same mood",
            "vary phrasing, same style",
            "vary timing, same rhythm",
            "vary tone, same delivery",
            "vary texture, same sources",
            "vary flow, same form",
        ]
        count = max(1, math.ceil(options["variety"] / 34))
        effective_styles = (
            styles + (", " if styles else "") + ", ".join(rng.sample(variations, count))
        )
    caption = effective_styles
    if options["gender"]:
        caption += (", " if caption else "") + options["gender"].lower() + " lead vocal character"
    if not caption.strip():
        caption = "music arranged around vocal samples" if sources else "expressive vocal song"
    return {
        "caption": caption,
        "lyrics": lyrics,
        "instrumental": not recording and not bool(lyrics.strip()),
        "workflow": "recording-style" if recording else "model",
        "duration": duration,
        "seed": seed,
        "steps": 32,
        "guidance": 1 + options["influence"] * 0.14,
        "shift": 1 + options["weirdness"] * 0.04,
        # Pinned SDE renoises on unshifted time, incompatible with our shift control.
        # Keep the supported upstream default at every exposed Weirdness value.
        "method": "ode",
        "original_styles": styles,
        "effective_styles": effective_styles,
        "variety_version": "requested-performance-v1" if options["variety"] else None,
        "requested": options,
        "duration_derivation": derivation,
    }


def stop_inference(process):
    """Stop our worker tree, including Windows virtual-environment redirectors."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            [
                str(Path(os.environ.get("WINDIR", "C:/Windows")) / "System32/taskkill.exe"),
                "/PID",
                str(process.pid),
                "/T",
                "/F",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            creationflags=CREATE_FLAGS,
        )
    if process.poll() is None:
        process.terminate()
    process.wait(timeout=15)


def fixed_effect(core, audio, settings):
    """Keep trimming offsets and stretch/tails within the original slot."""
    result = np.zeros_like(audio)
    effective = {**core.FX_DEFAULTS, "normalize": False, **settings}
    start, end = 0, len(audio)
    if effective.get("trim"):
        magnitude = np.max(np.abs(audio), axis=1)
        active = np.flatnonzero(
            magnitude > magnitude.max(initial=0) * core.db(-float(effective["trim_db"]))
        )
        if not len(active):
            return result
        start, end = int(active[0]), int(active[-1]) + 1
        effective["trim"] = False
    processed = core.apply_fx(audio[start:end], effective)
    count = min(len(processed), len(result) - start)
    result[start : start + count] = processed[:count]
    return result


class Songs:
    def __init__(self, core, models, media, invoke=None):
        self.core, self.models, self.media = core, models, media
        self.invoke = invoke or self._invoke
        self.local_inference = invoke is None

    def relative(self, path):
        return Path(path).relative_to(self.core.LIB).as_posix()

    def asset(self, relative):
        return safe_file(self.core.LIB, relative)

    def _invoke(self, action, values, progress, canceled):
        state = self.models.ready()
        if not state:
            raise ValueError("Install or verify a music model in Settings before this operation")
        root = self.models.storage.models
        owner_cache = root / "cache" / self.models.storage.preferences["installation_id"]
        before = {p for p in owner_cache.rglob("*") if p.is_file()}
        request = {
            "action": action,
            "root": str(root),
            "model": state["model"],
            "packages": str(safe_file(root, state["packages"])),
            "code": str(safe_file(root, state["code"])),
            "planner": self.models.manifest["models"][state["model"]].get("planner"),
            "lyric_writer": (self.models.planner() or {}).get("writer"),
            "writer_revision": (self.models.planner() or {}).get("writer_revision"),
            "runtime_revision": state["runtime_revision"],
            **values,
        }
        if action == "enrich_prompt":
            extra = self.models.enrichment_ready()
            profile = self.models.enrichment_profile()
            if not extra or not profile:
                raise ValueError("Local prompt enrichment support is unavailable")
            request.update(
                enrichment_packages=str(safe_file(root, extra["packages"])),
                enrichment_profile=profile,
                writer_path=str(safe_file(root, profile["writer_path"])),
            )
        request_file = root / "cache" / (uuid.uuid4().hex + ".json")
        env = cache_environment(root, self.models.storage.preferences["installation_id"])
        env["HF_HUB_OFFLINE"] = env["TRANSFORMERS_OFFLINE"] = "1"
        atomic_json(request_file, request)
        result = None
        started = time.monotonic()
        messages = []
        progress(
            "Starting local inference runtime",
            0,
            stage="initializing_runtime",
            timing_profile={"runtime_mode": "fresh_process"},
        )
        try:
            with subprocess.Popen(
                [sys.executable, str(ROOT / "backend" / "inference_runner.py"), str(request_file)],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=CREATE_FLAGS,
            ) as process:
                assert process.stdout is not None
                output = process.stdout
                lines = queue.Queue()
                threading.Thread(
                    target=lambda: [lines.put(line) for line in output], daemon=True
                ).start()
                try:
                    while process.poll() is None or not lines.empty():
                        if canceled():
                            stop_inference(process)
                            raise Canceled("Processing canceled; completed songs are preserved")
                        if action == "enrich_prompt" and time.monotonic() - started > 150:
                            stop_inference(process)
                            raise TimeoutError("Local prompt enrichment preparation timed out")
                        try:
                            line = lines.get(timeout=0.2).strip()
                        except queue.Empty:
                            continue
                        if line.startswith("TROGLO_EVENT "):
                            event = json.loads(line[len("TROGLO_EVENT ") :])
                            if event["stage"] == "complete":
                                result = event["result"]
                            elif event["stage"] == "failed":
                                messages.append(event["error"])
                            else:
                                fraction = event.pop("fraction", 0)
                                stage = event.pop("stage")
                                message = (
                                    event.pop("message", "") or stage.replace("_", " ").capitalize()
                                )
                                progress(message, fraction, stage=stage, **event)
                        else:
                            messages.append(line)
                    if process.returncode or result is None:
                        raise RuntimeError(messages[-1] if messages else "Inference process failed")
                finally:
                    if process.poll() is None:
                        stop_inference(process)
        finally:
            request_file.unlink(missing_ok=True)
            self.models.storage.owned(
                root, [p for p in owner_cache.rglob("*") if p.is_file() and p not in before]
            )
        return result

    def collect_sources(self, draft):
        sources = []
        for clip in draft.get("clips", []):
            saved = clip.get("saved_file")
            if saved:
                matching = []
                for song in self.core.list_items():
                    recipe = song.get("recipe") or {}
                    recipe = recipe.get("creation_recipe", recipe)
                    matching.extend(
                        source
                        for source in recipe.get("sources", [])
                        if source["id"] == clip["id"] and source.get("file") == saved
                    )
                if not matching:
                    raise ValueError("Saved input is not referenced by an available song recipe")
                source = matching[0]
                item = {
                    "id": source["id"],
                    "name": source["label"],
                    "duration": self.core.load(self.asset(saved)).shape[0] / self.core.SR,
                    "type": "generated" if source["source_type"] == "prior-song" else "voice",
                    "source_type": source["source_type"],
                }
            else:
                item = self.core.get_item(clip["id"])
            prior = song_item(item)
            clip_settings = (
                {} if draft.get("workflow") == "recording-style" else clip.get("settings", {})
            )
            settings = {
                **CLIP_DEFAULTS,
                **{key: value for key, value in clip_settings.items() if value is not None},
            }
            if (
                not 0.25 <= float(settings["sample_seconds"]) <= 8
                or not 1 <= int(settings["samples"]) <= 16
            ):
                raise ValueError("Sample length/count is outside supported limits")
            if (
                not -12 <= float(settings["pitch"]) <= 12
                or not 0.5 <= float(settings["stretch"]) <= 2
                or not -30 <= float(settings["gain"]) <= 12
            ):
                raise ValueError("Clip transformation is outside supported limits")
            item_recipe = item.get("recipe")
            duration = item["duration"]
            if draft.get("workflow") == "recording-style":
                # Catalog durations are rounded for display; the complete accepted
                # waveform, including its last partial millisecond, sets this timeline.
                info = sf.info(self.asset(saved) if saved else item["path"])
                duration = info.frames / info.samplerate
            sources.append(
                {
                    "id": item["id"],
                    "label": clip.get("label", item["name"]),
                    "source_type": "prior-song" if prior else item.get("source_type", "upload"),
                    "lineage": item_recipe.get("source_song_id")
                    if isinstance(item_recipe, dict)
                    else None,
                    "duration": duration,
                    "preset": clip.get("preset"),
                    "preset_version": settings.get("version"),
                    "settings": settings,
                    "saved_file": saved,
                }
            )
        return route_sources(sources)

    def arrange(
        self,
        sources,
        directory,
        parameters,
        progress,
        canceled=lambda: False,
        reused_source_ids=frozenset(),
        context=None,
    ):
        layer = np.zeros((round(parameters["duration"] * self.core.SR), 2), np.float32)
        assets, placements, analyses = [], [], []
        rng = random.Random(parameters["seed"])
        sample_audio, descriptors, tempos = {}, [], []
        prior_tempos = []
        weights = [source.get("routing", {}).get("duration_weight", 1.0) for source in sources]
        for source_index, source in enumerate(sources):
            if canceled():
                raise Canceled("Sample analysis canceled")
            audio = (
                self.core.load(self.asset(source["saved_file"]))
                if source.get("saved_file")
                else self.core.load_item(source["id"])
            )
            if not len(audio) or np.max(np.abs(audio)) < 1e-5:
                raise ValueError("Input clip has no audible samples: " + source["label"])
            input_file = directory / "inputs" / (f"{source_index}-{source['id']}.wav")
            input_file.parent.mkdir(parents=True, exist_ok=True)
            sf.write(input_file, audio, self.core.SR, subtype="FLOAT")
            source["file"] = self.relative(input_file)
            if source["id"] in reused_source_ids:
                analyses.append(
                    {
                        "source_id": source["id"],
                        "selection": {"method": "saved-arrangement"},
                        "arrangement": {"method": "saved-arrangement"},
                    }
                )
                continue
            progress(
                "Analyzing input audio",
                0,
                stage="analyzing",
                units_complete=0,
                units_total=1,
                timing_profile={"sample_planner": PLANNER_VERSION},
                timing_stage_profile={
                    "source_index": source_index,
                    "source_seconds": source["duration"],
                    "planner": PLANNER_VERSION,
                },
            )
            audio, channel_strategy = phase_safe_audio(audio)
            analysis = self.core.analyze_vocal(audio)
            regions, budget = select_regions(
                audio,
                self.core.SR,
                source["settings"],
                analysis,
                rng,
                parameters["duration"] * weights[source_index] / max(1, sum(weights)),
                source.get("routing"),
            )
            progress("Analyzed input audio", 1, stage="analyzing", units_complete=1, units_total=1)
            analyses.append({"source_id": source["id"], "analysis": analysis, "selection": budget})
            analyses[-1]["channel_strategy"] = channel_strategy
            if analysis.get("tempo_confidence", 0) > 2.0 and analysis.get("tempo_raw"):
                tempos.append(float(analysis["tempo_raw"]))
                if source["source_type"] == "prior-song":
                    prior_tempos.append(float(analysis["tempo_raw"]))
            sample_bpm = (
                min(180, max(60, float(analysis["tempo_raw"])))
                if analysis.get("tempo_confidence", 0) > 2.0 and analysis.get("tempo_raw")
                else 90
            )
            if context:
                sample_bpm = context["bpm"]
            transform_settings = source["settings"]
            if context and source["source_type"] != "prior-song":
                transform_settings, alignment = align_recording(
                    source["settings"], analysis, context
                )
                analyses[-1]["tonal_alignment"] = alignment
            total = len(regions) * VARIANTS_PER_REGION
            progress(
                "Transforming source samples",
                0,
                stage="sampling",
                units_complete=0,
                units_total=total,
                timing_stage_profile={
                    "source_index": source_index,
                    "sample_budget": len(regions),
                    "variants": VARIANTS_PER_REGION,
                    "planner": PLANNER_VERSION,
                },
            )
            for index, region in enumerate(regions):
                family = f"s{source_index}-{index}"
                for variant in range(VARIANTS_PER_REGION):
                    if canceled():
                        raise Canceled("Sample transformation canceled")
                    fragment = audio[region["start"] : region["end"]].copy()
                    fx = sample_transform(
                        transform_settings,
                        region,
                        index,
                        rng,
                        variant,
                        sample_bpm,
                        analysis,
                        source.get("routing"),
                    )
                    transformed = self.core.apply_fx(fragment, fx)
                    tail = min(0.25, 30 / sample_bpm) if fx["delay"] else 0
                    end = round(
                        (len(fragment) / self.core.SR / fx["stretch"] + tail) * self.core.SR
                    )
                    transformed = self.core.fade(transformed[:end], 0.01, 0.04)
                    peak = float(np.max(np.abs(transformed), initial=0))
                    headroom = min(1, 0.8 / peak) if peak else 1
                    transformed *= headroom
                    identifier = f"{family}-v{variant}"
                    filename = directory / "samples" / (identifier + ".wav")
                    filename.parent.mkdir(exist_ok=True)
                    sf.write(filename, transformed, self.core.SR, subtype="FLOAT")
                    descriptor = {
                        "id": identifier,
                        "family_id": family,
                        "variant": variant,
                        "source_index": source_index,
                        "source_type": source["source_type"],
                        "routing_role": source.get("routing", {}).get("role"),
                        "kind": region["kind"],
                        "role": ("statement", "response", "fill")[variant],
                        "length_samples": len(transformed),
                    }
                    assets.append(
                        {
                            **descriptor,
                            "source_id": source["id"],
                            "file": self.relative(filename),
                            "source_start": region["start"],
                            "source_end": region["end"],
                            "selection": region,
                            "transformation": fx,
                            "headroom_gain": headroom,
                        }
                    )
                    descriptors.append(descriptor)
                    sample_audio[identifier] = transformed
                    complete = index * VARIANTS_PER_REGION + variant + 1
                    progress(
                        "Transforming source samples",
                        complete / total,
                        stage="sampling",
                        source=source_index + 1,
                        sources_total=len(sources),
                        units_complete=complete,
                        units_total=total,
                    )
        grid_tempos = prior_tempos or tempos
        bpm = min(180, max(60, float(np.median(grid_tempos)) if grid_tempos else 90))
        if context:
            bpm = context["bpm"]
        if canceled():
            raise Canceled("Sample arrangement canceled")
        policy = sources[0].get("routing") if sources else None
        placements, plan = plan_events(
            descriptors, len(layer), self.core.SR, bpm, rng, policy, context
        )
        progress(
            "Arranging transformed samples",
            0,
            stage="planning",
            units_complete=0,
            units_total=len(placements),
            timing_stage_profile={"planner": PLANNER_VERSION},
        )
        for index, placement in enumerate(placements):
            if canceled():
                raise Canceled("Sample arrangement canceled")
            position, length = placement["offset_samples"], placement["length_samples"]
            layer[position : position + length] += (
                sample_audio[placement["sample_id"]][:length] * placement["gain"]
            )
            progress(
                "Arranging transformed samples",
                (index + 1) / len(placements),
                stage="planning",
                units_complete=index + 1,
                units_total=len(placements),
            )
        peak = float(np.max(np.abs(layer), initial=0))
        if peak > 0.8:
            gain = 0.8 / peak
            layer *= gain
            for placement in placements:
                placement["gain"] *= gain
        for analysis in analyses:
            if analysis["selection"]["method"] == "saved-arrangement":
                continue
            analysis["arrangement"] = {
                **plan,
                "bpm": bpm,
                "tempo_source": "backing-song"
                if context
                else "prior-song"
                if prior_tempos
                else "recordings"
                if tempos
                else "fallback",
                "source_routing": analysis["selection"].get("routing"),
            }
        return layer, assets, placements, analyses

    def match_samples(
        self, generated, directory, samples, placements, sources, draft, progress, canceled
    ):
        """Persist effective placement gains; replay never runs separation again."""
        reference = generated
        reference_kind = "song"
        reference_file = None
        song_level = sample_loudness(self.core, generated)
        if str(draft.get("lyrics", "")).strip():
            progress("Measuring generated vocal loudness", 0, stage="matching_samples")
            output = directory / "loudness-reference"
            self.invoke(
                "separate",
                {
                    "audio": str(directory / "musical-parts.wav"),
                    "output": str(output),
                    "reference_only": True,
                },
                progress,
                canceled,
            )
            vocal_file = output / "vocals.wav"
            vocal = self.core.load(vocal_file)
            if vocal.shape != generated.shape or not np.isfinite(vocal).all():
                raise ValueError("Vocal loudness reference does not match the generated song")
            vocal_level = sample_loudness(self.core, vocal)
            # Ignore effectively silent stems and very faint instrumental bleed.
            if vocal_level > -60 and vocal_level >= song_level - 30:
                reference, reference_kind = vocal, "vocals"
                reference_file = self.relative(vocal_file)
        target = sample_loudness(self.core, reference)
        layer = np.zeros_like(generated)
        settings = {source["id"]: source["settings"] for source in sources}
        measured = {}
        for sample in samples:
            if canceled():
                raise Canceled("Sample loudness matching canceled")
            audio = self.core.load(self.asset(sample["file"]))
            level = sample_loudness(self.core, audio)
            offset = float(settings[sample["source_id"]]["gain"])
            adjustment = (
                min(30.0, max(-30.0, target - level)) if target > -69 and level > -69 else 0.0
            )
            measured[sample["id"]] = (audio, 10 ** ((adjustment + offset) / 20))
            sample["loudness_match"] = {
                "measured_lufs": level,
                "adjustment_db": adjustment,
                "volume_offset_db": offset,
                "limited": abs(target - level) > 30,
            }
        for placement in placements:
            audio, gain = measured[placement["sample_id"]]
            placement["pre_match_gain"] = placement.get("gain", 1)
            placement["gain"] = gain
            start, length = placement["offset_samples"], placement["length_samples"]
            layer[start : start + length] += audio[:length] * gain
        progress("Sample loudness matched", 1, stage="matching_samples")
        return layer, {
            "version": 1,
            "reference": reference_kind,
            "reference_file": reference_file,
            "target_lufs": target,
            "max_adjustment_db": 30,
        }

    def enhance_guide(self, layer, enhancement_settings, progress):
        """Prepare the conditioning guide; the unchanged layer is never modified."""
        tier, strength = enhancement_settings["tier"], enhancement_settings["strength"]
        if tier != "off":
            progress(
                "Enhancing arrangement guide",
                0,
                stage="guide_enhancement",
                units_complete=0,
                units_total=1,
            )
        guide, info = guide_enhance.enhance_guide(layer, self.core.SR, tier, strength)
        if tier != "off":
            progress(
                info["fallback_reason"] or "Arrangement guide enhanced",
                1,
                stage="guide_enhancement",
                units_complete=1,
                units_total=1,
            )
        return guide, info

    def require_planner(self):
        if self.local_inference and not self.models.planner_ready():
            raise ValueError(
                "Install the optional song writing tools in Settings for automatic lyrics or song length, "
                "or choose an explicit duration between 10 and 300 seconds."
            )

    def musical_blueprint(self, parameters, mode, directory, progress, canceled):
        """Never let text-generated codes pre-empt source conditioning or rewrite inputs."""
        if mode["effective_mode"] == "conditioned":
            return {"status": "bypassed", "reason": "source_audio_supplies_structure"}, None
        model = self.models.manifest["models"][self.models.selected]
        if "musical_metadata" not in model.get("planning", []):
            return {
                "status": "unsupported",
                "reason": "model_has_no_validated_blueprint_input",
            }, None
        if not getattr(self.models, "planner_ready", lambda: False)():
            return {"status": "unavailable", "reason": "optional_planner_not_installed"}, None
        try:
            result = self.invoke("plan_blueprint", {"parameters": parameters}, progress, canceled)
            blueprint = validated_blueprint(result, parameters)
            filename = directory / "music-blueprint.json"
            atomic_json(filename, blueprint)
            return {
                "status": "applied",
                "file": self.relative(filename),
                **{
                    key: blueprint[key]
                    for key in (
                        "version",
                        "planner",
                        "runtime_revision",
                        "seed",
                        "duration",
                        "strategy",
                        "seconds",
                        "peak_vram",
                    )
                },
            }, blueprint["constraints"]
        except Canceled:
            raise
        except Exception as error:
            reason = str(error)
            progress(
                "Music blueprint unavailable; generating from original inputs. " + reason,
                0,
                stage="planning_fallback",
            )
            return {"status": "failed", "reason": reason}, None

    def lyrics(self, values, progress, canceled):
        prompt = str(values.get("prompt", "")).strip()
        language = str(values.get("language", "en"))
        if not 1 <= len(prompt) <= 1000:
            raise ValueError("Describe your song idea using 1–1000 characters")
        if language != "auto" and not re.fullmatch(r"[a-z]{2}", language):
            raise ValueError("Choose Auto or a two-letter lyrics language code")
        self.require_planner()
        result = self.invoke(
            "write_lyrics",
            {
                "prompt": prompt,
                "language": language,
                "seed": random.SystemRandom().randrange(2**31),
            },
            progress,
            canceled,
        )
        lyrics = result.get("lyrics")
        if not isinstance(lyrics, str) or not lyrics.strip() or len(lyrics) > 4096:
            raise ValueError("The local planner did not produce usable lyrics. Try another idea.")
        return {"message": "Lyrics ready to edit", "lyrics": lyrics, "planning": result}

    def arrange_over_song(self, draft, progress, canceled):
        """CPU-only source arrangement; model controls never enter this path."""
        count = draft.get("count", 2)
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 32:
            raise ValueError("Number of Generations must be an integer between 1 and 32")
        identifier = draft.get("backing_song_id")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("Choose one Library song as the backing track")
        try:
            backing_song = self.core.get_item(identifier)
        except (KeyError, ValueError) as error:
            raise ValueError(
                "The backing song is unavailable; choose another Library song"
            ) from error
        if not song_item(backing_song):
            raise ValueError("Choose a Library song as the backing track")
        sources = self.collect_sources(draft)
        if not sources:
            raise ValueError("Add at least one input recording to arrange over the backing song")
        if any(source["id"] == backing_song["id"] for source in sources):
            raise ValueError("The backing song cannot also be sampled as an input recording")
        backing = self.core.load_item(backing_song["id"])
        if (
            not np.isfinite(backing).all()
            or not self.core.SR <= len(backing) <= self.core.SR * 1200
        ):
            raise ValueError(
                "Backing arrangement supports finite songs from one second to twenty minutes"
            )
        progress("Analyzing the backing song", 0, stage="analyzing")
        context = backing_context(backing, self.core.SR, self.core.analyze_vocal)
        if canceled():
            raise Canceled("Arrangement canceled; the backing song is unchanged")
        writable_root(
            str(self.core.LIB),
            int(
                count
                * (
                    backing.nbytes * 4
                    + sum(source["duration"] for source in sources) * self.core.SR * 8
                )
            )
            + 64 * 1024 * 1024,
        )
        outcomes = []
        for index in range(count):
            if canceled():
                error = Canceled("Arrangement canceled; completed songs are preserved")
                error.result = {
                    "outcomes": outcomes
                    + [
                        {"index": remaining + 1, "status": "canceled"}
                        for remaining in range(index, count)
                    ]
                }
                raise error
            directory = safe_file(self.core.LIB, "assets/songs/" + uuid.uuid4().hex)
            directory.mkdir(parents=True, exist_ok=False)
            seed = random.SystemRandom().randrange(2**31)
            parameters = {
                "duration": len(backing) / self.core.SR,
                "seed": seed,
                "workflow": "arrange-over-song",
                "method": "source-arrangement",
                "model": None,
            }
            current_sources = copy.deepcopy(sources)

            def item_progress(message, fraction=0, **details):
                progress(
                    message,
                    fraction,
                    item=index + 1,
                    items_total=count,
                    items_complete=sum(output["status"] == "complete" for output in outcomes),
                    **details,
                )

            registered = False
            output_files = []
            try:
                musical_file = directory / "musical-parts.wav"
                sf.write(musical_file, backing, self.core.SR, subtype="FLOAT")
                layer, samples, placements, analyses = self.arrange(
                    current_sources, directory, parameters, item_progress, canceled, context=context
                )
                # Blank lyrics deliberately prevent separator/model invocation.
                layer, balance = self.match_samples(
                    backing,
                    directory,
                    samples,
                    placements,
                    current_sources,
                    {"lyrics": ""},
                    item_progress,
                    canceled,
                )
                arrangement_file = directory / "sample-arrangement.wav"
                sf.write(arrangement_file, layer, self.core.SR, subtype="FLOAT")
                item_progress("Mixing recordings over the backing song", 0, stage="rendering")
                mixed = self.core.master(backing + layer)
                if canceled():
                    raise Canceled("Arrangement canceled before saving")
                title = str(draft.get("title", "")).strip() or backing_song["name"] + " arrangement"
                if len(title) > 120:
                    raise ValueError("Choose a song title of at most 120 characters")
                if count > 1:
                    title += f" {index + 1}"
                recipe = {
                    "op": "song",
                    "version": 2,
                    "workflow": "arrange-over-song",
                    "render_mode": "postmix",
                    "backing_song_id": backing_song["id"],
                    "backing_name": backing_song["name"],
                    "musical_file": self.relative(musical_file),
                    "conditioning_file": self.relative(arrangement_file),
                    "draft": copy.deepcopy(draft),
                    "sources": current_sources,
                    "samples": samples,
                    "placements": placements,
                    "analysis": analyses,
                    "sample_loudness_match": balance,
                    "parameters": parameters,
                    "model": None,
                    "backing_context": {
                        key: value for key, value in context.items() if key != "energy"
                    },
                    "inactive_controls": [
                        "lyrics",
                        "styles",
                        "options",
                        "lyric_idea",
                        "lyric_language",
                        "audio_mode",
                        "audio_adherence",
                        "guide_enhancement",
                        "guide_enhancement_strength",
                        "enrich",
                        "prompt_enrichment",
                    ],
                }
                recipe["draft"]["workflow"] = "arrange-over-song"
                recipe["draft"]["clips"] = [
                    {key: value for key, value in clip.items() if key not in {"audio", "key"}}
                    for clip in draft.get("clips", [])
                ]
                output_id = uuid.uuid4().hex[:10]
                wav = safe_file(self.core.LIB, f"mixes/{self.core._slug(title)}_{output_id}.wav")
                mp3 = safe_file(self.core.LIB, f"mixes/{self.core._slug(title)}_{output_id}.mp3")
                if wav.exists() or mp3.exists():
                    raise ValueError("Arrangement output already exists; try again")
                with wav.open("xb"):
                    output_files.append(wav)
                self.core.save_wav(wav, mixed)
                item_progress("Encoding arranged song", 0, stage="exporting")
                with mp3.open("xb"):
                    output_files.append(mp3)
                self.core.to_mp3(wav, mp3)
                if canceled():
                    wav.unlink(missing_ok=True)
                    mp3.unlink(missing_ok=True)
                    raise Canceled("Arrangement canceled before registration")
                item = {
                    "id": output_id,
                    "name": title,
                    "type": "mix",
                    "is_song": True,
                    "origin": "arranged",
                    "path": str(wav),
                    "mp3": str(mp3),
                    "duration": round(len(backing) / self.core.SR, 3),
                    "source": "arranged over:" + backing_song["id"],
                    "created": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "tags": [],
                    "recipe": recipe,
                    "folder": backing_song.get("folder", ""),
                }
                self.core._add_item(item)
                registered = True
                outcomes.append(
                    {
                        "index": index + 1,
                        "status": "complete",
                        "song": item,
                        "audio": self.media(wav),
                        "download": self.media(mp3),
                        "workflow": "arrange-over-song",
                        "backing_name": backing_song["name"],
                        "arrangement_audio": self.media(arrangement_file),
                        "parameters": parameters,
                    }
                )
                item_progress(
                    "Arrangement saved",
                    1,
                    stage="output_complete",
                    outcomes=copy.deepcopy(outcomes),
                    cancel_safe=False,
                )
            except Canceled:
                if not registered:
                    for file in output_files:
                        file.unlink(missing_ok=True)
                error = Canceled("Arrangement canceled; completed songs are preserved")
                error.result = {
                    "outcomes": outcomes
                    + [
                        {"index": remaining + 1, "status": "canceled"}
                        for remaining in range(index + int(registered), count)
                    ]
                }
                raise error
            except Exception as error:
                if registered:
                    raise
                for file in output_files:
                    file.unlink(missing_ok=True)
                outcomes.append({"index": index + 1, "status": "failed", "message": str(error)})
            finally:
                asset_root = (self.core.LIB / "assets" / "songs").resolve()
                if (
                    not registered
                    and directory.exists()
                    and directory.resolve().is_relative_to(asset_root)
                    and not directory.is_symlink()
                    and not directory.is_junction()
                    and re.fullmatch(r"[0-9a-f]{32}", directory.name)
                ):
                    shutil.rmtree(directory)
        return {
            "message": f"Created {sum(output['status'] == 'complete' for output in outcomes)} of {count} arrangements",
            "outcomes": outcomes,
            "problems": [
                f"Output {output['index']}: {output['message']}"
                for output in outcomes
                if output["status"] == "failed"
            ],
        }

    def enrich_request(self, draft, caption, progress, canceled):
        enabled = prompt_enrichment.requested(draft)
        if not enabled:
            return prompt_enrichment.provenance(caption, enabled=False, reason="off")
        profile = prompt_enrichment.profile_for(self.models.manifest, self.models.selected)
        if not profile:
            return prompt_enrichment.provenance(caption, reason="no-qualified-profile")
        if not self.models.enrichment_ready():
            return prompt_enrichment.provenance(
                caption, profile=profile, reason="support-unavailable"
            )
        if canceled():
            raise Canceled("Prompt preparation canceled; supplied inputs are unchanged")
        try:
            data = self.invoke(
                "enrich_prompt",
                {
                    "caption": caption,
                    "seed": random.SystemRandom().randrange(2**31),
                    "instrumental": draft.get("workflow") != "recording-style"
                    and not bool(draft.get("lyrics", "").strip()),
                    "source_authoritative": bool(draft.get("clips") or draft.get("prior_song_ids")),
                },
                progress,
                canceled,
            )
            if not isinstance(data, dict) or data.get("original_caption") != caption:
                return prompt_enrichment.provenance(
                    caption, profile=profile, reason="invalid-result"
                )
            additions = data.get("additions", "")
            if (
                not isinstance(additions, str)
                or len(additions) > profile["max_characters"]
                or (additions and not prompt_enrichment.accepted(data.get("verdict")))
            ):
                return prompt_enrichment.provenance(
                    caption, profile=profile, reason="invalid-result"
                )
            details = {
                key: data[key]
                for key in ("seed", "verdict", "load_seconds", "seconds", "peak_vram")
                if key in data
            }
            return prompt_enrichment.provenance(
                caption,
                profile=profile,
                reason=data.get("fallback_reason"),
                additions=additions,
                **details,
            )
        except Canceled:
            raise
        except Exception as error:
            progress("Using original musical direction", 1, stage="enriching_prompt")
            return prompt_enrichment.provenance(
                caption, profile=profile, reason="runtime-error", diagnostic=str(error)[:200]
            )

    def generate(self, draft, progress, canceled):
        workflow = draft.get("workflow", "model")
        if workflow == "arrange-over-song":
            return self.arrange_over_song(draft, progress, canceled)
        recording = workflow == "recording-style"
        if workflow not in {"model", "recording-style"}:
            raise ValueError("Choose a supported Generation workflow")
        if recording:
            validate_recording_request(draft)
            if (
                self.models.manifest["models"][self.models.selected].get("recording_conditioning")
                != "cover-nofsq"
            ):
                raise ValueError("This model does not support direct recording conditioning")
        if self.local_inference and not self.models.ready():
            raise ValueError("Install or verify a music model in Settings before this operation")
        count = draft.get("count", 2)
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 32:
            raise ValueError("Number of Generations must be an integer between 1 and 32")
        enhancement_settings = guide_enhance.settings(
            {"guide_enhancement": "off"} if recording else draft
        )
        sources = self.collect_sources(draft)
        if generation_parameters(draft, sources, 0)["requested"]["duration"] == "auto":
            self.require_planner()
        estimate = count * (
            sum(
                source["duration"]
                + (
                    min(
                        source["duration"],
                        max(
                            float(source["settings"]["sample_seconds"]) * 2,
                            source["duration"] if source["duration"] <= 8 else 0,
                        ),
                    )
                    * 2
                    + 0.25
                )
                * int(source["settings"]["samples"])
                * VARIANTS_PER_REGION
                for source in sources
            )
            * self.core.SR
            * 8
            + 300 * self.core.SR * 32
        )
        writable_root(str(self.core.LIB), int(estimate) + 64 * 1024 * 1024)
        original_options = {**draft.get("options", {}), "variety": 0}
        base_caption = generation_parameters({**draft, "options": original_options}, sources, 0)[
            "caption"
        ]
        try:
            enrichment = self.enrich_request(draft, base_caption, progress, canceled)
        except Canceled as error:
            error.result = {
                "outcomes": [{"index": index + 1, "status": "canceled"} for index in range(count)]
            }
            raise
        outcomes = []
        for index in range(count):
            if canceled():
                outcomes.extend(
                    {"index": remaining + 1, "status": "canceled"}
                    for remaining in range(index, count)
                )
                error = Canceled("Generation canceled; completed songs are preserved")
                error.result = {"outcomes": outcomes}
                raise error
            directory = self.core.LIB / "assets" / "songs" / uuid.uuid4().hex
            directory.mkdir(parents=True, exist_ok=True)
            seed = random.SystemRandom().randrange(2**31)
            parameters = generation_parameters(draft, sources, seed)
            original_caption = parameters["caption"]
            parameters["caption"] += (
                ("; " + enrichment["additions"]) if enrichment["applied"] else ""
            )
            effective_enrichment = {
                **copy.deepcopy(enrichment),
                "original_caption": original_caption,
                "effective_caption": parameters["caption"],
            }
            current_sources = copy.deepcopy(sources)

            def item_progress(message, fraction=0, **details):
                progress(
                    message,
                    fraction,
                    item=index + 1,
                    items_total=count,
                    items_complete=sum(o["status"] == "complete" for o in outcomes),
                    **details,
                )

            try:
                if parameters["requested"]["duration"] == "auto":
                    plan = self.invoke(
                        "plan_song",
                        {"parameters": {**parameters, "caption": original_caption}},
                        item_progress,
                        canceled,
                    )
                    suggested = plan.get("duration")
                    if (
                        isinstance(suggested, bool)
                        or not isinstance(suggested, (int, float))
                        or not math.isfinite(suggested)
                        or suggested <= 0
                    ):
                        raise ValueError(
                            "The song planner did not produce a usable duration. Choose an explicit length or retry."
                        )
                    parameters["duration"] = min(300, max(10, suggested))
                    parameters["duration_derivation"] = {
                        "method": "local-model-planner",
                        "suggested_seconds": suggested,
                        "effective_seconds": parameters["duration"],
                        "planning": plan,
                    }
                    item_progress(
                        "Song length planned",
                        1,
                        stage="planning_song",
                        timing_profile={
                            "duration": parameters["duration"],
                            "duration_mode": "auto",
                        },
                    )
                if recording:
                    source = current_sources[0]
                    layer = (
                        self.core.load(self.asset(source["saved_file"]))
                        if source.get("saved_file")
                        else self.core.load_item(source["id"])
                    )
                    if not np.isfinite(layer).all() or np.max(np.abs(layer), initial=0) < 1e-5:
                        raise ValueError("The recording has no usable audible audio")
                    input_file = directory / "inputs" / "recording.wav"
                    input_file.parent.mkdir(parents=True)
                    sf.write(input_file, layer, self.core.SR, subtype="FLOAT")
                    source["file"] = self.relative(input_file)
                    samples, placements = [], []
                    analyses = [{"source_id": source["id"], "method": "intact-recording"}]
                    parameters["duration"] = len(layer) / self.core.SR
                    item_progress("Prepared intact recording", 1, stage="encoding")
                else:
                    layer, samples, placements, analyses = self.arrange(
                        current_sources,
                        directory,
                        parameters,
                        item_progress,
                        canceled,
                        {
                            s["source_id"]
                            for s in (draft.get("arrangement") or {}).get("samples", [])
                        },
                    )
                if draft.get("arrangement"):
                    imported = draft["arrangement"]
                    reused_source_ids = {sample["source_id"] for sample in imported["samples"]}
                    kept_samples = [
                        sample for sample in samples if sample["source_id"] not in reused_source_ids
                    ]
                    kept_ids = {sample["id"] for sample in kept_samples}
                    placements = [
                        placement for placement in placements if placement["sample_id"] in kept_ids
                    ]
                    samples = kept_samples
                    layer.fill(0)
                    for placement in placements:
                        sample = next(s for s in samples if s["id"] == placement["sample_id"])
                        fragment = self.core.load(self.asset(sample["file"]))
                        start, length = placement["offset_samples"], placement["length_samples"]
                        layer[start : start + length] += fragment[:length] * placement.get(
                            "gain", 1
                        )
                    reusable = {}
                    for old_sample in imported["samples"]:
                        original = self.asset(old_sample["file"])
                        sample = copy.deepcopy(old_sample)
                        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", str(sample["id"])):
                            raise ValueError("Invalid saved sample identifier")
                        identifier = "reused-" + sample["id"]
                        target = directory / "samples" / (identifier + ".wav")
                        target.parent.mkdir(exist_ok=True)
                        import shutil

                        shutil.copyfile(original, target)
                        sample.update(id=identifier, file=self.relative(target))
                        reusable[old_sample["id"]] = sample
                        samples.append(sample)
                    for old_placement in imported["placements"]:
                        sample = reusable[old_placement["sample_id"]]
                        audio = self.core.load(self.asset(sample["file"]))
                        offset, length = (
                            int(old_placement["offset_samples"]),
                            int(old_placement["length_samples"]),
                        )
                        if offset < 0 or length < 0 or offset + length > len(layer):
                            raise ValueError(
                                "Saved placements exceed the selected duration. Choose a longer duration or a fresh arrangement"
                            )
                        layer[offset : offset + length] += audio[:length] * old_placement.get(
                            "gain", 1
                        )
                        placements.append({**old_placement, "sample_id": sample["id"]})
                peak = float(np.max(np.abs(layer), initial=0))
                if peak > 0.8 and not recording:
                    gain = 0.8 / peak
                    layer *= gain
                    for placement in placements:
                        placement["gain"] = placement.get("gain", 1) * gain
                mode = generation_mode(
                    draft, self.models, bool(current_sources) if recording else bool(samples)
                )
                parameters.update(mode)
                arrangement_file = directory / "sample-arrangement.wav"
                raw_arrangement_file = directory / "sample-arrangement.raw.wav"
                guide, enhancement = layer, None
                if mode["effective_mode"] == "conditioned" and not recording:
                    # Postmix keeps mixing the unchanged layer; only the model guide is enhanced.
                    guide, enhancement = self.enhance_guide(
                        layer, enhancement_settings, item_progress
                    )
                    parameters["guide_enhancement"] = enhancement
                    if enhancement["applied"]:
                        sf.write(raw_arrangement_file, layer, self.core.SR, subtype="FLOAT")
                sf.write(arrangement_file, guide, self.core.SR, subtype="FLOAT")
                if mode["fallback_reason"]:
                    item_progress(mode["fallback_reason"], 0, stage="conditioning_fallback")
                planning, blueprint_metadata = self.musical_blueprint(
                    {**parameters, "caption": original_caption},
                    mode,
                    directory,
                    item_progress,
                    canceled,
                )
                inferred = self.invoke(
                    "generate",
                    {
                        "parameters": parameters,
                        "output": str(directory / "generated"),
                        "conditioning_audio": str(arrangement_file)
                        if mode["effective_mode"] == "conditioned"
                        else None,
                        "blueprint_metadata": blueprint_metadata,
                    },
                    item_progress,
                    canceled,
                )
                generated_path = Path(inferred["audio"])
                if not generated_path.resolve().is_relative_to(directory.resolve()):
                    raise ValueError("Inference returned an audio path outside the song assets")
                generated = self.core.load(generated_path)
                expected = round(parameters["duration"] * self.core.SR)
                if abs(len(generated) - expected) > self.core.SR:
                    raise ValueError(
                        "Model output duration differs materially from the requested duration"
                    )
                generated = generated[:expected]
                if len(generated) < expected:
                    generated = np.pad(generated, ((0, expected - len(generated)), (0, 0)))
                musical_file = directory / "musical-parts.wav"
                sf.write(musical_file, generated, self.core.SR, subtype="FLOAT")
                loudness_match = None
                if samples and mode["effective_mode"] == "postmix":
                    layer, loudness_match = self.match_samples(
                        generated,
                        directory,
                        samples,
                        placements,
                        current_sources,
                        draft,
                        item_progress,
                        canceled,
                    )
                    sf.write(arrangement_file, layer, self.core.SR, subtype="FLOAT")
                item_progress(
                    "Mixing and mastering", 0, stage="rendering", units_complete=0, units_total=1
                )
                mixed = self.core.master(
                    generated + layer if mode["effective_mode"] == "postmix" else generated
                )
                item_progress(
                    "Mixing and mastering", 1, stage="rendering", units_complete=1, units_total=1
                )
                title = str(draft.get("title", "")).strip()
                if not title:
                    words = re.findall(
                        r"[\w'-]+", draft.get("lyrics", "") or draft.get("styles", "")
                    )
                    title = " ".join(words[:6]) or "New song"
                if count > 1:
                    title += f" {index + 1}"
                recipe = {
                    "op": "song",
                    "version": 2,
                    "workflow": workflow,
                    "planning": planning,
                    "render_mode": mode["effective_mode"],
                    "prompt_enrichment": effective_enrichment,
                    "conditioning_file": self.relative(arrangement_file),
                    **({"guide_enhancement": enhancement} if enhancement is not None else {}),
                    **(
                        {"conditioning_raw_file": self.relative(raw_arrangement_file)}
                        if enhancement and enhancement["applied"]
                        else {}
                    ),
                    "draft": {
                        **copy.deepcopy(draft),
                        "audio_mode": mode["requested_mode"],
                        "audio_adherence": mode["audio_adherence"],
                        "guide_enhancement": enhancement_settings["tier"],
                        "guide_enhancement_strength": enhancement_settings["strength"],
                        "prompt_enrichment": prompt_enrichment.requested(draft),
                        "clips": [
                            {k: v for k, v in c.items() if k not in {"audio", "key"}}
                            for c in draft.get("clips", [])
                        ],
                    },
                    "sources": current_sources,
                    "samples": samples,
                    "placements": placements,
                    "sample_loudness_match": loudness_match,
                    "analysis": analyses,
                    "musical_file": self.relative(musical_file),
                    "original_model_file": self.relative(generated_path),
                    "parameters": parameters,
                    "model": self.models.selected,
                    "runtime_revision": self.models.manifest["runtime_revision"],
                    "model_assets": [
                        {"path": a["path"], "sha256": a["sha256"], "revision": a.get("revision")}
                        for a in self.models.manifest["models"][self.models.selected]["assets"]
                    ],
                    "inference": inferred,
                }
                # Keep recipe paths portable; runtime diagnostics must not embed absolute assets.
                recipe["inference"] = {k: v for k, v in inferred.items() if k != "audio"}
                item_progress("Saving song", 0, stage="saving", units_complete=0, units_total=1)
                item = self.core._new_entry(
                    "generated",
                    title,
                    mixed,
                    source="local-model:" + self.models.selected,
                    recipe=recipe,
                    extra={"is_song": True, "folder": ""},
                )
                item_progress(
                    "Saving song",
                    1,
                    stage="saving",
                    units_complete=1,
                    units_total=1,
                    cancel_safe=False,
                )
                item_progress(
                    "Encoding song download",
                    0,
                    stage="exporting",
                    units_complete=0,
                    units_total=1,
                    cancel_safe=False,
                )
                mp3 = self.core.to_mp3(item["path"])
                item_progress(
                    "Encoding song download",
                    1,
                    stage="exporting",
                    units_complete=1,
                    units_total=1,
                    cancel_safe=False,
                )
                item = self.core.update_item(item["id"], mp3=mp3)
                outcomes.append(
                    {
                        "index": index + 1,
                        "status": "complete",
                        "song": item,
                        "audio": self.media(item["path"]),
                        "download": self.media(mp3),
                        "effective_styles": parameters["effective_styles"],
                        "generation_mode": mode,
                        "workflow": workflow,
                        "planning": planning,
                        "recording_audio": self.media(input_file) if recording else None,
                        "arrangement_audio": self.media(arrangement_file) if samples else None,
                        "arrangement_raw_audio": self.media(raw_arrangement_file)
                        if enhancement and enhancement["applied"]
                        else None,
                        "guide_enhancement": enhancement,
                    }
                )
            except Canceled:
                outcomes.extend(
                    {"index": remaining + 1, "status": "canceled"}
                    for remaining in range(index, count)
                )
                error = Canceled("Generation canceled; completed songs are preserved")
                error.result = {"outcomes": outcomes}
                raise error
            except Exception as exc:
                outcomes.append({"index": index + 1, "status": "failed", "message": str(exc)})
                item_progress("Output failed: " + str(exc), 0, stage="failed_item")
            item_progress(
                "Output finished",
                1,
                stage="output_complete",
                outcomes=copy.deepcopy(outcomes),
                cancel_safe=False,
            )
        completed = sum(o["status"] == "complete" for o in outcomes)
        return {"message": f"Created {completed} of {count} songs", "outcomes": outcomes}

    def rerender(self, item_id, progress=lambda *_args, **_kwargs: None, canceled=lambda: False):
        progress("Loading saved arrangement audio", 0, stage="loading")
        item = self.core.get_item(item_id)
        recipe = item.get("recipe") or {}
        if recipe.get("op") == "vocal-fx-song":
            audio = self.core.load(self.asset(recipe["accompaniment_file"]))
            progress(
                "Mixing saved voice stems",
                0,
                stage="rendering",
                units_complete=0,
                units_total=len(recipe["edited_stems"]),
            )
            for index, filename in enumerate(recipe["edited_stems"].values()):
                if canceled():
                    raise Canceled("Saved arrangement rendering canceled")
                audio += self.core.load(self.asset(filename))
                progress(
                    "Mixing saved voice stems",
                    (index + 1) / len(recipe["edited_stems"]),
                    stage="rendering",
                    units_complete=index + 1,
                    units_total=len(recipe["edited_stems"]),
                )
            progress("Saving rendered song", 0, stage="saving")
            return self.core._new_entry(
                "generated",
                item["name"] + "_rerender",
                audio,
                "rerender:" + item_id,
                recipe=copy.deepcopy(recipe),
                extra={"is_song": True, "folder": item.get("folder", "")},
            )
        if recipe.get("op") != "song":
            raise ValueError("This song has no reusable sample arrangement")
        audio = self.core.load(self.asset(recipe["musical_file"]))
        samples = {s["id"]: s for s in recipe["samples"]}
        placements = (
            recipe["placements"] if recipe.get("render_mode", "postmix") == "postmix" else []
        )
        progress(
            "Mixing saved samples",
            0,
            stage="rendering",
            units_complete=0,
            units_total=len(placements),
        )
        for index, placement in enumerate(placements):
            if canceled():
                raise Canceled("Saved arrangement rendering canceled")
            fragment = self.core.load(self.asset(samples[placement["sample_id"]]["file"]))
            start = placement["offset_samples"]
            count = min(placement["length_samples"], len(fragment), len(audio) - start)
            audio[start : start + count] += fragment[:count] * placement.get("gain", 1)
            progress(
                "Mixing saved samples",
                (index + 1) / len(placements),
                stage="rendering",
                units_complete=index + 1,
                units_total=len(placements),
            )
        progress("Saving rendered song", 0, stage="saving")
        return self.core._new_entry(
            "generated",
            item["name"] + "_rerender",
            self.core.master(audio),
            "rerender:" + item_id,
            recipe=copy.deepcopy(recipe),
            extra={"is_song": True, "folder": item.get("folder", "")},
        )

    def ingredients(self, item_id):
        item = self.core.get_item(item_id)
        recipe = item.get("recipe") or {}
        if recipe.get("op") == "vocal-fx-song":
            recipe = recipe.get("creation_recipe") or {}
        draft = recipe.get("draft", {})
        available = {}
        if recipe.get("op") in {"generate", "mix"}:
            available["title"] = item["name"]
            settings = recipe.get("settings", {})
            if recipe.get("op") == "generate" and settings.get("style"):
                available["styles"] = settings["style"]
            if recipe.get("op") == "mix" and recipe.get("voice_id"):
                try:
                    voice = self.core.get_item(recipe["voice_id"])
                    available["clips"] = [
                        {
                            "id": voice["id"],
                            "label": voice["name"],
                            "settings": {},
                            "source_type": "upload",
                        }
                    ]
                except (KeyError, ValueError):
                    pass
        for key in (
            "workflow",
            "backing_song_id",
            "count",
            "styles",
            "lyrics",
            "title",
            "options",
            "clips",
            "audio_mode",
            "audio_adherence",
            "guide_enhancement",
            "guide_enhancement_strength",
            "prompt_enrichment",
        ):
            if key in draft and not (
                recipe.get("workflow") == "arrange-over-song"
                and key in recipe.get("inactive_controls", [])
            ):
                available[key] = copy.deepcopy(draft[key])
        if recipe.get("op") == "song_import":
            available["title"] = item["name"]
        if recipe.get("sources"):
            available["clips"] = [
                {
                    "id": s["id"],
                    "label": s["label"],
                    "preset": s.get("preset"),
                    "settings": s["settings"],
                    "saved_file": s["file"],
                    "source_type": s["source_type"],
                    "audio": self.media(self.asset(s["file"])),
                }
                for s in recipe["sources"]
            ]
        if recipe.get("samples"):
            available["arrangement"] = {
                "samples": recipe["samples"],
                "placements": recipe["placements"],
                "musical_file": recipe["musical_file"],
            }
        return {
            "song_id": item_id,
            "available": available,
            "unavailable": [
                key
                for key in (
                    "clips",
                    "styles",
                    "lyrics",
                    "title",
                    "options",
                    "audio_mode",
                    "audio_adherence",
                    "guide_enhancement",
                    "guide_enhancement_strength",
                    "arrangement",
                )
                if key not in available
            ],
        }

    def cache_context(self, item_id, progress, canceled):
        item = self.core.get_item(item_id)
        if not song_item(item):
            raise ValueError(
                "Vocal FX accepts library songs and FX versions, not standalone voice uploads"
            )
        recipe = item.get("recipe") or {}
        original_id = (
            recipe.get("source_song_id", item_id)
            if recipe.get("op") == "vocal-fx-song"
            else item_id
        )
        try:
            source = self.core.get_item(original_id)
            source_path = Path(source["path"])
        except KeyError:
            source_path = self.asset(recipe["source_file"])
            source = {
                "id": original_id,
                "recipe": recipe.get("creation_recipe"),
                "name": item["name"],
            }
        processor = {
            "alignment": 1,
            "model_manifest": digest(ROOT / "config" / "model-manifest.json"),
            "runtime_lock": runtime_signature(),
        }
        import hashlib

        key = hashlib.sha256(
            json.dumps(
                {"source": digest(source_path), "processor": processor}, sort_keys=True
            ).encode()
        ).hexdigest()[:24]
        directory = self.core.LIB / "assets" / "vocals" / original_id / key
        metadata_file = directory / "analysis.json"
        cached = False
        progress("Checking saved source stems", 0, stage="checking_cache")
        if metadata_file.exists():
            metadata = json.loads(metadata_file.read_text())
            cached = all(
                self.asset(path).is_file() and digest(self.asset(path)) == checksum
                for path, checksum in metadata["files"].items()
            )
        if not cached:
            progress(
                "Preparing fresh source stems", 0, stage="loading", timing_profile={"cache": False}
            )
            directory.mkdir(parents=True, exist_ok=True)
            import shutil

            source_copy = directory / "source.wav"
            shutil.copyfile(source_path, source_copy)
            output = self.invoke(
                "separate",
                {"audio": str(source_copy), "output": str(directory)},
                progress,
                canceled,
            )
            for group in output["groups"]:
                group["file"] = self.relative(directory / group["file"])
            metadata = {
                **output,
                "source_song_id": original_id,
                "source_file": self.relative(source_copy),
                "vocals_file": self.relative(directory / "vocals.wav"),
                "accompaniment_file": self.relative(directory / "accompaniment.wav"),
                "processor": processor,
                "cache_key": key,
                "creation_recipe": source.get("recipe"),
                "files": {},
            }
            for filename in directory.glob("*.wav"):
                metadata["files"][self.relative(filename)] = digest(filename)
            atomic_json(metadata_file, metadata)
        else:
            progress(
                "Using cached source stems and voice analysis",
                0.9,
                stage="cache_hit",
                cache_hit=True,
                timing_profile={
                    "cache": True,
                    "backend": "cpu-cache",
                    "gpu": "none",
                    "offload": "none",
                    "precision": "fp32",
                    "model": "hdemucs-high+ecapa",
                    "torch": None,
                    "cuda": None,
                    "threads": None,
                    "runtime_mode": "cached-files",
                    "memory_policy": "not-used",
                },
            )
        return item, metadata, recipe, cached

    def validate_segments(self, metadata, assignments):
        baseline = metadata["segments"]
        if len(assignments) != len(baseline):
            raise ValueError("Correction must retain every original timeline segment")
        for original, current in zip(baseline, assignments, strict=True):
            if (
                current.get("start") != original["start"]
                or current.get("end") != original["end"]
                or not re.fullmatch(r"g\d{1,3}", str(current.get("group")))
            ):
                raise ValueError(
                    "Correction can regroup segments but cannot shift the source timeline"
                )

    def prepare_fx(self, item_id, progress, canceled, segments=None):
        item, metadata, recipe, cached = self.cache_context(item_id, progress, canceled)
        segments = segments or recipe.get("segments", metadata["segments"])
        self.validate_segments(metadata, segments)
        groups = metadata["groups"]
        if segments != metadata["segments"]:
            import hashlib

            key = hashlib.sha256(json.dumps(segments, sort_keys=True).encode()).hexdigest()[:20]
            directory = self.asset(metadata["vocals_file"]).parent / "corrections" / key
            directory.mkdir(parents=True, exist_ok=True)
            vocal = self.core.load(self.asset(metadata["vocals_file"]))
            groups = []
            for group_id in sorted({s["group"] for s in segments}):
                filename = directory / (group_id + ".wav")
                if not filename.exists():
                    audio = np.zeros_like(vocal)
                    for segment in segments:
                        if segment["group"] == group_id:
                            audio[segment["start"] : segment["end"]] = vocal[
                                segment["start"] : segment["end"]
                            ]
                    sf.write(filename, audio, self.core.SR, subtype="FLOAT")
                groups.append(
                    {
                        "id": group_id,
                        "name": "Corrected voice group " + group_id[1:],
                        "file": self.relative(filename),
                        "uncertain": True,
                    }
                )
        return {
            "song": item,
            "cache_hit": cached,
            "metadata": metadata,
            "groups": [
                {
                    **group,
                    "audio": self.media(self.asset(group["file"])),
                    "settings": recipe.get("group_settings", {}).get(
                        group["id"], {"normalize": False}
                    ),
                }
                for group in groups
            ],
            "segments": segments,
            "warning": metadata["warning"],
            "vocal_audio": self.media(self.asset(metadata["vocals_file"])),
            "audio": self.media(item["path"]),
        }

    def render_fx(self, values, progress, canceled):
        item, metadata, recipe, _ = self.cache_context(values["song_id"], progress, canceled)
        assignments = values.get("segments", recipe.get("segments", metadata["segments"]))
        baseline = metadata["segments"]
        if len(assignments) != len(baseline):
            raise ValueError("Correction must retain every original timeline segment")
        for original, current in zip(baseline, assignments, strict=True):
            if (
                current.get("start") != original["start"]
                or current.get("end") != original["end"]
                or not re.fullmatch(r"g\d{1,3}", str(current.get("group")))
            ):
                raise ValueError(
                    "Correction can regroup segments but cannot shift the source timeline"
                )
        vocals = self.core.load(self.asset(metadata["vocals_file"]))
        audio = self.core.load(self.asset(metadata["accompaniment_file"]))
        settings = values.get("group_settings", recipe.get("group_settings", {}))
        edited = {}
        progress(
            "Rendering voice groups",
            0,
            stage="rendering",
            units_complete=0,
            units_total=len(assignments),
        )
        for index, segment in enumerate(assignments):
            if canceled():
                raise Canceled("Vocal rendering canceled")
            group = segment["group"]
            start, end = segment["start"], segment["end"]
            part = fixed_effect(
                self.core, vocals[start:end], settings.get(group, {"normalize": False})
            )
            audio[start:end] += part
            if group not in edited:
                edited[group] = np.zeros_like(vocals)
            edited[group][start:end] = part
            progress(
                "Rendering voice groups",
                (index + 1) / len(assignments),
                stage="rendering",
                units_complete=index + 1,
                units_total=len(assignments),
            )
        directory = self.core.LIB / "assets" / "vocal-edits" / uuid.uuid4().hex
        directory.mkdir(parents=True, exist_ok=True)
        progress(
            "Saving edited voice audio",
            0,
            stage="saving",
            units_complete=0,
            units_total=len(edited) + 1,
        )
        for group, stem in edited.items():
            sf.write(directory / (group + ".wav"), stem, self.core.SR, subtype="FLOAT")
        path = directory / "song.wav"
        self.core.save_wav(path, audio)
        progress(
            "Saving edited voice audio",
            1,
            stage="saving",
            units_complete=len(edited) + 1,
            units_total=len(edited) + 1,
        )
        if not values.get("save", True):
            return {"message": "Preview only", "audio": self.media(path)}
        saved_recipe = {
            "op": "vocal-fx-song",
            "source_song_id": metadata["source_song_id"],
            "source_file": metadata["source_file"],
            "cache_key": metadata["cache_key"],
            "accompaniment_file": metadata["accompaniment_file"],
            "creation_recipe": metadata["creation_recipe"],
            "group_settings": settings,
            "segments": assignments,
            "edited_stems": {
                group: self.relative(directory / (group + ".wav")) for group in edited
            },
            "alignment": {
                "sample_rate": self.core.SR,
                "samples": len(audio),
                "stretch": "fixed-slot",
                "tails": "clipped-at-slot-end",
            },
        }
        mode = values.get("mode", "new")
        if mode not in {"new", "update"}:
            raise ValueError("Choose update-current or save-new FX version")
        is_derivative = recipe.get("op") == "vocal-fx-song"
        if mode == "update" and not is_derivative:
            raise ValueError("The original song cannot be overwritten; save a new FX version")
        name = values.get("name") or (
            item["name"] if is_derivative and mode == "update" else item["name"] + "_FX"
        )
        if mode == "new":
            if not re.search(r"_FX(?:_\d+)?$", name):
                name += "_FX"
            existing = {song["name"] for song in self.core.list_items()}
            version, base_name = 2, name
            while name in existing:
                name = base_name + f"_{version}"
                version += 1
        progress(
            "Encoding edited song download", 0, stage="exporting", units_complete=0, units_total=1
        )
        mp3 = self.core.to_mp3(path)
        progress(
            "Encoding edited song download", 1, stage="exporting", units_complete=1, units_total=1
        )
        progress("Saving FX version", 0, stage="saving")
        if mode == "update":
            result = self.core.update_item(
                item["id"], name=name, path=str(path), mp3=mp3, recipe=saved_recipe, is_song=True
            )
        else:
            result = self.core._new_entry(
                "generated",
                name,
                audio,
                "fx:" + metadata["source_song_id"],
                recipe=saved_recipe,
                extra={"is_song": True, "folder": item.get("folder", ""), "mp3": mp3},
            )
        return {
            "message": "Updated FX version" if mode == "update" else "Saved new FX version",
            "song": result,
            "audio": self.media(result["path"]),
            "download": self.media(mp3),
        }
