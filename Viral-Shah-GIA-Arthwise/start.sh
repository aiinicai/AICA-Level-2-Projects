#!/usr/bin/env bash
# Automatically cd into the directory containing this script
cd "$(dirname "$0")"

# Release port 8000 if an old instance is lingering
EXISTING_PID=$(lsof -ti :8000 2>/dev/null)
if [ -n "$EXISTING_PID" ]; then
    kill -9 $EXISTING_PID 2>/dev/null
    sleep 1
fi

# Detect python executable from virtual environment
if [ -f ".venv/bin/python3" ]; then
    PY_BIN=".venv/bin/python3"
elif [ -f ".venv/bin/python" ]; then
    PY_BIN=".venv/bin/python"
else
    PY_BIN="python3"
fi

# Open browser in 2 seconds
(sleep 2 && open "http://127.0.0.1:8000") &

# Start platform server
exec $PY_BIN run.py
