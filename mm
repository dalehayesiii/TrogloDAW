#!/usr/bin/env bash
# musicmaker CLI (macOS/Linux)
DIR="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")" && pwd)"
exec "$DIR/.venv/bin/python" "$DIR/cli.py" "$@"
