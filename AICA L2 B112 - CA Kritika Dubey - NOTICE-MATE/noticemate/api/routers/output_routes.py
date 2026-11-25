"""Drafts, CA review/approval/export, AI gateway."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, Response

from ...services import ai_gateway, drafting, review
from .. import schemas as S
from ..deps import current_user

router = APIRouter()


@router.post("/cases/{case_id}/drafts")
def build(case_id: int, body: S.DraftBuildIn, user=Depends(current_user)):
    from ...services import ai_drafting

    rows = ai_drafting.rows_for_build(user, case_id, body.ai_draft_ids)
    info = None
    if rows:
        models = sorted({r["model"] for r in rows.values()})
        info = {"mode": "AI_LOCAL", "provider": "local", "model": ", ".join(models),
                "label": f"Issue paragraphs written with the AI model on this computer ({', '.join(models)}) and checked against "
                         "your records"}
    return drafting.build(user, case_id, body.notice_id,
                          reflect_reconciliation=body.reflect_reconciliation,
                          reconciliation_run_ids=body.reconciliation_run_ids,
                          options={"include_record_references": body.include_record_references,
                                   "include_legal_suggestions": body.include_legal_suggestions},
                          ai_rows=rows, drafting_info=info)


@router.get("/cases/{case_id}/drafts")
def list_drafts(case_id: int, user=Depends(current_user)):
    return drafting.list_drafts(user, case_id)


@router.get("/drafts/{draft_id}")
def get_draft(draft_id: int, user=Depends(current_user)):
    return drafting.get_draft(user, draft_id)


@router.put("/drafts/{draft_id}")
def edit(draft_id: int, body: S.DraftEditIn, user=Depends(current_user)):
    return drafting.edit(user, draft_id, body.updates)


@router.get("/drafts/{draft_id}/preview", response_class=PlainTextResponse)
def preview(draft_id: int, user=Depends(current_user)):
    return review.preview(user, draft_id)


@router.get("/drafts/{draft_id}/working-docx")
def working_docx(draft_id: int, filename: str = "NOTICE-MATE-working-reply", user=Depends(current_user)):
    # This is an editable CA working copy, never the approved final export.
    safe_name = re.sub(r'[<>:"/\\|?*]', "_", filename).strip(" .")[:120]
    safe_name = safe_name or "NOTICE-MATE-working-reply"
    if not safe_name.lower().endswith(".docx"):
        safe_name += ".docx"
    data = review.working_docx(user, draft_id)
    return Response(content=data,
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{safe_name}"'})


@router.get("/drafts/{draft_id}/checklist")
def checklist(draft_id: int, user=Depends(current_user)):
    return review.checklist(user, draft_id)


@router.post("/drafts/{draft_id}/checklist")
def tick(draft_id: int, body: S.TickIn, user=Depends(current_user)):
    return review.tick(user, draft_id, body.item_key, body.checked, body.note)


@router.post("/drafts/{draft_id}/checklist/confirm-all")
def tick_all(draft_id: int, user=Depends(current_user)):
    return review.tick_all(user, draft_id)


@router.post("/drafts/{draft_id}/approve")
def approve(draft_id: int, body: S.ApproveIn, user=Depends(current_user)):
    return review.approve(user, draft_id, declaration_accepted=body.declaration_accepted)


@router.get("/meta/declaration")
def declaration():
    return {"declaration": review.DECLARATION}


@router.post("/cases/{case_id}/approval/revoke")
def revoke(case_id: int, body: S.RevokeIn, user=Depends(current_user)):
    return review.revoke(user, case_id, body.reason)


@router.get("/cases/{case_id}/approval")
def approval(case_id: int, user=Depends(current_user)):
    return review.approval_status(user, case_id)


@router.get("/cases/{case_id}/export")
def export(case_id: int, format: str = "docx", user=Depends(current_user)):
    name, data = review.export(user, case_id, format)
    mt = "application/pdf" if format == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return Response(content=data, media_type=mt, headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/cases/{case_id}/review-memo", response_class=PlainTextResponse)
def memo(case_id: int, user=Depends(current_user)):
    return review.review_memo(user, case_id)


# ---- AI gateway ----
@router.get("/ai/status")
def ai_status(user=Depends(current_user)):
    return ai_gateway.status()


@router.post("/cases/{case_id}/ai/prepare")
def ai_prepare(case_id: int, body: S.AIPrepareIn, user=Depends(current_user)):
    purpose = "DRAFT_REPLY" if body.task == "DRAFT_REPLY" else "GENERAL"
    if purpose == "DRAFT_REPLY":
        if not body.related_id:
            from ...core.errors import ValidationError
            raise ValidationError("A draft ID is required for an AI-assisted reply suggestion.")
        draft = drafting.get_draft(user, body.related_id)
        if draft["case_id"] != case_id:
            from ...core.errors import ValidationError
            raise ValidationError("Draft must belong to the same case.")
    return ai_gateway.prepare(user, case_id, body.task, body.content, body.extra_instructions,
                              provider=body.provider, purpose=purpose, related_id=body.related_id)


@router.get("/ai/submissions/{sid}")
def ai_get(sid: int, user=Depends(current_user)):
    return ai_gateway.get_submission(user, sid)


@router.post("/ai/submissions/{sid}/send")
def ai_send(sid: int, body: S.AISendIn, user=Depends(current_user)):
    return ai_gateway.approve_and_send(user, sid, body.payload_hash, body.confirm)


@router.post("/ai/submissions/{sid}/cancel")
def ai_cancel(sid: int, user=Depends(current_user)):
    return ai_gateway.cancel(user, sid)


@router.get("/cases/{case_id}/ai/submissions")
def ai_list(case_id: int, user=Depends(current_user)):
    return ai_gateway.list_submissions(user, case_id)
