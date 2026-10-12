"""Version a checked Music Maker payload with native NSIS arguments, then record its checksum."""

import os
import re
import subprocess
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
version = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MM_VERSION", "0.0.0")
if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", version):
    raise SystemExit("Expected a stable semantic version")


def setting(key: str, env: str, default: str) -> str:
    return subprocess.check_output(
        [sys.executable, str(repo / "scripts/windows/cfg.py"), str(repo), key, env, default],
        text=True,
    ).strip()


work = Path(setting("build.work_dir", "MM_BUILD_WORK_DIR", str(repo / "scripts/windows/work")))
stage = work / "stage/MusicMaker"
output = Path(setting("build.output", "MM_BUILD_OUTPUT", str(repo / "dist/MusicMaker-Setup.exe")))
install = setting("windows.install_dir", "MM_WIN_INSTALL_DIR", r"$LOCALAPPDATA\MusicMaker")
library = setting("windows.library_dir", "MM_WIN_LIBRARY_DIR", r"$DOCUMENTS\MusicMaker\library")
if not (stage / "app/frontend/dist/browser/index.html").is_file():
    raise SystemExit("Checked payload is missing")
output.parent.mkdir(parents=True, exist_ok=True)
arguments = [
    os.environ.get("MM_MAKENSIS", "makensis"),
    "-V2",
    f"-DVERSION={version}",
    f"-DSTAGE={stage}",
    f"-DOUTFILE={output}",
    f"-DINSTALL_DIR={install}",
    f"-DLIBRARY_DIR={library}",
    str(repo / "cicd/windows/musicmaker.nsi"),
]
print(f"NSIS version {version}: {arguments!r}", flush=True)
subprocess.run(arguments, check=True)
subprocess.run(
    [sys.executable, str(repo / "scripts/build_manifest.py"), str(output)],
    env={**os.environ, "MM_VERSION": version},
    check=True,
    cwd=repo,
)
