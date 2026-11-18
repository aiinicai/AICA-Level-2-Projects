#!/usr/bin/env bash
# One-time setup: creates a virtual environment inside the skill folder and installs dependencies.
# Usage: bash scripts/setup_env.sh
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.10 or later from python.org." >&2
  exit 1
fi

"$PYTHON_BIN" - <<'EOF'
import sys
if sys.version_info < (3, 10):
    sys.exit(f"ERROR: Python 3.10 or later is required, found {sys.version.split()[0]}.")
EOF

if [ ! -x "$SKILL_DIR/.venv/bin/python" ]; then
  echo "Creating virtual environment in $SKILL_DIR/.venv"
  "$PYTHON_BIN" -m venv "$SKILL_DIR/.venv"
fi

echo "Installing yfinance, pandas, numpy and matplotlib. This takes 1 to 3 minutes and prints nothing until it is done..."
"$SKILL_DIR/.venv/bin/python" -m pip install --quiet --upgrade pip
"$SKILL_DIR/.venv/bin/python" -m pip install --quiet -r "$SKILL_DIR/scripts/requirements.txt"
"$SKILL_DIR/.venv/bin/python" -c "import yfinance, pandas, numpy, matplotlib; print('Bharat Stock Analyser environment ready.')"
