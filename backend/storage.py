"""Recoverable local storage preferences and manifest-scoped model ownership."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
import uuid
import folders
import copy
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
    protect_location(path)
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


def protect_location(path: Path, app_root=None):
    """User assets must not live in folders the installer replaces/removes."""
    root = Path(app_root) if app_root is not None else Path(__file__).resolve().parents[1]
    if app_root is None and not (root.parent / "python/python.exe").is_file():
        return  # Source libraries beside the repository remain supported.
    if any(
        path.resolve().is_relative_to(base.resolve()) for base in [root, root.parent / "python"]
    ):
        raise ValueError("Choose library/model storage outside the app and Python program folders")


def guard_uninstall(config_path: Path, app_root=None):
    config = {}
    for file in [config_path.parent / "config.json", config_path]:
        if not file.exists():
            continue
        try:
            value = json.loads(file.read_text(encoding="utf-8-sig"))
        except UnicodeError:
            value = json.loads(file.read_text(encoding="utf-16"))
        if not isinstance(value, dict):
            raise ValueError("Storage preferences could not be checked safely")
        config.update(value)
    for value in [config.get("library_dir"), config.get("model_dir")]:
        if value:
            path = Path(value)
            protect_location(path if path.is_absolute() else config_path.parent / path, app_root)
    for value in config.get("model_roots", []):
        path = Path(value)
        try:
            protect_location(path, app_root)
        except ValueError:
            # Completed moves can leave an empty historical root/ownership marker.
            if any(
                file.is_file() and ".troglodaw" not in file.relative_to(path).parts
                for file in path.rglob("*")
            ):
                raise


def copy_verified(source: Path, destination: Path, progress, excluded=(), included=None):
    """Copy to a sibling staging folder; retain source as a recovery copy."""
    source, destination = source.resolve(), destination.resolve()
    if not source.is_dir():
        raise ValueError("Original storage folder is unavailable")
    if source == destination:
        return {}
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("Source and destination folders must not contain each other")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(
            "Destination is not empty. Open the existing folder or choose an empty one"
        )
    candidates = (
        source.rglob("*")
        if included is None
        else (safe_file(source, relative) for relative in sorted(included))
    )
    files = [
        p
        for p in candidates
        if p.is_file()
        and p.relative_to(source).as_posix() not in excluded
        and (included is None or p.relative_to(source).as_posix() in included)
    ]
    copied = {}
    size = sum(p.stat().st_size for p in files)
    writable_root(str(destination.parent), size + 64 * 1024 * 1024)
    stage = destination.parent / (".troglodaw-relocate-" + uuid.uuid4().hex)
    stage.mkdir()
    atomic_json(
        stage / ".relocation.json", {"source": str(source), "destination": str(destination)}
    )
    try:
        progress(
            "Copying and verifying storage",
            0,
            stage="copying",
            units_complete=0,
            units_total=len(files),
            timing_profile={"storage_files": len(files), "storage_bytes": size},
        )
        for index, old in enumerate(files):
            relative = old.relative_to(source).as_posix()
            safe_file(source, relative)
            new = safe_file(stage, relative)
            new.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old, new)
            checksum = digest(old)
            if checksum != digest(new):
                raise ValueError("Relocation verification failed; original folder is unchanged")
            copied[relative] = checksum
            progress(
                "Copying and verifying storage",
                (index + 1) / max(1, len(files)),
                stage="copying",
                units_complete=index + 1,
                units_total=len(files),
            )
        (stage / ".relocation.json").unlink()
        if destination.exists():
            destination.rmdir()
        stage.rename(destination)
        return copied
    except Exception:
        # Staging is intentionally retained for diagnosis/recovery; source stays active.
        raise


class Storage:
    def __init__(self, core):
        self.core = core
        self.persist_lock = threading.RLock()
        self.ownership_lock = threading.RLock()
        self.config_path = core.CONFIG_DIR / "config.local.json"
        self.preferences = core._read_json(self.config_path)
        # Preserve setup history for upgrades of installations created before this flag.
        established = bool(self.preferences.get("installation_id"))
        self.model_manifest = {}
        changed = False
        if not self.preferences.get("installation_id"):
            self.preferences["installation_id"] = uuid.uuid4().hex
            changed = True
        if not self.preferences.get("model_dir"):
            self.preferences["model_dir"] = str(core.LIB.parent / "models")
            changed = True
        if "setup_seen" not in self.preferences:
            self.preferences["setup_seen"] = established
            changed = True
        if changed:
            self.persist()

    def persist(self):
        with self.persist_lock:
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
            "setup_seen": bool(self.preferences.get("setup_seen")),
            "native_folder_picker": folders.available(),
            "library_has_data": bool(self.core.list_items())
            or bool(self.core._read_json(self.core.CATALOG).get("folders"))
            or any(self.core.INBOX.glob("*")),
            "model_has_data": self.has_model_data(),
        }

    def has_model_data(self):
        root = self.models
        owner = self.preferences["installation_id"]
        try:
            paths = self.core._read_json(root / ".troglodaw" / (owner + ".json")).get("files", {})
            if any(safe_file(root, relative).is_file() for relative in paths):
                return True
            assets = [
                self.model_manifest.get("runtime", {}),
                *self.model_manifest.get("auxiliary_assets", []),
            ]
            for model in self.model_manifest.get("models", {}).values():
                assets.extend(model["assets"])
            return any(safe_file(root, a["path"]).is_file() for a in assets if "path" in a) or any(
                p.is_file() for p in (root / "cache" / owner).rglob("*")
            )
        except (OSError, ValueError, TypeError):
            # A damaged manifest must not prevent choosing another folder.
            return True

    def model_files(self):
        """Select this app's models/runtime/cache, never a whole arbitrary folder."""
        root = self.models
        owner = self.preferences["installation_id"]
        manifest = root / ".troglodaw" / (owner + ".json")
        owned = self.core._read_json(manifest).get("files", {})
        paths = set(owned)
        assets = [
            self.model_manifest.get("runtime", {}),
            *self.model_manifest.get("auxiliary_assets", []),
        ]
        for model in self.model_manifest.get("models", {}).values():
            assets.extend(model["assets"])
        paths.update(asset["path"] for asset in assets if "path" in asset)
        ready = root / ".troglodaw" / ("ready-" + owner + ".json")
        state = self.core._read_json(ready)
        directories = [state.get("code"), state.get("packages"), f"cache/{owner}"]
        if self.model_manifest.get("runtime_revision"):
            from models import runtime_signature

            directories.extend(
                [
                    f"inference-code/{self.model_manifest['runtime_revision']}",
                    f"runtime-packages/{runtime_signature()[:16]}",
                ]
            )
        for directory in directories:
            if directory:
                base = safe_file(root, directory)
                paths.update(p.relative_to(root).as_posix() for p in base.rglob("*") if p.is_file())
        for control in [manifest, ready]:
            if control.is_file():
                paths.add(control.relative_to(root).as_posix())
        return {relative for relative in paths if safe_file(root, relative).is_file()}

    def library_files(self, catalog=None):
        root = self.core.LIB
        paths = {"catalog.json"}
        for directory in [*self.core.TYPE_DIRS.values(), "assets", "inbox"]:
            base = safe_file(root, directory)
            paths.update(p.relative_to(root).as_posix() for p in base.rglob("*") if p.is_file())
        # Preserve cataloged files outside the normal managed directories, too.
        for item in catalog["items"] if catalog is not None else self.core.list_items():
            for key in ["file", "mp3_file"]:
                if item.get(key) and not Path(item[key]).is_absolute():
                    paths.add(item[key])
        return {relative for relative in paths if safe_file(root, relative).is_file()}

    def change(self, kind: str, value: str, mode: str, progress, committed=None):
        current = self.core.LIB if kind == "library" else self.models
        if (
            kind in {"library", "model"}
            and mode in {"open", "move", "relocate"}
            and Path(value).is_absolute()
            and Path(value).resolve() == current.resolve()
        ):
            return {**self.describe(), "recovery_copy": None, "retained_files": 0}
        guard = (
            self.core._locked_catalog()
            if kind == "library" and mode in {"relocate", "move"}
            else nullcontext()
        )
        with guard as catalog:
            return self._change(kind, value, mode, progress, committed, catalog)

    def _change(self, kind: str, value: str, mode: str, progress, committed=None, catalog=None):
        if kind not in {"library", "model"} or mode not in {"open", "relocate", "move"}:
            raise ValueError("Choose library/model and open/move")
        if kind == "library" and os.environ.get("TROGLODAW_LIBRARY"):
            raise ValueError(
                "TROGLODAW_LIBRARY overrides storage. Restart without that override to change it"
            )
        old = self.core.LIB if kind == "library" else self.models
        new = writable_root(value, 64 * 1024 * 1024)
        copied = {}
        own_name = self.preferences["installation_id"] + ".json"
        original_owner = (
            self.core._read_json(old / ".troglodaw" / own_name).get("files", {})
            if kind == "model"
            else {}
        )
        expected = dict(original_owner)
        if kind == "model":
            # A previously installed app can own the default folder's runtime.
            # Preserve its recorded checksum rather than claiming replacements.
            for record in (old / ".troglodaw").glob("*.json"):
                if record.name != own_name:
                    value = self.core._read_json(record).get("files", {})
                    if isinstance(value, dict):
                        expected = {**value, **expected}
            assets = [
                self.model_manifest.get("runtime", {}),
                *self.model_manifest.get("auxiliary_assets", []),
            ]
            for model in self.model_manifest.get("models", {}).values():
                assets.extend(model["assets"])
            expected = {**{a["path"]: a["sha256"] for a in assets if "path" in a}, **expected}
        if mode in {"relocate", "move"}:
            included = (
                (self.library_files(catalog) if kind == "library" else self.model_files())
                if mode == "move"
                else None
            )
            copied = copy_verified(
                old, new, progress, {"catalog.json.lock"} if kind == "library" else (), included
            )
            if kind == "model":
                unowned_runtime = {
                    relative
                    for relative in copied
                    if relative.startswith(("inference-code/", "runtime-packages/"))
                    and relative not in expected
                }
                expected.update(dict.fromkeys(unowned_runtime))
                # Co-owners still use the original root. Their copied manifests must
                # not claim references in this installation's independent copy.
                for manifest in (new / ".troglodaw").glob("*.json"):
                    if manifest.name not in {own_name, "ready-" + own_name}:
                        manifest.unlink()
                if mode == "move" and copied:
                    # Keep a changed original's ownership checksum, never claim its replacement.
                    atomic_json(
                        new / ".troglodaw" / own_name,
                        {
                            "files": {
                                relative: expected.get(relative, checksum)
                                for relative, checksum in copied.items()
                                if not relative.startswith(".troglodaw/")
                                and relative not in unowned_runtime
                            }
                        },
                    )
        previous = copy.deepcopy(self.preferences)
        if kind == "library":
            if (new / "catalog.json").exists():
                catalog = json.loads((new / "catalog.json").read_text(encoding="utf-8"))
                if not isinstance(catalog, dict) or not isinstance(catalog.get("items"), list):
                    raise ValueError("The destination contains an invalid library catalog")
            for directory in [*self.core.TYPE_DIRS.values(), "inbox"]:
                (new / directory).mkdir(exist_ok=True)
            progress("Updating selected folder", stage="committing_storage", cancel_safe=False)
            self.preferences["library_dir"] = str(new)
            try:
                self.persist()
            except OSError:
                self.preferences = previous
                raise
            self.core.LIB, self.core.CATALOG, self.core.INBOX = (
                new,
                new / "catalog.json",
                new / "inbox",
            )
        else:
            progress("Updating selected folder", stage="committing_storage", cancel_safe=False)
            self.preferences["model_dir"] = str(new)
            roots = self.preferences.setdefault("model_roots", [])
            if str(new) not in roots:
                roots.append(str(new))
            try:
                self.persist()
            except OSError:
                self.preferences = previous
                raise
        if committed:
            committed(old, new, copied)
        retained = (
            self.cleanup_move(old, copied, original_owner, kind, expected)
            if mode == "move" and old != new
            else []
        )
        return {
            **self.describe(),
            "recovery_copy": str(old) if mode == "relocate" else None,
            "retained_files": len(retained),
        }

    def cleanup_move(self, root, copied, original_owner, kind, expected):
        """Only individually verified unchanged files, never recursive deletion."""
        shared = set()
        owner_path = root / ".troglodaw" / (self.preferences["installation_id"] + ".json")
        if kind == "model":
            for other in owner_path.parent.glob("*.json"):
                if other != owner_path:
                    try:
                        value = json.loads(other.read_text(encoding="utf-8-sig"))
                        if not isinstance(value, dict) or not isinstance(
                            value.get("files", {}), dict
                        ):
                            raise ValueError("Invalid ownership metadata")
                        shared.update(value.get("files", {}))
                    except (OSError, ValueError):
                        # Unknown co-owner references: keep originals, the verified new copy works.
                        return sorted(copied)
        retained = []
        for relative, checksum in copied.items():
            if kind == "model" and relative == owner_path.relative_to(root).as_posix():
                continue
            try:
                path = safe_file(root, relative)
                if (
                    relative in shared
                    or expected.get(relative, checksum) != checksum
                    or digest(path) != checksum
                ):
                    retained.append(relative)
                else:
                    path.unlink()
            except (OSError, ValueError):
                retained.append(relative)
        if kind == "model" and owner_path.is_file():
            try:
                atomic_json(
                    owner_path,
                    {"files": {k: v for k, v in original_owner.items() if k not in copied}},
                )
            except OSError:
                retained.append(owner_path.relative_to(root).as_posix())
        for directory in sorted(
            {(root / relative).parent for relative in copied},
            key=lambda p: len(p.parts),
            reverse=True,
        ):
            while directory != root and directory.is_relative_to(root):
                try:
                    directory.rmdir()
                except OSError:
                    break
                directory = directory.parent
        return retained

    def owned(self, root: Path, files: list[Path], progress=None):
        with self.ownership_lock:
            self._owned(root, files, progress)

    def _owned(self, root: Path, files: list[Path], progress=None):
        path = root / ".troglodaw" / (self.preferences["installation_id"] + ".json")
        existing = json.loads(path.read_text()) if path.exists() else {"files": {}}
        reported = time.monotonic()
        if progress:
            progress(0, len(files))
        for index, file in enumerate(files):
            relative = file.relative_to(root).as_posix()
            safe_file(root, relative)
            existing["files"][relative] = digest(file)
            if progress and (time.monotonic() - reported >= 0.2 or index + 1 == len(files)):
                progress(index + 1, len(files))
                reported = time.monotonic()
        atomic_json(path, existing)
        roots = self.preferences.setdefault("model_roots", [])
        if str(root) not in roots:
            roots.append(str(root))
        self.persist()

    def reference(self, root: Path, files: list[Path]):
        """Co-reference app-owned assets; externally supplied files remain unowned."""
        with self.ownership_lock:
            self._reference(root, files)

    def _reference(self, root: Path, files: list[Path]):
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

    if "--guard-uninstall" in sys.argv:
        guard_uninstall(Path(sys.argv[1]))
        print("User storage is outside the program folders.")
    else:
        result = remove_owned_models(Path(sys.argv[1]))
        # Bound installer output; Python callers still receive detailed lists.
        print(json.dumps({key: len(value) for key, value in result.items()}))
