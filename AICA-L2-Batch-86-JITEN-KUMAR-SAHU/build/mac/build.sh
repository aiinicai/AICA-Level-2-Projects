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

# Remove the "chromium_headless_shell" variant if present. This app
# always launches with headless=False and never uses it -- it's only
# downloaded because newer Playwright versions fetch it automatically
# alongside regular Chromium for headless-mode performance elsewhere.
LIVE_BROWSERS=$(find build_venv -maxdepth 10 -type d -name ".local-browsers" 2>/dev/null | head -n1)
find build_venv -maxdepth 10 -type d -name "chromium_headless_shell-*" -print -exec rm -rf {} + 2>/dev/null

# -- Pristine snapshot / restore --------------------------------------
# The REAL root cause behind repeated "file not found" PyInstaller
# failures on a different file each time (first gdocs_script.js in the
# headless shell, then PrivacySandboxAttestationsPreloaded, potentially
# something else next time) isn't any one specific file -- it's that
# every time you actually LAUNCH the app to test it, Chrome's own
# background "component updater" silently adds, modifies, or removes
# various optional feature folders in the SAME Chromium copy
# PyInstaller is about to bundle. PyInstaller's official Playwright
# hook records a file manifest when it scans this folder (Analysis
# phase), then tries to copy those exact files moments later (Collect
# phase) -- if anything changed in between, that copy fails. Deleting
# one offending file after another never actually fixes this, since a
# different file breaks next time.
#
# The real fix: keep one pristine, snapshot copy of Chromium made right
# after download (before the app has ever been launched with real
# internet access), and restore FROM that snapshot immediately before
# every single build. Nothing runs or touches the browser files
# between that restore and PyInstaller's scan+copy within the same
# script execution, so they can never be a moving target again --
# regardless of how much real testing happens with the actual built
# app in between builds.
PRISTINE_BACKUP="build_venv/.local-browsers-pristine-backup"
if [ -n "$LIVE_BROWSERS" ] && [ -d "$LIVE_BROWSERS" ]; then
  if [ ! -d "$PRISTINE_BACKUP" ]; then
    echo "Creating a pristine snapshot of this Chromium copy..."
    echo "(only needs to happen once -- future builds restore from this"
    echo " snapshot instead, so real app usage in between never"
    echo " destabilizes what PyInstaller bundles)"
    cp -R "$LIVE_BROWSERS" "$PRISTINE_BACKUP" || { echo "ERROR: could not create pristine snapshot."; exit 1; }
  else
    echo "Restoring Chromium from the pristine snapshot before building..."
    echo "(this undoes anything Chrome's background updater changed the"
    echo " last time you ran the app -- expected and harmless)"
    rm -rf "$LIVE_BROWSERS"
    cp -R "$PRISTINE_BACKUP" "$LIVE_BROWSERS" || { echo "ERROR: could not restore from pristine snapshot."; exit 1; }
  fi
fi

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
