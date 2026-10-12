"""Validate PR titles and documentation-only claims without running PR-supplied shell text."""

import json
import os
import re
import subprocess
from pathlib import Path

TITLE = re.compile(
    r"^(feat|fix|perf|docs|build|ci|refactor|style|test|chore|revert)"
    r"(?:\([^()\r\n]+\))?(!)?: ([^\r\n]+)$"
)


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def is_doc(path):
    # A narrow allowlist: scripts, dependency files and generated agent skills
    # change executable behavior and must never masquerade as documentation.
    if path in {"README.md", "AGENTS.md", "CONTRIBUTING.md"}:
        return True
    return path.endswith(".md") and path.startswith(
        ("docs/", "openspec/specs/", "openspec/changes/")
    )


def validate(title, paths):
    match = TITLE.fullmatch(title)
    if not match or not match[3].strip():
        raise ValueError("Use a Conventional Commit PR title, e.g. feat: add a mixer")
    docs = match[1] == "docs"
    if docs and match[2]:
        raise ValueError("docs PRs cannot declare breaking changes")
    if docs and (not paths or not all(is_doc(path) for path in paths)):
        raise ValueError("docs PRs may change only approved documentation paths")
    return docs


def changed_paths(base, head):
    # Disable rename detection so both old and new paths are checked.
    return (
        subprocess.check_output(["git", "diff", "--no-renames", "--name-only", "-z", base, head])
        .decode()
        .rstrip("\0")
        .split("\0")
    )


def main():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    if os.environ["GITHUB_EVENT_NAME"] == "pull_request":
        pr = event["pull_request"]
        base = git("merge-base", pr["base"]["sha"], pr["head"]["sha"])
        docs = validate(pr["title"], changed_paths(base, pr["head"]["sha"]))
    else:
        before, head = event["before"], event["after"]
        if before == "0" * 40:
            raise ValueError("Main must already exist; releases require an existing main branch")
        docs = True
        for sha in git("rev-list", "--reverse", f"{before}..{head}").splitlines():
            parent = git("rev-parse", f"{sha}^1")
            title = git("show", "-s", "--format=%s", sha)
            docs = validate(title, changed_paths(parent, sha)) and docs
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"docs_only={str(docs).lower()}\n")


if __name__ == "__main__":
    main()
