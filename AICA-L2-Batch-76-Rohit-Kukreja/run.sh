#!/usr/bin/env bash
# AuditCraft startup (Linux / macOS). Build Prompt v2 §1.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

if [ ! -f .env ]; then
    echo "Creating .env from .env.example ..."
    cp .env.example .env
fi

python -m alembic upgrade head
python run.py
