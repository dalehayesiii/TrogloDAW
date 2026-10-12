"""Explicit verified release updates, independent of local audio processing."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import credentials
from storage import atomic_json, digest, safe_file, writable_root, protect_location, guard_uninstall

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "dalehayesiii/music-maker"
API = "https://api.github.com/repos/" + REPOSITORY
INSTALLER = "TrogloDAW-Setup.exe"
HOSTS = {
    "api.github.com",
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "github-releases.githubusercontent.com",
}


def version(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", value
    ):
        raise ValueError("Expected a published stable version")
    return tuple(int(part) for part in value.split("."))


def release_identity(root=ROOT):
    try:
        value = json.loads((root / "version.json").read_text(encoding="utf-8"))
        version(value["version"])
        if value.get("repository") != REPOSITORY or not re.fullmatch(r"[0-9a-f]{40}", value["sha"]):
            raise ValueError("Invalid installed identity")
        return value
    except (OSError, ValueError, KeyError, TypeError):
        return {"version": "0.0.0", "sha": None, "repository": REPOSITORY}


def approved_url(url):
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in HOSTS
        or parsed.port not in {None, 443}
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("Update download redirected outside approved HTTPS hosts")


class ReleaseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        approved_url(newurl)
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if (
            redirected
            and urllib.parse.urlsplit(req.full_url).hostname
            != urllib.parse.urlsplit(newurl).hostname
        ):
            redirected.remove_header("Authorization")
            redirected.remove_header("Cookie")
        return redirected


class Updates:
    def __init__(self, storage, *, root=ROOT, opener=None, token_source=None, launcher=None):
        self.storage = storage
        self.root = Path(root)
        self.identity = release_identity(self.root)
        self.supported = (
            os.name == "nt"
            and self.identity["version"] != "0.0.0"
            and (self.root.parent / "python/python.exe").is_file()
        )
        self.opener = opener or urllib.request.build_opener(ReleaseRedirect())
        self.credential_target = credentials.installation_target(
            storage.preferences["installation_id"]
        )
        self.token_source = token_source or (lambda: credentials.candidates(self.credential_target))
        self.launcher = launcher or subprocess.Popen
        self.lock = threading.RLock()
        self.cancel_event = threading.Event()
        self.thread = None
        self.release: dict | None = None
        self.token = ""
        self.ready_path: Path | None = None
        self.ready_manifest: dict | None = None
        saved_access = False
        if token_source is None:
            try:
                saved_access = credentials.read(self.credential_target) is not None
            except OSError:
                pass
        self.state = {
            "phase": "idle" if self.supported else "source",
            "message": "Ready to check releases"
            if self.supported
            else "Source/development build: update from Git and rebuild; in-app installation is available in Windows releases.",
            "version": self.identity["version"],
            "supported": self.supported,
            "credential_store": os.name == "nt",
            "available_version": None,
            "bytes_done": 0,
            "bytes_total": 0,
            "saved_access": saved_access,
        }

    def snapshot(self):
        with self.lock:
            return {
                **self.state,
                "check_on_startup": self.storage.preferences.get("check_updates", True),
            }

    def set_state(self, **values):
        with self.lock:
            self.state.update(values)

    def busy(self):
        with self.lock:
            return self.state["phase"] in {"checking", "downloading", "handoff"}

    def launch_thread(self, phase, target):
        with self.lock:
            if self.busy():
                raise ValueError("An update operation is already running")
            self.cancel_event.clear()
            self.set_state(phase=phase)
            self.thread = threading.Thread(target=target, daemon=True, name="troglodaw-updates")
            self.thread.start()
        return self.snapshot()

    def startup(self):
        if self.supported and self.storage.preferences.get("check_updates", True):
            self.check()

    def check(self):
        if not self.supported:
            return self.snapshot()
        return self.launch_thread("checking", self.check_release)

    def request(self, url, *, token=None, binary=False):
        approved_url(url)
        if not url.startswith((API + "/releases", API + "/git/ref/tags/", API + "/git/tags/")):
            raise ValueError("Unexpected release endpoint")
        headers = {
            "Accept": "application/octet-stream" if binary else "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "TrogloDAW/" + self.identity["version"],
        }
        if token := (self.token if token is None else token):
            if not re.fullmatch(r"[A-Za-z0-9_]{1,2000}", token):
                raise ValueError("Release access token has invalid formatting")
            headers["Authorization"] = "Bearer " + token
        return self.opener.open(urllib.request.Request(url, headers=headers), timeout=20)

    def metadata(self, url, *, token=None, binary=False, limit=1024 * 1024):
        with self.request(url, token=token, binary=binary) as response:
            data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Release metadata exceeds the supported size")
        return data

    def check_release(self):
        self.ready_path = None
        self.ready_manifest = None
        try:
            tokens = self.token_source()
            for index, (token, label) in enumerate(tokens):
                try:
                    release = json.loads(self.metadata(API + "/releases/latest", token=token))
                    self.token = token
                    self.set_state(
                        access=label,
                        saved_access=any(
                            label == "Windows Credential Manager" for _, label in tokens
                        ),
                    )
                    break
                except urllib.error.HTTPError as exc:
                    if (
                        exc.code in {401, 403, 404}
                        and index + 1 < len(tokens)
                        and exc.headers.get("X-RateLimit-Remaining") != "0"
                    ):
                        continue
                    raise
            if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
                raise ValueError("No published stable release is available")
            available = release["tag_name"]
            if not isinstance(available, str) or not available.startswith("v"):
                raise ValueError("Release tag is not a stable version")
            available = available[1:]
            if version(available) <= version(self.identity["version"]):
                self.release = None
                self.set_state(
                    phase="current", available_version=None, message="TrogloDAW is up to date."
                )
                return
            assets = {}
            for name in [INSTALLER, "release.json", "SHA256SUMS"]:
                matches = [
                    asset for asset in release.get("assets", []) if asset.get("name") == name
                ]
                if len(matches) != 1 or matches[0].get("state") != "uploaded":
                    raise ValueError("Stable release assets are incomplete or ambiguous")
                asset = matches[0]
                if (
                    type(asset.get("id")) is not int
                    or type(asset.get("size")) is not int
                    or not 0 < asset["size"] <= 512 * 1024 * 1024
                ):
                    raise ValueError("Release asset metadata is invalid")
                assets[name] = {
                    "url": API + f"/releases/assets/{asset['id']}",
                    "size": asset["size"],
                    "digest": asset.get("digest"),
                }
            self.release = {"version": available, "assets": assets}
            self.set_state(
                phase="available",
                available_version=available,
                message=f"TrogloDAW {available} is available.",
            )
        except Exception as exc:
            self.release = None
            self.set_state(available_version=None)
            self.error(exc)

    def error(self, exc):
        if isinstance(exc, urllib.error.HTTPError):
            message = "Release access is unavailable. For private releases, add repository Contents-read access in Settings."
            if (
                exc.code == 429
                or exc.headers.get("X-RateLimit-Remaining") == "0"
                or exc.headers.get("Retry-After")
            ):
                message = "GitHub rate limit reached. Try checking again later."
        elif isinstance(exc, (urllib.error.URLError, TimeoutError, OSError)):
            message = "Update access failed. Check the connection or available storage, then retry."
        else:
            message = (
                str(exc)
                if isinstance(exc, ValueError)
                else "Update verification failed. Retry checking releases."
            )
        self.set_state(phase="failed", message=message)

    def download(self):
        if not self.supported or not self.release:
            raise ValueError("Check for an available Windows release first")
        return self.launch_thread("downloading", self.download_release)

    def update_directory(self):
        relative = "cache/" + self.storage.preferences["installation_id"] + "/updates"
        path = safe_file(self.storage.models, relative)
        if path.resolve().is_relative_to(self.root.parent.resolve()):
            # A custom model folder can be inside the app. Keep the helper on
            # that same drive, outside the directory NSIS replaces.
            path = safe_file(
                self.root.parent.parent,
                "TrogloDAW-updates/" + self.storage.preferences["installation_id"],
            )
        writable_root(str(path), 600 * 1024 * 1024)
        return path

    def download_release(self):
        self.ready_path = None
        self.ready_manifest = None
        partial = None
        try:
            release = self.release
            if release is None:
                raise ValueError("Release selection is unavailable")
            manifest = json.loads(
                self.metadata(release["assets"]["release.json"]["url"], binary=True)
            )
            checksum = self.metadata(release["assets"]["SHA256SUMS"]["url"], binary=True).decode(
                "utf-8"
            )
            if (
                manifest.get("version") != release["version"]
                or manifest.get("installer") != INSTALLER
                or not re.fullmatch(r"[0-9a-f]{40}", manifest.get("sha", ""))
                or not re.fullmatch(r"[0-9a-f]{64}", manifest.get("sha256", ""))
            ):
                raise ValueError("Release source/version manifest does not match")
            if checksum.strip() != manifest["sha256"] + "  " + INSTALLER:
                raise ValueError("Release checksum entry does not match")
            tag = json.loads(self.metadata(API + "/git/ref/tags/v" + release["version"]))["object"]
            for _ in range(2):
                if tag.get("type") == "commit":
                    break
                if tag.get("type") != "tag" or not re.fullmatch(
                    r"[0-9a-f]{40}", tag.get("sha", "")
                ):
                    raise ValueError("Release source tag is invalid")
                tag = json.loads(self.metadata(API + "/git/tags/" + tag["sha"]))["object"]
            if tag.get("type") != "commit" or tag.get("sha") != manifest["sha"]:
                raise ValueError("Release source commit does not match its tag")
            asset = release["assets"][INSTALLER]
            if asset["digest"] and asset["digest"] != "sha256:" + manifest["sha256"]:
                raise ValueError("Published asset digest does not match")
            directory = self.update_directory()
            target = safe_file(directory, release["version"] + "-" + INSTALLER)
            partial = safe_file(directory, target.name + ".partial")
            done, started = 0, time.monotonic()
            self.set_state(
                bytes_done=0,
                bytes_total=asset["size"],
                message="Downloading verified Windows update",
                remaining_seconds=None,
            )
            with self.request(asset["url"], binary=True) as response, partial.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    if self.cancel_event.is_set():
                        raise InterruptedError("Update download canceled")
                    done += len(chunk)
                    if done > asset["size"]:
                        raise ValueError("Update download exceeds its published size")
                    output.write(chunk)
                    elapsed = time.monotonic() - started
                    self.set_state(
                        bytes_done=done,
                        remaining_seconds=(asset["size"] - done) * elapsed / done,
                        elapsed_seconds=elapsed,
                    )
            if self.cancel_event.is_set():
                raise InterruptedError("Update download canceled")
            if done != asset["size"] or digest(partial) != manifest["sha256"]:
                raise ValueError("Update installer size/checksum verification failed")
            partial.replace(target)
            owner_root = (
                self.storage.models if target.is_relative_to(self.storage.models) else directory
            )
            self.storage.owned(owner_root, [target])
            with self.lock:
                if self.cancel_event.is_set():
                    raise InterruptedError("Update download canceled")
                self.ready_path, self.ready_manifest = target, manifest
                self.set_state(
                    phase="ready",
                    remaining_seconds=0,
                    message="Update verified. Install when processing and recording are stopped.",
                )
        except InterruptedError:
            self.set_state(phase="canceled", message="Update download canceled. You can retry.")
        except Exception as exc:
            self.error(exc)
        finally:
            if partial and partial.exists():
                try:
                    partial.unlink()
                except OSError:
                    pass

    def cancel(self):
        with self.lock:
            if self.state["phase"] == "handoff":
                raise ValueError("Installation has already started")
            self.cancel_event.set()
            if self.state["phase"] == "ready":
                self.ready_path = None
                self.ready_manifest = None
                self.set_state(phase="canceled", message="Update canceled. You can retry.")
        return self.snapshot()

    def apply(self, *, pid, host, port):
        with self.lock:
            if (
                not self.supported
                or self.state["phase"] != "ready"
                or not self.ready_path
                or not self.ready_manifest
            ):
                raise ValueError("Download and verify the update before installing")
            if digest(self.ready_path) != self.ready_manifest["sha256"]:
                self.ready_path = None
                self.set_state(
                    phase="failed", message="Verified installer changed. Download it again."
                )
                raise ValueError("Verified installer changed")
            protect_location(self.storage.core.LIB, self.root)
            protect_location(self.storage.models, self.root)
            guard_uninstall(self.storage.config_path, self.root)
            directory = self.update_directory()
            helper = safe_file(directory, "apply-update.ps1")
            shutil.copyfile(self.root / "scripts/windows/app_update.ps1", helper)
            plan = safe_file(directory, "update-plan.json")
            status = safe_file(directory, "update-status.json")
            if status.exists():
                status.unlink()
            atomic_json(
                plan,
                {
                    "installer": str(self.ready_path),
                    "sha256": self.ready_manifest["sha256"],
                    "version": self.ready_manifest["version"],
                    "source_sha": self.ready_manifest["sha"],
                    "install_root": str(self.root.parent),
                    "pid": pid,
                    "host": host,
                    "port": port,
                    "status": str(status),
                },
            )
            process = self.launcher(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(helper),
                    "-Plan",
                    str(plan),
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000,
            )
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if status.is_file():
                        result = json.loads(status.read_text(encoding="utf-8-sig"))
                        if result.get("phase") == "waiting":
                            self.set_state(
                                phase="handoff",
                                message="Update started. TrogloDAW will reopen after installation.",
                            )
                            return self.snapshot()
                        raise OSError("Update helper could not acknowledge its plan")
                    if process.poll() is not None:
                        raise OSError("Update helper did not start")
                    time.sleep(0.05)
                raise OSError("Update helper did not acknowledge its plan")
            except Exception:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
                raise
