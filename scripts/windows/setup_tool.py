"""Bundle the exact locked Windows uv wheel's executable and license notices."""

import hashlib
import shutil
import sys
import tomllib
import urllib.request
import zipfile
from pathlib import Path

repo, cache, stage = map(Path, sys.argv[1:])
lock = tomllib.loads((repo / "uv.lock").read_text(encoding="utf-8"))
package = next(p for p in lock["package"] if p["name"] == "uv")
wheel = next(w for w in package["wheels"] if w["url"].endswith("win_amd64.whl"))
target = cache / Path(wheel["url"]).name
checksum = wheel["hash"].removeprefix("sha256:")


def verified(path):
    if not path.is_file() or path.stat().st_size != wheel["size"]:
        return False
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() == checksum


if not verified(target):
    partial = target.with_suffix(".partial")
    with urllib.request.urlopen(wheel["url"], timeout=60) as response, partial.open("wb") as stream:
        shutil.copyfileobj(response, stream)
    if not verified(partial):
        raise SystemExit("Locked Windows setup-tool wheel failed checksum verification")
    partial.replace(target)

with zipfile.ZipFile(target) as archive:
    executables = [name for name in archive.namelist() if name.endswith("/uv.exe")]
    if len(executables) != 1:
        raise SystemExit("Expected exactly one Windows uv setup executable")
    (stage / "python/uv.exe").write_bytes(archive.read(executables[0]))
    notices = stage / "app/docs/licenses" / ("uv-" + package["version"])
    notices.mkdir(parents=True, exist_ok=True)
    for name in ("LICENSE-MIT", "LICENSE-APACHE"):
        matches = [entry for entry in archive.namelist() if entry.endswith("/licenses/" + name)]
        if len(matches) != 1:
            raise SystemExit("Missing setup-tool license: " + name)
        (notices / name).write_bytes(archive.read(matches[0]))
print("Verified Windows uv " + package["version"] + " and bundled its notices")
