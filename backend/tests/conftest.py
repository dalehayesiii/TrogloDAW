import importlib
import sys

import pytest


@pytest.fixture
def core(tmp_path, monkeypatch):
    monkeypatch.setenv("MM_LIBRARY", str(tmp_path / "library"))
    monkeypatch.setenv("MM_CONFIG_DIR", str(tmp_path))
    for key in ("MM_FFMPEG", "MM_HOST", "MM_PORT"):
        monkeypatch.delenv(key, raising=False)
    sys.modules.pop("mmcore", None)
    return importlib.import_module("mmcore")
