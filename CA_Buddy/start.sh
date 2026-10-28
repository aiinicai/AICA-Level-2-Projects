#!/usr/bin/env bash
# CA_Buddy launcher for macOS / Linux
cd "$(dirname "$0")"
PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then echo "Install Python 3.10+ from https://www.python.org/downloads/"; exit 1; fi
if [ ! -x .venv/bin/python ]; then
  echo "First run: setting up (only once)..."
  "$PY" -m venv .venv && .venv/bin/python -m pip install --upgrade pip -q && .venv/bin/python -m pip install -r requirements.txt || exit 1
fi
exec .venv/bin/python app.py
