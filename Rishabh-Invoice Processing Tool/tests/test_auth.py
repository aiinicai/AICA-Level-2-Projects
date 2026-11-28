import pytest

from ipt.core.permissions import PermissionDenied
from ipt.services.auth_service import AuthError, AuthService


def test_first_user_must_be_admin(db):
    with pytest.raises(AuthError):
        AuthService(db).create_user("acc", "password123", "accountant")


def test_login_and_wrong_password(db, admin):
    svc = AuthService(db)
    assert svc.authenticate("ADMIN", "admin12345").role == "admin"
    with pytest.raises(AuthError):
        svc.authenticate("admin", "wrong-pass")


def test_short_password_rejected(db, admin):
    with pytest.raises(AuthError):
        AuthService(db).create_user("x", "short", "reviewer", actor=admin)


def test_reviewer_cannot_create_users(db, admin):
    svc = AuthService(db)
    rev = svc.create_user("rev", "password123", "reviewer", actor=admin)
    with pytest.raises(PermissionDenied):
        svc.create_user("y", "password123", "reviewer", actor=rev)


def test_last_admin_protected(db, admin):
    svc = AuthService(db)
    with pytest.raises(AuthError):
        svc.set_role(admin.id, "reviewer", admin)


def test_deactivated_user_cannot_login(db, admin):
    svc = AuthService(db)
    u = svc.create_user("acc", "password123", "accountant", actor=admin)
    svc.set_active(u.id, False, admin)
    with pytest.raises(AuthError):
        svc.authenticate("acc", "password123")


def test_password_not_in_audit(db, admin):
    from ipt.services.audit_service import AuditService
    for row in AuditService(db).recent():
        assert "admin12345" not in row.after_json
