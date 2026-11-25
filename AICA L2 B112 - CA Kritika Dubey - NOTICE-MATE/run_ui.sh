#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
