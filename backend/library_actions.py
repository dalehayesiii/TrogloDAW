"""Validated logical folder moves and recoverable managed-song deletion."""

from pathlib import Path
from uuid import uuid4

from models import Canceled
from songs import song_item


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
