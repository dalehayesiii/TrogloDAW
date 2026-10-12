"""Local Python service and browser launcher for the compiled Angular UI."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import threading
import time
import uuid
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import troglocore as troglodaw
import folders
from typing import Literal
from models import Canceled, Models
from songs import Songs, song_item
from storage import Storage
from timing import History, Tracking
from updates import Updates
import credentials
from instance import Instance, listening_socket

FRONTEND = Path(__file__).resolve().parents[1] / "frontend" / "dist" / "browser"
VOICE_T, MUSIC_T, ANY_T = "voice", "music,generated,mix", "voice,music,generated,mix"


class Action(BaseModel):
    action: str
    values: dict = {}


class FolderRequest(BaseModel):
    kind: Literal["library", "model"]


class UpdatePreference(BaseModel):
    check_on_startup: bool


class CaptureState(BaseModel):
    client_id: str
    active: bool


class MusicService:
    """One processing worker keeps heavy DSP off the HTTP event loop."""

    def __init__(self, core, updates_factory=Updates):
        self.core = core
        self.scratch = tempfile.TemporaryDirectory(prefix="troglodaw-")
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="troglodaw-dsp")
        self.setup_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="troglodaw-setup")
        self.jobs = {}
        self.media = {}
        self.uploads = {}
        self.lock = threading.RLock()
        self.storage = Storage(core)
        self.models = Models(self.storage)
        self.storage.model_manifest = self.models.manifest
        self.songs = Songs(core, self.models, self.file)
        self.cancel_events = {}
        self.timing = {}
        self.history = History(core.CONFIG_DIR / "timing-history.json")
        self.updates = updates_factory(self.storage)
        self.handoff = False
        self.active_uploads = 0
        self.recording_leases = {}

    def timing_profile(self, action, values):
        import platform
        import hashlib
        from songs import generation_mode, generation_parameters

        profile = {
            "operation": action,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "model": self.models.selected,
            "runtime": self.models.manifest["runtime_revision"],
            "manifest": hashlib.sha256(
                json.dumps(self.models.manifest, sort_keys=True).encode()
            ).hexdigest(),
            "outputs": values.get("count", 2) if action == "song_generate" else 1,
            "model_storage": self.storage.models.anchor,
            "library_storage": self.core.LIB.anchor,
        }
        profile.update(self.storage.preferences.get("timing_hardware", {}).get(action, {}))
        try:
            if action == "song_generate":
                sources = self.songs.collect_sources(values)
                params = generation_parameters(values, sources, 0)
                profile.update(
                    duration=None
                    if params["requested"]["duration"] == "auto"
                    else params["duration"],
                    duration_mode="auto"
                    if params["requested"]["duration"] == "auto"
                    else "explicit",
                    steps=params["steps"],
                    sources=len(sources),
                    input_seconds=round(sum(s["duration"] for s in sources), 1),
                    conditioning=generation_mode(values, self.models, bool(sources))[
                        "effective_mode"
                    ],
                    adherence=generation_mode(values, self.models, bool(sources))[
                        "audio_adherence"
                    ],
                    guidance=params["guidance"] > 1,
                    method=params["method"],
                    sample_caps=[s["settings"].get("samples", 8) for s in sources],
                )
            elif action in {"vocal_prepare", "vocal_render", "rerender_song"}:
                item = self.core.get_item(values["song_id"])
                profile.update(
                    duration=round(item["duration"], 1), fx=values.get("group_settings", {})
                )
                if action in {"vocal_prepare", "vocal_render"}:
                    original = (item.get("recipe") or {}).get("source_song_id", item["id"])
                    profile.update(
                        model="hdemucs-high+ecapa",
                        cache=any(
                            (self.core.LIB / "assets/vocals" / original).glob("*/analysis.json")
                        ),
                    )
            elif action == "model_install":
                profile.update(model=values["model"])
                from models import runtime_signature
                from storage import safe_file

                assets = self.models.assets(values["model"], bool(values.get("planner")))
                root = self.storage.models
                present = sum(
                    asset["bytes"]
                    for asset in assets
                    if (path := safe_file(root, asset["path"])).is_file()
                    and path.stat().st_size == asset["bytes"]
                )
                total = sum(asset["bytes"] for asset in assets)
                profile.update(
                    setup_cache="complete"
                    if present == total
                    else "partial"
                    if present
                    else "empty",
                    runtime_cached=(
                        root / "runtime-packages" / runtime_signature()[:16] / ".complete"
                    ).is_file(),
                )
            elif action == "storage":
                profile.update(
                    storage_kind=values.get("kind"), storage_mode=values.get("mode", "open")
                )
        except (KeyError, ValueError, OSError):
            # Invalid requests retain the normal worker failure/reporting path.
            pass
        return profile

    def job_snapshot(self, jid):
        state = {**self.jobs[jid], **self.timing[jid].snapshot()}
        if state["status"] == "queued":
            earlier = []
            for identifier, job in self.jobs.items():
                if identifier == jid:
                    break
                if (job["action"] == "model_install") != (state["action"] == "model_install"):
                    continue
                if job["status"] in {"queued", "running"}:
                    if job["status"] == "queued" and self.cancel_events[identifier].is_set():
                        continue
                    earlier.append(identifier)
            wait = {"low": 0, "high": 0, "basis": "queue", "samples": 0}
            for identifier in earlier:
                if self.jobs[identifier]["status"] == "running":
                    predicted = self.timing[identifier].snapshot()["request_remaining"]
                else:
                    predicted = self.history.estimate("request", self.timing[identifier].profile)
                if predicted is None:
                    wait = None
                    break
                wait["low"] += predicted["low"]
                wait["high"] += predicted["high"]
                wait["samples"] += predicted["samples"]
            state["queue_remaining"] = wait
        state["cancel_requested"] = self.cancel_events[jid].is_set()
        return state

    def close(self):
        self.pool.shutdown(wait=True)
        self.setup_pool.shutdown(wait=True)
        self.scratch.cleanup()

    def file(self, path):
        if not path:
            return None
        token = uuid.uuid4().hex
        with self.lock:
            self.media[token] = Path(path)
        return {"url": f"/api/media/{token}", "name": Path(path).name}

    def library(self):
        items = list(reversed(self.core.list_items()))
        with self.core._locked_catalog() as catalog:
            folders = catalog.get("folders", [])
        return {
            "items": items,
            "styles": list(self.core.DRUM_STYLES),
            "library": str(self.core.LIB),
            "inbox": str(self.core.INBOX),
            "folders": folders,
            "storage": self.storage.describe(),
            "models": self.models.describe(),
        }

    def result(self, message="", item=None, audio=None, mp3=None, **extra):
        return {
            "message": message,
            "audio": self.file(audio or (item or {}).get("path")),
            "download": self.file(mp3 or (item or {}).get("mp3")),
            **extra,
        }

    def submit(self, action, values):
        if action not in {
            "import",
            "inbox",
            "delete",
            "tags",
            "fx",
            "generate",
            "mix",
            "produce",
            "accept_audio",
            "song_generate",
            "lyrics_generate",
            "vocal_prepare",
            "vocal_render",
            "folder",
            "organize",
            "storage",
            "model_install",
            "rerender_song",
        }:
            raise HTTPException(422, "Unknown operation")
        jid = uuid.uuid4().hex
        tracker = Tracking(
            self.history,
            self.timing_profile(action, values),
            confirm_hardware=action in {"song_generate", "vocal_prepare", "vocal_render"},
        )
        with self.lock:
            if self.handoff:
                raise HTTPException(409, "The app is installing an update")
            if action in {"storage", "model_install"} and any(
                job["status"] in {"queued", "running"}
                and job["action"] == ("model_install" if action == "storage" else "storage")
                for job in self.jobs.values()
            ):
                raise HTTPException(
                    409, "Finish model installation before changing storage, and vice versa"
                )
            if action in {"storage", "model_install"} and self.updates.snapshot()["phase"] in {
                "downloading",
                "handoff",
            }:
                raise HTTPException(
                    409, "Wait for the update operation before changing model/storage setup"
                )
            if action == "model_install":
                self.storage.preferences["setup_seen"] = True
                self.storage.persist()
            self.jobs[jid] = {
                "status": "queued",
                "progress": 0,
                "message": "Queued",
                "result": None,
                "id": jid,
                "action": action,
                "created_at": time.time(),
                "song_id": values.get("song_id"),
            }
            self.cancel_events[jid] = threading.Event()
            self.timing[jid] = tracker
        worker = self.setup_pool if action == "model_install" else self.pool
        worker.submit(self._work, jid, action, values)
        return {"id": jid}

    def _work(self, jid, action, values):
        cancel = self.cancel_events[jid]
        tracker = self.timing[jid]

        def progress(message, fraction=0, **details):
            cancel_safe = details.pop("cancel_safe", True)
            if cancel.is_set() and cancel_safe:
                raise Canceled("Processing canceled; completed songs are preserved")
            with self.lock:
                hardware = details.get("timing_profile")
                if hardware and "gpu" in hardware:
                    # Remember actual hardware for later queued estimates; no audio data.
                    known = self.storage.preferences.setdefault("timing_hardware", {})
                    known[action] = {
                        k: v for k, v in hardware.items() if k not in {"duration", "steps", "model"}
                    }
                    try:
                        self.storage.persist()
                    except OSError:
                        # Optional timing metadata must not fail an audio operation.
                        pass
                tracker.update(message, fraction, **details)
                self.jobs[jid].update(
                    status="running",
                    progress=tracker.snapshot()["stage_progress"] or 0,
                    message=message,
                    **{
                        k: v
                        for k, v in details.items()
                        if k not in {"diagnostic", "timing_profile", "timing_stage_profile"}
                    },
                )

        tracker.start()
        with self.lock:
            self.jobs[jid]["started_at"] = time.time()
        try:
            progress("Initializing operation", 0, stage="initializing")
            if cancel.is_set():
                raise Canceled("Canceled before processing")
            result = self.execute(action, values, progress, cancel.is_set)
            with self.lock:
                self.jobs[jid].update(status="complete", progress=1, result=result)
                tracker.finish("complete")
        except Canceled as exc:
            with self.lock:
                self.jobs[jid].update(
                    status="canceled", message=str(exc), result=exc.result or self.result(str(exc))
                )
                tracker.finish("canceled")
        except Exception as exc:
            message = f"Produce failed: {exc}" if action == "produce" else str(exc)
            with self.lock:
                self.jobs[jid].update(status="failed", message=message, result=self.result(message))
                tracker.finish("failed")

    def execute(self, action, v, progress, canceled=lambda: False):
        core = self.core
        if action == "accept_audio":
            accepted = []
            for token in v.get("uploads", []):
                upload = self.uploads[token]
                audio = core.decode_any(upload["path"])
                if not len(audio) or float(abs(audio).max()) < 1e-5:
                    raise ValueError(
                        "This take has no audible audio. Record again or choose another file"
                    )
                item = core._new_entry(
                    "voice",
                    v.get("name") or Path(upload["name"]).stem,
                    audio,
                    "import:" + upload["name"],
                    recipe={"op": "import", "original": upload["name"], "normalized": False},
                )
                item = core.update_item(
                    item["id"],
                    source_type="microphone" if v.get("source_type") == "microphone" else "upload",
                )
                accepted.append({"item": item, "audio": self.file(item["path"])})
            return self.result("Audio added", accepted=accepted)
        if action == "song_generate":
            return self.songs.generate(v, progress, canceled)
        if action == "lyrics_generate":
            return self.songs.lyrics(v, progress, canceled)
        if action == "vocal_prepare":
            return self.songs.prepare_fx(v["song_id"], progress, canceled, v.get("segments"))
        if action == "vocal_render":
            return self.songs.render_fx(v, progress, canceled)
        if action == "rerender_song":
            return self.result(
                "Rerendered arrangement", self.songs.rerender(v["song_id"], progress, canceled)
            )
        if action == "model_install":
            if not isinstance(v.get("planner", False), bool):
                raise ValueError("Choose whether to install the optional song planner")
            if v.get("planner"):
                return self.result(
                    "Song writing tools and music model setup complete",
                    models=self.models.install(v["model"], progress, canceled, planner=True),
                )
            return self.result(
                "Model setup complete", models=self.models.install(v["model"], progress, canceled)
            )
        if action == "storage":

            def committed(old, new, copied):
                if v["kind"] == "library" and old != new:
                    with self.lock:
                        for token, path in self.media.items():
                            if path.is_relative_to(old):
                                relative = path.relative_to(old).as_posix()
                                if relative in copied:
                                    self.media[token] = new / relative

            changed = self.storage.change(
                v["kind"], v["path"], v.get("mode", "open"), progress, committed
            )
            return self.result(
                f"Storage updated; {changed['retained_files']} shared, changed or unavailable original files were retained"
                if changed.get("retained_files")
                else "Storage updated; the original remains as a recovery copy"
                if changed.get("recovery_copy")
                else "Storage updated",
                storage=changed,
            )
        if action == "folder":
            name = str(v.get("name", "")).strip()
            if not name or len(name) > 120:
                raise ValueError("Choose a folder name between 1 and 120 characters")
            with core._locked_catalog(write=True) as catalog:
                folders = catalog.setdefault("folders", [])
                if name not in folders:
                    folders.append(name)
            return self.result("Folder created")
        if action == "organize":
            item = core.get_item(v["id"])
            if not song_item(item):
                raise ValueError("Choose a library song")
            fields = {}
            if "name" in v:
                name = str(v["name"]).strip()
                if not name or len(name) > 120:
                    raise ValueError("Choose a song name between 1 and 120 characters")
                fields["name"] = name
            if "folder" in v:
                with core._locked_catalog() as catalog:
                    if v["folder"] and v["folder"] not in catalog.get("folders", []):
                        raise ValueError("Choose an existing folder")
                fields["folder"] = v["folder"]
            core.update_item(item["id"], **fields)
            return self.result("Song updated")
        if action == "import":
            if not v.get("uploads"):
                return self.result("No files.")
            messages = []
            for token in v["uploads"]:
                upload = self.uploads[token]
                item = core.import_file(
                    upload["path"],
                    v.get("type", "voice"),
                    name=Path(upload["name"]).stem,
                    tags=[tag.strip() for tag in v.get("tags", "").split(",") if tag.strip()],
                )
                messages.append(f"Imported {item['name']} ({item['id']}, {item['duration']:.1f}s)")
            return self.result("\n".join(messages))
        if action == "inbox":
            items = core.import_paths([core.INBOX], v.get("type", "voice"), move_from_inbox=True)
            return self.result(
                f"Imported {len(items)} file(s) from {core.INBOX}"
                if items
                else f"Inbox empty ({core.INBOX})"
            )
        if action in {"delete", "tags"}:
            if not v.get("id"):
                return self.result("Pick an item.")
            if action == "delete":
                item = core.delete_item(v["id"])
                return self.result(f"Deleted {item['name']}")
            fields = {"tags": [tag.strip() for tag in v.get("tags", "").split(",") if tag.strip()]}
            if v.get("name", "").strip():
                fields["name"] = v["name"].strip()
            core.update_item(v["id"], **fields)
            return self.result("Updated.")
        if action == "fx":
            if not v.get("voice"):
                return self.result("Pick a voice.")
            if v.get("save"):
                item = core.voice_fx(v["voice"], v["settings"], name=v.get("name") or None)
                return self.result(f"Saved new voice {item['name']} ({item['id']})", item)
            audio = core.apply_fx(core.load_item(v["voice"]), v["settings"])
            path = Path(self.scratch.name) / f"{uuid.uuid4().hex}.wav"
            core.save_wav(path, audio)
            return self.result("Preview only (not saved)", audio=path)
        if action == "generate":
            settings = dict(v["settings"])
            seed = settings.get("seed", -1)
            settings["seed"] = int(seed) if seed is not None and float(seed) >= 0 else None
            settings["progression"] = settings.get("progression") or None
            item = core.generate(settings, name=v.get("name") or None)
            saved = item["recipe"]["settings"]
            return self.result(
                f"Generated {item['name']} ({item['id']}), seed={saved['seed']}, progression={saved['progression']}",
                item,
            )
        if action == "mix":
            if not v.get("voice") or not v.get("music"):
                return self.result("Pick a voice and a music track.")
            settings = dict(v["settings"])
            if v.get("fx", "").strip():
                try:
                    settings["voice_fx"] = json.loads(v["fx"])
                except Exception as exc:
                    return self.result(f"Bad voice FX JSON: {exc}")
            item = core.mix(v["voice"], v["music"], settings, name=v.get("name") or None)
            return self.result(f"Mixed {item['name']} ({item['id']})\nmp3: {item['mp3']}", item)
        if action == "produce":
            voice = v.get("voice")
            if v.get("upload"):
                progress("Importing recording...", 0.05)
                upload = self.uploads[v["upload"]]
                voice = core.import_file(upload["path"], "voice", name=Path(upload["name"]).stem)[
                    "id"
                ]
            if not voice:
                return self.result("Pick a voice or drop a recording first.")
            steps = {
                "analyzing vocal...": 0.15,
                "generating beat...": 0.45,
                "mixing & mastering...": 0.75,
            }
            item = core.produce(
                voice,
                style=None if v.get("style", "auto") == "auto" else v["style"],
                mood=None if v.get("mood", "auto") == "auto" else v["mood"],
                bpm=float(v["bpm"]) if v.get("bpm") else None,
                key=v.get("key", "").strip() or None,
                tune=v.get("tune", "auto"),
                seed=int(v["seed"])
                if v.get("seed") is not None and float(v["seed"]) >= 0
                else None,
                log=lambda msg: progress(
                    msg.capitalize() if msg in steps else msg, steps.get(msg, 0.5)
                ),
            )
            production = item["recipe"]["produce"]
            return self.result(item=item, production=production, song=item)
        raise ValueError("Unknown operation")


def create_app(
    core=troglodaw,
    frontend=FRONTEND,
    quit_callback=None,
    folder_picker=None,
    updates_factory=None,
    instance_id=None,
):
    service = MusicService(core, updates_factory or Updates)

    @asynccontextmanager
    async def lifespan(_app):
        service.updates.startup()
        yield
        service.close()

    api = FastAPI(title="troglodaw", lifespan=lifespan)
    api.state.service = service
    picker_lock = threading.Lock()
    pick_folder = folder_picker or folders.choose

    @api.middleware("http")
    async def local_mutations(request: Request, call_next):
        # Custom headers cannot be sent by cross-origin forms; no CORS is enabled.
        if (
            request.method in {"POST", "PATCH", "DELETE"}
            and request.headers.get("x-troglodaw-request") != "1"
        ):
            from fastapi.responses import JSONResponse

            return JSONResponse({"detail": "Missing local request header"}, status_code=403)
        uploading = request.method == "POST" and request.url.path == "/api/uploads"
        with service.lock:
            if request.method in {"POST", "PATCH", "DELETE"} and service.handoff:
                from fastapi.responses import JSONResponse

                return JSONResponse({"detail": "The app is installing an update"}, status_code=409)
            if uploading:
                service.active_uploads += 1
        try:
            return await call_next(request)
        finally:
            if uploading:
                with service.lock:
                    service.active_uploads -= 1

    @api.get("/api/updates")
    def update_status():
        with service.lock:
            blocked = bool(
                service.active_uploads
                or picker_lock.locked()
                or any(job["status"] in {"queued", "running"} for job in service.jobs.values())
                or any(expiry > time.monotonic() for expiry in service.recording_leases.values())
            )
            return {
                **service.updates.snapshot(),
                "install_allowed": not blocked and not service.handoff,
            }

    @api.post("/api/updates/preferences")
    def update_preferences(preference: UpdatePreference):
        with service.lock:
            service.storage.preferences["check_updates"] = preference.check_on_startup
            service.storage.persist()
        return service.updates.snapshot()

    @api.post("/api/updates/check")
    def check_updates():
        try:
            return service.updates.check()
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @api.post("/api/updates/access")
    async def save_release_access(request: Request):
        # Avoid validation errors echoing a sensitive request field.
        try:
            payload = await request.json()
            token = payload.get("token") if isinstance(payload, dict) else None
            if not isinstance(token, str):
                raise ValueError("Enter a GitHub release-access token")
            credentials.save(token, service.updates.credential_target)
            service.updates.set_state(saved_access=True)
            return service.updates.snapshot()
        except (ValueError, OSError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @api.post("/api/updates/access/remove")
    def remove_release_access():
        try:
            credentials.remove(service.updates.credential_target)
            service.updates.set_state(saved_access=False)
            return service.updates.snapshot()
        except OSError as exc:
            raise HTTPException(400, str(exc)) from exc

    @api.post("/api/updates/capture")
    def report_capture(capture: CaptureState):
        try:
            client = uuid.UUID(capture.client_id).hex
        except ValueError as exc:
            raise HTTPException(400, "Invalid recording session") from exc
        with service.lock:
            now = time.monotonic()
            service.recording_leases = {
                key: expiry for key, expiry in service.recording_leases.items() if expiry > now
            }
            if capture.active:
                if len(service.recording_leases) >= 64 and client not in service.recording_leases:
                    raise HTTPException(409, "Too many active recording sessions")
                service.recording_leases[client] = now + 30
            else:
                service.recording_leases.pop(client, None)
        return {"message": "Recording state updated"}

    @api.post("/api/updates/download")
    def download_update():
        with service.lock:
            if any(
                job["status"] in {"queued", "running"}
                and job["action"] in {"storage", "model_install"}
                for job in service.jobs.values()
            ):
                raise HTTPException(409, "Finish model/storage setup before downloading an update")
            try:
                return service.updates.download()
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from exc

    @api.post("/api/updates/cancel")
    def cancel_update():
        try:
            return service.updates.cancel()
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @api.post("/api/updates/apply")
    def apply_update(request: Request):
        with service.lock:
            if (
                service.active_uploads
                or picker_lock.locked()
                or any(job["status"] in {"queued", "running"} for job in service.jobs.values())
                or any(expiry > time.monotonic() for expiry in service.recording_leases.values())
            ):
                raise HTTPException(
                    409,
                    "Finish processing, uploads and folder selection, and stop recordings in all app tabs before updating",
                )
            service.handoff = True
            try:
                host = request.url.hostname
                if host not in {"127.0.0.1", "localhost", "::1"}:
                    raise ValueError("Open the app on localhost before installing an update")
                result = service.updates.apply(
                    pid=os.getpid(), host=host, port=request.url.port or 80
                )
            except (ValueError, OSError) as exc:
                service.handoff = False
                raise HTTPException(409, str(exc)) from exc
            callback = quit_callback or (lambda: os._exit(0))
            threading.Timer(0.8, callback).start()
            return result

    @api.post("/api/setup/acknowledge")
    def acknowledge_setup():
        with service.lock:
            service.storage.preferences["setup_seen"] = True
            service.storage.persist()
        return {"message": "Setup can be resumed from Settings"}

    @api.get("/api/library")
    def library():
        return service.library()

    @api.get("/api/items/{iid}")
    def item(iid: str):
        try:
            entry = core.get_item(iid)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        rec = entry.get("recipe") or {}
        rec = rec.get("creation_recipe", rec)
        references = [
            (
                "Generated whole mix"
                if rec.get("render_mode") == "conditioned"
                else "Generated musical parts",
                rec.get("musical_file"),
            ),
            ("Transformed sample arrangement", rec.get("conditioning_file")),
        ]
        references.extend(
            ("Original input: " + value.get("label", value["id"]), value.get("file"))
            for value in rec.get("sources", [])
        )
        references.extend(
            ("Transformed sample: " + value["id"], value.get("file"))
            for value in rec.get("samples", [])
        )
        assets = []
        for label, relative in references:
            if not relative:
                continue
            try:
                path = service.songs.asset(relative)
                assets.append(
                    {"label": label, "media": service.file(path) if path.is_file() else None}
                )
            except ValueError:
                assets.append({"label": label, "media": None})
        return {"item": entry, "audio": service.file(entry["path"]), "assets": assets}

    @api.get("/api/recipes/{iid}")
    def recipe(iid: str):
        try:
            entry = core.get_item(iid)
            rec = entry["recipe"]
            if rec.get("op") != "mix":
                raise ValueError("Not a saved mix recipe")
            settings = {**core.MIX_DEFAULTS, **rec["settings"]}
            return {
                "voice": rec["voice_id"],
                "music": rec["music_id"],
                "name": entry["name"] + "_remix",
                "fx": json.dumps(settings["voice_fx"]) if settings.get("voice_fx") else "",
                "settings": settings,
            }
        except (KeyError, ValueError) as exc:
            raise HTTPException(404, str(exc)) from exc

    @api.post("/api/storage/pick")
    def select_folder(selection: FolderRequest):
        with service.lock:
            if service.handoff:
                raise HTTPException(409, "The app is installing an update")
            if not picker_lock.acquire(blocking=False):
                raise HTTPException(409, "A folder picker is already open")
        try:
            initial = str(service.storage.models if selection.kind == "model" else core.LIB)
            return {"path": pick_folder(initial, f"Choose {selection.kind} storage folder")}
        except OSError as exc:
            raise HTTPException(503, str(exc)) from exc
        finally:
            picker_lock.release()

    @api.post("/api/uploads")
    async def upload(file: UploadFile = File(...)):
        token = uuid.uuid4().hex
        name = Path((file.filename or "recording").replace("\\", "/")).name
        path = Path(service.scratch.name) / f"{token}{Path(name).suffix}"
        with path.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                target.write(chunk)
        await file.close()
        with service.lock:
            service.uploads[token] = {"name": name, "path": path}
        return {"id": token, "name": name}

    @api.post("/api/jobs")
    def jobs(action: Action):
        return service.submit(action.action, action.values)

    @api.get("/api/jobs")
    def active_jobs():
        with service.lock:
            return {"jobs": [service.job_snapshot(jid) for jid in service.jobs]}

    @api.post("/api/jobs/{jid}/cancel")
    def cancel_job(jid: str):
        with service.lock:
            if jid not in service.jobs:
                raise HTTPException(404, "Unknown job")
            service.cancel_events[jid].set()
        return {"message": "Cancellation requested"}

    @api.get("/api/ingredients/{iid}")
    def ingredients(iid: str):
        try:
            return service.songs.ingredients(iid)
        except (KeyError, ValueError) as exc:
            raise HTTPException(404, str(exc)) from exc

    @api.get("/api/jobs/{jid}")
    def job(jid: str):
        with service.lock:
            if jid not in service.jobs:
                raise HTTPException(404, "Unknown job")
            return service.job_snapshot(jid)

    @api.get("/api/media/{token}")
    def media(token: str, download: bool = False):
        path = service.media.get(token)
        if path is None or not path.is_file():
            raise HTTPException(404, "Media unavailable")
        return FileResponse(
            path,
            filename=path.name,
            content_disposition_type="attachment" if download else "inline",
        )

    @api.post("/api/shutdown")
    def shutdown():
        for event in service.cancel_events.values():
            event.set()
        callback = quit_callback or (lambda: os._exit(0))
        threading.Timer(0.8, callback).start()
        return {"message": "TrogloDAW has stopped. You can close this browser tab."}

    @api.get("/api/health")
    def health():
        return {
            "application": "troglodaw",
            "product": "TrogloDAW",
            "frontend": (Path(frontend) / "index.html").is_file(),
            "version": service.updates.identity["version"],
            "sha": service.updates.identity["sha"],
            "instance_id": instance_id,
        }

    if Path(frontend).is_dir():
        api.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return api


def main():
    parser = argparse.ArgumentParser(description="troglodaw web UI")
    parser.add_argument("--host", default=str(troglodaw.setting("host")))
    parser.add_argument("--port", type=int, default=int(troglodaw.setting("port") or 0) or None)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if sys.stdout is None or sys.stderr is None:
        log = open(troglodaw.LIB / "troglodaw.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log
    if not FRONTEND.joinpath("index.html").is_file():
        parser.exit(
            1, "Frontend missing. Run npm ci --ignore-scripts && npm run build, then start again.\n"
        )
    instance = Instance(troglodaw.CONFIG_DIR, args.host)
    listener = None
    try:
        if url := instance.claim_or_reopen():
            if not args.no_browser:
                webbrowser.open(url)
            return
        listener, port = listening_socket(args.host, args.port)
        url = instance.publish(args.host, port)

        def stop_server():
            server.should_exit = True

        api = create_app(quit_callback=stop_server, instance_id=instance.id)
        server = uvicorn.Server(uvicorn.Config(api, host=args.host, port=port, log_config=None))
        if not args.no_browser:

            def open_when_ready():
                for _ in range(200):
                    if server.should_exit:
                        return
                    if server.started:
                        webbrowser.open(url)
                        return
                    time.sleep(0.1)

            threading.Thread(target=open_when_ready, daemon=True).start()
        print(f"troglodaw {time.strftime('%Y-%m-%d %H:%M:%S')} library: {troglodaw.LIB}")
        server.run(sockets=[listener])
    finally:
        if listener is not None:
            listener.close()
        instance.close()


if __name__ == "__main__":
    main()
