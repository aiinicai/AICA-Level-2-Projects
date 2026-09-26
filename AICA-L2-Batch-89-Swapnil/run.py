"""Start the app locally. Easiest: double-click START_APP.bat. Or:  python run.py

* Works with any Python on the PATH: if the project's .venv exists, run.py re-launches itself
  with that interpreter (which has the dependencies).
* First run creates .env with fresh keys and migrates the database automatically.
* Opens the browser at http://127.0.0.1:5000 (set NO_BROWSER=1 to skip).
"""
import os
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

# ---- 1. make sure we run inside the project's virtualenv --------------------------------------
if VENV_PY.exists() and Path(sys.prefix).resolve() != (ROOT / ".venv").resolve() and not os.environ.get("MCA_IN_VENV"):
    env = {**os.environ, "MCA_IN_VENV": "1"}
    sys.exit(subprocess.call([str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]], env=env))

try:
    import flask  # noqa: F401
    import sqlalchemy  # noqa: F401
except ImportError as missing:
    print(f"\nA required package is missing ({missing.name}).\n"
          "Double-click START_APP.bat (it sets everything up), or run:\n"
          "  python -m venv .venv\n"
          "  .venv\\Scripts\\python -m pip install -r requirements.txt\n"
          "  .venv\\Scripts\\python run.py\n")
    if os.name == "nt" and sys.stdin and sys.stdin.isatty():
        input("Press Enter to close…")
    sys.exit(1)

sys.path.insert(0, str(ROOT))
from app.config import ensure_env_file  # noqa: E402

if ensure_env_file():
    print("Created .env with fresh keys.")

import cli  # noqa: E402
from app import NotMigrated, create_app  # noqa: E402
from engine import RulePackError  # noqa: E402


def port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def open_browser(url: str) -> None:
    if os.environ.get("NO_BROWSER"):
        return
    import threading
    import webbrowser
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    url = f"http://{'127.0.0.1' if host in ('0.0.0.0', '') else host}:{port}"
    if port_in_use("127.0.0.1", port):
        print(f"\nSomething is already running on port {port}.\n"
              f"If it is this app, just open {url} in your browser.\n"
              f"Otherwise stop the other program, or start on another port:  set PORT=5050 && python run.py\n")
        open_browser(url)
        return
    try:
        cli.migrate()                     # idempotent: brings any existing database to the latest schema
        app = create_app()
    except NotMigrated:
        sys.exit("Database migration failed — see the message above.")
    except RulePackError as e:
        sys.exit(f"Rule pack is invalid — refusing to start:\n{e}")
    with app.app_context():
        from app.models import User, db
        if db.session.query(User).count() == 0:
            print("\nNo users yet. Run once:\n"
                  "  .venv\\Scripts\\python cli.py seed-demo            (fictitious demo firm)\n"
                  "  .venv\\Scripts\\python cli.py create-owner --username owner --name \"Your Name\"\n")
    if app.config.get("SCHEDULER"):
        from app.exports import nightly, start_scheduler
        start_scheduler(app)
        with app.app_context():                      # catch up if the PC was off at 01:00
            from app.auth import today
            print("Start-up recompute and reminders:", nightly(today(), catch_up=False))
        print("Nightly recompute + reminders scheduled for 01:00 IST.")
    print(f"\n  MCA Compliance Mapper is running:  {url}\n  Keep this window open. Press Ctrl+C to stop.\n")
    open_browser(url)
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
