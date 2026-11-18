#!/bin/sh
set -eu
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "Install Python 3.10+ for your user account first."; exit 1; }
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
exec .venv/bin/python main.py "$@"
