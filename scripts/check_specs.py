"""Require finished OpenSpec lifecycles, with an explicit proposal-only exception."""

import json
import os
import re
from pathlib import Path

root = Path("openspec/changes")
active = [path for path in root.iterdir() if path.is_dir() and path.name != "archive"]
event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
pr = event.get("pull_request", {})
exception = any(label["name"] == "openspec:proposal-only" for label in pr.get("labels", []))
if active and not exception:
    raise SystemExit("Archive completed OpenSpec changes in the implementation PR")
if exception:
    if not pr.get("title", "").startswith("docs"):
        raise SystemExit("Proposal-only exceptions require a docs PR (no implementation)")
    if not active:
        raise SystemExit("Proposal-only label requires an active proposal")
for tasks in root.glob("archive/*/tasks.md"):
    if re.search(r"^\s*-\s+\[ \]", tasks.read_text(encoding="utf-8"), re.MULTILINE):
        raise SystemExit(f"Archived change has unfinished tasks: {tasks}")
