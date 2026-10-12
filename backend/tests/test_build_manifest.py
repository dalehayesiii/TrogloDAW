import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("version", ["0.0.0", "2.4.10"])
@pytest.mark.parametrize("custom_output", [False, True])
def test_manifest_and_checksum_identify_versioned_installer(tmp_path, version, custom_output):
    name = f"TrogloDAW-Setup-{version}.exe"
    installer = tmp_path / ("custom setup.exe" if custom_output else name)
    content = b"synthetic installer bytes"
    installer.write_bytes(content)
    script = Path(__file__).resolve().parents[2] / "scripts/build_manifest.py"
    subprocess.run(
        [sys.executable, str(script), str(installer)],
        env={**os.environ, "TROGLODAW_VERSION": version},
        check=True,
        capture_output=True,
    )
    checksum = hashlib.sha256(content).hexdigest()
    manifest = json.loads((tmp_path / "release.json").read_text())
    assert manifest["version"] == version
    assert manifest["installer"] == name
    assert manifest["sha256"] == checksum
    assert (tmp_path / name).read_bytes() == content
    assert (tmp_path / "SHA256SUMS").read_text() == f"{checksum}  {name}\n"
    assert not (tmp_path / "TrogloDAW-Setup.exe").exists()
