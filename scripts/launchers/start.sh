#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
command -v uv >/dev/null || { echo 'Install uv from https://docs.astral.sh/uv/getting-started/installation/'; exit 1; }
uv sync --locked
if [[ ! -f frontend/dist/browser/index.html ]]; then
  command -v npm >/dev/null || { echo 'Source setup needs Node 24.15+; the installer has a prebuilt UI.'; exit 1; }
  npm ci --ignore-scripts
  npm run build
fi
exec uv run --locked python backend/app.py "$@"
