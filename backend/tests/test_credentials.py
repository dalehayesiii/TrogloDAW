import subprocess
from types import SimpleNamespace

import credentials
import pytest


def test_cli_discovery_uses_standard_install_when_path_is_stale(tmp_path, monkeypatch):
    executable = tmp_path / "GitHub CLI/gh.exe"
    executable.parent.mkdir()
    executable.write_bytes(b"synthetic CLI boundary")
    monkeypatch.setattr(credentials.shutil, "which", lambda _: None)
    monkeypatch.setattr(credentials, "cli_locations", lambda: [executable])
    assert credentials.find_cli() == str(executable)


def test_cli_candidates_use_only_active_account_without_logging_tokens(monkeypatch, capsys):
    monkeypatch.setattr(credentials, "read", lambda _: None)
    monkeypatch.delenv("TROGLODAW_GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(credentials, "find_cli", lambda: "synthetic-gh")
    calls = []

    def run(arguments, **_kwargs):
        calls.append(arguments)
        return SimpleNamespace(returncode=0, stdout="synthetic_active_token\n")

    monkeypatch.setattr(credentials.subprocess, "run", run)
    assert credentials.candidates() == [
        ("synthetic_active_token", "GitHub CLI: active account"),
        ("", "Public release access"),
    ]
    assert calls == [["synthetic-gh", "auth", "token", "--hostname", "github.com"]]
    assert "synthetic_active_token" not in str(capsys.readouterr())


def test_duplicate_cli_token_keeps_other_access_available(monkeypatch):
    monkeypatch.setattr(credentials, "read", lambda _: "synthetic_saved_token")
    monkeypatch.setenv("TROGLODAW_GITHUB_TOKEN", "synthetic_environment_token")
    monkeypatch.setattr(credentials, "find_cli", lambda: "synthetic-gh")

    def run(arguments, **_kwargs):
        return SimpleNamespace(returncode=0, stdout="synthetic_saved_token")

    monkeypatch.setattr(credentials.subprocess, "run", run)
    assert credentials.candidates() == [
        ("synthetic_saved_token", "Windows Credential Manager"),
        ("synthetic_environment_token", "Environment"),
        ("", "Public release access"),
    ]


@pytest.mark.parametrize("failure", ["timeout", "launch", "unauthenticated"])
def test_cli_failure_keeps_explicit_and_public_access_without_switching(monkeypatch, failure):
    monkeypatch.setattr(credentials, "read", lambda _: "synthetic_saved_token")
    monkeypatch.setenv("TROGLODAW_GITHUB_TOKEN", "synthetic_environment_token")
    monkeypatch.setattr(credentials, "find_cli", lambda: "synthetic-gh")
    calls = []

    def run(arguments, **_kwargs):
        calls.append(arguments)
        if failure == "timeout":
            raise subprocess.TimeoutExpired("synthetic-gh", 5)
        if failure == "launch":
            raise OSError("Synthetic unavailable CLI")
        return SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setattr(credentials.subprocess, "run", run)
    assert credentials.candidates() == [
        ("synthetic_saved_token", "Windows Credential Manager"),
        ("synthetic_environment_token", "Environment"),
        ("", "Public release access"),
    ]
    assert calls == [["synthetic-gh", "auth", "token", "--hostname", "github.com"]]
