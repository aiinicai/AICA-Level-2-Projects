# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Access levels and the rights they carry - the single definition used by the pages, the workflow and the tests.

A user has ONE access level. Existing accounts made before access levels existed are mapped from their old role
(Admin -> admin, Reviewer -> edit_approve, Preparer -> edit), so nothing changes for them. The database's ``role`` column
only allows Preparer / Reviewer / Admin, so each level also has the closest ``role`` (used for the older checks).
Pure Python: no UI framework and no database.
"""
RIGHTS = {
    "view": "See leases, the dashboard, reports and exports",
    "edit": "Add, upload, edit and resubmit leases; save memos",
    "approve": "Approve or reject leases",
    "audit": "See the audit log",
    "delete": "Delete leases",
    "manage_users": "Create users and set their access",
}

ACCESS_LEVELS = {
    "view": {
        "label": "View only",
        "description": "Can only see: leases, results, the dashboard, reports and exports. Cannot change anything.",
        "rights": ("view",),
        "role": "Preparer",
    },
    "edit": {
        "label": "Editor",
        "description": "Can see everything and add, upload, edit and resubmit leases. Cannot approve.",
        "rights": ("view", "edit"),
        "role": "Preparer",
    },
    "approve": {
        "label": "Approver",
        "description": "Can see everything, approve or reject leases and read the audit log. Cannot edit.",
        "rights": ("view", "approve", "audit"),
        "role": "Reviewer",
    },
    "edit_approve": {
        "label": "Editor and Approver",
        "description": "Can edit leases, approve or reject them and read the audit log.",
        "rights": ("view", "edit", "approve", "audit"),
        "role": "Reviewer",
    },
    "admin": {
        "label": "Admin",
        "description": "Everything, plus deleting leases and managing users. Deletion is only ever an Admin's right.",
        "rights": ("view", "edit", "approve", "audit", "delete", "manage_users"),
        "role": "Admin",
    },
}
DEFAULT_LEVEL = "view"  # the safest level: what an unknown or missing level means
LEGACY_ROLE_LEVEL = {"Admin": "admin", "Reviewer": "edit_approve", "Preparer": "edit"}


def is_level(value) -> bool:
    return isinstance(value, str) and value in ACCESS_LEVELS


def level_for(access_level, role=None) -> str:
    """The user's access level: the stored one, else the one mapped from the old role, else 'view' (never more than intended)."""
    if is_level(access_level):
        return access_level
    return LEGACY_ROLE_LEVEL.get(role, DEFAULT_LEVEL)


def rights_of(level_or_role) -> frozenset:
    """The rights of an access level or of an old role name; nothing for anything unknown."""
    key = level_or_role if is_level(level_or_role) else LEGACY_ROLE_LEVEL.get(level_or_role)
    return frozenset(ACCESS_LEVELS[key]["rights"]) if key else frozenset()


def has_right(level_or_role, right: str) -> bool:
    return right in rights_of(level_or_role)


def role_for_level(level: str) -> str:
    """The database ``role`` value that goes with an access level (Preparer / Reviewer / Admin)."""
    if not is_level(level):
        raise ValueError("Unknown access level: {!r}".format(level))
    return ACCESS_LEVELS[level]["role"]


def level_label(level) -> str:
    return ACCESS_LEVELS[level]["label"] if is_level(level) else str(level)
