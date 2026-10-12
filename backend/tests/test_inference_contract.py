import pytest

from inference_runner import adapt_generation, gpu_memory
from types import SimpleNamespace
import inference_runner


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
