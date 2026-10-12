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
from pathlib import Path

import numpy as np
import soundfile as sf

from arrangement import phase_safe_audio, positions, sample_transform, select_regions
from models import CREATE_FLAGS, ROOT, Canceled, cache_environment, runtime_signature
from storage import atomic_json, digest, safe_file, writable_root

PRESET = {
    "version": "prior-song-v1",
    "sample_seconds": 1.0,
    "samples": 8,
    "pitch": 2.0,
    "stretch": 1.1,
    "gain": -12.0,
}
CLIP_DEFAULTS = {"sample_seconds": 2.0, "samples": 8, "pitch": 0.0, "stretch": 1.0, "gain": -6.0}
OPTIONS = {"gender": "", "duration": "auto", "weirdness": 50, "influence": 50, "variety": 0}


def song_item(item):
    return item.get("is_song", False) or item["type"] in {"generated", "mix"}


def generation_mode(draft, models, has_samples):
    requested = draft.get("audio_mode", "conditioned")
    if requested not in {"conditioned", "postmix"}:
        raise ValueError("Choose audio-conditioned generation or post-generation sample mixing")
    adherence = draft.get("audio_adherence", 75)
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


def generation_parameters(draft: dict, sources: list[dict], seed: int):
    options: dict = {**OPTIONS, **draft.get("options", {})}
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
    if options["duration"] == "auto":
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
    if not math.isfinite(duration) or not 10 <= duration <= 120:
        raise ValueError(
            "This configuration supports 10–120 seconds. Choose a duration in that range"
        )
    effective_styles = styles
    rng = random.Random(seed)
    if options["variety"]:
        variations = [
            "sparse opening",
            "syncopated transitions",
            "rising final chorus",
            "warm acoustic accents",
            "spacious breaks",
            "restrained bridge",
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
        "duration": duration,
        "seed": seed,
        "steps": 32,
        "guidance": 1 + options["influence"] * 0.14,
        "shift": 1 + options["weirdness"] * 0.04,
        "method": "sde" if options["weirdness"] > 50 else "ode",
        "original_styles": styles,
        "effective_styles": effective_styles,
        "requested": options,
        "duration_derivation": derivation,
    }


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
            **values,
        }
        request_file = root / "cache" / (uuid.uuid4().hex + ".json")
        env = cache_environment(root, self.models.storage.preferences["installation_id"])
        env["HF_HUB_OFFLINE"] = env["TRANSFORMERS_OFFLINE"] = "1"
        atomic_json(request_file, request)
        result = None
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
                while process.poll() is None or not lines.empty():
                    if canceled():
                        process.terminate()
                        process.wait(timeout=15)
                        raise Canceled("Processing canceled; completed songs are preserved")
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
            if prior and clip.get("preset") not in {"apply", "keep"}:
                raise ValueError(
                    "Choose recommended prior-song defaults or keep settings for each prior song"
                )
            settings = {
                **CLIP_DEFAULTS,
                **(PRESET if prior and clip.get("preset") == "apply" else {}),
                **{
                    key: value
                    for key, value in clip.get("settings", {}).items()
                    if value is not None
                },
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
            sources.append(
                {
                    "id": item["id"],
                    "label": clip.get("label", item["name"]),
                    "source_type": "prior-song" if prior else item.get("source_type", "upload"),
                    "lineage": item_recipe.get("source_song_id")
                    if isinstance(item_recipe, dict)
                    else None,
                    "duration": item["duration"],
                    "preset": clip.get("preset"),
                    "preset_version": PRESET["version"] if prior else None,
                    "settings": settings,
                    "saved_file": saved,
                }
            )
        return sources

    def arrange(self, sources, directory, parameters, progress, canceled=lambda: False):
        layer = np.zeros((round(parameters["duration"] * self.core.SR), 2), np.float32)
        assets, placements, analyses = [], [], []
        rng = random.Random(parameters["seed"])
        source_samples, tempos = [], []
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
            progress(
                "Analyzing input audio",
                0,
                stage="analyzing",
                units_complete=0,
                units_total=1,
                timing_stage_profile={
                    "source_index": source_index,
                    "source_seconds": source["duration"],
                },
            )
            audio, channel_strategy = phase_safe_audio(audio)
            analysis = self.core.analyze_vocal(audio)
            regions, budget = select_regions(audio, self.core.SR, source["settings"], analysis)
            progress("Analyzed input audio", 1, stage="analyzing", units_complete=1, units_total=1)
            analyses.append({"source_id": source["id"], "analysis": analysis, "selection": budget})
            analyses[-1]["channel_strategy"] = channel_strategy
            if analysis.get("tempo_confidence", 0) >= 0.25 and analysis.get("tempo_raw"):
                tempos.append(float(analysis["tempo_raw"]))
            transformed_samples = []
            progress(
                "Transforming source samples",
                0,
                stage="sampling",
                units_complete=0,
                units_total=len(regions),
                timing_stage_profile={"source_index": source_index, "sample_budget": len(regions)},
            )
            for index, region in enumerate(regions):
                if canceled():
                    raise Canceled("Sample transformation canceled")
                fragment = audio[region["start"] : region["end"]].copy()
                fx = sample_transform(source["settings"], region, index, rng)
                transformed = self.core.fade(self.core.apply_fx(fragment, fx), 0.01, 0.03)
                filename = directory / "samples" / f"{source_index}-{index}.wav"
                filename.parent.mkdir(exist_ok=True)
                sf.write(filename, transformed, self.core.SR, subtype="FLOAT")
                identifier = f"s{source_index}-{index}"
                assets.append(
                    {
                        "id": identifier,
                        "source_id": source["id"],
                        "file": self.relative(filename),
                        "source_start": region["start"],
                        "source_end": region["end"],
                        "selection": region,
                        "transformation": fx,
                    }
                )
                transformed_samples.append((identifier, transformed))
                progress(
                    "Transforming source samples",
                    (index + 1) / len(regions),
                    stage="sampling",
                    source=source_index + 1,
                    sources_total=len(sources),
                    units_complete=index + 1,
                    units_total=len(regions),
                )
            source_samples.append(transformed_samples)
        bpm = min(180, max(60, float(np.median(tempos)) if tempos else 90))
        progress(
            "Arranging transformed samples",
            0,
            stage="planning",
            units_complete=0,
            units_total=len(source_samples),
        )
        for source_index, transformed_samples in enumerate(source_samples):
            for index, position, gain in positions(
                len(transformed_samples), source_index, len(sources), len(layer), self.core.SR, bpm
            ):
                if canceled():
                    raise Canceled("Sample arrangement canceled")
                identifier, transformed = transformed_samples[index]
                length = min(len(layer) - position, len(transformed))
                layer[position : position + length] += transformed[:length] * gain
                placements.append(
                    {
                        "sample_id": identifier,
                        "offset_samples": position,
                        "length_samples": length,
                        "gain": gain,
                    }
                )
            progress(
                "Arranging transformed samples",
                (source_index + 1) / len(source_samples),
                stage="planning",
                units_complete=source_index + 1,
                units_total=len(source_samples),
            )
        peak = float(np.max(np.abs(layer), initial=0))
        if peak > 0.8:
            gain = 0.8 / peak
            layer *= gain
            for placement in placements:
                placement["gain"] *= gain
        for analysis in analyses:
            analysis["arrangement"] = {
                "method": "shared-grid-recurring-motifs-v1",
                "bpm": bpm,
                "tempo_source": "detected" if tempos else "fallback",
            }
        return layer, assets, placements, analyses

    def generate(self, draft, progress, canceled):
        if self.local_inference and not self.models.ready():
            raise ValueError("Install or verify a music model in Settings before this operation")
        count = draft.get("count", 1)
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 32:
            raise ValueError("Number of Generations must be an integer between 1 and 32")
        sources = self.collect_sources(draft)
        estimate = count * (
            sum(
                source["duration"]
                + min(source["duration"], float(source["settings"]["sample_seconds"]))
                * int(source["settings"]["samples"])
                * 2
                for source in sources
            )
            * self.core.SR
            * 8
            + 120 * self.core.SR * 32
        )
        writable_root(str(self.core.LIB), int(estimate) + 64 * 1024 * 1024)
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
                layer, samples, placements, analyses = self.arrange(
                    current_sources, directory, parameters, item_progress, canceled
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
                mode = generation_mode(draft, self.models, bool(samples))
                parameters.update(mode)
                arrangement_file = directory / "sample-arrangement.wav"
                sf.write(arrangement_file, layer, self.core.SR, subtype="FLOAT")
                if mode["fallback_reason"]:
                    item_progress(mode["fallback_reason"], 0, stage="conditioning_fallback")
                inferred = self.invoke(
                    "generate",
                    {
                        "parameters": parameters,
                        "output": str(directory / "generated"),
                        "conditioning_audio": str(arrangement_file)
                        if mode["effective_mode"] == "conditioned"
                        else None,
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
                    "render_mode": mode["effective_mode"],
                    "conditioning_file": self.relative(arrangement_file),
                    "draft": {
                        **copy.deepcopy(draft),
                        "audio_mode": mode["requested_mode"],
                        "audio_adherence": mode["audio_adherence"],
                        "clips": [
                            {k: v for k, v in c.items() if k not in {"audio", "key"}}
                            for c in draft.get("clips", [])
                        ],
                    },
                    "sources": current_sources,
                    "samples": samples,
                    "placements": placements,
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
                        "arrangement_audio": self.media(arrangement_file) if samples else None,
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
            "styles",
            "lyrics",
            "title",
            "options",
            "clips",
            "audio_mode",
            "audio_adherence",
        ):
            if key in draft:
                available[key] = copy.deepcopy(draft[key])
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
