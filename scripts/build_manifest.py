"""Record the installer source/version and publish its checksum."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

dist = Path("dist")
checksum = hashlib.sha256((dist / "MusicMaker-Setup.exe").read_bytes()).hexdigest()
manifest = {
    "version": os.environ["MM_VERSION"],
    "sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "sha256": checksum,
}
(dist / "release.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
(dist / "SHA256SUMS").write_text(f"{checksum}  MusicMaker-Setup.exe\n", encoding="utf-8")
