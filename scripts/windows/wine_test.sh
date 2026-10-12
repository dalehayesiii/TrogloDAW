#!/usr/bin/env bash
# Smoke-test the built installer under Wine: silent install, then `mm.bat produce <vocal>` (or `mm.bat demo`).
# Wine's builtin ucrtbase lacks crealf (numpy needs it), so the prefix gets Microsoft's UCRT via winetricks.
# Paths: env > config.local.json > config.json > defaults (build.wine_prefix, build.output, build.test_vocal).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO="$(cd "$HERE/../.." && pwd)"
cfg() { python3 "$HERE/cfg.py" "$REPO" "$1" "$2" "$3"; }
export WINEPREFIX="$(cfg build.wine_prefix MM_WINE_PREFIX "$HERE/work/wineprefix")" WINEDEBUG=-all
OUT="$(cfg build.output MM_BUILD_OUTPUT "$REPO/dist/TrogloDAW-Setup.exe")"
VOCAL="$(cfg build.test_vocal MM_TEST_VOCAL "")"
CACHE="$(cfg build.cache_dir MM_BUILD_CACHE_DIR "$HERE/cache")"
command -v wine >/dev/null || { echo "wine not installed"; exit 1; }
if [ ! -f "$WINEPREFIX/system.reg" ]; then
    wineboot -i
    [ -x "$CACHE/winetricks" ] || curl -fL -o "$CACHE/winetricks" https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
    chmod +x "$CACHE/winetricks"; "$CACHE/winetricks" -q ucrtbase2019 vcrun2022
fi
wine "$OUT" /S
U="$WINEPREFIX/drive_c/users/$USER"; I="$U/AppData/Local/MusicMaker"
ls "$I" "$I/app"
cd "$I"
if [ -n "$VOCAL" ]; then
    NAME="$(basename "$VOCAL")"
    cp "$VOCAL" "$U/Documents/$NAME"
    wine cmd /c "mm.bat produce C:\\users\\$USER\\Documents\\$NAME --seed 2026 --name wine_test_song"
else
    wine cmd /c "mm.bat demo"
fi
