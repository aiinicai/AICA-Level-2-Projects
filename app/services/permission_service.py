"""Per-user module rights. Administrator always has full access."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.models.user import User

MODULES = (
    ("dashboard", "Control Tower"),
    ("daybook", "Day Book"),
    ("cash_rec", "Cash Rec"),
    ("card_qr", "Card / QR Rec"),
    ("aggregators", "Aggregators"),
    ("attendance", "Attendance Rec"),
    ("reports", "Reports & Analytics"),
    ("gst_report", "GST Payable Report"),
)

ACTIONS = (
    ("view", "Open the screen"),
    ("enter", "Add or import new data"),
    ("edit_saved", "Change data after it is saved"),
)

_EMPTY_MODULE = {"view": False, "enter": False, "edit_saved": False}


def _all_true() -> Dict[str, Dict[str, bool]]:
    return {key: {"view": True, "enter": True, "edit_saved": True} for key, _ in MODULES}


def default_permissions(role_name: Optional[str]) -> Dict[str, Dict[str, bool]]:
    role = (role_name or "").strip()
    perms = {key: dict(_EMPTY_MODULE) for key, _ in MODULES}
    perms["dashboard"]["view"] = True
    if role == "Administrator":
        return _all_true()
    if role == "Accounts Manager":
        return _all_true()
    if role == "Branch User":
        for key in ("dashboard", "daybook", "cash_rec", "attendance"):
            perms[key] = {"view": True, "enter": True, "edit_saved": False}
        for key in ("card_qr", "aggregators", "reports", "gst_report"):
            perms[key] = {"view": True, "enter": False, "edit_saved": False}
        return perms
    # Viewer
    for key, _ in MODULES:
        perms[key] = {"view": True, "enter": False, "edit_saved": False}
    return perms


def normalize_permissions(raw: Any, role_name: Optional[str] = None) -> Dict[str, Dict[str, bool]]:
    base = default_permissions(role_name)
    if not isinstance(raw, dict):
        return base
    for key, _ in MODULES:
        incoming = raw.get(key) or {}
        if not isinstance(incoming, dict):
            continue
        for action, _label in ACTIONS:
            if action in incoming:
                base[key][action] = bool(incoming[action])
        if base[key]["enter"] or base[key]["edit_saved"]:
            base[key]["view"] = True
        if base[key]["edit_saved"]:
            base[key]["enter"] = True
    return base


def effective_permissions(user: Optional[User]) -> Dict[str, Dict[str, bool]]:
    if not user:
        return {key: dict(_EMPTY_MODULE) for key, _ in MODULES}
    role = user.role.name if user.role else ""
    if role == "Administrator":
        return _all_true()
    return normalize_permissions(getattr(user, "permissions", None), role)


def user_can(user: Optional[User], module: str, action: str) -> bool:
    if not user:
        return False
    role = user.role.name if user.role else ""
    if role == "Administrator":
        return True
    perms = effective_permissions(user)
    return bool((perms.get(module) or {}).get(action))


def require_module(user: User, module: str, action: str) -> None:
    if user_can(user, module, action):
        return
    labels = {k: v for k, v in MODULES}
    acts = {k: v for k, v in ACTIONS}
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"You cannot {acts.get(action, action).lower()} on {labels.get(module, module)}.",
    )


def assert_write(user: User, module: str, record_exists: bool) -> None:
    require_module(user, module, "edit_saved" if record_exists else "enter")


def module_catalog() -> list:
    return [{"key": k, "label": v} for k, v in MODULES]
