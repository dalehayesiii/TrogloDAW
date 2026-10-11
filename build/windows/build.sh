#!/usr/bin/env bash
# Build the Windows installer (MusicMaker-Setup.exe) from this repo on a Linux host - no Windows needed.
# Requires: makensis (apt install nsis), curl, unzip, python3, and a Python venv containing
#           uv, pefile, packaging and pillow  (e.g. python3 -m venv .venv && .venv/bin/pip install uv pefile packaging pillow)
# Paths come from env vars > config.local.json ("build" section) > config.json > defaults below.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
cfg() { python3 "$HERE/cfg.py" "$REPO" "$1" "$2" "$3"; }

VENV="$(cfg build.venv MM_BUILD_VENV "$REPO/.venv")"
WORK="$(cfg build.work_dir MM_BUILD_WORK_DIR "$HERE/work")"
CACHE="$(cfg build.cache_dir MM_BUILD_CACHE_DIR "$HERE/cache")"
OUT="$(cfg build.output MM_BUILD_OUTPUT "$REPO/dist/MusicMaker-Setup.exe")"
PARTS="$(cfg build.parts_dir MM_BUILD_PARTS_DIR "")"
PYV="$(cfg build.python_embed_version MM_PYTHON_EMBED_VERSION "3.12.10")"
WIN_INSTALL="$(cfg windows.install_dir MM_WIN_INSTALL_DIR '$LOCALAPPDATA\MusicMaker')"
WIN_LIBRARY="$(cfg windows.library_dir MM_WIN_LIBRARY_DIR '$DOCUMENTS\MusicMaker\library')"
PY="$VENV/bin/python"; UV="$VENV/bin/uv"
[ -x "$PY" ] && [ -x "$UV" ] || { echo "build venv not found at $VENV (needs uv, pefile, packaging, pillow); set build.venv in config.local.json"; exit 1; }
command -v makensis >/dev/null || { echo "makensis not found: sudo apt install nsis"; exit 1; }

echo "venv=$VENV  work=$WORK  cache=$CACHE  output=$OUT  python=$PYV"
mkdir -p "$CACHE" "$WORK" "$(dirname "$OUT")"
ZIP="$CACHE/python-$PYV-embed-amd64.zip"
[ -f "$ZIP" ] || curl -fL -o "$ZIP" "https://www.python.org/ftp/python/$PYV/python-$PYV-embed-amd64.zip"

S="$WORK/stage/MusicMaker"; SP="$S/python/Lib/site-packages"
rm -rf "$WORK/stage" && mkdir -p "$S/python" "$S/app"
(cd "$S/python" && unzip -q "$ZIP")
PTH=$(ls "$S/python"/python3*._pth)
printf 'python%s.zip\r\n.\r\nLib\\site-packages\r\n..\\app\r\n\r\nimport site\r\n' "$(echo "$PYV" | cut -d. -f1,2 | tr -d .)" > "$PTH"

# Windows wheels; uv evaluates environment markers for the Windows/cp3xx target (pip does not)
"$UV" pip install --target "$SP" --python-platform x86_64-pc-windows-msvc --python-version "$(echo "$PYV" | cut -d. -f1,2)" \
    --only-binary :all: -r "$REPO/requirements.txt" -c "$HERE/constraints.txt"
rm -rf "$SP/bin"; find "$SP/numpy" "$SP/scipy" "$SP/pandas" -type d -name tests -prune -exec rm -rf {} + 2>/dev/null || true
# app-local MSVC C++ runtime (Microsoft msvcp140, shipped renamed inside the numpy wheel) for pedalboard
cp "$SP"/numpy.libs/msvcp140-*.dll "$S/python/msvcp140.dll"

cp "$REPO"/{mmcore.py,cli.py,app.py,README.md,requirements.txt} "$S/app/"
cp "$HERE"/launchers/* "$S/"
"$PY" "$HERE/make_icon.py" "$S/musicmaker.ico"
"$PY" "$HERE/validate.py" "$S"

makensis -V2 -DSTAGE="$S" -DOUTFILE="$OUT" -DINSTALL_DIR="$WIN_INSTALL" -DLIBRARY_DIR="$WIN_LIBRARY" "$HERE/musicmaker.nsi"
ls -la "$OUT"; sha256sum "$OUT"
if [ -n "$PARTS" ]; then
    rm -rf "$PARTS" && mkdir -p "$PARTS"
    split -b 15M -d -a 2 "$OUT" "$PARTS/mm.part"
    ls -l "$PARTS"
fi
