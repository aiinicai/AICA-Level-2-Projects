"""Per-user module permissions. A role gives the starting set; an admin can tick or untick modules for each person."""
import json

from flask import g

from .models import FirmSetting

MODULES = {
    "clients": "Clients", "trackers": "GST / ITR / TDS", "calendar": "Compliance calendar", "tasks": "Tasks",
    "messages": "WhatsApp & Email", "timesheet": "Time sheet", "matters": "Matters & hearings", "billing": "Billing", "reports": "Reports", "staff": "Staff",
    "activity": "Activity log", "settings": "Settings & backup",
}
BLUEPRINT_MODULE = {"clients": "clients", "trackers": "trackers", "calendar": "calendar", "tasks": "tasks", "whatsapp": "messages",
                    "timesheet": "timesheet", "matters": "matters", "billing": "billing", "reports": "reports", "staff": "staff", "activity": "activity", "settings": "settings"}
BASIC = ["clients", "trackers", "calendar", "tasks", "messages", "timesheet", "matters"]
ROLE_DEFAULTS = {"employee": BASIC, "manager": BASIC + ["billing", "reports", "staff"],
                 "partner": list(MODULES), "super_admin": list(MODULES)}
ELEVATED = {"billing", "reports", "staff", "activity", "settings"}  # normally need a senior role; can be granted per person


def role_default(role: str) -> set[str]:
    return set(ROLE_DEFAULTS.get(role, BASIC))


def stored(user) -> set[str] | None:
    raw = FirmSetting.get(f"perm_user_{user.id}")
    if not raw:
        return None
    try:
        return {m for m in json.loads(raw) if m in MODULES}
    except (ValueError, TypeError):
        return None


def effective(user) -> set[str]:
    if user.role == "super_admin":
        return set(MODULES)  # the owner can never be locked out
    custom = stored(user)
    return role_default(user.role) if custom is None else custom


def can(user, module: str) -> bool:
    if user is None:
        return False
    cache = g.setdefault("_perm_cache", {})
    if user.id not in cache:
        cache[user.id] = effective(user)
    return module in cache[user.id]


def granted_elevated(user, blueprint: str | None) -> bool:
    module = BLUEPRINT_MODULE.get(blueprint or "")
    return module in ELEVATED and can(user, module)


def save(user, modules: list[str]) -> None:
    chosen = sorted(m for m in set(modules) if m in MODULES)
    if set(chosen) == role_default(user.role):
        FirmSetting.put(f"perm_user_{user.id}", "")
    else:
        FirmSetting.put(f"perm_user_{user.id}", json.dumps(chosen))
