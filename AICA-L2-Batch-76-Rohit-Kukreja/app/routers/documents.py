"""Document preview. Build Prompt v2 §8.8 — the printable surface."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.models.masters import Client, ClientProfile
from app.render.html import render
from app.services.applicability import applicable_flags, exclusion_reasons
from app.services.document import build_document
from app.services.engagement import (
    EngagementError,
    answer_map,
    child_row_dicts,
    get_engagement,
)
from app.services.export import ExportError, draft_document, issued_document, letterhead_for
from app.services.render_context import firm_for_client, signing_context
from app.templating import build_templates

router = APIRouter(prefix="/documents", tags=["documents"])

# autoescape is on by default in Jinja2Templates (§13).
templates = build_templates()


@router.get("/{engagement_id}/{document_id}/preview", response_class=HTMLResponse)
def preview(
    request: Request,
    engagement_id: int,
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> HTMLResponse:
    """A printable document rendered from this engagement's real answers.

    Phase 3 rendered a hard-coded fixture; that stand-in is gone. Everything
    here now comes from `engagement_response` and the child tables.
    """
    from app.main import get_clause_set  # late import: app wires state at startup

    clause_set = get_clause_set()
    if document_id not in clause_set.documents:
        # §8.10 / §19 — never a stack trace.
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        engagement = get_engagement(session, engagement_id)
    except EngagementError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    client = session.get(Client, engagement.client_id)
    profile = session.get(ClientProfile, engagement.profile_id) if engagement.profile_id else None

    child_data = {
        clause.id: child_row_dicts(session, engagement_id, clause.repeating_block.entity)
        for clause in clause_set.for_document(document_id, engagement.fy_end)
        if clause.repeating_block is not None
    }

    built = build_document(
        clause_set,
        document_id,
        engagement.fy_end,
        responses=answer_map(session, engagement_id),
        child_rows=child_data,
        context=signing_context(session, engagement, client, profile),
        applicable=applicable_flags(session, engagement),
    )

    return templates.TemplateResponse(
        request=request,
        name="preview.html",
        context={
            "built": built,
            "document_html": render(built.document),
            "documents": clause_set.documents,
            "current_document": document_id,
            "engagement": engagement,
            "financial_year": f"FY {engagement.fy_code}",
            # So the preview shows the letterhead the .docx will carry, rather
            # than bare body text that looks nothing like the issued document.
            # The same function the .docx uses, so the preview cannot show one
            # party's letterhead and the export another.
            "letterhead": letterhead_for(
                clause_set.documents[document_id],
                firm_for_client(session, client),
                client,
                profile,
            ),
            "client": client,
            "profile": profile,
            # Why a clause is absent. Without this a document whose every
            # clause was ruled out rendered as a bare title.
            "exclusions": exclusion_reasons(
                profile,
                engagement.fy_end,
                get_settings().content_path / "applicability_rules.yaml",
            ),
        },
    )


@router.get("/{engagement_id}/{document_id}/issued", response_model=None)
def issued_on_letterhead(
    engagement_id: int,
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> FileResponse:
    """Download the ISSUED document -- registered, hashed, and unstamped.

    Decision 77. Distinct from `/draft` on purpose: this one only ever serves a
    file that went through `generate_document`, so what a user downloads from a
    finished engagement is the thing that was actually issued.
    """
    from app.main import get_clause_set

    engagement = get_engagement(session, engagement_id)
    if document_id not in get_clause_set().documents:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        path, version_no = issued_document(session, engagement, document_id)
    except ExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    client = session.get(Client, engagement.client_id)
    stem = f"{client.client_code if client else engagement.client_id}_{document_id}"
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{stem}_FY{engagement.fy_code}_v{version_no}.docx",
    )


@router.get("/{engagement_id}/{document_id}/draft", response_model=None)
def draft_on_letterhead(
    request: Request,
    engagement_id: int,
    document_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> FileResponse | HTMLResponse:
    """Download the current preview as a .docx on the firm's letterhead.

    Available while the file is still in data collection, which is the whole
    request: the partner wanted to read the document on firm paper before every
    finding is cleared. Nothing is frozen, hashed or registered -- see
    `draft_document` -- and the file carries a DRAFT stamp.
    """
    from app.main import get_clause_set  # late import: app wires state at startup

    engagement = get_engagement(session, engagement_id)
    clause_set = get_clause_set()
    if document_id not in clause_set.documents:
        raise HTTPException(status_code=404, detail="Document not found")

    # Decision 77. A finalised year is frozen, so a draft of it can only be the
    # issued document with a DRAFT stamp added -- which is exactly what the
    # firm downloaded and reported.
    if engagement.is_locked:
        raise HTTPException(
            status_code=400,
            detail=(
                f"FY {engagement.fy_code} is finalised. Use the issued document — "
                "a draft of a finalised year would carry a DRAFT stamp it has outgrown."
            ),
        )

    client = session.get(Client, engagement.client_id)
    try:
        path = draft_document(
            session, engagement, document_id, clause_set, firm_for_client(session, client)
        )
    except ExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stem = f"{client.client_code if client else engagement.client_id}_{document_id}"
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"DRAFT_{stem}_FY{engagement.fy_code}.docx",
    )
