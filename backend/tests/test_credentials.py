import subprocess
from types import SimpleNamespace

import credentials


def test_cli_discovery_uses_standard_install_when_path_is_stale(tmp_path, monkeypatch):
    executable = tmp_path / "GitHub CLI/gh.exe"
    executable.parent.mkdir()
    executable.write_bytes(b"synthetic CLI boundary")
    monkeypatch.setattr(credentials.shutil, "which", lambda _: None)
    monkeypatch.setattr(credentials, "cli_locations", lambda: [executable])
    assert credentials.find_cli() == str(executable)


def test_cli_candidates_use_preferred_then_active_account_without_logging_tokens(monkeypatch):
    monkeypatch.setattr(credentials, "read", lambda _: None)
    monkeypatch.delenv("TROGLODAW_GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(credentials, "find_cli", lambda: "synthetic-gh")
    calls = []

    def run(arguments, **_kwargs):
        calls.append(arguments)
        if "--user" in arguments:
            return SimpleNamespace(returncode=1, stdout="")
        return SimpleNamespace(returncode=0, stdout="synthetic_active_token\n")

    monkeypatch.setattr(credentials.subprocess, "run", run)
    assert credentials.candidates() == [
        ("synthetic_active_token", "GitHub CLI: active account"),
        ("", "Public release access"),
    ]
    assert calls[0][-1] == "purpledragondude7"
    assert calls[1][-1] == "s116821"
    assert "--user" not in calls[2]


def test_cli_failure_and_duplicate_tokens_keep_other_access_available(monkeypatch):
    monkeypatch.setattr(credentials, "read", lambda _: "synthetic_saved_token")
    monkeypatch.setenv("TROGLODAW_GITHUB_TOKEN", "synthetic_environment_token")
    monkeypatch.setattr(credentials, "find_cli", lambda: "synthetic-gh")

    def run(arguments, **_kwargs):
        if arguments[-1] == "s116821":
            raise subprocess.TimeoutExpired("synthetic-gh", 5)
        return SimpleNamespace(returncode=0, stdout="synthetic_saved_token")

    monkeypatch.setattr(credentials.subprocess, "run", run)
    assert credentials.candidates() == [
        ("synthetic_saved_token", "Windows Credential Manager"),
        ("synthetic_environment_token", "Environment"),
        ("", "Public release access"),
    ]
