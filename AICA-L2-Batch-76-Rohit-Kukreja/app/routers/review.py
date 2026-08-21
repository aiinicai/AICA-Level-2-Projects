"""Validation, review comments, workflow and export. §9, §10, §11."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import ClauseSet
from app.config import get_settings
from app.core.consistency import DocumentBlocks, blocking, check, summarise
from app.core.permissions import LOCAL_ACTOR
from app.db import get_session
from app.models.engagement import Engagement
from app.models.enums import EngagementStatus
from app.models.issuance import DocumentInstance
from app.models.masters import Client, ClientProfile
from app.services.applicability import applicable_flags
from app.services.applicability import resolve as resolve_applicability
from app.services.auth import CsrfError, check_csrf
from app.services.document import build_document
from app.services.engagement import answer_map, child_row_dicts, get_engagement
from app.services.excel import export_workbook
from app.services.export import ExportError, build_audit_pack, generate_document
from app.services.render_context import signing_context
from app.services.review import (
    ReviewError,
    advance,
    comment_thread,
    create_revision,
    finalise,
    raise_comment,
    resolve_comment,
    respond_to_comment,
)
from app.templating import build_templates

router = APIRouter(prefix="/engagements", tags=["review"])
templates = build_templates()


def _clause_set() -> ClauseSet:
    from app.main import get_clause_set

    return get_clause_set()


def _findings(session: Session, engagement: Engagement):
    clause_set = _clause_set()
    profile = session.get(ClientProfile, engagement.profile_id) if engagement.profile_id else None
    # `resolve`, not `compute`: compute returns the engine's raw reading and
    # ignores what the firm has stored against the profile, so every override
    # was invisible to the findings check. That was survivable while the engine
    # inferred CARO and IFC — its answer was usually the same one — and stopped
    # being survivable when they became declared, since the auditor's answer is
    # then the ONLY answer and the check could not see it.
    applicability = (
        resolve_applicability(
            profile,
            engagement.fy_end,
            get_settings().content_path / "applicability_rules.yaml",
        )[0]
        if profile
        else None
    )
    # Render every document once and ask what it could not resolve. The
    # catalogue cannot answer that -- see `_completeness_rules`.
    # Kept apart by kind, not merged. A table with no rows and a modified
    # opinion with no explanation are different problems and read differently
    # on the findings list (decision 76).
    unanswered: set[str] = set()
    missing_narratives: set[str] = set()
    missing_rows: set[str] = set()
    placeholders: dict[str, tuple[str, ...]] = {}
    client = session.get(Client, engagement.client_id)
    profile = session.get(ClientProfile, engagement.profile_id) if engagement.profile_id else None
    context = signing_context(session, engagement, client, profile)
    applicable = applicable_flags(session, engagement)
    responses = answer_map(session, engagement.engagement_id)

    for document_id in clause_set.documents:
        child_data = {
            clause.id: child_row_dicts(
                session, engagement.engagement_id, clause.repeating_block.entity
            )
            for clause in clause_set.for_document(document_id, engagement.fy_end)
            if clause.repeating_block is not None
        }
        built = build_document(
            clause_set,
            document_id,
            engagement.fy_end,
            responses=responses,
            child_rows=child_data,
            context=context,
            applicable=applicable,
        )
        unanswered.update(built.unanswered)
        missing_narratives.update(built.missing_narratives)
        missing_rows.update(built.missing_rows)
        if built.placeholders:
            placeholders[document_id] = built.placeholders

    return check(
        session,
        engagement,
        clause_set,
        applicability=applicability,
        rendered_placeholders=placeholders,
        blocks=DocumentBlocks(
            unanswered=frozenset(unanswered),
            missing_narratives=frozenset(missing_narratives),
            missing_rows=frozenset(missing_rows),
        ),
    )


def _validation_context(
    session: Session, engagement_id: int, error: str | None = None
) -> dict[str, object]:
    engagement = get_engagement(session, engagement_id)
    findings = _findings(session, engagement)
    return {
        "documents": {},
        "engagement": engagement,
        "client": session.get(Client, engagement.client_id),
        "findings": findings,
        "summary": summarise(findings),
        "blocking_count": len(blocking(findings)),
        "comments": comment_thread(session, engagement_id),
        "statuses": list(EngagementStatus),
        "instances": list(
            session.scalars(
                select(DocumentInstance)
                .where(DocumentInstance.engagement_id == engagement_id)
                .order_by(DocumentInstance.doc_id.desc())
            ).all()
        ),
        "error": error,
    }


@router.get("/{engagement_id}/validation", response_class=HTMLResponse)
def validation(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="validation.html",
        context=_validation_context(session, engagement_id),
    )


def _error(request: Request, session, engagement_id: int, message: str):
    session.rollback()
    return templates.TemplateResponse(
        request=request,
        name="validation.html",
        context=_validation_context(session, engagement_id, error=message),
        status_code=400,
    )


def _back(engagement_id: int) -> RedirectResponse:
    return RedirectResponse(
        f"/engagements/{engagement_id}/validation", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{engagement_id}/comments", response_model=None)
def add_comment(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
    body: Annotated[str, Form()] = "",
    field_key: Annotated[str, Form()] = "",
    parent_id: Annotated[int | None, Form()] = None,
) -> HTMLResponse | RedirectResponse:
    try:
        check_csrf(request.cookies.get("auditcraft_csrf"), csrf_token)
        if parent_id:
            respond_to_comment(session, parent_id, body, responder=LOCAL_ACTOR)
        else:
            raise_comment(
                session,
                engagement_id,
                body,
                raised_by=LOCAL_ACTOR,
                field_key=field_key or None,
            )
        session.commit()
    except (CsrfError, ReviewError) as exc:
        return _error(request, session, engagement_id, str(exc))
    return _back(engagement_id)


@router.post("/{engagement_id}/comments/{comment_id}/resolve", response_model=None)
def resolve(
    request: Request,
    engagement_id: int,
    comment_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
) -> HTMLResponse | RedirectResponse:
    try:
        check_csrf(request.cookies.get("auditcraft_csrf"), csrf_token)
        resolve_comment(session, comment_id, resolved_by=LOCAL_ACTOR)
        session.commit()
    except (CsrfError, ReviewError) as exc:
        return _error(request, session, engagement_id, str(exc))
    return _back(engagement_id)


@router.post("/{engagement_id}/status", response_model=None)
def change_status(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
    target: Annotated[str, Form()],
) -> HTMLResponse | RedirectResponse:
    try:
        check_csrf(request.cookies.get("auditcraft_csrf"), csrf_token)
        engagement = get_engagement(session, engagement_id)
        advance(
            session,
            engagement_id,
            EngagementStatus(target),
            actor=LOCAL_ACTOR,
            blocking_findings=len(blocking(_findings(session, engagement))),
        )
        session.commit()
    except (CsrfError, ReviewError, ValueError, ArithmeticError) as exc:
        return _error(request, session, engagement_id, str(exc))
    return _back(engagement_id)


@router.post("/{engagement_id}/finalise", response_model=None)
def do_finalise(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
    udin: Annotated[str, Form()] = "",
) -> HTMLResponse | RedirectResponse:
    try:
        check_csrf(request.cookies.get("auditcraft_csrf"), csrf_token)
        engagement = get_engagement(session, engagement_id)
        finalise(
            session,
            engagement_id,
            actor=LOCAL_ACTOR,
            udin=udin,
            blocking_findings=len(blocking(_findings(session, engagement))),
        )
        session.commit()
    except (CsrfError, ReviewError, ValueError, ArithmeticError) as exc:
        return _error(request, session, engagement_id, str(exc))
    return _back(engagement_id)


@router.post("/{engagement_id}/revision", response_model=None)
def do_revision(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
    reason: Annotated[str, Form()] = "",
) -> HTMLResponse | RedirectResponse:
    try:
        check_csrf(request.cookies.get("auditcraft_csrf"), csrf_token)
        create_revision(session, engagement_id, reason, actor=LOCAL_ACTOR)
        session.commit()
    except (CsrfError, ReviewError) as exc:
        return _error(request, session, engagement_id, str(exc))
    return _back(engagement_id)


@router.post("/{engagement_id}/generate/{document_id}", response_model=None)
def generate(
    request: Request,
    engagement_id: int,
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
) -> HTMLResponse | RedirectResponse:
    try:
        check_csrf(request.cookies.get("auditcraft_csrf"), csrf_token)
        engagement = get_engagement(session, engagement_id)
        generate_document(session, engagement, document_id, _clause_set(), generated_by=LOCAL_ACTOR)
        session.commit()
    except (CsrfError, ExportError, ValueError, ArithmeticError) as exc:
        return _error(request, session, engagement_id, str(exc))
    return _back(engagement_id)


@router.post("/{engagement_id}/audit-pack", response_model=None)
def audit_pack(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
) -> HTMLResponse | FileResponse:
    try:
        check_csrf(request.cookies.get("auditcraft_csrf"), csrf_token)
        engagement = get_engagement(session, engagement_id)
        path = build_audit_pack(session, engagement, _clause_set(), generated_by=LOCAL_ACTOR)
        session.commit()
    except (CsrfError, ExportError, ValueError, ArithmeticError) as exc:
        return _error(request, session, engagement_id, str(exc))
    # §13 — served through an authorised route, never a guessable path.
    return FileResponse(path, filename=path.name, media_type="application/zip")


@router.get("/{engagement_id}/documents/{doc_id}/download", response_model=None)
def download(
    engagement_id: int,
    doc_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> FileResponse:
    instance = session.get(DocumentInstance, doc_id)
    if instance is None or instance.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Document not found")
    from pathlib import Path

    path = Path(instance.docx_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="The generated file is missing")
    return FileResponse(path, filename=path.name)


@router.get("/export/workbook", response_model=None)
def workbook(
    session: Annotated[Session, Depends(get_session)],
) -> FileResponse:
    target = get_settings().data_path / "exports" / "auditcraft.xlsx"
    export_workbook(session, target)
    return FileResponse(target, filename="auditcraft.xlsx")
