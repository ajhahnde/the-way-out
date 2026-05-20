#!/usr/bin/env bash
# Builds "The Way Out.app" — a thin launcher that auto-updates its game
# code from GitHub. Run on macOS only. Rebuild + re-send is only needed
# when the Python version or dependencies change (rare); normal code
# changes ship via `git push` + the in-game Update button.
set -euo pipefail
cd "$(dirname "$0")"

PY=".venv/bin/python"                       # NEVER system python3 (3.14)
[ -x "$PY" ] || { echo "missing $PY"; exit 1; }
"$PY" -m pip install --quiet --upgrade pyinstaller certifi

APPNAME="The Way Out"
SEEDPARENT="$(mktemp -d)"; SEED="$SEEDPARENT/_seed"; mkdir -p "$SEED"
rsync -a --delete \
  --exclude '.git' --exclude '.venv' --exclude '__pycache__' \
  --exclude 'build' --exclude 'dist' --exclude '*.spec' \
  --exclude '.DS_Store' --exclude 'ajhahnde' --exclude '.venv-intel' \
  ./ "$SEED/"                                # assets/ MUST be in (offline 1st run)

rm -rf build dist "$APPNAME.spec"
"$PY" -m PyInstaller --noconfirm --windowed --clean \
  --name "$APPNAME" \
  --osx-bundle-identifier de.ajhahn.thewayout \
  --icon assets/icon.icns \
  --collect-all pygame \
  --collect-all certifi \
  --add-data "$SEED:_seed" \
  launcher.py

# Declare the bundle as a game so macOS Sonoma+ auto-enables Game Mode
# (priority CPU/GPU, lower Bluetooth latency) whenever it runs
# fullscreen — there is no runtime API for this, only this plist key.
# Must run before codesign: the re-sign below covers the edited bundle.
PLIST="dist/$APPNAME.app/Contents/Info.plist"
/usr/libexec/PlistBuddy \
  -c "Add :LSApplicationCategoryType string public.app-category-games" \
  "$PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy \
  -c "Set :LSApplicationCategoryType public.app-category-games" "$PLIST"

codesign --force --deep --sign - "dist/$APPNAME.app"
( cd dist && ditto -c -k --keepParent "$APPNAME.app" "TheWayOut-mac.zip" )
echo "Done: dist/TheWayOut-mac.zip — 1st launch: right-click > Open > Open"
