"""Print one build setting. Precedence: env var > config.local.json > config.json > default.
Usage: python3 cfg.py <repo_dir> <key> <ENV_VAR> <default>    (key may be dotted, e.g. build.venv)"""
import json, os, sys
from pathlib import Path

repo, key, env, default = sys.argv[1:5]
if os.environ.get(env):
    print(os.environ[env]); sys.exit()
val = None
for name in ("config.json", "config.local.json"):
    p = Path(repo) / name
    if not p.exists():
        continue
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception as e:
        sys.exit(f"cannot parse {p}: {e}")
    cur = data
    for part in key.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
    if cur not in (None, ""):
        val = cur
print(os.path.expanduser(str(val)) if val is not None else default)
