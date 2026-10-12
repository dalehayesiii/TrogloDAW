import hashlib
import io
import json
import os
import threading
import urllib.error
import urllib.request
import uuid
from email.message import Message

import pytest

import credentials
from storage import Storage, atomic_json, remove_owned_models
from updates import API, INSTALLER, ReleaseRedirect, Updates, version


def http_error(code, *, limited=False):
    headers = Message()
    if limited:
        headers["X-RateLimit-Remaining"] = "0"
    return urllib.error.HTTPError(API, code, "Synthetic HTTP failure", headers, None)


class Response(io.BytesIO):
    pass


def test_update_preserves_legacy_library_inside_program_files(core, tmp_path):
    manager, _ = make_update_manager(core, tmp_path)
    complete(manager, "check")
    complete(manager, "download")
    core.LIB = manager.root / "legacy-library"
    core.LIB.mkdir()
    song = core.LIB / "song.wav"
    song.write_bytes(b"synthetic retained personal data")
    with pytest.raises(ValueError, match="program folders"):
        manager.apply(pid=1, host="127.0.0.1", port=7860)
    assert song.read_bytes() == b"synthetic retained personal data"
    assert manager.snapshot()["phase"] == "ready"


class ReleaseFixture:
    def __init__(self, *, historical=False):
        self.installer_name = INSTALLER if historical else "TrogloDAW-Setup-2.0.0.exe"
        self.installer = b"MZ" + b"synthetic Windows installer" * 100
        self.sha = "a" * 40
        self.manifest = {
            "version": "2.0.0",
            "sha": self.sha,
            "sha256": hashlib.sha256(self.installer).hexdigest(),
            "installer": self.installer_name,
        }
        self.release = {
            "tag_name": "v2.0.0",
            "draft": False,
            "prerelease": False,
            "assets": [
                {
                    "name": self.installer_name,
                    "id": 1,
                    "state": "uploaded",
                    "size": len(self.installer),
                    "digest": "sha256:" + self.manifest["sha256"],
                },
                {"name": "release.json", "id": 2, "state": "uploaded", "size": 200},
                {"name": "SHA256SUMS", "id": 3, "state": "uploaded", "size": 87},
            ],
        }
        self.requests = []
        self.failure = None
        self.block = None

    def open(self, request, timeout):
        self.requests.append(request)
        if self.block:
            self.block.wait(3)
        if self.failure:
            raise self.failure
        url = request.full_url
        if url.endswith("/latest"):
            data = json.dumps(self.release).encode()
        elif url.endswith("/assets/1"):
            data = self.installer
        elif url.endswith("/assets/2"):
            data = json.dumps(self.manifest).encode()
        elif url.endswith("/assets/3"):
            data = (self.manifest["sha256"] + "  " + self.installer_name + "\n").encode()
        elif "/git/ref/tags/" in url:
            data = json.dumps({"object": {"type": "commit", "sha": self.sha}}).encode()
        else:
            raise AssertionError(url)
        return Response(data)


def make_update_manager(core, tmp_path):
    root = tmp_path / "installation with spaces/app"
    root.mkdir(parents=True)
    atomic_json(
        root / "version.json",
        {"version": "1.0.0", "sha": "b" * 40, "repository": "dalehayesiii/music-maker"},
    )
    (root.parent / "python").mkdir()
    (root.parent / "python/python.exe").write_bytes(b"synthetic embedded Python")
    fixture = ReleaseFixture()
    manager = Updates(
        Storage(core),
        root=root,
        opener=fixture,
        token_source=lambda: [("synthetic_token", "Fixture")],
    )
    manager.supported = True  # OS-independent transport tests, no real installer launch.
    manager.state["supported"] = True
    return manager, fixture


@pytest.fixture
def update_manager(core, tmp_path):
    return make_update_manager(core, tmp_path)


def complete(manager, action):
    getattr(manager, action)()
    manager.thread.join(5)
    assert not manager.thread.is_alive()
    return manager.snapshot()


def test_check_runs_asynchronously_and_can_be_disabled(update_manager):
    manager, fixture = update_manager
    fixture.block = threading.Event()
    manager.startup()
    assert manager.snapshot()["phase"] == "checking"
    assert manager.snapshot()["message"] == "Checking for the latest release…"
    assert manager.snapshot()["available_version"] is None
    fixture.block.set()
    manager.thread.join(3)
    assert manager.snapshot()["phase"] == "available"
    manager.storage.preferences["check_updates"] = False
    previous = len(fixture.requests)
    manager.startup()
    assert len(fixture.requests) == previous


@pytest.mark.parametrize(
    "tag,draft,prerelease,phase",
    [
        ("v1.0.0", False, False, "current"),
        ("v0.9.0", False, False, "current"),
        ("v2.0.0", True, False, "failed"),
        ("v2.0.0", False, True, "failed"),
        ("v2.0.0-rc.1", False, False, "failed"),
        ("v2.0.0", False, False, "available"),
    ],
)
def test_stable_release_selection(update_manager, tag, draft, prerelease, phase):
    manager, fixture = update_manager
    fixture.release.update(tag_name=tag, draft=draft, prerelease=prerelease)
    assert complete(manager, "check")["phase"] == phase


@pytest.mark.parametrize(
    "failure,message",
    [
        (urllib.error.URLError("offline"), "connection"),
        (http_error(404), "Contents-read"),
        (
            http_error(403, limited=True),
            "rate limit",
        ),
        (http_error(429), "rate limit"),
    ],
)
def test_release_failures_are_quiet_bounded_and_redacted(update_manager, failure, message):
    manager, fixture = update_manager
    fixture.failure = failure
    state = complete(manager, "check")
    assert state["phase"] == "failed" and message in state["message"]
    assert "synthetic_token" not in json.dumps(state)


def test_private_access_can_fall_back_to_the_other_authorized_account(update_manager):
    manager, fixture = update_manager
    manager.token_source = lambda: [("preferred", "purpledragondude7"), ("fallback", "s116821")]
    original = fixture.open

    def open_request(request, timeout):
        if request.get_header("Authorization") == "Bearer preferred":
            raise http_error(404)
        return original(request, timeout)

    fixture.open = open_request
    assert complete(manager, "check")["access"] == "s116821"
    assert "fallback" not in json.dumps(manager.snapshot())


def test_redirect_removes_cross_host_credentials_and_rejects_other_hosts():
    original = urllib.request.Request(
        API + "/releases/assets/1",
        headers={"Authorization": "Bearer synthetic_token", "Cookie": "synthetic"},
    )
    handler = ReleaseRedirect()
    redirect = handler.redirect_request(
        original, None, 302, "Found", {}, "https://release-assets.githubusercontent.com/asset"
    )
    assert redirect.get_header("Authorization") is None and redirect.get_header("Cookie") is None
    assert original.get_header("Authorization") == "Bearer synthetic_token"
    for url in [
        "http://release-assets.githubusercontent.com/asset",
        "https://unapproved.example/asset",
        "https://api.github.com:444/asset",
    ]:
        with pytest.raises(ValueError, match="approved HTTPS"):
            handler.redirect_request(original, None, 302, "Found", {}, url)


def test_download_verifies_source_version_checksum_size_and_ownership(update_manager):
    manager, fixture = update_manager
    complete(manager, "check")
    unrelated = manager.storage.models / "unrelated.txt"
    unrelated.parent.mkdir(parents=True, exist_ok=True)
    unrelated.write_text("preserve")
    state = complete(manager, "download")
    assert state["phase"] == "ready" and state["bytes_done"] == state["bytes_total"]
    assert manager.ready_path.read_bytes() == fixture.installer
    assert manager.ready_path.name == "TrogloDAW-Setup-2.0.0.exe"
    assert manager.ready_path.is_relative_to(manager.storage.models)
    assert not list(manager.ready_path.parent.glob("*.partial"))
    remove_owned_models(manager.storage.config_path)
    assert not manager.ready_path.exists() and unrelated.read_text() == "preserve"


def test_historical_fixed_name_release_remains_verifiable(update_manager):
    manager, _ = update_manager
    fixture = ReleaseFixture(historical=True)
    manager.opener = fixture
    assert complete(manager, "check")["phase"] == "available"
    assert manager.release["installer"] == INSTALLER
    assert complete(manager, "download")["phase"] == "ready"
    assert manager.ready_path.read_bytes() == fixture.installer


def test_versioned_asset_is_preferred_without_verification_fallback(update_manager):
    manager, fixture = update_manager
    historical = dict(fixture.release["assets"][0], name=INSTALLER, id=4)
    fixture.release["assets"].append(historical)
    assert complete(manager, "check")["phase"] == "available"
    assert manager.release["installer"] == fixture.installer_name
    fixture.manifest["installer"] = INSTALLER
    assert complete(manager, "download")["phase"] == "failed"
    assert manager.ready_path is None
    assert not any(request.full_url.endswith("/assets/4") for request in fixture.requests)


def test_wrong_version_asset_name_is_rejected(update_manager):
    manager, fixture = update_manager
    fixture.release["assets"][0]["name"] = "TrogloDAW-Setup-3.0.0.exe"
    assert complete(manager, "check")["phase"] == "failed"
    assert manager.release is None


@pytest.mark.parametrize(
    "corruption", ["version", "source", "filename", "sha256", "size", "ambiguous"]
)
def test_invalid_release_cannot_become_ready(update_manager, corruption):
    manager, fixture = update_manager
    if corruption == "ambiguous":
        fixture.release["assets"].append(dict(fixture.release["assets"][0]))
    complete(manager, "check")
    if corruption == "ambiguous":
        assert manager.snapshot()["phase"] == "failed"
        return
    if corruption == "version":
        fixture.manifest["version"] = "3.0.0"
    elif corruption == "source":
        fixture.manifest["sha"] = "c" * 40
    elif corruption == "filename":
        fixture.manifest["installer"] = "Other.exe"
    elif corruption == "sha256":
        fixture.installer = b"changed downloaded content".ljust(len(fixture.installer), b"!")
    elif corruption == "size":
        fixture.installer = fixture.installer[:-1]
    assert complete(manager, "download")["phase"] == "failed"
    assert manager.ready_path is None


def test_cancel_download_clears_readiness_and_allows_retry(update_manager):
    manager, fixture = update_manager
    complete(manager, "check")
    original = fixture.open

    def open_request(request, timeout):
        if request.full_url.endswith("/assets/1"):
            manager.cancel()
        return original(request, timeout)

    fixture.open = open_request
    assert complete(manager, "download")["phase"] == "canceled"
    assert manager.ready_path is None
    fixture.open = original
    assert complete(manager, "download")["phase"] == "ready"
    assert manager.cancel()["phase"] == "canceled" and manager.ready_path is None


def test_source_build_never_checks_or_installs(core, tmp_path):
    def unexpected_access():
        raise AssertionError("No source startup network")

    manager = Updates(Storage(core), root=tmp_path, token_source=unexpected_access)
    manager.startup()
    assert manager.check()["phase"] == "source"
    with pytest.raises(ValueError):
        manager.download()


def test_stable_version_comparison_rejects_unstable_or_noncanonical_values():
    assert version("2.10.0") > version("2.9.9")
    for value in ["02.0.0", "2.0.0-beta", "2.0", "v2.0.0", None]:
        with pytest.raises(ValueError):
            version(value)


@pytest.mark.skipif(os.name != "nt", reason="Windows Credential Manager boundary")
def test_native_credential_roundtrip_uses_an_isolated_test_slot():
    target = "TrogloDAW-test:" + uuid.uuid4().hex
    try:
        credentials.save("synthetic_token_only", target)
        assert credentials.read(target) == "synthetic_token_only"
    finally:
        credentials.remove(target)
    assert credentials.read(target) is None


def test_invalid_credentials_are_not_echoed_in_errors(update_manager):
    manager, _ = update_manager
    manager.token_source = lambda: [("synthetic_secret\ninjected_header", "Fixture")]
    state = complete(manager, "check")
    assert state["phase"] == "failed"
    assert "synthetic_secret" not in json.dumps(state)
