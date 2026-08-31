"""One configured Jinja environment, shared by every router.

Exists for `asset_url`, which stamps a content fingerprint onto the stylesheet
and the workspace script.

**Why that matters here.** `app.css` and `workspace.js` are served under fixed
names, so a browser that has held a page open across a change keeps its cached
copy: the HTML is new and the stylesheet is months old. That produced a
dashboard rendering with the new markup and none of its rules — an 800-pixel
logo, quick actions as a run of underlined links — which looks like a broken
build and is not one. Telling someone to hard-refresh is not a fix; it just
moves the failure to the next person who does not.

The vendored HTMX and Alpine files do not need this: their version is already in
the filename, so a new version is a new URL.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal, InvalidOperation
from functools import lru_cache

from fastapi.templating import Jinja2Templates

from app.config import PROJECT_ROOT
from app.core.formatting import group_indian

STATIC_DIR = PROJECT_ROOT / "app" / "static"


@lru_cache(maxsize=32)
def _fingerprint(name: str) -> str:
    """Eight hex characters of the file's content hash.

    Content, not modification time: a file restored from a backup or checked out
    again keeps its identity, and two machines serving the same bytes agree.
    Cached, so this is one read per file per process rather than one per request.
    """
    path = STATIC_DIR / name
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:8]
    except OSError:
        # A missing asset is the template's problem to show, not a reason to
        # fail the whole page render.
        return "0"


def asset_url(name: str) -> str:
    """`/static/app.css` with the content fingerprint attached."""
    return f"/static/{name}?v={_fingerprint(name)}"


def accounting(value: object) -> str:
    """A figure the way it is written in a set of accounts.

    Lakh/crore grouping, and a loss in brackets rather than with a minus sign.
    The screen has to agree with the printed report, and the report has used
    `group_indian` since the first build -- a schedule showing "-500000.00"
    beside a Board's Report showing "(5,00,000)" is the same figure twice in
    two languages.

    Empty for a blank cell, deliberately: nought is a figure someone arrived
    at, and not-yet-entered is not.
    """
    if value is None or value == "":
        return ""
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        return str(value)
    grouped = group_indian(abs(amount))
    return f"({grouped})" if amount < 0 else grouped


def build_templates() -> Jinja2Templates:
    templates = Jinja2Templates(directory=str(PROJECT_ROOT / "app" / "templates"))
    templates.env.globals["asset_url"] = asset_url
    templates.env.filters["accounting"] = accounting
    return templates
