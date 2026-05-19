#!/usr/bin/env bash
# Cross-build "The Way Out.app" for Intel Macs (x86_64), to be tested by
# a friend on macOS Monterey 12.7.6. The WHOLE toolchain runs under
# Rosetta so the produced bundle is pure x86_64. The arm64 build
# (build_mac.sh / .venv/) is deliberately left untouched.
#
# Prereqs (see ajhahnde/Pipeline.md — Schritt 1+2, both DONE+verified):
#   - Rosetta 2 installed and working
#   - /Library/Frameworks/Python.framework/Versions/3.12 — universal2,
#     python.org 3.12.10, x86_64 slice min-OS 10.13 (<= Monterey 12.7)
#   - .venv-intel/ created from it under Rosetta
#     (pygame 2.6.1, pyinstaller 6.20.0, x86_64-clean, no arm64 leak)
#
# This script self-verifies the result (no arm64 anywhere + min-OS
# <= 12.7) and fails loudly if the bundle would not run on the friend's
# Mac — that check is the whole point of the exercise.
set -euo pipefail
cd "$(dirname "$0")"

PY=".venv-intel/bin/python"
[ -x "$PY" ] || { echo "missing $PY — run ajhahnde/Pipeline.md Schritt 1+2 first"; exit 1; }

# Robust Rosetta probe. NOT 'arch -x86_64 uname -m': uname can report
# the real hardware (arm64) and that one-liner gives a false negative.
/usr/bin/arch -x86_64 /usr/bin/true 2>/dev/null \
  || { echo "Rosetta 2 not working (arch -x86_64 failed)"; exit 1; }
MACH="$(arch -x86_64 "$PY" -c 'import platform;print(platform.machine())')"
[ "$MACH" = "x86_64" ] \
  || { echo "venv python is not x86_64 under Rosetta (got: $MACH)"; exit 1; }

arch -x86_64 "$PY" -m pip install --quiet --upgrade pyinstaller

APPNAME="The Way Out"

# 'rm -rf dist' below would destroy an existing arm64 artifact. Back the
# arm64 zip up OUTSIDE the repo first (so neither the rm nor the seed
# rsync can touch it). The two builds' final zips have different names,
# but dist/ itself is NOT shared — only one .app lives there at a time.
if [ -f "dist/TheWayOut-mac.zip" ]; then
  BK="../TheWayOut-mac-arm64-$(git rev-parse --short HEAD 2>/dev/null || date +%s).zip"
  cp -p "dist/TheWayOut-mac.zip" "$BK"
  echo "Backed up existing arm64 zip -> $BK"
fi

SEEDPARENT="$(mktemp -d)"; SEED="$SEEDPARENT/_seed"; mkdir -p "$SEED"
trap 'rm -rf "$SEEDPARENT"' EXIT
rsync -a --delete \
  --exclude '.git' --exclude '.venv' --exclude '.venv-intel' \
  --exclude '__pycache__' --exclude 'build' --exclude 'dist' \
  --exclude '*.spec' --exclude '.DS_Store' \
  --exclude 'ajhahnde' \
  ./ "$SEED/"                                # assets/ MUST be in (offline 1st run)

rm -rf build dist "$APPNAME.spec"
arch -x86_64 "$PY" -m PyInstaller --noconfirm --windowed --clean \
  --name "$APPNAME" \
  --osx-bundle-identifier de.ajhahn.thewayout \
  --icon assets/icon.icns \
  --collect-all pygame \
  --target-architecture x86_64 \
  --add-data "$SEED:_seed" \
  launcher.py

# Declare the bundle as a game so macOS Sonoma+ auto-enables Game Mode
# (parity with build_mac.sh). Must run before codesign.
PLIST="dist/$APPNAME.app/Contents/Info.plist"
/usr/libexec/PlistBuddy \
  -c "Add :LSApplicationCategoryType string public.app-category-games" \
  "$PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy \
  -c "Set :LSApplicationCategoryType public.app-category-games" "$PLIST"

codesign --force --deep --sign - "dist/$APPNAME.app"

# ---- Hardened verification: this is why the script exists ----
APP="dist/$APPNAME.app"
EXE="$APP/Contents/MacOS/$APPNAME"
echo "=== verify: main executable ==="
file "$EXE"

echo "=== verify: NO arm64 slice anywhere in the bundle ==="
LEAK="$(find "$APP" -type f \( -name '*.so' -o -name '*.dylib' -o -perm -111 \) \
  -exec sh -c 'lipo -archs "$1" 2>/dev/null | grep -qw arm64 && echo "$1"' _ {} \;)"
if [ -n "$LEAK" ]; then
  echo "FAIL: arm64 slices present — will NOT run on the Intel Mac:"
  echo "$LEAK"
  exit 2
fi
echo "OK: no arm64 slices (pure x86_64 bundle)"

echo "=== verify: min-OS <= Monterey 12.7 on key binaries ==="
OK=1
for b in "$EXE" \
  "$APP/Contents/Frameworks"/Python \
  "$APP/Contents/Frameworks"/Python.framework/Versions/*/Python \
  "$APP/Contents/Frameworks"/libpython*.dylib \
  "$APP/Contents/Frameworks"/SDL2*.dylib ; do
  [ -e "$b" ] || continue
  MIN="$(otool -l "$b" 2>/dev/null \
    | awk '/LC_VERSION_MIN_MACOSX|LC_BUILD_VERSION/{f=1} f&&/(minos|version) /{print $2;f=0}' \
    | head -1)"
  echo "  $(basename "$b"): minos=${MIN:-unknown}"
  case "$MIN" in
    ""|*[!0-9.]*) : ;;                       # unknown -> report only
    *) maj=${MIN%%.*}; rest=${MIN#*.}; mn=${rest%%.*}; mn=${mn:-0}
       if [ "$maj" -gt 12 ] || { [ "$maj" -eq 12 ] && [ "$mn" -gt 7 ]; }; then
         echo "  FAIL: $b requires macOS $MIN (> 12.7)"; OK=0
       fi ;;
  esac
done
[ "$OK" -eq 1 ] || { echo "FAIL: a binary needs newer than Monterey 12.7"; exit 2; }
echo "OK: all checked binaries run on Monterey 12.7.6"

( cd dist && ditto -c -k --keepParent "$APPNAME.app" "TheWayOut-mac-intel.zip" )
echo
echo "Done: dist/TheWayOut-mac-intel.zip  (x86_64, Monterey-verified)"
echo "Next: Pipeline.md Schritt 6 — AirDrop this zip + send the friend block."
