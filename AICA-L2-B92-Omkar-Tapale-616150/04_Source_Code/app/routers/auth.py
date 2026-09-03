from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models
from ..auth import verify_password, hash_password, get_current_user, log_audit
from ..main import templates  # noqa: E402  (templates configured in main)

router = APIRouter()


@router.get("/login")
def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse(request, "login.html", {"request": request, "error": None})


@router.post("/login")
def login_submit(
    request: Request,
    employee_code: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(
        models.User.employee_code == employee_code.strip(),
        models.User.is_active == True,  # noqa: E712
    ).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(request, "login.html", {"request": request, "error": "Invalid employee code or password."}
        )
    request.session["user_id"] = user.id
    log_audit(db, user, "LOGIN", f"{user.employee_code} logged in")
    if user.must_change_password:
        return RedirectResponse("/change-password", status_code=303)
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/change-password")
def change_password_page(request: Request, user: models.User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "change_password.html", {"request": request, "user": user, "error": None})


@router.post("/change-password")
def change_password_submit(
    request: Request,
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if new_password != confirm_password:
        return templates.TemplateResponse(request, "change_password.html", {"request": request, "user": user, "error": "Passwords do not match."}
        )
    if len(new_password) < 8:
        return templates.TemplateResponse(request, "change_password.html", {"request": request, "user": user, "error": "Password must be at least 8 characters."}
        )
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()
    log_audit(db, user, "PASSWORD_CHANGE", f"{user.employee_code} changed their own password")
    return RedirectResponse("/dashboard", status_code=303)
