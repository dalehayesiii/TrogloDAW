import json
import io
import os
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

import pytest

from instance import Instance


def test_stale_discovery_and_unrelated_health_do_not_own_the_app(tmp_path, monkeypatch):
    first = Instance(tmp_path)
    second = Instance(tmp_path)
    try:
        first.publish("127.0.0.1", 7860)
        assert first.claim_or_reopen() is None  # Stale metadata never prevents ownership.
        monkeypatch.setattr(second, "existing_url", lambda: None)
        with pytest.raises(RuntimeError, match="starting or stopping"):
            second.claim_or_reopen(timeout=0)
    finally:
        first.close()
        second.close()
    third = Instance(tmp_path)
    try:
        assert third.claim_or_reopen() is None
    finally:
        third.close()


def test_discovery_rejects_foreign_host_before_network_access(tmp_path, monkeypatch):
    instance = Instance(tmp_path)
    instance.metadata.write_text(json.dumps({"host": "unapproved.example", "port": 80, "id": "x"}))

    def unexpected_network(*_):
        raise AssertionError("Unexpected network")

    monkeypatch.setattr(urllib.request, "build_opener", unexpected_network)
    try:
        assert instance.existing_url() is None
    finally:
        instance.close()


def test_discovery_requires_this_launch_identity(tmp_path, monkeypatch):
    instance = Instance(tmp_path)
    instance.publish("127.0.0.1", 7860)

    class OtherApp:
        def open(self, *_args, **_kwargs):
            return io.BytesIO(b'{"application":"troglodaw","instance_id":"other-launch"}')

    monkeypatch.setattr(urllib.request, "build_opener", lambda *_: OtherApp())
    try:
        assert instance.existing_url() is None
    finally:
        instance.close()


def test_concurrent_launch_reopen_crash_and_quit_use_one_service(tmp_path):
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text("<html>Synthetic app</html>")
    root = Path(__file__).resolve().parents[2]
    env = {
        **os.environ,
        "PYTHONPATH": str(root / "backend"),
        "TROGLODAW_CONFIG_DIR": str(tmp_path),
        "TROGLODAW_LIBRARY": str(tmp_path / "library"),
        "TROGLODAW_HOST": "127.0.0.1",
        "TROGLODAW_PORT": "0",
        "SYNTHETIC_FRONTEND": str(frontend),
    }
    command = [
        sys.executable,
        "-c",
        "import os; from pathlib import Path; import app; app.FRONTEND=Path(os.environ['SYNTHETIC_FRONTEND']); app.main()",
        "--no-browser",
    ]
    processes = []
    blocker = socket.socket()
    try:
        blocker.bind(("127.0.0.1", 7860))
        blocker.listen(1)
    except OSError:
        blocker.close()  # An existing unrelated listener already exercises fallback.

    def start():
        process = subprocess.Popen(
            command,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        processes.append(process)
        return process

    probe = Instance(tmp_path)

    def ready():
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if url := probe.existing_url():
                return url
            time.sleep(0.1)
        raise AssertionError("Synthetic app did not become healthy")

    try:
        one, two = start(), start()
        url = ready()
        assert ":7860/" not in url
        deadline = time.monotonic() + 15
        while one.poll() is None and two.poll() is None and time.monotonic() < deadline:
            time.sleep(0.1)
        survivor = one if one.poll() is None else two
        duplicate = two if survivor is one else one
        assert duplicate.wait(timeout=2) == 0 and survivor.poll() is None
        assert start().wait(timeout=15) == 0  # Reopening after the tab is gone reuses it.
        assert probe.existing_url() == url
        survivor.kill()
        survivor.wait(timeout=5)
        assert probe.metadata.exists()  # Crash leaves discovery, not an OS lock.
        replacement = start()
        url = ready()
        request = urllib.request.Request(
            url + "api/shutdown", data=b"", headers={"X-TrogloDAW-Request": "1"}
        )
        with urllib.request.urlopen(request, timeout=5):
            pass
        assert replacement.wait(timeout=15) == 0
        assert not probe.metadata.exists()
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
        blocker.close()
        probe.close()


def test_stalled_http_shutdown_exits_and_releases_launch_lock(tmp_path):
    root = Path(__file__).resolve().parents[2]
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text("<html>Synthetic shutdown</html>")
    marker = tmp_path / "request-entered"
    env = {
        **os.environ,
        "TROGLODAW_CONFIG_DIR": str(tmp_path),
        "TROGLODAW_LIBRARY": str(tmp_path / "library"),
        "SYNTHETIC_FRONTEND": str(frontend),
        "TROGLODAW_TEST_BLOCKED_MARKER": str(marker),
    }
    process = subprocess.Popen(
        [sys.executable, str(root / "scripts/serve_shutdown_fixture.py"), "--no-browser"],
        cwd=root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=0x08000000 if os.name == "nt" else 0,
    )
    probe = Instance(tmp_path)
    connection = socket.socket()
    try:
        deadline = time.monotonic() + 20
        url = None
        while time.monotonic() < deadline and not url:
            url = probe.existing_url()
            time.sleep(0.1)
        assert url, "Shutdown fixture did not start"
        address = urllib.parse.urlsplit(url)
        connection.connect((address.hostname, address.port))
        connection.sendall(
            b"GET /api/fixture/blocked HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        )
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert marker.exists(), "Stalled request did not enter the app"
        request = urllib.request.Request(
            url + "api/shutdown", data=b"", headers={"X-TrogloDAW-Request": "1"}
        )
        with urllib.request.urlopen(request, timeout=5):
            pass
        assert process.wait(timeout=20) == 0
        assert not probe.metadata.exists()
        assert probe.acquire(), "Exited service left launch ownership locked"
    finally:
        connection.close()
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        probe.close()
