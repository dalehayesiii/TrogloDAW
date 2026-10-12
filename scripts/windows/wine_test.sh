#!/usr/bin/env bash
# Smoke-test the built installer under Wine: silent install, then `troglodaw.bat produce <vocal>` (or `troglodaw.bat demo`).
# Wine's builtin ucrtbase lacks crealf (numpy needs it), so the prefix gets Microsoft's UCRT via winetricks.
# Paths: env > config.local.json > config.json > defaults (build.wine_prefix, build.output, build.test_vocal).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO="$(cd "$HERE/../.." && pwd)"
cfg() { python3 "$HERE/cfg.py" "$REPO" "$1" "$2" "$3"; }
export WINEPREFIX="$(cfg build.wine_prefix TROGLODAW_WINE_PREFIX "$HERE/work/wineprefix")" WINEDEBUG=-all
VERSION="${TROGLODAW_VERSION:-0.0.0}"
OUT="$(cfg build.output TROGLODAW_BUILD_OUTPUT "$REPO/dist/TrogloDAW-Setup-$VERSION.exe")"
VOCAL="$(cfg build.test_vocal TROGLODAW_TEST_VOCAL "")"
CACHE="$(cfg build.cache_dir TROGLODAW_BUILD_CACHE_DIR "$HERE/cache")"
command -v wine >/dev/null || { echo "wine not installed"; exit 1; }
if [ ! -f "$WINEPREFIX/system.reg" ]; then
    wineboot -i
    [ -x "$CACHE/winetricks" ] || curl -fL -o "$CACHE/winetricks" https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
    chmod +x "$CACHE/winetricks"; "$CACHE/winetricks" -q ucrtbase2019 vcrun2022
fi
wine "$OUT" /S
U="$WINEPREFIX/drive_c/users/$USER"; I="$U/AppData/Local/TrogloDAW"
ls "$I" "$I/app"
cd "$I"
if [ -n "$VOCAL" ]; then
    NAME="$(basename "$VOCAL")"
    cp "$VOCAL" "$U/Documents/$NAME"
    wine cmd /c "troglodaw.bat produce C:\\users\\$USER\\Documents\\$NAME --seed 2026 --name wine_test_song"
else
    wine cmd /c "troglodaw.bat demo"
fi
