"""
Standalone launcher — Flask's built-in dev server, single machine.
Not for LAN mode; see wsgi_lan.py for the Waitress-based launcher
(Blueprint Section 26).
"""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Stage 15 hardening: this used to hard-code debug=True. Flask's
    # interactive debugger (enabled by debug=True) lets anyone who can
    # reach an error page on this server execute arbitrary Python via
    # the browser once they have the console PIN — a real risk to
    # default to ON, even though this launcher only binds to 127.0.0.1
    # (loopback-only, so only processes on this same machine could ever
    # reach it; wsgi_lan.py is the actual LAN-facing launcher and never
    # enables debug mode at all). Defaulting to off here, with an
    # explicit opt-in for local development, is the safer default
    # without removing the capability:
    #   FINSIGHT_DEV_DEBUG=true python run.py
    debug = os.environ.get("FINSIGHT_DEV_DEBUG", "false").lower() == "true"
    app.run(host="127.0.0.1", port=5000, debug=debug)
