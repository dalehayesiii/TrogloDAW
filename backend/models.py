"""Explicit pinned model acquisition; inference has no implicit network setup."""

from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import sys
import tomllib
import urllib.request
import uuid
import zipfile
from pathlib import Path

from storage import atomic_json, digest, safe_file, writable_root

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "model-manifest.json"
CREATE_FLAGS = 0x08000000 if os.name == "nt" else 0


def runtime_signature(root=ROOT):
    """Fingerprint the locked inference graph, independent of unrelated app dependencies."""
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    packages = lock["package"]
    local = next(p for p in packages if p["name"] == project["project"]["name"])
    names = {p["name"] for p in local["optional-dependencies"]["inference"]}
    selected = []
    pending = set(names)
    while pending:
        name = pending.pop()
        for package in packages:
            if package["name"] != name:
                continue
            selected.append(package)
            for dependency in package.get("dependencies", []):
                if dependency["name"] not in names:
                    names.add(dependency["name"])
                    pending.add(dependency["name"])
    value = {
        "packages": sorted(selected, key=lambda p: (p["name"], p["version"])),
        "python": sys.implementation.cache_tag,
        "platform": sys.platform,
        "pins": project["project"]["optional-dependencies"]["inference"],
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class Canceled(Exception):
    result: dict | None = None


def cache_environment(root: Path, owner: str | None = None) -> dict:
    env = dict(os.environ)
    cache = root / "cache" / (owner or "")
    for key, suffix in {
        "HF_HOME": "hf",
        "TORCH_HOME": "torch",
        "TORCHINDUCTOR_CACHE_DIR": "torchinductor",
        "TRITON_CACHE_DIR": "triton",
        "XDG_CACHE_HOME": "",
        "UV_CACHE_DIR": "uv",
        "TEMP": "temp",
        "TMP": "temp",
        "PYTHONPYCACHEPREFIX": "pycache",
        "CUDA_CACHE_PATH": "cuda",
        "NUMBA_CACHE_DIR": "numba",
        "MPLCONFIGDIR": "matplotlib",
        "HF_MODULES_CACHE": "hfmodules",
    }.items():
        path = cache / suffix
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    project_cache = cache / "acestep"
    project_cache.mkdir(parents=True, exist_ok=True)
    env["ACESTEP_PROJECT_ROOT"] = str(project_cache)
    env["ACESTEP_CHECKPOINTS_DIR"] = str(root / "checkpoints")
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    return env


def download(asset: dict, root: Path, progress, canceled) -> tuple[Path, bool]:
    target = safe_file(root, asset["path"])
    target.parent.mkdir(parents=True, exist_ok=True)
    if (
        target.is_file()
        and target.stat().st_size == asset["bytes"]
        and digest(target) == asset["sha256"]
    ):
        progress("Reusing verified " + target.name, 1, stage="verifying")
        return target, False
    if target.exists():
        raise ValueError(
            "An existing file has different contents: "
            + str(target)
            + ". Choose another model folder to preserve it."
        )
    partial = target.with_name(target.name + ".partial")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"Range": f"bytes={offset}-"} if offset and offset < asset["bytes"] else {}
    request = urllib.request.Request(asset["url"], headers=headers)
    progress(
        "Downloading " + target.name,
        0,
        stage="downloading",
        downloaded=offset,
        total_bytes=asset["bytes"],
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        resume = bool(offset and response.status == 206)
        if not resume:
            offset = 0
        with partial.open("ab" if resume else "wb") as stream:
            while chunk := response.read(1024 * 1024):
                if canceled():
                    raise Canceled("Model installation canceled; partial downloads can resume")
                stream.write(chunk)
                offset += len(chunk)
                progress(
                    "Downloading " + target.name,
                    min(0.99, offset / asset["bytes"]),
                    stage="downloading",
                    downloaded=offset,
                    total_bytes=asset["bytes"],
                )
    progress("Verifying " + target.name, 0.99, stage="verifying")
    if partial.stat().st_size != asset["bytes"] or digest(partial) != asset["sha256"]:
        partial.unlink(missing_ok=True)
        raise ValueError("Downloaded asset failed size/checksum verification: " + target.name)
    os.replace(partial, target)
    return target, True


def unpack_runtime(archive: Path, root: Path, revision: str) -> tuple[Path, list[Path]]:
    destination = root / "inference-code" / revision
    marker = destination / ".complete"
    if marker.exists():
        with zipfile.ZipFile(archive) as zipped:
            for entry in zipped.infolist():
                parts = Path(entry.filename).parts
                if len(parts) < 2 or entry.is_dir():
                    continue
                relative = Path(*parts[1:])
                if relative.parts[0] != "acestep" and relative.as_posix() != "LICENSE":
                    continue
                target = safe_file(destination, relative.as_posix())
                if not target.is_file() or target.read_bytes() != zipped.read(entry):
                    raise ValueError(
                        "Existing inference code differs from the verified archive. Choose another model folder."
                    )
        return destination, []
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(
            "Incomplete runtime directory; choose another model folder or remove incomplete setup"
        )
    destination.mkdir(parents=True, exist_ok=True)
    files = []
    with zipfile.ZipFile(archive) as zipped:
        for entry in zipped.infolist():
            parts = Path(entry.filename).parts
            if len(parts) < 2 or entry.is_dir():
                continue
            relative = Path(*parts[1:])
            if relative.parts[0] != "acestep" and relative.as_posix() != "LICENSE":
                continue
            target = safe_file(destination, relative.as_posix())
            target.parent.mkdir(parents=True, exist_ok=True)
            with zipped.open(entry) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            files.append(target)
    marker.write_text(revision)
    return destination, [*files, marker]


def run_setup(command, env, progress, canceled):
    with subprocess.Popen(
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_FLAGS,
    ) as process:
        # Reader thread prevents quiet network operations from blocking cancel requests.
        import queue
        import threading

        lines = queue.Queue()
        assert process.stdout is not None
        output = process.stdout
        threading.Thread(target=lambda: [lines.put(line) for line in output], daemon=True).start()
        messages = []
        while process.poll() is None or not lines.empty():
            if canceled():
                process.terminate()
                process.wait(timeout=10)
                raise Canceled("Runtime installation canceled")
            try:
                line = lines.get(timeout=0.2).strip()
                messages.append(line)
                progress("Installing inference runtime", 0, stage="installing", diagnostic=line)
            except queue.Empty:
                continue
        if process.returncode:
            raise RuntimeError("Inference runtime setup failed: " + "\n".join(messages[-8:]))


class Models:
    def __init__(self, storage):
        self.storage = storage
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    @property
    def selected(self):
        return self.storage.preferences.get("music_model", "acestep-v15-base")

    def state_path(self, root=None):
        return (
            (root or self.storage.models)
            / ".troglodaw"
            / ("ready-" + self.storage.preferences["installation_id"] + ".json")
        )

    def ready(self):
        try:
            return self._ready()
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _ready(self):
        path = self.state_path()
        if not path.exists():
            return None
        state = json.loads(path.read_text())
        if state.get("model") != self.selected or state.get("lock") != runtime_signature():
            return None
        expected = {
            a["path"]
            for a in [
                self.manifest["runtime"],
                *self.manifest["models"][self.selected]["assets"],
                *self.manifest.get("auxiliary_assets", []),
            ]
        }
        if {entry["path"] for entry in state.get("verified", [])} != expected:
            return None
        for entry in [*state.get("verified", []), *state.get("code_verified", [])]:
            asset = safe_file(self.storage.models, entry["path"])
            if not asset.is_file() or asset.stat().st_size != entry["bytes"]:
                return None
            if asset.stat().st_mtime_ns != entry["mtime"] and digest(asset) != entry["sha256"]:
                return None
        code = safe_file(self.storage.models, state["code"])
        packages = safe_file(self.storage.models, state["packages"])
        if not (packages / ".complete").exists() or not (code / ".complete").exists():
            return None
        if (packages / ".complete").read_text() != state["lock"] or (
            code / ".complete"
        ).read_text() != self.manifest["runtime_revision"]:
            return None
        return state

    def describe(self):
        return {
            "selected": self.selected,
            "ready": bool(self.ready()),
            "destination": str(self.storage.models),
            "choices": [
                {
                    "id": key,
                    "name": value["name"],
                    "bytes": sum(a["bytes"] for a in value["assets"]),
                    "hardware": "RTX 3070 validated; sequential CPU offload"
                    if key == "acestep-v15-base"
                    else "Compatible Base-family alternative; not separately benchmarked",
                    "role": "Local music generation",
                }
                for key, value in self.manifest["models"].items()
            ],
        }

    def install(self, model: str, progress, canceled):
        root = writable_root(str(self.storage.models))
        owner = self.storage.preferences["installation_id"]
        cache = root / "cache" / owner
        before = {p for p in cache.rglob("*") if p.is_file()} if cache.exists() else set()
        try:
            return self._install(model, progress, canceled)
        finally:
            self.storage.owned(
                root, [p for p in cache.rglob("*") if p.is_file() and p not in before]
            )

    def _install(self, model: str, progress, canceled):
        if model not in self.manifest["models"]:
            raise ValueError("Unsupported music model")
        assets = [
            self.manifest["runtime"],
            *self.manifest["models"][model]["assets"],
            *self.manifest.get("auxiliary_assets", []),
        ]
        root = writable_root(
            str(self.storage.models), sum(a["bytes"] for a in assets) + 12 * 1024**3
        )
        owned = []
        verified = []
        for index, asset in enumerate(assets):
            path, acquired = download(asset, root, progress, canceled)
            if acquired:
                owned.append(path)
                # Record immediately so failed setup can be uninstalled safely.
                self.storage.owned(root, [path])
            else:
                self.storage.reference(root, [path])
            verified.append(
                {
                    "path": asset["path"],
                    "bytes": asset["bytes"],
                    "sha256": asset["sha256"],
                    "mtime": path.stat().st_mtime_ns,
                }
            )
            progress(
                "Verified model assets",
                (index + 1) / len(assets),
                stage="verifying",
                assets_complete=index + 1,
                assets_total=len(assets),
            )
        code, code_files = unpack_runtime(
            root / self.manifest["runtime"]["path"], root, self.manifest["runtime_revision"]
        )
        self.storage.owned(root, code_files)
        if not code_files:
            self.storage.reference(root, [p for p in code.rglob("*") if p.is_file()])
        lock = runtime_signature()
        packages = root / "runtime-packages" / lock[:16]
        env = cache_environment(root, self.storage.preferences["installation_id"])
        if not (packages / ".complete").exists():
            uv = Path(sys.executable).parent / ("uv.exe" if os.name == "nt" else "uv")
            if not uv.exists():
                found = shutil.which("uv")
                if not found:
                    raise RuntimeError("Bundled inference setup tool is unavailable")
                uv = Path(found)
            temporary = root / "cache" / ("requirements-" + uuid.uuid4().hex + ".txt")
            try:
                run_setup(
                    [
                        str(uv),
                        "export",
                        "--project",
                        str(ROOT),
                        "--locked",
                        "--extra",
                        "inference",
                        "--no-dev",
                        "--no-emit-project",
                        "--format",
                        "requirements-txt",
                        "--output-file",
                        str(temporary),
                    ],
                    env,
                    progress,
                    canceled,
                )
                packages.mkdir(parents=True, exist_ok=True)
                run_setup(
                    [
                        str(uv),
                        "pip",
                        "install",
                        "--python",
                        sys.executable,
                        "--target",
                        str(packages),
                        "--require-hashes",
                        "--only-binary",
                        ":all:",
                        "--extra-index-url",
                        "https://download.pytorch.org/whl/cu128",
                        "--index-strategy",
                        "unsafe-best-match",
                        "-r",
                        str(temporary),
                    ],
                    env,
                    progress,
                    canceled,
                )
                (packages / ".complete").write_text(lock)
            finally:
                temporary.unlink(missing_ok=True)
                self.storage.owned(root, [p for p in packages.rglob("*") if p.is_file()])
        else:
            self.storage.reference(root, [p for p in packages.rglob("*") if p.is_file()])
        probe = root / "cache" / ("probe-" + uuid.uuid4().hex + ".json")
        atomic_json(probe, {"action": "probe", "packages": str(packages), "code": str(code)})
        try:
            run_setup(
                [sys.executable, str(ROOT / "backend/inference_runner.py"), str(probe)],
                env,
                progress,
                canceled,
            )
        finally:
            probe.unlink(missing_ok=True)
        state = {
            "model": model,
            "lock": lock,
            "packages": packages.relative_to(root).as_posix(),
            "code": code.relative_to(root).as_posix(),
            "verified": verified,
            "runtime_revision": self.manifest["runtime_revision"],
            "code_verified": [
                {
                    "path": p.relative_to(root).as_posix(),
                    "bytes": p.stat().st_size,
                    "mtime": p.stat().st_mtime_ns,
                    "sha256": digest(p),
                }
                for p in code.rglob("*")
                if p.is_file()
            ],
        }
        atomic_json(self.state_path(root), state)
        self.storage.owned(root, [self.state_path(root)])
        self.storage.preferences["music_model"] = model
        self.storage.persist()
        return self.describe()
