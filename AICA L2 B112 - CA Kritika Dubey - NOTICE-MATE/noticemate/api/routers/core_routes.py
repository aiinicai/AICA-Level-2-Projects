"""Auth, users, cases, documents, audit."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Header, UploadFile
from fastapi.responses import Response

from ...core import audit as audit_core
from ...core.config import get_settings
from ...core.errors import ValidationError
from ...services import auth, cases, documents
from .. import schemas as S
from ..deps import bearer, current_user

router = APIRouter()


@router.post("/auth/login")
def login(body: S.LoginIn):
    return auth.login(body.username, body.password)


@router.post("/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    auth.logout(bearer(authorization))
    return {"ok": True}


@router.get("/auth/me")
def me(user=Depends(current_user)):
    return user


@router.post("/auth/password")
def change_password(body: S.PasswordChangeIn, user=Depends(current_user)):
    auth.change_password(user, body.old_password, body.new_password)
    return {"ok": True, "note": "All sessions revoked; please log in again."}


@router.get("/users")
def users(user=Depends(current_user)):
    auth.require_role(user, "ADMIN", "CA")
    return auth.list_users()


@router.post("/users")
def create_user(body: S.UserIn, user=Depends(current_user)):
    return auth.create_user(body.username, body.full_name, body.role, body.password, membership_no=body.membership_no, actor_id=user["id"])


@router.post("/users/{user_id}/unlock")
def unlock(user_id: int, user=Depends(current_user)):
    auth.unlock_user(user_id, user)
    return {"ok": True}


# ---- cases ----
@router.get("/cases")
def list_cases(user=Depends(current_user)):
    return cases.list_cases(user)


@router.post("/cases")
def create_case(body: S.CaseIn, user=Depends(current_user)):
    return cases.create_case(user, **body.model_dump())


@router.get("/cases/{case_id}")
def get_case(case_id: int, user=Depends(current_user)):
    return cases.get_case(user, case_id)


@router.put("/cases/{case_id}/redaction-terms")
def terms(case_id: int, body: S.TermsIn, user=Depends(current_user)):
    return cases.update_party_names(user, case_id, body.names)


@router.post("/cases/{case_id}/members")
def add_member(case_id: int, body: S.MemberIn, user=Depends(current_user)):
    cases.add_member(user, case_id, body.user_id)
    return {"ok": True}


@router.put("/cases/{case_id}/status")
def set_status(case_id: int, body: S.StatusIn, user=Depends(current_user)):
    cases.set_status(user, case_id, body.status)
    return {"ok": True}


@router.get("/cases/{case_id}/delete-preview")
def delete_preview(case_id: int, user=Depends(current_user)):
    return cases.deletion_preview(user, case_id)


@router.post("/cases/{case_id}/delete")
def delete_case(case_id: int, body: S.CaseDeleteIn, user=Depends(current_user)):
    return cases.delete_case(user, case_id, body.confirm_case_ref)


@router.get("/cases/{case_id}/history")
def history(case_id: int, user=Depends(current_user)):
    return cases.history(user, case_id)


# ---- documents ----
@router.post("/cases/{case_id}/documents")
async def upload(case_id: int, file: UploadFile = File(...), user=Depends(current_user)):
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise ValidationError(f"File exceeds {get_settings().max_upload_mb} MB limit.")
    return documents.upload(user, case_id, file.filename or "upload", data)


@router.get("/cases/{case_id}/documents")
def list_docs(case_id: int, user=Depends(current_user)):
    return documents.list_documents(user, case_id)


@router.get("/cases/{case_id}/search")
def search(case_id: int, q: str, user=Depends(current_user)):
    return documents.search(user, case_id, q)


@router.get("/documents/{doc_id}/text")
def doc_text(doc_id: int, user=Depends(current_user)):
    return documents.get_text(user, doc_id)


@router.get("/documents/{doc_id}/original")
def original(doc_id: int, user=Depends(current_user)):
    name, data = documents.get_original(user, doc_id)
    return Response(content=data, media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.put("/documents/{doc_id}/type")
def doc_type(doc_id: int, body: S.DocTypeIn, user=Depends(current_user)):
    return documents.set_type(user, doc_id, body.doc_type)


@router.put("/documents/{doc_id}/annexure")
def annexure(doc_id: int, body: S.AnnexureIn, user=Depends(current_user)):
    return documents.set_annexure(user, doc_id, body.is_annexure, body.label)


@router.get("/documents/{doc_id}/delete-impact")
def delete_impact(doc_id: int, user=Depends(current_user)):
    return documents.delete_impact(user, doc_id)


@router.delete("/documents/{doc_id}")
def delete_doc(doc_id: int, user=Depends(current_user)):
    return {"ok": True, "removed": documents.delete(user, doc_id)}


@router.get("/audit/verify")
def verify(user=Depends(current_user)):
    auth.require_role(user, "ADMIN", "CA")
    return audit_core.verify_chain()
