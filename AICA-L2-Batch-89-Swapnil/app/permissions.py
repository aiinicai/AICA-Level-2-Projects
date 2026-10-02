"""Role -> permission map and the @require decorator (brief §4).
Every protected route is decorated; hiding a button is never the control."""
from __future__ import annotations

from functools import wraps

from flask import abort, g, request
from flask_login import current_user

PERMISSIONS: dict[str, set[str]] = {
    "VIEWER": {"view"},
    "PREPARER": {"view", "edit_entity", "record_event", "work_status"},
    "MANAGER": {"view", "view_all", "edit_entity", "record_event", "work_status", "approve", "assign",
                "archive_entity", "read_audit"},
    "PARTNER": {"view", "view_all", "edit_entity", "record_event", "work_status", "approve", "assign",
                "archive_entity", "delete_entity", "read_audit", "mark_filed", "waive", "verify_rule",
                "decide", "reveal_pan"},
    "OWNER": {"view", "view_all", "edit_entity", "record_event", "work_status", "approve", "assign",
              "archive_entity", "delete_entity", "read_audit", "mark_filed", "waive", "verify_rule",
              "decide", "reveal_pan", "edit_rulepack", "manage_users", "settings"},
}

DENIED_MESSAGES = {
    "mark_filed": "A preparer cannot mark an obligation filed. Mark it Ready for review; a partner will confirm.",
    "approve": "Only a manager, partner or owner can approve an obligation for filing.",
    "waive": "Only a partner or owner can mark an obligation Not applicable or Waived.",
    "read_audit": "The audit trail is visible to managers, partners and the owner only.",
    "manage_users": "Only the owner can manage staff accounts.",
    "delete_entity": "Only a partner or owner can delete an entity. Managers can archive it instead.",
    "archive_entity": "Only a manager, partner or owner can archive an entity.",
    "assign": "Only a manager, partner or owner can assign work.",
    "verify_rule": "Only a partner or owner can verify a rule.",
    "edit_rulepack": "Only the owner can edit or publish the rule pack.",
    "settings": "Only the owner can change firm settings.",
    "edit_entity": "Your role cannot add or edit entities.",
    "record_event": "Your role cannot record corporate events.",
    "work_status": "Your role cannot change the status of obligations.",
    "decide": "Only a partner or owner can record a classification decision.",
    "reveal_pan": "Only a partner or owner can view a full PAN.",
}


def has(user, perm: str) -> bool:
    return bool(user and getattr(user, "is_authenticated", False) and perm in PERMISSIONS.get(user.role, set()))


class Denied(Exception):
    def __init__(self, perm: str, message: str | None = None, status: int = 403):
        self.perm, self.status = perm, status
        self.message = message or DENIED_MESSAGES.get(perm, "You do not have permission to do that.")
        super().__init__(self.message)


def deny(perm: str, message: str | None = None, status: int = 403, object_type: str = "route",
         object_id=None, entity_id=None):
    """Write the denied attempt to the audit log (own transaction) and abort."""
    from . import audit
    from .auth import actor
    from .models import db
    s = db.session
    s.rollback()
    audit.record(s, actor(), "DENIED", object_type, object_id or request.path, entity_id,
                 after={"permission": perm, "method": request.method, "message": message or
                        DENIED_MESSAGES.get(perm, "")})
    s.commit()
    g.denied_message = message or DENIED_MESSAGES.get(perm, "You do not have permission to do that.")
    abort(status)


def require(perm: str):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if not current_user.is_authenticated:
                from flask import current_app
                return current_app.login_manager.unauthorized()
            if not has(current_user, perm):
                deny(perm)
            return fn(*a, **kw)
        wrapper.required_permission = perm
        return wrapper
    return deco


def can_see_entity(user, entity) -> bool:
    if has(user, "view_all"):
        return True
    return entity is not None and user.id in (entity.preparer_id, entity.rm_id)
