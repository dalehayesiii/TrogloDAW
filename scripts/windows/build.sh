#!/usr/bin/env bash
# Build the Windows installer on Linux or Windows (Git Bash).
# Use --stage-only to validate the runtime payload without invoking NSIS.
# Requires: makensis (apt install nsis / choco install nsis), curl, python3, and the locked development
#           environment (run uv sync --locked at the repository root).
# Paths come from env vars > config.local.json ("build" section) > config.json > defaults below.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
PYTHON=python3
[[ "$OSTYPE" == msys* ]] && PYTHON=python
cfg() { "$PYTHON" "$HERE/cfg.py" "$REPO" "$1" "$2" "$3"; }

VENV="$(cfg build.venv MM_BUILD_VENV "$REPO/.venv")"
WORK="$(cfg build.work_dir MM_BUILD_WORK_DIR "$HERE/work")"
CACHE="$(cfg build.cache_dir MM_BUILD_CACHE_DIR "$HERE/cache")"
OUT="$(cfg build.output MM_BUILD_OUTPUT "$REPO/dist/TrogloDAW-Setup.exe")"
PARTS="$(cfg build.parts_dir MM_BUILD_PARTS_DIR "")"
PYV="$(cfg build.python_embed_version MM_PYTHON_EMBED_VERSION "3.12.10")"
VERSION="${MM_VERSION:-0.0.0}"
[[ "$VERSION" =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]] || { echo "MM_VERSION must be a stable semantic version"; exit 1; }
PY="$VENV/bin/python"; UV="$VENV/bin/uv"
if [[ -f "$VENV/Scripts/python.exe" ]]; then
    PY="$VENV/Scripts/python.exe"; UV="$VENV/Scripts/uv.exe"
fi
[ -x "$PY" ] && [ -x "$UV" ] || { echo "build venv not found at $VENV (needs uv, pefile, packaging, pillow); set build.venv in config.local.json"; exit 1; }

echo "venv=$VENV  work=$WORK  cache=$CACHE  output=$OUT  python=$PYV"
mkdir -p "$CACHE" "$WORK" "$(dirname "$OUT")"
ZIP="$CACHE/python-$PYV-embed-amd64.zip"
[ -f "$ZIP" ] || curl -fL -o "$ZIP" "https://www.python.org/ftp/python/$PYV/python-$PYV-embed-amd64.zip"

S="$WORK/stage/MusicMaker"; SP="$S/python/Lib/site-packages"
rm -rf "$WORK/stage" && mkdir -p "$S/python" "$S/app"
"$PY" -m zipfile -e "$ZIP" "$S/python"
PTH=$(ls "$S/python"/python3*._pth)
printf 'python%s.zip\r\n.\r\nLib\\site-packages\r\n..\\app\\backend\r\n..\\app\r\n\r\nimport site\r\n' "$(echo "$PYV" | cut -d. -f1,2 | tr -d .)" > "$PTH"

# Windows wheels; uv evaluates environment markers for the Windows/cp3xx target (pip does not)
"$UV" export --project "$REPO" --locked --no-dev --no-emit-project --format requirements-txt --output-file "$WORK/requirements.txt" --quiet
"$UV" pip install --target "$SP" --python-platform x86_64-pc-windows-msvc --python-version "$(echo "$PYV" | cut -d. -f1,2)" \
    --only-binary :all: --require-hashes -r "$WORK/requirements.txt"
rm -rf "$SP/bin"; find "$SP/numpy" "$SP/scipy" -type d -name tests -prune -exec rm -rf {} + 2>/dev/null || true
# app-local MSVC C++ runtime (Microsoft msvcp140, shipped renamed inside the numpy wheel) for pedalboard
cp "$SP"/numpy.libs/msvcp140-*.dll "$S/python/msvcp140.dll"

mkdir -p "$S/app/backend"
cp "$REPO/backend"/{mmcore.py,cli.py,app.py,storage.py,models.py,songs.py,arrangement.py,inference_runner.py} "$S/app/backend/"
mkdir -p "$S/app/config"
cp "$REPO/config/model-manifest.json" "$S/app/config/"
cp "$REPO"/{pyproject.toml,uv.lock} "$S/app/"
# Extract the locked Windows executable even when packaging from a Linux development host.
"$PY" "$HERE/setup_tool.py" "$REPO" "$CACHE" "$S"
cp "$REPO/README.md" "$S/app/"
[[ -f "$REPO/frontend/dist/browser/index.html" ]] || { echo "Build the Angular frontend with npm run build first"; exit 1; }
mkdir -p "$S/app/frontend/dist"
cp -r "$REPO/frontend/dist/browser" "$S/app/frontend/dist/"
mkdir -p "$S/app/docs"
cp -r "$REPO/docs/licenses" "$S/app/docs/licenses"
cp "$REPO"/cicd/windows/launchers/* "$S/"
"$PY" "$HERE/make_icon.py" "$S/musicmaker.ico"
"$PY" "$HERE/validate.py" "$S"

[[ "${1:-}" == --stage-only ]] && exit 0
"$PY" "$HERE/package.py" "$VERSION"
ls -la "$OUT"; sha256sum "$OUT"
if [ -n "$PARTS" ]; then
    rm -rf "$PARTS" && mkdir -p "$PARTS"
    split -b 15M -d -a 2 "$OUT" "$PARTS/mm.part"
    ls -l "$PARTS"
fi
