"""Isolated, offline inference process using explicitly installed local dependencies."""

from __future__ import annotations

import json
import inspect
import os
import sys
import time
from importlib import import_module
from pathlib import Path


def emit(stage, fraction=0, **values):
    print(
        "TROGLO_EVENT " + json.dumps({"stage": stage, "fraction": fraction, **values}), flush=True
    )


def adapt_generation(model):
    """The pinned Base/SFT checkpoint uses an older misspelled CFG argument."""
    original = model.generate_audio
    parameters = inspect.signature(original).parameters
    if "diffusion_guidance_sale" in parameters and "diffusion_guidance_scale" not in parameters:

        def generate_audio(**values):
            if "diffusion_guidance_scale" in values:
                values["diffusion_guidance_sale"] = values.pop("diffusion_guidance_scale")
            return original(**values)

        model.generate_audio = generate_audio
    elif "diffusion_guidance_scale" not in parameters:
        raise RuntimeError(
            "This checkpoint cannot apply Style Influence; select a supported model."
        )


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

    emit("loading")
    free, total = torch.cuda.mem_get_info() if torch.cuda.is_available() else (0, 0)
    if not torch.cuda.is_available() or free < 5.5 * 1024**3:
        raise RuntimeError(
            "This model needs at least 5.5 GiB free CUDA memory for the validated offload configuration. Close GPU-heavy apps and retry."
        )
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
    adapt_generation(handler.model)
    emit(
        "generating",
        device="cuda",
        free_vram=free,
        total_vram=total,
        offload="cpu+dit",
        checkpoint=request["model"],
    )
    parameters = request["parameters"]
    params = GenerationParams(
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

    def progress(fraction, desc="", **_):
        emit("generating", min(0.99, max(0, float(fraction))), message=desc)

    started = time.monotonic()
    result = generate_music(
        handler,
        None,
        params,
        GenerationConfig(
            batch_size=1, use_random_seed=False, seeds=[parameters["seed"]], audio_format="wav32"
        ),
        save_dir=request["output"],
        progress=progress,
    )
    if not result.success or not result.audios:
        raise RuntimeError(result.error or "Music inference produced no audio")
    first = result.audios[0]
    emit(
        "complete",
        1,
        result={
            "audio": first["path"],
            "sample_rate": first.get("sample_rate", 48000),
            "parameters": first.get("params", {}),
            "seconds": time.monotonic() - started,
            "peak_vram": torch.cuda.max_memory_allocated(),
            "device": "cuda",
            "offload": "cpu+dit",
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
    emit("loading")
    free = torch.cuda.mem_get_info()[0] if torch.cuda.is_available() else 0
    device = "cuda" if free >= 2 * 1024**3 else "cpu"
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
    emit("identifying")
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
