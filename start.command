#!/usr/bin/env bash
# musicmaker launcher for macOS / Linux: creates .venv, installs deps, opens the UI.
set -e
cd "$(dirname "$0")"
PY=""
for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,14) else 1)'; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "Python 3.10-3.14 not found. Install it from https://www.python.org/downloads/ and run this again."
  exit 1
fi
[ -x .venv/bin/python ] || "$PY" -m venv .venv
if ! cmp -s requirements.txt .venv/requirements.installed; then
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
  cp requirements.txt .venv/requirements.installed
fi
exec .venv/bin/python app.py "$@"
