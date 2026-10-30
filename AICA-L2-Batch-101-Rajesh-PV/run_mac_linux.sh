#!/usr/bin/env bash
# Judgement Insights Analyser - macOS / Linux launcher.
# The environment lives in your user profile so it survives replacing this
# folder; packages are installed only when missing or requirements change.
set -u
cd "$(dirname "$0")"
if [ "$(uname)" = "Darwin" ]; then BASE="$HOME/Library/Application Support/JudgmentInsightAnalyzer"
else BASE="${XDG_DATA_HOME:-$HOME/.local/share}/JudgmentInsightAnalyzer"; fi
VENV_DIR="$BASE/venv"; VENV_PY="$VENV_DIR/bin/python"; MARKER="$VENV_DIR/requirements-installed.txt"
CHECK="import customtkinter, pymupdf, google.genai, docx, reportlab, PIL, keyring, pytesseract, dotenv, openpyxl"

if [ ! -x "$VENV_PY" ]; then
  echo "First-time setup: creating the Python environment..."
  mkdir -p "$BASE"
  python3 -m venv "$VENV_DIR" || { echo "ERROR: could not create venv (install Python 3.10+ and python3-venv)"; exit 1; }
fi
if ! cmp -s requirements.txt "$MARKER" || ! "$VENV_PY" -c "$CHECK" >/dev/null 2>&1; then
  echo "Installing required packages (needed only once)..."
  "$VENV_PY" -m pip install --disable-pip-version-check -q --upgrade pip
  "$VENV_PY" -m pip install --disable-pip-version-check -r requirements.txt || { echo "ERROR: package installation failed (see above)."; exit 1; }
  cp requirements.txt "$MARKER"
else
  echo "Packages already installed."
fi
exec "$VENV_PY" main.py
