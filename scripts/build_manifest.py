"""Record the installer source/version and publish its checksum."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

version = os.environ["TROGLODAW_VERSION"]
if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", version):
    raise SystemExit("Expected a stable semantic version")
name = f"TrogloDAW-Setup-{version}.exe"
installer = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist") / name
dist = installer.parent
checksum = hashlib.sha256(installer.read_bytes()).hexdigest()
canonical = dist / name
if canonical.resolve() != installer.resolve():
    shutil.copyfile(installer, canonical)
manifest = {
    "version": version,
    "sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "sha256": checksum,
    "installer": canonical.name,
}
(dist / "release.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
(dist / "SHA256SUMS").write_text(f"{checksum}  {canonical.name}\n", encoding="utf-8")
