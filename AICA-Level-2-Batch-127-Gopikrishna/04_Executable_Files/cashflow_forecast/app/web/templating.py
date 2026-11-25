"""Jinja2 environment and display filters."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app import __version__
from app.core.config import PROJECT_ROOT
from app.web.deps import CAN_ADMIN, CAN_APPROVE, CAN_AUDIT, CAN_EDIT, csrf_token

templates = Jinja2Templates(directory=PROJECT_ROOT / "app" / "templates")


def money(v, blank_zero: bool = True) -> str:
    """#,##0.000 with negatives in brackets and zero as '-' (the export uses the same format)."""
    if v is None or v == "":
        return ""
    d = Decimal(str(v))
    if d == 0 and blank_zero:
        return "-"
    s = f"{abs(d):,.3f}"
    return f"({s})" if d < 0 else s


def neg(v) -> bool:
    try:
        return Decimal(str(v)) < 0
    except Exception:
        return False


def local_time(v: datetime) -> datetime:
    """Stored times are UTC; show them in local time (CFF_UTC_OFFSET_HOURS, default +4 for Oman)."""
    from app.core.config import get_settings
    if v.tzinfo is not None:
        v = v.astimezone(timezone.utc).replace(tzinfo=None)
    return v + timedelta(hours=get_settings().utc_offset_hours)


def dmy(v) -> str:
    if isinstance(v, datetime):
        return f"{local_time(v):%d-%b-%Y %H:%M}"
    if isinstance(v, date):
        return f"{v:%d-%b-%Y}"
    return v or ""


templates.env.filters.update(money=money, neg=neg, dmy=dmy)
templates.env.globals.update(version=__version__)


def render(request: Request, name: str, ctx: dict | None = None, status_code: int = 200, headers=None):
    user = (ctx or {}).get("user")
    base = {"request": request, "csrf": csrf_token(request), "user": user,
            "can_edit": bool(user and user.role in CAN_EDIT), "can_admin": bool(user and user.role in CAN_ADMIN),
            "can_approve": bool(user and user.role in CAN_APPROVE),
            "can_audit": bool(user and user.role in CAN_AUDIT),
            "flash": request.session.pop("flash", None)}
    return templates.TemplateResponse(request, name, {**base, **(ctx or {})}, status_code=status_code,
                                      headers=headers)


def flash(request: Request, message: str, kind: str = "success") -> None:
    request.session["flash"] = {"message": message, "kind": kind}
