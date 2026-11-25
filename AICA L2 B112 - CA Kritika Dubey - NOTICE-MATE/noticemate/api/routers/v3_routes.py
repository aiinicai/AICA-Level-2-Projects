"""V3 endpoints: system checks, legal authorities, reasoning trace, notice-first intake."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from ...core.config import get_settings
from ...core.errors import ValidationError
from ...services import extraction, intake
from ..deps import current_user

router = APIRouter()


# ---- system ----
@router.get("/system/ocr-health")
def ocr_health(user=Depends(current_user)):
    return extraction.ocr_health()


# ---- legal sources ----
from ...services import authorities as A  # noqa: E402
from .. import schemas as S  # noqa: E402


@router.get("/legal-sources")
def list_sources(source_class: str | None = None, status: str | None = None, q: str | None = None, user=Depends(current_user)):
    return A.list_sources(source_class=source_class, status=status, q=q)


@router.get("/legal-sources/portals")
def portals(user=Depends(current_user)):
    return {"portals": A.OFFICIAL_PORTALS, "disclaimer": A.UNVERIFIED_LAW_NOTICE}


@router.post("/legal-sources")
def add_source(body: S.SourceIn, user=Depends(current_user)):
    return A.add_source(user, **body.model_dump())


@router.get("/legal-sources/{source_id}")
def get_source(source_id: int, user=Depends(current_user)):
    return A.get_source(source_id)


@router.put("/legal-sources/{source_id}")
def update_source(source_id: int, body: S.SourceUpdateIn, user=Depends(current_user)):
    return A.update_source(user, source_id, body.updates)


@router.post("/legal-sources/{source_id}/decision")
def decide_source(source_id: int, body: S.SourceDecisionIn, user=Depends(current_user)):
    return A.decide_source(user, source_id, **body.model_dump())


# ---- propositions & trace ----
@router.post("/cases/{case_id}/propositions")
def add_prop(case_id: int, body: S.PropositionIn, user=Depends(current_user)):
    return A.add_proposition(user, case_id, body.text, issue_id=body.issue_id, kind=body.kind)


@router.get("/propositions/{prop_id}")
def get_prop(prop_id: int, user=Depends(current_user)):
    return A.proposition_view(user, prop_id)


@router.put("/propositions/{prop_id}")
def edit_prop(prop_id: int, body: S.PropositionEditIn, user=Depends(current_user)):
    return A.edit_proposition(user, prop_id, body.text)


@router.post("/propositions/{prop_id}/sources")
def link(prop_id: int, body: S.LinkSourceIn, user=Depends(current_user)):
    return A.link_source(user, prop_id, body.source_id, stance=body.stance, relevance_note=body.relevance_note, pinpoint=body.pinpoint)


@router.delete("/propositions/{prop_id}/sources/{source_id}")
def unlink(prop_id: int, source_id: int, user=Depends(current_user)):
    return A.unlink_source(user, prop_id, source_id)


@router.post("/propositions/{prop_id}/facts")
def add_fact(prop_id: int, body: S.FactIn, user=Depends(current_user)):
    return A.add_fact(user, prop_id, **body.model_dump())


@router.delete("/proposition-facts/{fact_id}")
def remove_fact(fact_id: int, user=Depends(current_user)):
    return A.remove_fact(user, fact_id)


@router.post("/propositions/{prop_id}/decision")
def decide_prop(prop_id: int, body: S.PropDecisionIn, user=Depends(current_user)):
    return A.decide_proposition(user, prop_id, decision=body.decision, note=body.note)


@router.get("/issues/{issue_id}/trace")
def trace(issue_id: int, user=Depends(current_user)):
    return A.issue_trace(user, issue_id)


@router.post("/issues/{issue_id}/seed-propositions")
def seed(issue_id: int, user=Depends(current_user)):
    return A.seed_issue_propositions(user, issue_id)


# ---- notice-first intake & guided workflow ----
@router.post("/intake/notice")
async def intake_notice(file: UploadFile = File(...), user=Depends(current_user)):
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise ValidationError(f"File exceeds {get_settings().max_upload_mb} MB limit.")
    return intake.start_from_notice(user, file.filename or "notice", data)


@router.post("/intake/documents/{doc_id}/acknowledge-partial")
def intake_ack(doc_id: int, user=Depends(current_user)):
    return intake.acknowledge_and_parse(user, doc_id)


@router.put("/cases/{case_id}/confirm-details")
def confirm(case_id: int, body: S.ConfirmCaseIn, user=Depends(current_user)):
    return intake.confirm_case(user, case_id, **body.model_dump())


@router.get("/cases/{case_id}/workflow")
def workflow(case_id: int, user=Depends(current_user)):
    return intake.workflow_status(user, case_id)


# ---- document-to-issue mapping ----
from ...services import mapping as M  # noqa: E402


@router.post("/cases/{case_id}/map-documents")
def map_documents(case_id: int, user=Depends(current_user)):
    M.map_case(user, case_id)
    return M.summary(user, case_id)


@router.get("/cases/{case_id}/mapping-summary")
def mapping_summary(case_id: int, user=Depends(current_user)):
    return M.summary(user, case_id)


@router.get("/issues/{issue_id}/links")
def issue_links(issue_id: int, user=Depends(current_user)):
    return M.links_for_issue(user, issue_id)


@router.put("/doc-links/{link_id}")
def set_link(link_id: int, body: S.DocLinkStatusIn, user=Depends(current_user)):
    return M.set_link_status(user, link_id, body.status)


# ---- AI drafting (V3.2) ----
from ...services import ai_drafting as AD, appsettings as AS  # noqa: E402
from ...services.ai_providers import local_readiness  # noqa: E402


@router.get("/ai/drafting-status")
def drafting_status(user=Depends(current_user)):
    return AD.engine_status()


@router.get("/ai/local-check")
def local_check(url: str | None = None, model: str | None = None, user=Depends(current_user)):
    return local_readiness(url, model)


@router.post("/issues/{issue_id}/ai-draft")
def ai_draft_issue(issue_id: int, user=Depends(current_user)):
    return AD.draft_issue_local(user, issue_id)


@router.post("/cases/{case_id}/ai-draft/cloud")
def ai_draft_cloud(case_id: int, body: S.CloudDraftIn, user=Depends(current_user)):
    return AD.prepare_cloud(user, case_id, body.provider)


@router.get("/settings/app")
def get_app_settings(user=Depends(current_user)):
    return AS.all_settings()


@router.put("/settings/app")
def put_app_setting(body: S.AppSettingIn, user=Depends(current_user)):
    return AS.set_value(user, body.key, body.value)
