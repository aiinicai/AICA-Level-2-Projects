"""
RBAC role names used across the FAR system.

Modelled directly on the blueprint's security section: "separate rights for
data entry, verification, and approval; no single user can create and
approve a disposal." Roles are plain Django Groups so they stay editable
from /admin without a code change, but every view that needs a role check
imports the constants from here rather than hard-coding strings.
"""

DATA_ENTRY = "Data Entry"
VERIFIER = "Verifier"
APPROVER = "Approver"
ADMIN_CFO = "Admin/CFO"
AUDITOR_READONLY = "Auditor (Read-only)"

ALL_ROLES = [DATA_ENTRY, VERIFIER, APPROVER, ADMIN_CFO, AUDITOR_READONLY]


def user_has_role(user, *role_names):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=role_names).exists()
