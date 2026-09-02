"""
CSRF protection (Stage 15 section 13).

A plain synchronizer-token check, standard-library only (`secrets` +
Flask's existing signed-cookie `session`, already in use since Stage 5
for `current_engagement_id`) — no new dependency. Flask-WTF was never
on the approved package list (Blueprint Section L, requirements.txt's
own header comment: "Do not add a new dependency without flagging it
first"), and wsgi_lan.py's own docstring already recorded this as a
"MANDATORY PRE-LAN REQUIREMENT... deliberately NOT added now... belongs
immediately before [LAN mode]" — this module is that requirement, now
implemented ahead of Stage 16.

How it works: every response mints (or reuses) a per-session random
token, exposed to templates as `csrf_field()` — a hidden `<input>`
rendered into every `<form method="post">`. Every non-safe-method
request (POST/PUT/PATCH/DELETE) must submit that same token back in its
form body; a missing or mismatched token is rejected with 400 before
the view function ever runs, so no state-changing route needs its own
CSRF check.

Test-suite note: `TestConfig.CSRF_ENABLED = False` (config.py) turns
this off for the existing HTTP test suites, which POST directly without
first scraping a token out of rendered HTML — the same, widely-used
convention as Flask-WTF's own `WTF_CSRF_ENABLED = False` test setting.
`tests/test_stage15_security.py` exercises real enforcement with its
own config that re-enables it.
"""
from __future__ import annotations

import secrets

from flask import Flask, abort, request, session
from markupsafe import Markup

SESSION_KEY = "_csrf_token"
FORM_FIELD = "csrf_token"

# GET/HEAD/OPTIONS never change state, so they carry no CSRF risk and
# are never blocked — matches the same "safe method" convention every
# mainstream CSRF implementation (Django, Flask-WTF, Rails) uses.
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _get_or_create_token() -> str:
    token = session.get(SESSION_KEY)
    if not token:
        token = secrets.token_hex(32)
        session[SESSION_KEY] = token
    return token


def csrf_field() -> Markup:
    """Called from Jinja as `{{ csrf_field() }}` — the ONE deliberate,
    reviewed use of unescaped HTML output in this codebase (Stage 14's
    audit confirmed no template uses `|safe`/`Markup` anywhere; this is
    the sole addition). The value itself is a server-generated random
    hex token, never user input, so there is no injection surface here."""
    token = _get_or_create_token()
    return Markup(f'<input type="hidden" name="{FORM_FIELD}" value="{token}">')


def init_csrf_protection(app: Flask) -> None:
    app.jinja_env.globals["csrf_field"] = csrf_field

    @app.before_request
    def _enforce_csrf():
        if not app.config.get("CSRF_ENABLED", True):
            return None
        if request.method in _SAFE_METHODS:
            return None
        if request.endpoint == "static":
            return None

        expected = session.get(SESSION_KEY)
        submitted = request.form.get(FORM_FIELD)
        if not expected or not submitted or not secrets.compare_digest(submitted, expected):
            abort(
                400,
                description=(
                    "Your session appears to have expired, or this form was submitted from an "
                    "unexpected source. Please go back, refresh the page, and try again."
                ),
            )
        return None
