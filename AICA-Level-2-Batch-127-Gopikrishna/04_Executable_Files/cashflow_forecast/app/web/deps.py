"""Request dependencies: database session, signed-in user, role checks, CSRF."""
from __future__ import annotations

import hmac
import secrets

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Role, User

# what each role may do. Everyone signed in can read and export. Approver reads, exports and
# approves; it changes no data itself. Nobody approves their own change (services.overrides).
CAN_EDIT = {Role.ADMIN, Role.PREPARER}      # uploads, overrides, balances, exceptions, snapshots
CAN_APPROVE = {Role.ADMIN, Role.APPROVER}   # approve / reject changes waiting for approval
CAN_AUDIT = {Role.ADMIN, Role.APPROVER}     # read the audit log
CAN_ADMIN = {Role.ADMIN}                    # settings, categories, scenarios, users


class LoginRequired(Exception):
    pass


class PasswordChangeRequired(Exception):
    pass


class Forbidden(Exception):
    def __init__(self, message: str = "You do not have permission for this."):
        self.message = message


def csrf_token(request: Request) -> str:
    tok = request.session.get("csrf")
    if not tok:
        tok = request.session["csrf"] = secrets.token_urlsafe(32)
    return tok


async def check_csrf(request: Request) -> None:
    """Every state-changing request must echo the session's token (form field or HTMX header)."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    sent = request.headers.get("x-csrf-token")
    if not sent:
        form = await request.form()
        sent = form.get("csrf_token")
    expected = request.session.get("csrf", "")
    if not expected or not sent or not hmac.compare_digest(str(sent), expected):
        raise Forbidden("The form has expired. Reload the page and try again.")


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    uid = request.session.get("uid")
    user = db.get(User, uid) if uid else None
    if user is None or not user.is_active or request.session.get("pwv") != user.password_hash[-16:]:
        request.session.pop("uid", None)
        raise LoginRequired()
    if user.must_change_password and request.url.path not in ("/account/password", "/logout"):
        raise PasswordChangeRequired()
    return user


def viewer(user: User = Depends(current_user), _=Depends(check_csrf)) -> User:
    return user


def editor(user: User = Depends(current_user), _=Depends(check_csrf)) -> User:
    if user.role not in CAN_EDIT:
        raise Forbidden("Only a Preparer or Admin can change data.")
    return user


def approver(user: User = Depends(current_user), _=Depends(check_csrf)) -> User:
    if user.role not in CAN_APPROVE:
        raise Forbidden("Only an Approver or Admin can approve changes.")
    return user


def auditor(user: User = Depends(current_user), _=Depends(check_csrf)) -> User:
    if user.role not in CAN_AUDIT:
        raise Forbidden("Only an Admin or Approver can read the audit log.")
    return user


def admin(user: User = Depends(current_user), _=Depends(check_csrf)) -> User:
    if user.role not in CAN_ADMIN:
        raise Forbidden("Only an Admin can do this.")
    return user


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ""
