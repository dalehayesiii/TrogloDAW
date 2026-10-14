import pytest

from inference_runner import adapt_generation, gpu_memory
from types import SimpleNamespace
import inference_runner
import numpy as np
import soundfile as sf


def test_old_checkpoint_cfg_argument_receives_requested_value():
    class OldCheckpoint:
        def generate_audio(self, diffusion_guidance_sale=7, **_kwargs):
            return diffusion_guidance_sale

    checkpoint = OldCheckpoint()
    adapt_generation(checkpoint)
    assert checkpoint.generate_audio(diffusion_guidance_scale=1) == 1
    assert checkpoint.generate_audio(diffusion_guidance_scale=15) == 15


def test_unknown_checkpoint_cannot_silently_ignore_style_influence():
    class Unsupported:
        def generate_audio(self, **_kwargs):
            return None

    with pytest.raises(RuntimeError, match="Style Influence"):
        adapt_generation(Unsupported())


@pytest.mark.parametrize("strength", [0, 0.25, 0.75, 1])
def test_pinned_partial_cover_switch_occurs_once_with_cfg(strength):
    class PinnedCheckpoint:
        def generate_audio(
            self, diffusion_guidance_sale=7, infer_steps=32, audio_cover_strength=1, **kwargs
        ):
            cover_steps = int(infer_steps * audio_cover_strength)
            batch = ["conditional"]
            switches = 0
            for step_idx in range(infer_steps):
                if step_idx >= cover_steps:
                    if diffusion_guidance_sale > 1:
                        batch = batch + batch
                    switches += 1
                assert len(batch) <= 2
            return switches, diffusion_guidance_sale, kwargs["use_progress_bar"]

    checkpoint = PinnedCheckpoint()
    adapt_generation(checkpoint, conditioned=True)
    assert checkpoint.generate_audio(diffusion_guidance_scale=8, audio_cover_strength=strength) == (
        0 if strength == 1 else 1,
        8,
        False,
    )


def test_unrecognized_pinned_cover_implementation_fails_clearly():
    class DifferentCheckpoint:
        def generate_audio(self, diffusion_guidance_sale=7, **kwargs):
            return kwargs

    with pytest.raises(RuntimeError, match="incompatible"):
        adapt_generation(DifferentCheckpoint(), conditioned=True)


def test_driver_memory_caps_optimistic_cuda_budget_and_matches_visible_gpu(monkeypatch):
    identifier = "12345678-1234-1234-1234-123456789abc"
    torch = SimpleNamespace(
        cuda=SimpleNamespace(
            is_available=lambda: True,
            mem_get_info=lambda: (7 * 1024**3, 8 * 1024**3),
            current_device=lambda: 0,
            get_device_properties=lambda _: SimpleNamespace(uuid=identifier),
        )
    )
    monkeypatch.setattr(inference_runner.shutil, "which", lambda _: "nvidia-smi")
    monkeypatch.setattr(
        inference_runner.subprocess,
        "check_output",
        lambda *_args, **_kwargs: f"GPU-other, 7000, 8192\nGPU-{identifier}, 1500, 8192\n",
    )
    free, total, basis = gpu_memory(torch)
    assert free == 1500 * 1024**2 and total == 8 * 1024**3
    assert basis == "cuda+driver"


def test_missing_driver_query_preserves_cuda_budget_without_a_dependency(monkeypatch):
    torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: True, mem_get_info=lambda: (7, 8))
    )
    monkeypatch.setattr(inference_runner.shutil, "which", lambda _: None)
    assert gpu_memory(torch) == (7, 8, "cuda")


def test_direct_result_removes_decoder_padding_without_cutting_source_timeline(tmp_path):
    path = tmp_path / "model.wav"
    audio = np.arange(5120, dtype=np.float32)[:, None] / 10000
    sf.write(path, audio, 1000, subtype="FLOAT")
    params = {"workflow": "recording-style", "duration": 1}
    first = {"path": str(path)}
    assert inference_runner.trim_recording_padding(first, params, True) == 4120
    rendered, sr = sf.read(path, dtype="float32", always_2d=True)
    assert sr == 1000
    np.testing.assert_array_equal(rendered, audio[:1000])
    assert inference_runner.trim_recording_padding(first, params, True) == 0
    with pytest.raises(RuntimeError, match="complete recording timeline"):
        inference_runner.trim_recording_padding(first, {**params, "duration": 2}, True)
    assert (
        inference_runner.trim_recording_padding(first, {**params, "workflow": "model"}, True) == 0
    )


@pytest.mark.parametrize("samples", [48000, 336000, 3024000, 3024144, 3025872, 3028800, 14400000])
def test_direct_encoder_preserves_last_samples_before_frame_quantization(samples):
    # Mimic the pinned VAE's floor encode / exact-frame decode, including the
    # nonaligned ~63-second upload which integer-second checks missed.
    audio = np.linspace(-0.4, 0.4, samples, dtype=np.float32)[None, :]
    snapshot = audio.copy()
    received = []

    def encoder(value, *, offload_latent_to_cpu):
        assert offload_latent_to_cpu is True
        received.append(value)
        return value[..., : value.shape[-1] // 1920 * 1920]

    handler = SimpleNamespace(
        vae=SimpleNamespace(
            config=SimpleNamespace(sampling_rate=48000, downsampling_ratios=[2, 4, 4, 6, 10])
        ),
        tiled_encode=encoder,
    )
    torch = SimpleNamespace(
        nn=SimpleNamespace(
            functional=SimpleNamespace(pad=lambda value, widths: np.pad(value, ((0, 0), widths)))
        )
    )
    alignment = inference_runner.align_recording_encoder(handler, torch)
    decoded = handler.tiled_encode(audio, offload_latent_to_cpu=True)
    assert len(decoded[0]) >= samples
    assert len(decoded[0]) - samples < 1920
    np.testing.assert_array_equal(decoded[..., :samples], snapshot)
    np.testing.assert_array_equal(audio, snapshot)
    assert not np.any(decoded[..., samples:])
    assert alignment["padding_samples"] == len(decoded[0]) - samples


def test_direct_alignment_rejects_unvalidated_decoder():
    handler = SimpleNamespace(
        vae=SimpleNamespace(
            config=SimpleNamespace(sampling_rate=44100, downsampling_ratios=[2, 4, 4, 6, 10])
        )
    )
    with pytest.raises(RuntimeError, match="decoder cannot preserve"):
        inference_runner.align_recording_encoder(handler, None)


def test_direct_trim_uses_exact_source_frames_not_rounded_duration(tmp_path):
    source, result = tmp_path / "source.wav", tmp_path / "result.wav"
    sf.write(source, np.ones((630034, 2), dtype=np.float32) * 0.2, 10000, subtype="FLOAT")
    generated = np.ones((630040, 2), dtype=np.float32) * 0.3
    sf.write(result, generated, 10000, subtype="FLOAT")
    params = {"workflow": "recording-style", "duration": 63.003}
    assert inference_runner.trim_recording_padding({"path": result}, params, True, source) == 6
    audio, _ = sf.read(result, always_2d=True, dtype="float32")
    np.testing.assert_array_equal(audio, generated[:630034])
    assert sf.info(source).frames == 630034
    sf.write(result, generated[:630033], 10000, subtype="FLOAT")
    with pytest.raises(RuntimeError, match="complete recording timeline"):
        inference_runner.trim_recording_padding({"path": result}, params, True, source)
