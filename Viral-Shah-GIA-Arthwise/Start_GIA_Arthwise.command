#!/usr/bin/env bash
# ==============================================================================
# GIA_Arthwise 1-Click Platform Launcher for macOS
# Double-click this file from Finder or Desktop to start the application.
# ==============================================================================

# Find the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR" || exit 1

clear
echo "================================================================================"
echo "          GIA_ARTHWISE LOAN PROPOSAL EVALUATION & SYNDICATION PLATFORM          "
echo "================================================================================"
echo ""

# Release port 8000 if an old instance is lingering
EXISTING_PID=$(lsof -ti :8000 2>/dev/null)
if [ -n "$EXISTING_PID" ]; then
    echo "Notice: Freeing up port 8000 (stopping old process $EXISTING_PID)..."
    kill -9 $EXISTING_PID 2>/dev/null
    sleep 1
fi

# Detect python executable from virtual environment
if [ -f "$DIR/.venv/bin/python3" ]; then
    PY_BIN="$DIR/.venv/bin/python3"
elif [ -f "$DIR/.venv/bin/python" ]; then
    PY_BIN="$DIR/.venv/bin/python"
else
    PY_BIN="python3"
fi

echo "🚀 Starting server at http://127.0.0.1:8000 ..."
echo ""
echo "🔑 Pre-seeded Login Credentials:"
echo "   • Administrator:   admin@giaarthwise.com    / Admin@123"
echo "   • Senior Analyst:  analyst@giaarthwise.com  / Analyst@123"
echo "   • Credit Reviewer: reviewer@giaarthwise.com / Reviewer@123"
echo "   • Borrower Client: client@giaarthwise.com   / Client@123"
echo ""
echo "🌐 Launching your web browser automatically in 2 seconds..."
echo "   (Keep this Terminal window open while working)"
echo "   (Press Ctrl+C in this window anytime to stop the platform)"
echo "================================================================================"

# Open default browser in 2 seconds
(sleep 2 && open "http://127.0.0.1:8000") &

# Start platform server
exec "$PY_BIN" run.py
