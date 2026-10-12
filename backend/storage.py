"""Recoverable local storage preferences and manifest-scoped model ownership."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path
from contextlib import nullcontext


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def safe_file(root: Path, relative: str) -> Path:
    """Only regular paths below the selected root; reject links/junctions."""
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or any(p in {"..", "."} for p in rel.parts):
        raise ValueError("Unsafe managed asset path")
    candidate = root / rel
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()) or resolved == root.resolve():
        raise ValueError("Managed asset leaves its storage folder")
    for path in [root, *(root / Path(*rel.parts[:i]) for i in range(1, len(rel.parts) + 1))]:
        if path.is_symlink() or path.is_junction():
            raise ValueError("Managed assets cannot use links or junctions")
    return candidate


def writable_root(value: str, required_bytes=0) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute() or path == Path(path.anchor):
        raise ValueError("Choose an absolute folder path, not a drive root")
    # Do not manufacture a missing Windows drive or silently fall back.
    if not Path(path.anchor).exists():
        raise ValueError("The selected drive is unavailable")
    path = path.resolve()
    if path.exists() and not path.is_dir():
        raise ValueError("Choose a folder rather than a file")
    path.mkdir(parents=True, exist_ok=True)
    probe = path / (".troglodaw-write-" + uuid.uuid4().hex)
    try:
        probe.write_bytes(b"storage check")
    finally:
        probe.unlink(missing_ok=True)
    if shutil.disk_usage(path).free < required_bytes:
        raise ValueError("The selected folder does not have enough free space")
    return path


def copy_verified(source: Path, destination: Path, progress, excluded=()):
    """Copy to a sibling staging folder; retain source as a recovery copy."""
    source, destination = source.resolve(), destination.resolve()
    if not source.is_dir():
        raise ValueError("Original storage folder is unavailable")
    if source == destination:
        return
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("Source and destination folders must not contain each other")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(
            "Destination is not empty. Open the existing folder or choose an empty one"
        )
    files = [
        p
        for p in source.rglob("*")
        if p.is_file() and p.relative_to(source).as_posix() not in excluded
    ]
    size = sum(p.stat().st_size for p in files)
    writable_root(str(destination.parent), size + 64 * 1024 * 1024)
    stage = destination.parent / (".troglodaw-relocate-" + uuid.uuid4().hex)
    stage.mkdir()
    atomic_json(
        stage / ".relocation.json", {"source": str(source), "destination": str(destination)}
    )
    try:
        for index, old in enumerate(files):
            relative = old.relative_to(source).as_posix()
            safe_file(source, relative)
            new = safe_file(stage, relative)
            new.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old, new)
            if digest(old) != digest(new):
                raise ValueError("Relocation verification failed; original folder is unchanged")
            progress("Copying and verifying storage", (index + 1) / max(1, len(files)))
        (stage / ".relocation.json").unlink()
        if destination.exists():
            destination.rmdir()
        stage.rename(destination)
    except Exception:
        # Staging is intentionally retained for diagnosis/recovery; source stays active.
        raise


class Storage:
    def __init__(self, core):
        self.core = core
        self.config_path = core.CONFIG_DIR / "config.local.json"
        self.preferences = core._read_json(self.config_path)
        changed = False
        if not self.preferences.get("installation_id"):
            self.preferences["installation_id"] = uuid.uuid4().hex
            changed = True
        if not self.preferences.get("model_dir"):
            self.preferences["model_dir"] = str(core.LIB.parent / "models")
            changed = True
        if changed:
            self.persist()

    def persist(self):
        atomic_json(self.config_path, self.preferences)
        self.core.CONFIG.update(self.preferences)

    @property
    def models(self) -> Path:
        value = self.preferences.get("model_dir") or self.core.setting("model_dir")
        return Path(value).expanduser().resolve() if value else self.core.LIB.parent / "models"

    def describe(self):
        return {
            "library_dir": str(self.core.LIB),
            "model_dir": str(self.models),
            "installation_id": self.preferences["installation_id"],
        }

    def change(self, kind: str, value: str, mode: str, progress):
        guard = (
            self.core._locked_catalog()
            if kind == "library" and mode == "relocate"
            else nullcontext()
        )
        with guard:
            return self._change(kind, value, mode, progress)

    def _change(self, kind: str, value: str, mode: str, progress):
        if kind not in {"library", "model"} or mode not in {"open", "relocate"}:
            raise ValueError("Choose library/model and open/relocate")
        if kind == "library" and os.environ.get("MM_LIBRARY"):
            raise ValueError(
                "MM_LIBRARY overrides storage. Restart without that override to change it"
            )
        old = self.core.LIB if kind == "library" else self.models
        new = writable_root(value, 64 * 1024 * 1024)
        if mode == "relocate":
            copy_verified(old, new, progress, {"catalog.json.lock"} if kind == "library" else ())
            if kind == "model":
                # Co-owners still use the original root. Their copied manifests must
                # not claim references in this installation's independent copy.
                own_name = self.preferences["installation_id"] + ".json"
                for manifest in (new / ".troglodaw").glob("*.json"):
                    if manifest.name != own_name:
                        manifest.unlink()
        if kind == "library":
            if (new / "catalog.json").exists():
                catalog = json.loads((new / "catalog.json").read_text(encoding="utf-8"))
                if not isinstance(catalog, dict) or not isinstance(catalog.get("items"), list):
                    raise ValueError("The destination contains an invalid library catalog")
            for directory in [*self.core.TYPE_DIRS.values(), "inbox"]:
                (new / directory).mkdir(exist_ok=True)
            self.preferences["library_dir"] = str(new)
            self.persist()
            self.core.LIB, self.core.CATALOG, self.core.INBOX = (
                new,
                new / "catalog.json",
                new / "inbox",
            )
        else:
            self.preferences["model_dir"] = str(new)
            roots = self.preferences.setdefault("model_roots", [])
            if str(new) not in roots:
                roots.append(str(new))
            self.persist()
        return {**self.describe(), "recovery_copy": str(old) if mode == "relocate" else None}

    def owned(self, root: Path, files: list[Path]):
        path = root / ".troglodaw" / (self.preferences["installation_id"] + ".json")
        existing = json.loads(path.read_text()) if path.exists() else {"files": {}}
        for file in files:
            relative = file.relative_to(root).as_posix()
            safe_file(root, relative)
            existing["files"][relative] = digest(file)
        atomic_json(path, existing)
        roots = self.preferences.setdefault("model_roots", [])
        if str(root) not in roots:
            roots.append(str(root))
        self.persist()

    def reference(self, root: Path, files: list[Path]):
        """Co-reference app-owned assets; externally supplied files remain unowned."""
        known = {}
        directory = root / ".troglodaw"
        if directory.exists():
            for manifest in directory.glob("*.json"):
                known.update(json.loads(manifest.read_text()).get("files", {}))
        # Retain the original owner's checksum, never claim a user's replacement.
        # Rehashing the multi-gigabyte wheel tree twice on every reuse is unnecessary:
        # unchanged downloads/code are verified separately; uninstall checks every file.
        path = directory / (self.preferences["installation_id"] + ".json")
        existing = json.loads(path.read_text()) if path.exists() else {"files": {}}
        for file in files:
            relative = file.relative_to(root).as_posix()
            if relative in known:
                existing["files"][relative] = known[relative]
        atomic_json(path, existing)
        roots = self.preferences.setdefault("model_roots", [])
        if str(root) not in roots:
            roots.append(str(root))
        self.persist()


def remove_owned_models(config_path: Path) -> dict:
    """Uninstaller entry point: remove recorded unchanged files, never an arbitrary tree."""
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    removed, retained = [], []
    owner = config.get("installation_id")
    if not owner or not isinstance(owner, str) or not owner.isalnum():
        return {"removed": removed, "retained": retained}
    for value in config.get("model_roots", []):
        root = Path(value)
        if not root.is_absolute() or root == Path(root.anchor):
            continue
        path = safe_file(root, f".troglodaw/{owner}.json")
        if not path.exists():
            continue
        own = json.loads(path.read_text())
        shared = set()
        for other in path.parent.glob("*.json"):
            if other != path:
                shared.update(json.loads(other.read_text()).get("files", {}))
        for relative, checksum in own.get("files", {}).items():
            target = safe_file(root, relative)
            if relative in shared or (target.exists() and digest(target) != checksum):
                retained.append(str(target))
            elif target.is_file():
                target.unlink()
                removed.append(str(target))
        path.unlink()
    return {"removed": removed, "retained": retained}


if __name__ == "__main__":
    import sys

    print(json.dumps(remove_owned_models(Path(sys.argv[1]))))
