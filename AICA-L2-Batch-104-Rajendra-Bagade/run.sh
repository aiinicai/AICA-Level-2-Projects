#!/usr/bin/env bash
# AuditLens - start on macOS or Linux.
# Sets up a private environment on first run, then starts the server. The
# browser is opened by the launcher only once the server is listening.
set -euo pipefail
cd "$(dirname "$0")"

echo
echo "  AuditLens - starting up"
echo "  ======================"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "  Python 3 was not found. Install Python 3.10 or later, then run this again."
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "  First run - setting up. This takes a minute or two."
  echo
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -e ".[dev]"
  echo
  echo "  Setup complete."
  echo
fi

exec .venv/bin/python -m auditlens.launch "$@"
