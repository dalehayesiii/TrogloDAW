"""Validated logical folder moves and recoverable managed-song deletion."""

from pathlib import Path
from uuid import uuid4
from datetime import datetime

import numpy as np
import soundfile as sf

from models import Canceled
from songs import song_item
from storage import digest, safe_file


def import_song(core, upload, values, progress, canceled):
    """Prepare managed copies before registering one imported finished WAV."""
    title = values.get("title", "")
    folder = values.get("folder", "")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
        raise ValueError("Name the imported song using 1–120 characters")
    if not isinstance(folder, str):
        raise ValueError("Choose an existing Library folder")
    with core._locked_catalog() as catalog:
        if folder and folder not in catalog.get("folders", []):
            raise ValueError("Choose an existing Library folder")
    source = Path(upload["path"])
    try:
        info = sf.info(source)
        if info.format not in {"WAV", "WAVEX", "RF64"} or not info.frames:
            raise ValueError("Choose a valid WAV audio file")
        if info.duration > 1200:
            raise ValueError("WAV song import supports audio up to twenty minutes")
        original, _ = sf.read(source, dtype="float32", always_2d=True)
        if not np.isfinite(original).all():
            raise ValueError("The WAV contains invalid non-finite audio")
    except (sf.LibsndfileError, OSError) as error:
        raise ValueError("The selected file is not a readable WAV") from error
    if canceled():
        raise Canceled("Song import canceled; no song was added")
    progress("Preparing imported song", 0, stage="loading")
    audio = core.load(source)
    peak = float(np.max(np.abs(audio), initial=0))
    headroom = min(1.0, 0.95 / peak) if peak else 1.0
    audio *= headroom
    identifier = uuid4().hex[:10]
    directory = safe_file(core.LIB, "assets/imports/" + identifier)
    wav = safe_file(core.LIB, f"mixes/{core._slug(title)}_{identifier}.wav")
    mp3 = safe_file(core.LIB, f"mixes/{core._slug(title)}_{identifier}.mp3")
    if wav.exists() or mp3.exists():
        raise ValueError("Import output already exists; try again")
    directory.mkdir(parents=True, exist_ok=False)
    original_file = directory / "original.wav"
    created = []
    registered = False
    try:
        with source.open("rb") as input_file, original_file.open("xb") as output:
            created.append(original_file)
            while chunk := input_file.read(8 * 1024 * 1024):
                if canceled():
                    raise Canceled("Song import canceled; no song was added")
                output.write(chunk)
        checksum = digest(source)
        if digest(original_file) != checksum:
            raise ValueError("The original WAV could not be copied completely")
        with wav.open("xb"):
            created.append(wav)
        core.save_wav(wav, audio)
        progress("Encoding imported song", 0, stage="exporting")
        with mp3.open("xb"):
            created.append(mp3)
        core.to_mp3(wav, mp3)
        if canceled():
            raise Canceled("Song import canceled; no song was added")
        # Validate the folder again at the atomic registration boundary.
        item = {
            "id": identifier,
            "name": title.strip(),
            "type": "mix",
            "is_song": True,
            "origin": "imported",
            "path": str(wav),
            "mp3": str(mp3),
            "duration": round(len(audio) / core.SR, 3),
            "source": "imported WAV",
            "created": datetime.now().astimezone().isoformat(timespec="seconds"),
            "tags": [],
            "folder": folder,
            "recipe": {
                "op": "song_import",
                "version": 1,
                "original_file": original_file.relative_to(core.LIB).as_posix(),
                "original_name": upload["name"],
                "original_sha256": checksum,
                "original_format": {
                    "sample_rate": info.samplerate,
                    "channels": info.channels,
                    "subtype": info.subtype,
                },
                "playable_format": {
                    "sample_rate": core.SR,
                    "channels": 2,
                    "subtype": "PCM_16",
                    "headroom_gain": headroom,
                },
            },
        }
        with core._locked_catalog(write=True) as catalog:
            if folder and folder not in catalog.get("folders", []):
                raise ValueError("The selected Library folder is no longer available")
            catalog["items"].append(item)
        registered = True
        progress("Song imported", 1, stage="saving", cancel_safe=False)
        return {"message": "Song imported", "song": item}
    except Exception:
        if not registered:
            for path in created:
                path.unlink(missing_ok=True)
            if not any(directory.iterdir()):
                directory.rmdir()
        raise


def selection(catalog, values):
    ids = values.get("ids")
    if not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids):
        raise ValueError("Select at least one song")
    if len(set(ids)) != len(ids):
        raise ValueError("Choose each song only once")
    items = {item["id"]: item for item in catalog["items"]}
    if any(i not in items or not song_item(items[i]) for i in ids):
        raise ValueError(
            "A selected song is no longer available. Refresh the library and select again"
        )
    return [items[i] for i in ids]


def move(core, values, canceled):
    folder = values.get("folder", "")
    if not isinstance(folder, str):
        raise ValueError("Choose a folder name")
    folder = folder.strip()
    if len(folder) > 120 or (values.get("create_folder") and not folder):
        raise ValueError("Choose a folder name between 1 and 120 characters")
    with core._locked_catalog(write=True) as catalog:
        items = selection(catalog, values)
        folders = catalog.setdefault("folders", [])
        if folder and folder not in folders:
            if not values.get("create_folder"):
                raise ValueError("Choose an existing folder")
            folders.append(folder)
        if canceled():
            raise Canceled("Move canceled; no songs changed")
        for item in items:
            item["folder"] = folder
    return {
        "message": f"Moved {len(items)} songs to {folder or 'Unfiled'}",
        "completed_ids": [item["id"] for item in items],
        "folder": folder,
    }


def delete_one(core, identifier):
    staged = []
    try:
        with core._locked_catalog(write=True) as catalog:
            item = selection(catalog, {"ids": [identifier]})[0]
            paths = {Path(p).resolve() for p in (item.get("path"), item.get("mp3")) if p}
            if any(not path.is_relative_to(core.LIB.resolve()) for path in paths):
                raise ValueError("Audio is outside managed library storage; it was not deleted")
            shared = {
                Path(p).resolve()
                for other in catalog["items"]
                if other["id"] != identifier
                for p in (other.get("path"), other.get("mp3"))
                if p
            }
            for path in paths - shared:
                if path.exists():
                    temporary = path.with_name(f".troglodaw-delete-{uuid4().hex}-{path.name}")
                    path.rename(temporary)
                    staged.append((path, temporary))
            catalog["items"] = [other for other in catalog["items"] if other["id"] != identifier]
    except Exception:
        for original, temporary in reversed(staged):
            temporary.rename(original)
        raise
    warnings = []
    for _, temporary in staged:
        try:
            temporary.unlink()
        except OSError:
            warnings.append(f"Deleted song, but cleanup retained {temporary.name}")
    return warnings


def delete(core, values, progress, canceled):
    with core._locked_catalog() as catalog:
        items = selection(catalog, values)
    outcomes = []
    for index, item in enumerate(items):
        if canceled():
            break
        progress(f"Deleting song {index + 1} of {len(items)}", index / len(items), stage="deleting")
        try:
            warnings = delete_one(core, item["id"])
            outcomes.append(
                {"id": item["id"], "name": item["name"], "status": "deleted", "warnings": warnings}
            )
        except (OSError, ValueError) as error:
            outcomes.append(
                {"id": item["id"], "name": item["name"], "status": "failed", "message": str(error)}
            )
    completed = [item["id"] for item in outcomes if item["status"] == "deleted"]
    failures = [
        f"{item['name']}: {item['message']}" for item in outcomes if item["status"] == "failed"
    ]
    warnings = [warning for item in outcomes for warning in item.get("warnings", [])]
    result = {
        "message": f"Deleted {len(completed)} of {len(items)} songs",
        "completed_ids": completed,
        "outcomes": outcomes,
        "problems": failures + warnings,
    }
    if len(outcomes) != len(items):
        error = Canceled(f"Deletion canceled. {result['message']}; remaining songs were kept")
        error.result = result
        raise error
    return result
