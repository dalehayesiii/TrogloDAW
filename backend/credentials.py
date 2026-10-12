"""Optional release access; secrets never belong in app configuration."""

from __future__ import annotations

import ctypes
import os
import re
import shutil
import subprocess
from pathlib import Path

TARGET = "TrogloDAW:GitHub:dalehayesiii/music-maker"


def installation_target(owner):
    if not isinstance(owner, str) or not owner.isalnum():
        raise ValueError("Invalid installation identity")
    return TARGET + ":" + owner


class Credential(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint32),
        ("kind", ctypes.c_uint32),
        ("target", ctypes.c_wchar_p),
        ("comment", ctypes.c_wchar_p),
        ("written", ctypes.c_uint32 * 2),
        ("size", ctypes.c_uint32),
        ("blob", ctypes.c_void_p),
        ("persist", ctypes.c_uint32),
        ("attribute_count", ctypes.c_uint32),
        ("attributes", ctypes.c_void_p),
        ("alias", ctypes.c_wchar_p),
        ("username", ctypes.c_wchar_p),
    ]


def credential_api():
    if os.name != "nt":
        raise OSError("Saved release access is available in Windows Credential Manager")
    api = getattr(ctypes, "WinDLL")("advapi32", use_last_error=True)
    api.CredReadW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.POINTER(Credential)),
    ]
    api.CredReadW.restype = ctypes.c_int32
    api.CredWriteW.argtypes = [ctypes.POINTER(Credential), ctypes.c_uint32]
    api.CredWriteW.restype = ctypes.c_int32
    api.CredDeleteW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
    api.CredDeleteW.restype = ctypes.c_int32
    api.CredFree.argtypes = [ctypes.c_void_p]
    return api


def read(target=TARGET):
    if os.name != "nt":
        return None
    api = credential_api()
    value = ctypes.POINTER(Credential)()
    if not api.CredReadW(target, 1, 0, ctypes.byref(value)):
        if getattr(ctypes, "get_last_error")() == 1168:
            return None
        raise OSError("Windows release credential could not be read")
    try:
        return ctypes.string_at(value.contents.blob, value.contents.size).decode("utf-8")
    finally:
        api.CredFree(value)


def save(token: str, target=TARGET):
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,2000}", token):
        raise ValueError("Enter a GitHub access token without spaces")
    api = credential_api()
    data = token.encode("utf-8")
    buffer = ctypes.create_string_buffer(data)
    value = Credential(
        kind=1,
        target=target,
        size=len(data),
        blob=ctypes.cast(buffer, ctypes.c_void_p),
        persist=2,
        username="TrogloDAW release access",
    )
    if not api.CredWriteW(ctypes.byref(value), 0):
        raise OSError("Windows release credential could not be saved")


def remove(target=TARGET):
    api = credential_api()
    if not api.CredDeleteW(target, 1, 0) and getattr(ctypes, "get_last_error")() != 1168:
        raise OSError("Windows release credential could not be removed")


def cli_locations():
    if os.name != "nt":
        return []
    locations = [Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "GitHub CLI/gh.exe"]
    if local := os.environ.get("LOCALAPPDATA"):
        locations.extend(
            [
                Path(local) / "Programs/GitHub CLI/gh.exe",
                Path(local) / "Microsoft/WinGet/Links/gh.exe",
            ]
        )
    return locations


def find_cli():
    if executable := shutil.which("gh"):
        return executable
    return next((str(path) for path in cli_locations() if path.is_file()), None)


def candidates(target=TARGET):
    """Keep tokens in memory, with the user's preferred CLI identity first."""
    result = []
    try:
        if token := read(target):
            result.append((token, "Windows Credential Manager"))
    except OSError:
        pass
    if token := os.environ.get("TROGLODAW_GITHUB_TOKEN"):
        result.append((token, "Environment"))
    if gh := find_cli():
        for account in ["purpledragondude7", "s116821", None]:
            try:
                arguments = [gh, "auth", "token", "--hostname", "github.com"]
                if account is not None:
                    arguments.extend(["--user", account])
                command = subprocess.run(
                    arguments,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    timeout=5,
                    creationflags=0x08000000 if os.name == "nt" else 0,
                )
                if command.returncode == 0 and (token := command.stdout.strip()):
                    if all(token != existing for existing, _ in result):
                        result.append((token, "GitHub CLI: " + (account or "active account")))
            except (OSError, subprocess.TimeoutExpired):
                pass
    return [*result, ("", "Public release access")]


if __name__ == "__main__":
    import json
    import sys

    path = Path(sys.argv[1])
    value = {}
    if path.exists():
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
        except UnicodeError:
            value = json.loads(path.read_text(encoding="utf-16"))
    if value.get("installation_id"):
        remove(installation_target(value["installation_id"]))
    print("This installation's saved release access was removed.")
