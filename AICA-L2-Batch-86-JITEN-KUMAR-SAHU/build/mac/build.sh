#!/bin/bash
# =============================================================
# ClientLedger India - macOS build script
# Run this ON A MAC with Python 3.11+ and Xcode command line tools.
# Produces: build/mac/dist/ClientLedgerIndia.app
#       and build/mac/dist/ClientLedgerIndia.dmg  (the single installer file)
#
# INCREMENTAL BY DEFAULT: after the first successful run, the virtual
# environment (build_venv) and the downloaded Chromium browser are
# BOTH reused automatically on every later run -- only the actual app
# gets rebuilt from your current source files. Nothing is
# re-downloaded. There is no need to delete build_venv between
# rebuilds -- doing so throws away the downloaded Chromium
# (~150-300MB) and everything pip installed, forcing a slow,
# data-hungry re-download next time.
#
# Only if you genuinely suspect the environment itself is broken
# (not just your app code), run:   ./build.sh clean
# which wipes build_venv and re-downloads everything from scratch.
# =============================================================
set -e

cd "$(dirname "$0")/../../app"

if [ "$1" == "clean" ]; then
  echo "Clean build requested -- removing existing environment..."
  rm -rf build_venv
  echo "Done. This run will re-download Chromium and reinstall dependencies."
fi

if [ -f "build_venv/bin/activate" ]; then
  echo "[1/6] Reusing existing virtual environment (build_venv already exists)..."
  echo "      Run './build.sh clean' instead if you want a fresh one."
else
  echo "[1/6] Creating virtual environment (first run, or after './build.sh clean')..."
  python3 -m venv build_venv
fi
source build_venv/bin/activate

echo "[2/6] Checking Python dependencies..."
echo "      (pip skips anything already installed that satisfies"
echo "      requirements.txt -- this will not re-download packages"
echo "      you already have)"
pip install --upgrade pip
pip install -r requirements.txt

if find build_venv -type d -path "*.local-browsers/chromium-*" 2>/dev/null | grep -q .; then
  echo "[3/6] Chromium already downloaded -- skipping (no internet used)."
else
  echo "[3/6] Downloading Chromium (first run, or after './build.sh clean') --"
  echo "      this is the only step that uses significant data"
  echo "      (~150-300MB), and only happens once..."
  export PLAYWRIGHT_BROWSERS_PATH=0
  python -m playwright install chromium
  if ! find build_venv -type d -name ".local-browsers" | grep -q .; then
    echo "ERROR: Chromium install did not land where expected. Aborting."
    exit 1
  fi
fi

# Remove the "chromium_headless_shell" variant if present. Newer
# Playwright versions download this automatically alongside regular
# Chromium (used only for headless-mode performance) even though this
# app always launches with headless=False and never touches it. Its
# own official PyInstaller hook tries to bundle every browser folder it
# finds under .local-browsers, and on some Chromium/headless-shell
# revisions that fails with "Unable to find ...gdocs_script.js" because
# a file the hook expects isn't actually present in that particular
# shell build. Since the app never needs the shell at all, the simplest
# fix is to delete it before PyInstaller ever sees it.
find build_venv -maxdepth 10 -type d -name "chromium_headless_shell-*" -print -exec rm -rf {} + 2>/dev/null

echo "[4/6] Building ClientLedgerIndia.app with PyInstaller..."
echo "      (this only repackages your current source files -- no"
echo "      internet access needed for this step)"
pyinstaller ../build/mac/ClientLedgerIndia.spec --distpath ../build/mac/dist --workpath ../build/mac/work --noconfirm

echo "[5/6] Creating a single .dmg installer..."
if ! command -v create-dmg &> /dev/null; then
  echo "  'create-dmg' not found - installing via Homebrew..."
  brew install create-dmg
fi
rm -f ../build/mac/dist/ClientLedgerIndia.dmg
create-dmg \
  --volname "ClientLedger India" \
  --window-size 540 380 \
  --icon-size 96 \
  --icon "ClientLedgerIndia.app" 140 160 \
  --app-drop-link 400 160 \
  "../build/mac/dist/ClientLedgerIndia.dmg" \
  "../build/mac/dist/ClientLedgerIndia.app"

echo "[6/6] Done."
echo "App:       build/mac/dist/ClientLedgerIndia.app"
echo "Installer: build/mac/dist/ClientLedgerIndia.dmg   <- send this ONE file to Mac clients"
echo
echo "For future rebuilds after code changes: just run ./build.sh again"
echo "(plain, no arguments) -- it will NOT re-download anything."
echo
echo "NOTE: an unsigned .app will show a Gatekeeper warning on first open."
echo "To avoid that, sign + notarize with an Apple Developer ID:"
echo "  codesign --deep --force --sign \"Developer ID Application: Your Name\" dist/ClientLedgerIndia.app"
echo "  (then notarize via 'xcrun notarytool submit' and staple with 'xcrun stapler')"
