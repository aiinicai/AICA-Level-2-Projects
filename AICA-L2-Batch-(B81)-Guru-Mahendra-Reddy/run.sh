#!/usr/bin/env bash
# Cash Runway — start the application.
#
# The frontend is pre-built and served by the backend, so this starts one
# server and needs Python only.
set -euo pipefail
cd "$(dirname "$0")"

PY=${PYTHON:-python3}
command -v "$PY" >/dev/null || { echo "Python 3.12 or newer is required."; exit 1; }
echo "  Using $("$PY" --version)"
echo

cd backend

if ! "$PY" -c "import fastapi, sqlalchemy, pydantic, jwt, bcrypt, openpyxl, requests, dateutil, uvicorn" 2>/dev/null; then
  echo "==> [1/2] Installing Python packages"
  # backend/vendor holds Windows wheels; on macOS and Linux install normally.
  "$PY" -m pip install --prefer-binary -r requirements.txt || {
    echo
    echo "  Could not install the packages. If you have no internet access,"
    echo "  the bundled packages in backend/vendor are Windows-only — you will"
    echo "  need to install them from a machine that does."
    exit 1
  }
else
  echo "==> [1/2] Python packages already installed"
fi

# No seeding here, deliberately. The application creates the sign-in accounts
# itself on first start and then ASKS which data to load. Loading the demo here
# would answer that question on the user's behalf, and the first-run screen
# would never appear.
#
# To load the demo from the command line instead:  "$PY" seed_db.py

cat <<'MSG'

  ==================================================================

    Cash Runway is starting.

    Open   http://localhost:8000

    Sign in with
      guru@northwindrobotics.in  /  cashrunway

    First time? You will be asked whether to load the demonstration
    company or set up your own.

    API documentation is at http://localhost:8000/docs
    Ctrl-C to stop.

  ==================================================================

MSG
echo "==> [2/2] Starting"
# Bound to this machine only by default. CR_HOST=0.0.0.0 lets others on the
# network sign in -- on a trusted network, since there is no HTTPS.
exec "$PY" -m uvicorn app.main:app --host "${CR_HOST:-127.0.0.1}" --port 8000
