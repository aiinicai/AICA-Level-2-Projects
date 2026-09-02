"""
Small pieces shared between every real launcher — wsgi_lan.py (LAN-only,
manual dev/ops use), run.py (local-only, manual dev use), and the new
Stage 17 packaged entry point, finsight_app.py (either mode, chosen at
runtime, one PyInstaller build).

Factored out here, rather than importing from wsgi_lan.py directly, so
that importing these two functions never has the side effect of also
building a second, redundant Flask app / requiring Waitress to already
be importable just to check a secret key. wsgi_lan.py imports and
re-exports these under their original names, so nothing about its own
behavior or the existing Stage 16 tests that reference
`wsgi_lan._refuse_if_dev_secret_key` changes.
"""
from __future__ import annotations

import sys

from flask import Flask


def refuse_if_dev_secret_key(app: Flask) -> None:
    """Stage 2 review, condition #3, generalized at Stage 17: no
    launcher that binds beyond 127.0.0.1-only, single-process local use
    should ever run with the development SECRET_KEY fallback. Hard
    stop, not a warning — a warning is too easy to miss before exposing
    the app to other machines on the network."""
    from config import DEV_SECRET_KEY_FALLBACK

    if app.config["SECRET_KEY"] == DEV_SECRET_KEY_FALLBACK:
        sys.exit(
            "FinSight LAN mode refused to start: SECRET_KEY is still the "
            "development fallback. Set a real secret before enabling LAN "
            "mode, e.g.:\n"
            "    export FINSIGHT_SECRET_KEY=$(python3 -c "
            "'import secrets; print(secrets.token_hex(32))')\n"
            "then re-run wsgi_lan.py.\n"
            "(The packaged FINsight.exe generates and stores a real secret "
            "automatically on first run and should never hit this.)"
        )


def print_lan_startup_banner(port: int) -> None:
    """Section 14/15: show the local and LAN URLs on startup. IP
    detection is local-only (see get_local_lan_ip's own docstring) and
    must never block startup if it fails."""
    from app.security.lan_auth import get_local_lan_ip

    lan_ip = get_local_lan_ip()
    print("FinSight LAN Server Started")
    print()
    print("Local:")
    print(f"  http://127.0.0.1:{port}")
    print()
    print("LAN:")
    if lan_ip:
        print(f"  http://{lan_ip}:{port}")
    else:
        print("  Could not automatically detect this computer's LAN IPv4 address.")
        print("  Use the host computer's local IPv4 address shown in your network settings,")
        print(f"  and connect to it on port {port}.")
    print()
    print("Open the LAN address from another computer connected to the same network.")
    print("LAN users must be on the same trusted network — this is not internet-facing.")
    print()
