#!/usr/bin/env bash
# Start Advance Tax Desk on macOS or Linux:  ./start.sh
set -e
cd "$(dirname "$0")"
ENVDIR="$HOME/.advance-tax-desk/venv"
PY="$(command -v python3 || command -v python)"
if ! "$PY" -c "import streamlit, pandas, openpyxl, docx, requests, selenium, pypdf" 2>/dev/null; then
  if [ ! -x "$ENVDIR/bin/python" ]; then
    echo "First run: setting up (needs internet, done only once)..."
    "$PY" -m venv "$ENVDIR"
  fi
  PY="$ENVDIR/bin/python"
  "$PY" -c "import streamlit, pandas, openpyxl, docx, requests, selenium, pypdf" 2>/dev/null || "$PY" -m pip install -r requirements.txt
fi
exec "$PY" -m streamlit run app.py
