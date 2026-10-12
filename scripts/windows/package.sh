#!/usr/bin/env bash
# Repackage an already checked payload with semantic-release's version; no dependency or frontend rebuild.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
PYTHON=python3
[[ "$OSTYPE" == msys* ]] && PYTHON=python
cfg() { "$PYTHON" "$HERE/cfg.py" "$REPO" "$1" "$2" "$3"; }
VERSION="${1:-${MM_VERSION:-0.0.0}}"
[[ "$VERSION" =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]] || { echo "Expected a stable semantic version"; exit 1; }
WORK="$(cfg build.work_dir MM_BUILD_WORK_DIR "$HERE/work")"
STAGE="$WORK/stage/MusicMaker"
OUT="$(cfg build.output MM_BUILD_OUTPUT "$REPO/dist/MusicMaker-Setup.exe")"
WIN_INSTALL="$(cfg windows.install_dir MM_WIN_INSTALL_DIR '$LOCALAPPDATA\MusicMaker')"
WIN_LIBRARY="$(cfg windows.library_dir MM_WIN_LIBRARY_DIR '$DOCUMENTS\MusicMaker\library')"
command -v makensis >/dev/null || { echo "Install NSIS and add it to PATH"; exit 1; }
[[ -f "$STAGE/app/frontend/dist/browser/index.html" ]] || { echo "Checked payload is missing"; exit 1; }
NSIS_SCRIPT="$REPO/cicd/windows/musicmaker.nsi"
[[ "$OSTYPE" == msys* ]] && NSIS_SCRIPT="$(cygpath -w "$NSIS_SCRIPT")"
mkdir -p "$(dirname "$OUT")"
MSYS_NO_PATHCONV=1 makensis -V2 -DVERSION="$VERSION" -DSTAGE="$STAGE" -DOUTFILE="$OUT" \
    -DINSTALL_DIR="$WIN_INSTALL" -DLIBRARY_DIR="$WIN_LIBRARY" "$NSIS_SCRIPT"
MM_VERSION="$VERSION" "$PYTHON" "$REPO/scripts/build_manifest.py" "$OUT"
