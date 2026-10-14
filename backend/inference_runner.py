"""Isolated, offline inference process using explicitly installed local dependencies."""

from __future__ import annotations

import json
import inspect
import os
import sys
import time
import textwrap
import shutil
import subprocess
import re
from types import MethodType
from importlib import import_module
from pathlib import Path


def emit(stage, fraction=0, **values):
    print(
        "\nTROGLO_EVENT " + json.dumps({"stage": stage, "fraction": fraction, **values}), flush=True
    )


def adapt_generation(model, conditioned=False):
    """The pinned Base/SFT checkpoint uses an older misspelled CFG argument."""
    original = model.generate_audio
    parameters = inspect.signature(original).parameters
    if "diffusion_guidance_sale" in parameters and "diffusion_guidance_scale" not in parameters:
        if conditioned:
            # The verified pinned checkpoint repeats this switch, doubling CFG tensors
            # again each step. Switch exactly once. Assets and their hashes stay intact.
            source = textwrap.dedent(inspect.getsource(original))
            marker = "if step_idx >= cover_steps:"
            if (
                source.count(marker) != 1
                or "cover_steps = int(infer_steps * audio_cover_strength)" not in source
            ):
                raise RuntimeError("This checkpoint's partial audio conditioning is incompatible.")
            namespace = {}
            exec(
                compile(
                    source.replace(marker, "if step_idx == cover_steps:"),
                    "<verified-checkpoint-cover-adapter>",
                    "exec",
                ),
                original.__func__.__globals__,
                namespace,
            )
            original = MethodType(namespace[original.__name__], model)

        def generate_audio(**values):
            if "diffusion_guidance_scale" in values:
                values["diffusion_guidance_sale"] = values.pop("diffusion_guidance_scale")
            values["use_progress_bar"] = False
            return original(**values)

        model.generate_audio = generate_audio
    elif "diffusion_guidance_scale" not in parameters:
        raise RuntimeError(
            "This checkpoint cannot apply Style Influence; select a supported model."
        )


def gpu_memory(torch):
    """Use driver-wide headroom as well as CUDA's process budget (Windows WDDM)."""
    if not torch.cuda.is_available():
        return 0, 0, "unavailable"
    free, total = torch.cuda.mem_get_info()
    command = shutil.which("nvidia-smi")
    if command:
        try:
            output = subprocess.check_output(
                [
                    command,
                    "--query-gpu=uuid,memory.free,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                text=True,
                timeout=3,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000 if os.name == "nt" else 0,
            )
            rows = [line.split(",") for line in output.strip().splitlines()]
            properties = torch.cuda.get_device_properties(torch.cuda.current_device())
            match = re.search(
                r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}",
                str(getattr(properties, "uuid", "")),
                re.I,
            )
            selected = next(
                (row for row in rows if match and match[0].lower() in row[0].lower()),
                rows[0] if len(rows) == 1 and not match else None,
            )
            if selected is not None:
                driver_free, driver_total = int(selected[1]) * 1024**2, int(selected[2]) * 1024**2
                if 0 <= driver_free <= driver_total and abs(driver_total - total) < 256 * 1024**2:
                    return min(free, driver_free), total, "cuda+driver"
        except (OSError, ValueError, subprocess.SubprocessError, IndexError):
            pass
    return free, total, "cuda"


def hardware(torch, device):
    return {
        "gpu": torch.cuda.get_device_name() if device == "cuda" else "none",
        "backend": device,
        "cpu": import_module("platform").processor(),
        "threads": torch.get_num_threads(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda if device == "cuda" else None,
    }


def align_recording_encoder(handler, torch):
    """Keep the last source samples in the pinned VAE's final complete frame."""
    config = handler.vae.config
    if config.sampling_rate != 48000 or tuple(config.downsampling_ratios) != (2, 4, 4, 6, 10):
        raise RuntimeError("This decoder cannot preserve the complete recording timeline")
    original_encode = handler.tiled_encode
    alignment = {"frame_samples": 1920, "sample_rate": 48000, "padding_samples": 0}

    def encode(audio, *args, **kwargs):
        padding = (-audio.shape[-1]) % alignment["frame_samples"]
        if padding:
            audio = torch.nn.functional.pad(audio, (0, padding))
            alignment["padding_samples"] = max(alignment["padding_samples"], padding)
        return original_encode(audio, *args, **kwargs)

    handler.tiled_encode = encode
    return alignment


def trim_recording_padding(first, parameters, conditioned, source_audio=None):
    if not conditioned or parameters.get("workflow") != "recording-style":
        return 0
    # The pinned decoder pads short sources to 5.12 seconds. Remove only its
    # generated tail so the result retains the complete original timeline.
    sf = import_module("soundfile")
    audio, sample_rate = sf.read(first["path"], dtype="float32", always_2d=True)
    if source_audio:
        source = sf.info(source_audio)
        expected = round(source.frames * sample_rate / source.samplerate)
    else:
        expected = round(parameters["duration"] * sample_rate)
    if len(audio) < expected:
        raise RuntimeError("The model did not render the complete recording timeline")
    trimmed = len(audio) - expected
    if trimmed:
        sf.write(first["path"], audio[:expected], sample_rate, subtype="FLOAT")
    return trimmed


def generate(request):
    parameters = request["parameters"]
    blueprint_codes = request.get("blueprint_codes")
    if blueprint_codes:
        if request.get("conditioning_audio") or parameters.get("effective_mode") == "conditioned":
            raise ValueError("A text blueprint cannot replace an active source recording")
        raise ValueError("Semantic-code blueprints are not qualified for this runtime")
    blueprint = request.get("blueprint_metadata")
    if blueprint:
        if request.get("conditioning_audio") or parameters.get("effective_mode") == "conditioned":
            raise ValueError("A text blueprint cannot replace an active source recording")
        from planning import validated_blueprint

        blueprint = validated_blueprint({"metadata": blueprint}, parameters)["constraints"]
    if import_module("psutil").virtual_memory().available < 12 * 1024**3:
        raise RuntimeError(
            "This offload configuration needs 12 GiB of available system RAM. Close memory-heavy apps and retry."
        )
    torch = import_module("torch")
    AceStepHandler = import_module("acestep.handler").AceStepHandler
    inference = import_module("acestep.inference")
    GenerationConfig, GenerationParams, generate_music = (
        inference.GenerationConfig,
        inference.GenerationParams,
        inference.generate_music,
    )

    free, total, memory_policy = gpu_memory(torch)
    if not torch.cuda.is_available() or free < 5.5 * 1024**3:
        raise RuntimeError(
            "This model needs at least 5.5 GiB free CUDA memory for the validated offload configuration. Close GPU-heavy apps and retry."
        )
    context = {
        **hardware(torch, "cuda"),
        "offload": "cpu+dit",
        "quantization": "none",
        "precision": "bf16",
        "runtime_mode": "fresh_process",
        "memory_policy": memory_policy,
    }
    emit("loading", timing_profile=context, stage_device="cuda")
    handler = AceStepHandler()
    # Acquisition is exclusively handled by explicit setup. No upstream auto-download/code rewrite.
    handler._ensure_models_present = lambda **_: None
    handler._sync_model_code_if_needed = lambda *_: None
    status, success = handler.initialize_service(
        project_root=request["root"],
        config_path=request["model"],
        device="cuda",
        use_flash_attention=False,
        compile_model=False,
        offload_to_cpu=True,
        offload_dit_to_cpu=True,
        quantization=None,
        use_mlx_dit=False,
    )
    if not success:
        raise RuntimeError(status)
    conditioned = parameters.get("effective_mode") == "conditioned"
    adapt_generation(handler.model, conditioned=conditioned)
    recording_alignment = (
        align_recording_encoder(handler, torch)
        if conditioned and parameters.get("workflow") == "recording-style"
        else None
    )
    emit(
        "encoding",
        device="cuda",
        free_vram=free,
        total_vram=total,
        offload="cpu+dit",
        checkpoint=request["model"],
    )
    params = GenerationParams(
        task_type="cover-nofsq"
        if conditioned and parameters.get("workflow") == "recording-style"
        else "cover"
        if conditioned
        else "text2music",
        src_audio=request.get("conditioning_audio") if conditioned else None,
        audio_codes="",
        bpm=blueprint["bpm"] if blueprint else None,
        keyscale=blueprint["keyscale"] if blueprint else "",
        timesignature=blueprint["timesignature"] if blueprint else "",
        audio_cover_strength=parameters.get("effective_audio_adherence", 1.0)
        if conditioned
        else 1.0,
        caption=parameters["caption"],
        lyrics=parameters["lyrics"],
        instrumental=parameters.get("instrumental", not bool(parameters["lyrics"].strip())),
        duration=parameters["duration"],
        seed=parameters["seed"],
        inference_steps=parameters["steps"],
        guidance_scale=parameters["guidance"],
        shift=parameters["shift"],
        infer_method=parameters["method"],
        thinking=False,
        use_cot_metas=False,
        use_cot_caption=False,
        use_cot_language=False,
        use_cot_lyrics=False,
    )

    completed = 0

    def before_step(_module, _inputs):
        if completed == 0:
            emit(
                "generating", units_complete=0, units_total=parameters["steps"], stage_device="cuda"
            )

    def diffusion_step(_module, _inputs, _output):
        nonlocal completed
        torch.cuda.synchronize()
        completed += 1
        emit(
            "generating",
            min(0.99, completed / parameters["steps"]),
            units_complete=completed,
            units_total=parameters["steps"],
            stage_device="cuda",
        )
        if completed >= parameters["steps"]:
            emit("finalizing_music", message="Finalizing generated music", stage_device="cuda")

    pre_hook = handler.model.decoder.register_forward_pre_hook(before_step)
    hook = handler.model.decoder.register_forward_hook(diffusion_step)
    original_decode = handler.tiled_decode

    def decode(*args, **kwargs):
        emit("decoding", units_complete=0, units_total=1, stage_device="cuda")
        audio = original_decode(*args, **kwargs)
        torch.cuda.synchronize()
        emit("decoding", units_complete=1, units_total=1, stage_device="cuda")
        return audio

    handler.tiled_decode = decode

    started = time.monotonic()
    result = generate_music(
        handler,
        None,
        params,
        GenerationConfig(
            batch_size=1, use_random_seed=False, seeds=[parameters["seed"]], audio_format="wav32"
        ),
        save_dir=request["output"],
        # The upstream timer callback guesses fractions; use actual forward calls.
        progress=lambda *_args, **_kwargs: None,
    )
    hook.remove()
    pre_hook.remove()
    if not result.success or not result.audios:
        raise RuntimeError(result.error or "Music inference produced no audio")
    first = result.audios[0]
    trimmed_padding = trim_recording_padding(
        first, parameters, conditioned, request.get("conditioning_audio")
    )
    emit(
        "complete",
        1,
        result={
            "audio": first["path"],
            "sample_rate": first.get("sample_rate", 48000),
            "parameters": {**parameters, "task_type": params.task_type},
            "seconds": time.monotonic() - started,
            "peak_vram": torch.cuda.max_memory_allocated(),
            "device": "cuda",
            "offload": "cpu+dit",
            "trimmed_padding_samples": trimmed_padding,
            **({"recording_alignment": recording_alignment} if recording_alignment else {}),
            "conditioning": params.task_type
            if conditioned
            else "musical_metadata"
            if blueprint
            else "text2music",
            "audio_cover_strength": params.audio_cover_strength if conditioned else None,
        },
    )


def last_token_logits(model):
    """Use the supported inference-only Qwen argument to avoid full-prefill logits."""
    if "logits_to_keep" not in inspect.signature(model.forward).parameters:
        return None

    def before_forward(_module, inputs, values):
        return inputs, {**values, "logits_to_keep": 1}

    return model.register_forward_pre_hook(before_forward, with_kwargs=True)


def write_lyrics(request):
    """Use an explicitly installed instruction model without remote code or APIs."""
    torch = import_module("torch")
    transformers = import_module("transformers")
    torch.set_num_threads(8)
    torch.manual_seed(request["seed"])
    free, _total, policy = gpu_memory(torch)
    if not torch.cuda.is_available() or free < 2 * 1024**3:
        raise RuntimeError(
            "Local lyric writing needs 2 GiB of free CUDA memory. Close GPU-heavy apps and retry."
        )
    if import_module("psutil").virtual_memory().available < 3 * 1024**3:
        raise RuntimeError("Local lyric writing needs 3 GiB of available system RAM.")
    if request.get("lyric_writer") != "Qwen3-0.6B-lyrics":
        raise ValueError("This model has no supported local lyric writer")
    emit(
        "loading_planner",
        message="Loading local lyric writer",
        stage_device="cuda",
        timing_profile={
            **hardware(torch, "cuda"),
            "planner": request["lyric_writer"],
            "runtime_mode": "fresh_process",
            "memory_policy": policy,
            "planning_mode": "instruction-lyrics-v1",
        },
    )
    path = str(Path(request["root"]) / "checkpoints" / request["lyric_writer"])
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        path, local_files_only=True, trust_remote_code=False
    )
    model = (
        transformers.AutoModelForCausalLM.from_pretrained(
            path, local_files_only=True, trust_remote_code=False, dtype=torch.bfloat16
        )
        .to("cuda")
        .eval()
    )
    messages = [
        {
            "role": "system",
            "content": "Write song lyrics following the requested idea and language. Return only singable lyrics with [Verse] and [Chorus] section labels. Keep the complete draft under 350 words. Do not include commentary.",
        },
        {
            "role": "user",
            "content": f"Language: {request['language']}\nSong idea: {request['prompt']}",
        },
    ]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    inputs = tokenizer(text, return_tensors="pt").to("cuda")
    passes = 0

    def decoded(_module, _inputs, _output):
        nonlocal passes
        passes += 1
        if passes == 1 or passes % 16 == 0:
            emit(
                "writing_lyrics",
                message=f"Writing lyrics locally · {passes} decode steps",
                planner_decode_steps=passes,
                stage_device="cuda",
            )

    hook = model.register_forward_hook(decoded)
    started = time.monotonic()
    try:
        with torch.inference_mode():
            output = model.generate(
                **inputs, max_new_tokens=768, do_sample=True, temperature=0.7, top_p=0.8, top_k=20
            )
        if int(output[0][-1]) != tokenizer.eos_token_id:
            raise RuntimeError(
                "The lyric writer reached its draft limit. Request a shorter song idea and retry."
            )
        lyrics = tokenizer.decode(
            output[0][inputs.input_ids.shape[1] :], skip_special_tokens=True
        ).strip()
        emit(
            "complete",
            1,
            result={
                "lyrics": lyrics,
                "planner": request["lyric_writer"],
                "writer_revision": request.get("writer_revision"),
                "runtime_revision": request.get("runtime_revision"),
                "decode_steps": passes,
                "seconds": time.monotonic() - started,
                "peak_vram": torch.cuda.max_memory_allocated(),
            },
        )
    finally:
        hook.remove()


def plan_song(request, *, blueprint=False):
    """Use ACE's public local planner before loading any music-generation weights."""
    torch = import_module("torch")
    torch.set_num_threads(8)
    torch.manual_seed(request["parameters"]["seed"])
    free, _total, policy = gpu_memory(torch)
    if not torch.cuda.is_available() or free < 4.5 * 1024**3:
        raise RuntimeError(
            "The local song planner needs 4.5 GiB of free CUDA memory. Close GPU-heavy apps and retry."
        )
    if import_module("psutil").virtual_memory().available < 6 * 1024**3:
        raise RuntimeError("The local song planner needs 6 GiB of available system RAM.")
    if request.get("planner") != "acestep-5Hz-lm-1.7B":
        raise ValueError("This model has no supported local song planner")
    context = {
        **hardware(torch, "cuda"),
        "planner": request["planner"],
        "runtime_mode": "fresh_process",
        "memory_policy": policy,
        "planning_mode": "musical-metadata-last-logit-v1"
        if blueprint
        else "metadata-only-last-logit-v1",
    }
    emit(
        "loading_planner",
        timing_profile=context,
        stage_device="cuda",
        message="Loading local song planner",
    )
    handler = import_module("acestep.llm_inference").LLMHandler()
    status, success = handler.initialize(
        checkpoint_dir=str(Path(request["root"]) / "checkpoints"),
        lm_model_path=request["planner"],
        backend="pt",
        device="cuda",
        dtype=torch.bfloat16,
        offload_to_cpu=True,
    )
    if not success:
        raise RuntimeError(status)
    handler.disable_tqdm = True
    # This process only plans text/metadata; DiT is loaded after it exits.
    handler.constrained_processor.set_max_duration(300)
    stage = "planning_blueprint" if blueprint else "planning_song"
    message = "Planning musical structure locally" if blueprint else "Planning song length locally"
    passes = 0

    def decoded(_module, _inputs, _output):
        nonlocal passes
        passes += 1
        if passes == 1 or passes % 16 == 0:
            emit(
                stage,
                message=f"{message} · {passes} decode steps",
                planner_decode_steps=passes,
                stage_device="cuda",
            )

    emit(stage, message=message, stage_device="cuda")
    hook = handler.llm.register_forward_hook(decoded)
    logits_hook = last_token_logits(handler.llm)
    started = time.monotonic()
    try:
        parameters = request["parameters"]
        if blueprint:
            from planning import explicit_music_metadata

            result = handler.generate_with_stop_condition(
                caption=parameters["caption"],
                lyrics=parameters["lyrics"],
                infer_type="dit",
                target_duration=parameters["duration"],
                user_metadata=explicit_music_metadata(parameters),
                temperature=0.85,
                cfg_scale=1.0,
                use_cot_metas=True,
                use_cot_caption=False,
                use_cot_language=False,
            )
            if not result.get("success"):
                raise RuntimeError(result.get("error") or "Musical blueprint generation failed")
            emit(
                "complete",
                1,
                result={
                    "planner": request["planner"],
                    "runtime_revision": request.get("runtime_revision"),
                    "metadata": result.get("metadata", {}),
                    "decode_steps": passes,
                    "seconds": time.monotonic() - started,
                    "peak_vram": torch.cuda.max_memory_allocated(),
                },
            )
            return
        prompt = handler.build_formatted_prompt_for_format(
            parameters["caption"], parameters["lyrics"]
        )
        text, status = handler.generate_from_formatted_prompt(
            formatted_prompt=prompt,
            cfg={
                "temperature": 0.85,
                "top_k": None,
                "top_p": None,
                "repetition_penalty": 1.0,
                "target_duration": None,
                "user_metadata": None,
                "skip_caption": False,
                "skip_language": False,
                "skip_genres": False,
                "generation_phase": "understand",
                "caption": "",
                "lyrics": "",
            },
            use_constrained_decoding=True,
            stop_at_reasoning=True,
        )
        if not text:
            raise RuntimeError(status or "Local metadata planning failed")
        metadata, _codes = handler.parse_lm_output(text)
        from types import SimpleNamespace

        result = SimpleNamespace(
            success=True,
            lyrics=parameters["lyrics"],
            duration=metadata.get("duration"),
            bpm=metadata.get("bpm"),
            keyscale=metadata.get("keyscale", ""),
            language=metadata.get("language", ""),
            timesignature=metadata.get("timesignature", ""),
            caption=metadata.get("caption", ""),
        )
        if not result.success:
            raise RuntimeError(result.error or "Local song planning failed")
        emit(
            "complete",
            1,
            result={
                "planner": request["planner"],
                "runtime_revision": request.get("runtime_revision"),
                "lyrics": result.lyrics,
                "duration": result.duration,
                "bpm": result.bpm,
                "keyscale": result.keyscale,
                "language": result.language,
                "timesignature": result.timesignature,
                "suggested_caption": result.caption,
                "decode_steps": passes,
                "seconds": time.monotonic() - started,
                "peak_vram": torch.cuda.max_memory_allocated(),
            },
        )
    finally:
        hook.remove()
        if logits_hook:
            logits_hook.remove()


def separate(request):
    import numpy as np
    import soundfile as sf

    torch = import_module("torch")
    torchaudio = import_module("torchaudio")

    torch.set_num_threads(min(8, os.cpu_count() or 1))
    root = Path(request["root"])
    free, _, memory_policy = gpu_memory(torch)
    device = "cuda" if free >= 2 * 1024**3 else "cpu"
    emit(
        "loading",
        stage_device=device,
        timing_profile={
            **hardware(torch, device),
            "model": "hdemucs-high" if request.get("reference_only") else "hdemucs-high+ecapa",
            "offload": "none",
            "precision": "fp32",
            "quantization": "none",
            "runtime_mode": "fresh_process",
            "cache": False,
            "memory_policy": memory_policy,
        },
    )
    model = torchaudio.models.hdemucs_high(sources=["drums", "bass", "other", "vocals"])
    state = torch.load(
        root / "separation" / "hdemucs_high_trained.pt", map_location="cpu", weights_only=True
    )
    model.load_state_dict(state)
    model.to(device).eval()
    audio, sr = sf.read(request["audio"], dtype="float32", always_2d=True)
    if sr != 44100 or audio.shape[1] != 2:
        raise ValueError("Editing requires normalized 44.1 kHz stereo library audio")
    waveform = torch.from_numpy(audio.T.copy())
    length = waveform.shape[-1]
    chunk, overlap = 8 * sr, sr
    vocals = torch.zeros((2, length))
    weights = torch.zeros(length)
    starts = list(range(0, length, chunk - overlap))
    emit("separating", units_complete=0, units_total=len(starts), stage_device=device)
    with torch.inference_mode():
        for index, start in enumerate(starts):
            end = min(length, start + chunk)
            part = waveform[:, start:end]
            mean, std = part.mean(), part.std().clamp_min(1e-5)
            normalized = (part - mean) / std
            padded = torch.nn.functional.pad(normalized, (0, max(0, chunk - normalized.shape[-1])))
            result = model(padded[None].to(device))[0, 3, :, : end - start].cpu() * std + mean
            window = torch.ones(end - start)
            fade = min(overlap, len(window))
            if start:
                window[:fade] *= torch.linspace(0.001, 1, fade)
            if end != length:
                window[-fade:] *= torch.linspace(1, 0.001, fade)
            vocals[:, start:end] += result * window
            weights[start:end] += window
            emit(
                "separating",
                (index + 1) / len(starts),
                units_complete=index + 1,
                units_total=len(starts),
                device=device,
            )
    vocals /= weights.clamp_min(1e-9)
    model.to("cpu")
    del model
    if device == "cuda":
        torch.cuda.empty_cache()
    output = Path(request["output"])
    output.mkdir(parents=True, exist_ok=True)
    sf.write(output / "vocals.wav", vocals.T.numpy(), sr, subtype="FLOAT")
    # Retain the exact residual; bypass reconstruction is sample-aligned by construction.
    sf.write(output / "accompaniment.wav", audio - vocals.T.numpy(), sr, subtype="FLOAT")
    if request.get("reference_only"):
        emit("complete", 1, result={"samples": length, "sample_rate": sr})
        return
    EncoderClassifier = import_module("speechbrain.inference.speaker").EncoderClassifier
    LocalStrategy = import_module("speechbrain.utils.fetching").LocalStrategy
    emit("loading_voices", stage_device="cpu")
    speaker = root / "speaker"
    # Load verified local hparams directly: from_hparams also tries an absent custom.py.
    with (speaker / "hyperparams.yaml").open(encoding="utf-8") as stream:
        hparams = import_module("hyperpyyaml").load_hyperpyyaml(
            stream, {"pretrained_path": speaker.as_posix()}
        )
    hparams["savedir"] = str(Path(os.environ["HF_HOME"]).parent / "speaker")
    hparams["pretrainer"].set_collect_in(hparams["savedir"])
    hparams["pretrainer"].collect_files(
        default_source=speaker.as_posix(), local_strategy=LocalStrategy.COPY
    )
    hparams["pretrainer"].load_collected()
    classifier = EncoderClassifier(hparams["modules"], hparams, run_opts={"device": "cpu"})
    mono = torchaudio.functional.resample(vocals.mean(dim=0), sr, 16000)
    centroids, counts, groups, segments = [], [], [], []
    slot = 3 * sr
    count = (length + slot - 1) // slot
    emit("identifying", units_complete=0, units_total=count, stage_device="cpu")
    with torch.inference_mode():
        for index, start in enumerate(range(0, length, slot)):
            end = min(length, start + slot)
            fragment = mono[int(start * 16000 / sr) : int(end * 16000 / sr)]
            if fragment.numel() < 8000 or fragment.square().mean().sqrt() < 0.004:
                group, similarity = 0, None
            else:
                embedding = classifier.encode_batch(fragment[None]).reshape(-1)
                embedding = torch.nn.functional.normalize(embedding, dim=0)
                similarities = [float(torch.dot(embedding, c)) for c in centroids]
                best = (
                    max(range(len(similarities)), key=lambda i: similarities[i])
                    if similarities
                    else -1
                )
                similarity = similarities[best] if best >= 0 else 0
                if best >= 0 and similarity >= 0.78:
                    group = best + 1
                    counts[best] += 1
                    centroids[best] = torch.nn.functional.normalize(
                        centroids[best] * (counts[best] - 1) + embedding, dim=0
                    )
                elif len(centroids) < 4:
                    centroids.append(embedding)
                    counts.append(1)
                    group = len(centroids)
                else:
                    group = 0
            segments.append(
                {
                    "start": start,
                    "end": end,
                    "group": f"g{group}",
                    "similarity": similarity,
                    "uncertain": True,
                }
            )
            emit(
                "identifying",
                (index + 1) / count,
                units_complete=index + 1,
                units_total=count,
                device="cpu",
            )
    for identifier in sorted({s["group"] for s in segments}):
        ranges = [
            {"start": s["start"], "end": s["end"]} for s in segments if s["group"] == identifier
        ]
        group_audio = np.zeros_like(audio)
        for segment in ranges:
            group_audio[segment["start"] : segment["end"]] = vocals[
                :, segment["start"] : segment["end"]
            ].T.numpy()
        filename = identifier + ".wav"
        sf.write(output / filename, group_audio, sr, subtype="FLOAT")
        groups.append(
            {
                "id": identifier,
                "name": "Uncertain / shared vocals"
                if identifier == "g0"
                else "Candidate voice " + identifier[1:],
                "file": filename,
                "segments": ranges,
                "uncertain": True,
            }
        )
    emit(
        "complete",
        1,
        result={
            "groups": groups,
            "segments": segments,
            "sample_rate": sr,
            "samples": length,
            "device": device,
            "peak_vram": torch.cuda.max_memory_allocated() if device == "cuda" else 0,
            "warning": "Voice candidates use speech embeddings. Singing, leakage and overlapping voices may stay together or need regrouping; review each segment.",
        },
    )


def analyze_phrases(request):
    """Run the explicitly installed detector on CPU, without music-model loading."""
    from phrase_analysis import ANALYSIS_RATE, WINDOW_SAMPLES, probability_spans

    torch = import_module("torch")
    np = import_module("numpy")
    sf = import_module("soundfile")
    signal = import_module("scipy.signal")
    torch.set_num_threads(1)
    emit("loading_phrases", stage_device="cpu", message="Loading local CPU phrase detector")
    detector = torch.jit.load(request["speech_model"], map_location="cpu").eval()
    source, sr = sf.read(request["audio"], dtype="float32", always_2d=True)
    # Parent already chooses phase-safe analysis channels. This never changes saved audio.
    mono = source.mean(axis=1)
    mono = mono - np.median(mono)
    reference = float(np.percentile(np.abs(mono), 95))
    gain = 0.2 / reference if reference > 1e-8 else 1.0
    mono = np.clip(mono * gain, -1, 1).astype(np.float32)
    divisor = import_module("math").gcd(sr, ANALYSIS_RATE)
    audio = signal.resample_poly(mono, ANALYSIS_RATE // divisor, sr // divisor).astype(np.float32)
    detector.reset_states()
    total = (len(audio) + WINDOW_SAMPLES - 1) // WINDOW_SAMPLES
    scores = []
    with torch.inference_mode():
        for index in range(total):
            start = index * WINDOW_SAMPLES
            window = audio[start : start + WINDOW_SAMPLES]
            window = np.pad(window, (0, WINDOW_SAMPLES - len(window)))
            scores.append(float(detector(torch.from_numpy(window), ANALYSIS_RATE)))
            if index % 32 == 0 or index + 1 == total:
                emit(
                    "analyzing_phrases",
                    units_complete=index + 1,
                    units_total=total,
                    stage_device="cpu",
                    message="Identifying complete vocal phrases",
                )
    evidence = probability_spans(scores, len(source), sr)
    emit("complete", 1, result={**evidence, "analysis_gain": gain, "device": "cpu"})


def main():
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    sys.path.insert(0, request["packages"])
    if request.get("code"):
        sys.path.insert(0, request["code"])
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        if request["action"] == "generate":
            generate(request)
        elif request["action"] == "write_lyrics":
            write_lyrics(request)
        elif request["action"] == "plan_song":
            plan_song(request)
        elif request["action"] == "plan_blueprint":
            plan_song(request, blueprint=True)
        elif request["action"] == "separate":
            separate(request)
        elif request["action"] == "analyze_phrases":
            analyze_phrases(request)
        elif request["action"] == "probe":
            for module in (
                "acestep.handler",
                "acestep.inference",
                "torchaudio",
                "speechbrain.inference.speaker",
            ):
                import_module(module)
            torch = import_module("torch")
            emit("complete", 1, result={"cuda_available": torch.cuda.is_available()})
        else:
            raise ValueError("Unsupported inference action")
    except Exception as exc:
        import traceback

        traceback.print_exc()
        emit("failed", error=str(exc))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
