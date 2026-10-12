"""Record the installer source/version and publish its checksum."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

installer = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist/TrogloDAW-Setup.exe")
dist = installer.parent
checksum = hashlib.sha256(installer.read_bytes()).hexdigest()
canonical, legacy = dist / "TrogloDAW-Setup.exe", dist / "MusicMaker-Setup.exe"
for alias in (canonical, legacy):
    if alias.resolve() != installer.resolve():
        shutil.copyfile(installer, alias)
manifest = {
    "version": os.environ["MM_VERSION"],
    "sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "sha256": checksum,
    "installer": canonical.name,
    "legacy_installer": legacy.name,
}
(dist / "release.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
(dist / "SHA256SUMS").write_text(
    f"{checksum}  {canonical.name}\n{checksum}  {legacy.name}\n", encoding="utf-8"
)
