"""Process-owned launch coordination for one local app per configuration root."""

from __future__ import annotations

import json
import os
import re
import socket
import time
import urllib.request
import uuid
from pathlib import Path

from storage import atomic_json


class Instance:
    def __init__(self, root, host="127.0.0.1"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.metadata = self.root / ".troglodaw-instance.json"
        self.file = (self.root / ".troglodaw-instance.lock").open("a+b")
        if self.file.seek(0, os.SEEK_END) == 0:
            self.file.write(b"0")
            self.file.flush()
        self.owned = False
        self.id = uuid.uuid4().hex
        self.host = self.browser_host(host)

    @staticmethod
    def browser_host(host):
        if host in {"0.0.0.0", "localhost"}:
            return "127.0.0.1"
        return "::1" if host == "::" else host

    def acquire(self):
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        self.owned = True
        return True

    def publish(self, host, port):
        host = self.browser_host(host)
        if host != self.host:
            raise ValueError("App launch host differs from configuration")
        address = f"[{host}]" if ":" in host else host
        atomic_json(self.metadata, {"host": host, "port": port, "id": self.id})
        return f"http://{address}:{port}/"

    def existing_url(self):
        try:
            value = json.loads(self.metadata.read_text(encoding="utf-8"))
            host, port = value["host"], value["port"]
            if (
                host != self.host
                or type(port) is not int
                or not 0 < port < 65536
                or not isinstance(value.get("id"), str)
                or not re.fullmatch(r"[0-9a-f]{32}", value["id"])
            ):
                return None
            address = f"[{host}]" if ":" in host else host
            url = f"http://{address}:{port}/"
            # Local ownership checks must never use a configured network proxy.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(url + "api/health", timeout=0.5) as response:
                health = json.loads(response.read(4096))
            if (
                isinstance(health, dict)
                and health.get("application") == "troglodaw"
                and health.get("instance_id") == value["id"]
            ):
                return url
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return None

    def claim_or_reopen(self, timeout=20):
        deadline = time.monotonic() + timeout
        while True:
            if self.acquire():
                return None
            if url := self.existing_url():
                return url
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "TrogloDAW is starting or stopping. Try the shortcut again shortly."
                )
            time.sleep(0.1)

    def close(self):
        try:
            if self.owned:
                self.metadata.unlink(missing_ok=True)
        finally:
            self.file.close()


def listening_socket(host, port=None):
    """Reserve the selected port before publishing it or starting the server."""
    candidate = port or 7860
    while candidate < 65536:
        listener = socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET)
        if os.name == "nt":
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind((host, candidate))
            listener.listen(128)
            return listener, candidate
        except OSError:
            listener.close()
            if port is not None:
                raise
            candidate += 1
    raise OSError("No local app port is available")
