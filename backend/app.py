"""Local Python service and browser launcher for the compiled Angular UI."""

from __future__ import annotations

import argparse
import json
import os
import socket
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
from models import Canceled, Models
from songs import Songs, song_item
from storage import Storage

FRONTEND = Path(__file__).resolve().parents[1] / "frontend" / "dist" / "browser"
VOICE_T, MUSIC_T, ANY_T = "voice", "music,generated,mix", "voice,music,generated,mix"


class Action(BaseModel):
    action: str
    values: dict = {}


class MusicService:
    """One processing worker keeps heavy DSP off the HTTP event loop."""

    def __init__(self, core):
        self.core = core
        self.scratch = tempfile.TemporaryDirectory(prefix="troglodaw-")
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="troglodaw-dsp")
        self.jobs = {}
        self.media = {}
        self.uploads = {}
        self.lock = threading.RLock()
        self.storage = Storage(core)
        self.models = Models(self.storage)
        self.songs = Songs(core, self.models, self.file)
        self.cancel_events = {}

    def close(self):
        self.pool.shutdown(wait=True)
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
        with self.lock:
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
        self.pool.submit(self._work, jid, action, values)
        return {"id": jid}

    def _work(self, jid, action, values):
        cancel = self.cancel_events[jid]

        def progress(message, fraction=0, **details):
            with self.lock:
                self.jobs[jid].update(
                    status="running",
                    progress=min(0.99, fraction),
                    message=message,
                    **{k: v for k, v in details.items() if k != "diagnostic"},
                )

        progress("Processing...", 0.05)
        try:
            if cancel.is_set():
                raise Canceled("Canceled before processing")
            result = self.execute(action, values, progress, cancel.is_set)
            with self.lock:
                self.jobs[jid].update(status="complete", progress=1, result=result)
        except Canceled as exc:
            with self.lock:
                self.jobs[jid].update(
                    status="canceled", message=str(exc), result=exc.result or self.result(str(exc))
                )
        except Exception as exc:
            message = f"Produce failed: {exc}" if action == "produce" else str(exc)
            with self.lock:
                self.jobs[jid].update(status="failed", message=message, result=self.result(message))

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
        if action == "vocal_prepare":
            return self.songs.prepare_fx(v["song_id"], progress, canceled, v.get("segments"))
        if action == "vocal_render":
            return self.songs.render_fx(v, progress, canceled)
        if action == "rerender_song":
            return self.result("Rerendered arrangement", self.songs.rerender(v["song_id"]))
        if action == "model_install":
            return self.result(
                "Model setup complete", models=self.models.install(v["model"], progress, canceled)
            )
        if action == "storage":
            changed = self.storage.change(v["kind"], v["path"], v.get("mode", "open"), progress)
            # Previously registered tokens remain valid against the retained original copy.
            return self.result(
                "Storage updated; the original remains as a recovery copy"
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


def create_app(core=troglodaw, frontend=FRONTEND, quit_callback=None):
    service = MusicService(core)

    @asynccontextmanager
    async def lifespan(_app):
        yield
        service.close()

    api = FastAPI(title="troglodaw", lifespan=lifespan)
    api.state.service = service

    @api.middleware("http")
    async def local_mutations(request: Request, call_next):
        # Custom headers cannot be sent by cross-origin forms; no CORS is enabled.
        if (
            request.method in {"POST", "PATCH", "DELETE"}
            and request.headers.get("x-troglodaw-request") != "1"
        ):
            from fastapi.responses import JSONResponse

            return JSONResponse({"detail": "Missing local request header"}, status_code=403)
        return await call_next(request)

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
            return {"jobs": [dict(job) for job in service.jobs.values()]}

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
            return dict(service.jobs[jid])

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
        }

    if Path(frontend).is_dir():
        api.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return api


def _port_in_use(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.5)
        return connection.connect_ex((host, port)) == 0


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
    if args.port is None and _port_in_use("127.0.0.1", 7860):
        import urllib.request

        try:
            data = json.load(urllib.request.urlopen("http://127.0.0.1:7860/api/health", timeout=3))
            if data.get("application") == "troglodaw":
                if not args.no_browser:
                    webbrowser.open("http://127.0.0.1:7860/")
                return
        except Exception:
            pass
    port = args.port or 7860
    if args.port is None:
        while _port_in_use(args.host, port):
            port += 1
    if not args.no_browser:

        def open_when_ready():
            for _ in range(100):
                if _port_in_use(args.host, port):
                    webbrowser.open(f"http://{args.host}:{port}/")
                    return
                time.sleep(0.1)

        threading.Thread(target=open_when_ready, daemon=True).start()
    print(f"troglodaw {time.strftime('%Y-%m-%d %H:%M:%S')} library: {troglodaw.LIB}")
    uvicorn.run(create_app(), host=args.host, port=port, log_config=None)


if __name__ == "__main__":
    main()
