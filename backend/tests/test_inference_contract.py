import pytest

from inference_runner import adapt_generation


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
