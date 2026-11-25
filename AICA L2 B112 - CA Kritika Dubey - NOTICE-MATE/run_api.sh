#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python scripts/init_db.py
exec python -m noticemate.api.main
