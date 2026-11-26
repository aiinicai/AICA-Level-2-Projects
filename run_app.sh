#!/usr/bin/env bash
# One-click launcher (macOS/Linux)
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv && . .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
else
  . .venv/bin/activate
fi
streamlit run app.py
