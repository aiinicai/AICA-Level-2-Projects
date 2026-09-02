"""
FINsight packaged entry point (Stage 17 — EXE Packaging).

This is the PyInstaller build target — the ONE executable that
supports both Local and LAN modes, chosen at runtime (Section 7/15:
"do not duplicate the application into two complete EXEs if the same
executable can safely support both modes").

Not used by local/dev `python` invocations (use run.py, unchanged) or
by a manual LAN launch from a terminal (use wsgi_lan.py, unchanged) —
this file does not replace or import from either of them; it composes
the same underlying, already-approved pieces directly:
app.create_app, app.bootstrap (Stage 17, new), app.launch_common
(Stage 17, new — factored out of wsgi_lan.py so both can share it).

Startup order matters and is deliberate:
  1. Determine the data root (frozen-aware, mirrors config.py exactly
     — duplicated rather than imported; see _APP_DATA_ROOT below for
     why importing config this early would be a mistake).
  2. Load-or-create the local secret key file and set
     FINSIGHT_SECRET_KEY from it — BEFORE config.py (or anything that
     imports it, i.e. anything at all in this application) is ever
     imported, since Config.SECRET_KEY is read from that environment
     variable at class-body (import) time, once, permanently, for the
     life of the process.
  3. Only now import create_app / initialize_database and build the
     real application.
"""
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Mirrors config.py's own Stage 17 frozen-check exactly. Duplicated,
# not imported — see the module docstring above for why.
if getattr(sys, "frozen", False):
    _APP_DATA_ROOT = Path(sys.executable).resolve().parent
else:
    _APP_DATA_ROOT = Path(__file__).resolve().parent


def _bootstrap_secret_key() -> None:
    from app.bootstrap import get_or_create_secret_key

    if not os.environ.get("FINSIGHT_SECRET_KEY"):
        os.environ["FINSIGHT_SECRET_KEY"] = get_or_create_secret_key(_APP_DATA_ROOT)


def _choose_mode() -> str:
    """FINSIGHT_LAUNCH_MODE lets a desktop shortcut, or a scripted/
    unattended run, skip the interactive prompt entirely (Section 21 —
    a "FINsight LAN Host" shortcut can set this and never show a
    prompt at all)."""
    preset = os.environ.get("FINSIGHT_LAUNCH_MODE")
    if preset in ("local", "lan"):
        return preset

    print("How would you like to start?")
    print("  [1] Local Computer   - only this computer can access FINsight.")
    print("  [2] Private LAN Host - other computers on this trusted network can access FINsight through their browser.")
    while True:
        choice = input("Enter 1 or 2: ").strip()
        if choice == "1":
            return "local"
        if choice == "2":
            return "lan"
        print("Please enter 1 or 2.")


def _run_local(app) -> None:
    port = 5000

    def _open_browser():
        time.sleep(1.0)
        try:
            webbrowser.open(f"http://127.0.0.1:{port}")
        except Exception:
            pass  # Section 13: never block startup if this fails

    print(f"Local: http://127.0.0.1:{port}")
    print("Opening your browser... if it doesn't open automatically, use the address above.")
    threading.Thread(target=_open_browser, daemon=True).start()
    # Section 13: local mode must NOT bind to 0.0.0.0 unless LAN mode
    # was explicitly chosen — 127.0.0.1 only, exactly like run.py.
    app.run(host="127.0.0.1", port=port, debug=False)


def _run_lan(app) -> None:
    from waitress import serve

    from app.launch_common import print_lan_startup_banner, refuse_if_dev_secret_key

    app.config["LAN_MODE_ENABLED"] = True
    # Defense in depth (Section 18): _bootstrap_secret_key() above
    # should already guarantee a real secret was generated and set
    # before create_app() ever ran, so this should never actually
    # trigger in the packaged app — kept exactly as wsgi_lan.py's own
    # equivalent guard, unweakened.
    refuse_if_dev_secret_key(app)
    port = app.config["LAN_MODE_PORT"]
    print_lan_startup_banner(port)
    serve(app, host="0.0.0.0", port=port)


def main() -> None:
    print("FinSight")
    print("Offline Financial Review & Compliance Assistant")
    print()

    _bootstrap_secret_key()

    print("Initializing FinSight...")
    print("Creating local data directories...")

    from config import Config

    # Read before create_app() touches anything database-related — see
    # app/bootstrap.py's initialize_database() docstring for exactly
    # why this ordering matters.
    db_existed_before = Config.DATABASE_PATH.exists()

    from app import create_app
    from app.bootstrap import initialize_database

    app = create_app(Config)
    initialize_database(app.config, db_existed_before=db_existed_before, log=print)

    print("FinSight is ready.")
    print()

    mode = _choose_mode()
    if mode == "local":
        _run_local(app)
    else:
        _run_lan(app)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise  # e.g. refuse_if_dev_secret_key's sys.exit(...) — its own message is already user-safe
    except Exception as exc:  # noqa: BLE001 — Section 12: never show a raw traceback to the end user
        import logging

        logging.getLogger("app.bootstrap").exception("FINsight failed to start")
        print()
        print("FINsight could not start. Details were written to the logs/ folder next to this application.")
        print(f"({exc.__class__.__name__})")
        sys.exit(1)
