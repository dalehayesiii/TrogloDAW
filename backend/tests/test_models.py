import hashlib
import io

import pytest

import models
from models import Canceled, cache_environment, download


def asset(data):
    return {
        "path": "checkpoints/weights.bin",
        "url": "https://example.invalid/weights",
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


class Response(io.BytesIO):
    def __init__(self, data, status=200):
        super().__init__(data)
        self.status = status


def test_verified_asset_reused_without_network(tmp_path, monkeypatch):
    data = b"verified weights"
    path = tmp_path / "checkpoints" / "weights.bin"
    path.parent.mkdir()
    path.write_bytes(data)

    def no_network(*_args, **_kwargs):
        raise AssertionError("Network called for a verified asset")

    monkeypatch.setattr(models.urllib.request, "urlopen", no_network)
    result, owned = download(asset(data), tmp_path, lambda *_args, **_kwargs: None, lambda: False)
    assert result == path and not owned


def test_resume_range_and_checksum(tmp_path, monkeypatch):
    data = b"verified weights"
    partial = tmp_path / "checkpoints" / "weights.bin.partial"
    partial.parent.mkdir()
    partial.write_bytes(data[:5])

    def response(request, **_):
        assert request.headers["Range"] == "bytes=5-"
        return Response(data[5:], 206)

    monkeypatch.setattr(models.urllib.request, "urlopen", response)
    path, owned = download(asset(data), tmp_path, lambda *_args, **_kwargs: None, lambda: False)
    assert owned and path.read_bytes() == data and not partial.exists()


def test_range_ignored_restarts_safely(tmp_path, monkeypatch):
    data = b"verified weights"
    partial = tmp_path / "checkpoints" / "weights.bin.partial"
    partial.parent.mkdir()
    partial.write_bytes(data[:5])
    monkeypatch.setattr(models.urllib.request, "urlopen", lambda *_args, **_kwargs: Response(data))
    path, _ = download(asset(data), tmp_path, lambda *_args, **_kwargs: None, lambda: False)
    assert path.read_bytes() == data


def test_invalid_download_never_activates(tmp_path, monkeypatch):
    monkeypatch.setattr(
        models.urllib.request, "urlopen", lambda *_args, **_kwargs: Response(b"bad")
    )
    with pytest.raises(ValueError, match="verification"):
        download(asset(b"good"), tmp_path, lambda *_args, **_kwargs: None, lambda: False)
    assert not (tmp_path / "checkpoints" / "weights.bin").exists()


def test_canceled_download_keeps_partial_for_resume(tmp_path, monkeypatch):
    data = b"x" * (1024 * 1024 + 1)
    monkeypatch.setattr(models.urllib.request, "urlopen", lambda *_args, **_kwargs: Response(data))
    count = 0

    def canceled():
        nonlocal count
        count += 1
        return count > 1

    with pytest.raises(Canceled):
        download(asset(data), tmp_path, lambda *_args, **_kwargs: None, canceled)
    assert (tmp_path / "checkpoints" / "weights.bin.partial").stat().st_size == 1024 * 1024
    assert not (tmp_path / "checkpoints" / "weights.bin").exists()


def test_cache_environment_keeps_assets_in_selected_folder(tmp_path):
    env = cache_environment(tmp_path)
    for key in [
        "HF_HOME",
        "TORCH_HOME",
        "UV_CACHE_DIR",
        "TEMP",
        "TMP",
        "TRITON_CACHE_DIR",
        "TORCHINDUCTOR_CACHE_DIR",
    ]:
        assert env[key].startswith(str(tmp_path))


def test_existing_different_file_is_preserved(tmp_path):
    path = tmp_path / "checkpoints/weights.bin"
    path.parent.mkdir()
    path.write_bytes(b"someone else's asset")
    with pytest.raises(ValueError, match="different contents"):
        download(asset(b"good"), tmp_path, lambda *_args, **_kwargs: None, lambda: False)
    assert path.read_bytes() == b"someone else's asset"


def test_runtime_fingerprint_ignores_unrelated_packages_but_tracks_transitive_pins(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="app"\n[project.optional-dependencies]\ninference=["model==1"]\n'
    )
    prefix = '[[package]]\nname="app"\nversion="0"\n[package.optional-dependencies]\ninference=[{name="model"}]\n[[package]]\nname="model"\nversion="1"\ndependencies=[{name="engine"}]\n[[package]]\nname="engine"\nversion="1"\n'
    lock = tmp_path / "uv.lock"
    lock.write_text(prefix)
    first = models.runtime_signature(tmp_path)
    lock.write_text(prefix + '[[package]]\nname="unrelated"\nversion="2"\n')
    assert models.runtime_signature(tmp_path) == first
    lock.write_text(prefix.replace('name="engine"\nversion="1"', 'name="engine"\nversion="2"'))
    assert models.runtime_signature(tmp_path) != first
