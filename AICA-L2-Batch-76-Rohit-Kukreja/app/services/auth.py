"""CSRF tokens. Build Prompt v2 §13.

**Single-user build.** There is no login, no session and no user record — the
firm asked for a local application anyone can open. Password hashing and
session cookies have been removed with the rest of the auth layer.

The CSRF token stays. It costs one cookie and one hidden field, and it still
stops another page in the browser from POSTing into this one — which is worth
having even when there is no session to hijack.
"""

from __future__ import annotations

import hmac
import secrets

CSRF_COOKIE = "auditcraft_csrf"
CSRF_MAX_AGE = 8 * 60 * 60  # one working day


class CsrfError(Exception):
    """Message is safe to show a user."""


def issue_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def check_csrf(cookie_token: str | None, form_token: str | None) -> None:
    """Double-submit cookie check on every mutating form."""
    if not cookie_token or not form_token:
        raise CsrfError("Missing CSRF token — reload the page and try again")
    if not hmac.compare_digest(cookie_token, form_token):
        raise CsrfError("CSRF token mismatch — reload the page and try again")
