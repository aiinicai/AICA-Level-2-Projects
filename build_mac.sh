#!/bin/bash
# Builds dist/GXVAN.app. Needs Python 3.12 or 3.13 (python.org installer).
set -e
cd "$(dirname "$0")"
PY=$(command -v python3.12 || command -v python3.13 || true)
[ -z "$PY" ] && { echo "Install Python 3.12 from python.org first"; exit 1; }
"$PY" -m venv .buildenv
.buildenv/bin/python -m pip install --upgrade pip
.buildenv/bin/python -m pip install -r requirements.txt pyinstaller
.buildenv/bin/python -m pip uninstall -y opencv-python
.buildenv/bin/python -m pip install opencv-python-headless
.buildenv/bin/python -m PyInstaller GXVAN.spec --noconfirm
echo "Done. Your app is in: $(pwd)/dist/GXVAN.app"
