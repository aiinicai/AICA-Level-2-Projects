"""
Local Network Mode launcher (Blueprint Section 26; implemented Stage 16).

Serves the same Flask app via Waitress (a production-grade, pure-Python
WSGI server — chosen so the EXE build, Blueprint Section L, doesn't need
a C-extension WSGI server) bound to 0.0.0.0 so other machines on the same
trusted LAN can reach it at http://<host-ip>:<port>.

V1 scope reminder (Blueprint Section N): this is a single shared
access password (Stage 16), not multi-user accounts. Not
internet-facing — do not port-forward this beyond a trusted local
network; see documentation/stage16_lan_mode.md for firewall guidance
and known limitations.

CSRF protection (the "MANDATORY PRE-LAN REQUIREMENT" this docstring
used to record as outstanding) was implemented in Stage 15
(app/security/csrf.py) and remains fully enabled here — Stage 16 does
not weaken it. The LAN access password gate (app/security/lan_auth.py,
app/api/access_bp.py) is Stage 16's own addition, layered on top of,
not instead of, CSRF and the existing session-cookie hardening
(SESSION_COOKIE_HTTPONLY / SESSION_COOKIE_SAMESITE, config.py).
"""
from waitress import serve

from app import create_app
# Stage 17: these two helpers now live in app/launch_common.py so the
# new packaged entry point (finsight_app.py) can reuse them without
# importing this whole module (which would build a second, redundant
# Flask app just to reach them). Re-exported under their original names
# so this module's own behavior, and the existing Stage 16 tests that
# reference wsgi_lan._refuse_if_dev_secret_key directly, are unchanged.
from app.launch_common import refuse_if_dev_secret_key as _refuse_if_dev_secret_key
from app.launch_common import print_lan_startup_banner as _print_startup_banner

app = create_app()

# Only this launcher ever turns LAN mode on. run.py (local/dev,
# 127.0.0.1-only) never sets this, so the access-gate before_request
# hook (app/security/lan_auth.py) stays a permanent no-op there — the
# two launchers share 100% of the same application code, per Stage 16
# Section 25, and differ only in this one flag plus the WSGI server and
# bind address below.
app.config["LAN_MODE_ENABLED"] = True


if __name__ == "__main__":
    _refuse_if_dev_secret_key(app)
    port = app.config["LAN_MODE_PORT"]
    _print_startup_banner(port)
    serve(app, host="0.0.0.0", port=port)
