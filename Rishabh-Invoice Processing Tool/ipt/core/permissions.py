"""Role-based permissions. UI hides controls; services enforce them too."""
from __future__ import annotations

ADMIN, ACCOUNTANT, REVIEWER = "admin", "accountant", "reviewer"
ROLES = (ADMIN, ACCOUNTANT, REVIEWER)

PERMISSIONS: dict[str, set[str]] = {
    ADMIN: {"*"},
    ACCOUNTANT: {"invoice.process", "invoice.edit", "invoice.approve", "invoice.delete", "invoice.view", "mapping.edit",
                 "tally.import", "gst.upload", "recon.run", "recon.edit", "report.view",
                 "export.run", "company.view", "backup.run"},
    REVIEWER: {"invoice.view", "invoice.approve", "recon.edit", "report.view", "company.view"},
}


def has_permission(role: str | None, permission: str) -> bool:
    perms = PERMISSIONS.get(role or "", set())
    return "*" in perms or permission in perms


class PermissionDenied(Exception):
    pass


def require(role: str | None, permission: str) -> None:
    if not has_permission(role, permission):
        raise PermissionDenied(f"Your role ({role}) does not allow: {permission}")
