from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.services.audit import audit
from app.services.auth import AuthError, authenticate, change_password
from app.web.deps import check_csrf, client_ip, current_user
from app.web.templating import flash, render

router = APIRouter()


LOCAL = {"127.0.0.1", "::1", "localhost"}


def _no_users(db: Session) -> bool:
    return not db.scalar(select(func.count()).select_from(User))


def _demo_hint(request: Request) -> str | None:
    """Sign-in details of the demo copy (synthetic data), shown only on the PC running it."""
    from app.core.config import get_settings
    f = get_settings().instance_dir / "demo_users.txt"
    if client_ip(request) in LOCAL and f.exists():
        return f.read_text(encoding="utf-8", errors="replace")
    return None


@router.get("/login")
def login_page(request: Request, db: Session = Depends(get_db)):
    if _no_users(db):
        return RedirectResponse("/setup", status_code=303)
    return render(request, "login.html", {"next": request.query_params.get("next", "/"),
                                          "demo_hint": _demo_hint(request)})


# ---------------------------------------------------------------- first Admin (no users yet)
@router.get("/setup")
def setup_page(request: Request, db: Session = Depends(get_db)):
    if not _no_users(db):
        return RedirectResponse("/login", status_code=303)
    return render(request, "setup.html", {"local": client_ip(request) in LOCAL})


@router.post("/setup", dependencies=[Depends(check_csrf)])
def setup(request: Request, username: str = Form(""), full_name: str = Form(""), password: str = Form(""),
          confirm: str = Form(""), db: Session = Depends(get_db)):
    from app.services.auth import create_user
    if not _no_users(db):
        return RedirectResponse("/login", status_code=303)
    if client_ip(request) not in LOCAL:            # only on the PC running the app
        return render(request, "setup.html", {"local": False}, status_code=403)
    try:
        if password != confirm:
            raise AuthError("The two passwords do not match.")
        u = create_user(db, username, password, "admin", full_name, must_change_password=False)
    except AuthError as exc:
        db.rollback()
        return render(request, "setup.html", {"local": True, "error": str(exc), "username": username,
                                              "full_name": full_name}, status_code=400)
    audit(db, "setup.first_admin", "user", u.username, user_id=u.id, ip=client_ip(request))
    db.commit()
    request.session.clear()
    request.session.update(uid=u.id, pwv=u.password_hash[-16:])
    flash(request, f"Welcome. You are the Admin. Add the other users in Admin → Users.")
    return RedirectResponse("/", status_code=303)


@router.post("/login", dependencies=[Depends(check_csrf)])
def login(request: Request, username: str = Form(""), password: str = Form(""), next: str = Form("/"),
          db: Session = Depends(get_db)):
    try:
        user = authenticate(db, username, password, client_ip(request))
    except AuthError as exc:
        db.commit()
        return render(request, "login.html", {"error": str(exc), "username": username, "next": next,
                                              "demo_hint": _demo_hint(request)}, status_code=401)
    db.commit()
    request.session.clear()                                   # new session id content on login
    request.session.update(uid=user.id, pwv=user.password_hash[-16:])
    target = next if next.startswith("/") and not next.startswith("//") else "/"
    return RedirectResponse("/account/password" if user.must_change_password else target, status_code=303)


@router.post("/logout")
def logout(request: Request, user: User = Depends(current_user), _=Depends(check_csrf),
           db: Session = Depends(get_db)):
    audit(db, "logout", "user", user.username, user_id=user.id, ip=client_ip(request))
    db.commit()
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/account/password")
def password_page(request: Request, user: User = Depends(current_user)):
    return render(request, "password.html", {"user": user})


@router.post("/account/password")
def password_change(request: Request, current: str = Form(""), new: str = Form(""), confirm: str = Form(""),
                    user: User = Depends(current_user), _=Depends(check_csrf), db: Session = Depends(get_db)):
    try:
        change_password(db, user, current, new, confirm)
    except AuthError as exc:
        return render(request, "password.html", {"user": user, "error": str(exc)}, status_code=400)
    db.commit()
    request.session["pwv"] = user.password_hash[-16:]
    flash(request, "Password changed.")
    return RedirectResponse("/", status_code=303)
