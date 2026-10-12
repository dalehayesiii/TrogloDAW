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


def generate(request):
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
    parameters = request["parameters"]
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
    emit(
        "encoding",
        device="cuda",
        free_vram=free,
        total_vram=total,
        offload="cpu+dit",
        checkpoint=request["model"],
    )
    params = GenerationParams(
        task_type="cover" if conditioned else "text2music",
        src_audio=request.get("conditioning_audio") if conditioned else None,
        audio_cover_strength=parameters.get("effective_audio_adherence", 1.0)
        if conditioned
        else 1.0,
        caption=parameters["caption"],
        lyrics=parameters["lyrics"],
        instrumental=not bool(parameters["lyrics"].strip()),
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
            "conditioning": "cover" if conditioned else "text2music",
            "audio_cover_strength": params.audio_cover_strength if conditioned else None,
        },
    )


def separate(request):
    import numpy as np
    import soundfile as sf

    torch = import_module("torch")
    torchaudio = import_module("torchaudio")
    EncoderClassifier = import_module("speechbrain.inference.speaker").EncoderClassifier
    LocalStrategy = import_module("speechbrain.utils.fetching").LocalStrategy

    torch.set_num_threads(min(8, os.cpu_count() or 1))
    root = Path(request["root"])
    free, _, memory_policy = gpu_memory(torch)
    device = "cuda" if free >= 2 * 1024**3 else "cpu"
    emit(
        "loading",
        stage_device=device,
        timing_profile={
            **hardware(torch, device),
            "model": "hdemucs-high+ecapa",
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
        elif request["action"] == "separate":
            separate(request)
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
