"""Engagement workspace. Build Prompt v2 §8.4.

Every control posts to a real endpoint and every endpoint re-reads from the
database, so a refresh loses nothing — that is Phase 6's exit test.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.clauses.model import Clause, ClauseSet
from app.config import get_settings
from app.core.permissions import LOCAL_ACTOR
from app.db import get_session
from app.models.enums import GoingConcern, OpinionType
from app.models.masters import Client, ClientProfile
from app.render.html import render
from app.services.applicability import (
    OverrideError,
    applicable_flags,
    exclusion_reasons,
    flag_question,
    flag_views,
    governing_flag,
    set_override,
)
from app.services.auth import CsrfError, check_csrf
from app.services.client import ACTIVE_FIRM_COOKIE, active_firm, signing_partners
from app.services.defaults import apply_defaults
from app.services.document import build_document
from app.services.engagement import (
    CHILD_MODELS,
    ENGAGEMENT_FIELDS,
    EngagementError,
    accept_clean_defaults,
    add_child_row,
    child_row_dicts,
    child_row_views,
    confirm_carry_forward,
    delete_child_row,
    field_states,
    get_engagement,
    is_computed,
    prior_engagement,
    readiness,
    save_schedule,
    schedule_state,
    set_engagement_field,
    set_response,
)
from app.services.engagement import answer_map as engagement_answers
from app.services.export import letterhead_for
from app.services.progress import page_index, sections, stages
from app.services.render_context import firm_for_client, signing_context
from app.templating import build_templates

router = APIRouter(prefix="/engagements", tags=["engagements"])
templates = build_templates()


def _clause_set() -> ClauseSet:
    from app.main import get_clause_set

    return get_clause_set()


def _rules_path() -> Path:
    return get_settings().content_path / "applicability_rules.yaml"


def _gated_keys(clause_set: ClauseSet, applicable: frozenset[str] | None) -> set[str]:
    """Input keys belonging to clauses an applicability flag rules out.

    A question the engagement can never print is a question nobody should be
    asked. Key Audit Matters was the case that surfaced it.
    """
    if applicable is None:
        return set()
    gated: set[str] = set()
    for clause in clause_set.clauses:
        if set(clause.requires) <= applicable:
            continue
        if clause.input is not None:
            gated.add(clause.input.key)
        # A narrative is catalogued as `<clause id>.narrative`, NOT under the
        # input key, so filtering on input keys alone left every explanation
        # box on screen for a document the engine had ruled out -- 47 of CARO's
        # 96 fields survived answering "CARO does not apply". Same trap the note
        # in `field_states` records from the other direction.
        gated.add(f"{clause.id}.narrative")
    return gated


def _workspace_context(
    session: Session,
    engagement_id: int,
    document: str,
    error: str | None = None,
    request_cookie: str | None = None,
) -> dict[str, object]:
    engagement = get_engagement(session, engagement_id)
    clause_set = _clause_set()

    if document not in clause_set.documents:
        document = next(iter(clause_set.documents))

    client = session.get(Client, engagement.client_id)
    profile = session.get(ClientProfile, engagement.profile_id) if engagement.profile_id else None

    # Applicability governs the workspace too, not just the export. Without
    # this the form asked for Key Audit Matters on an unlisted private company
    # and the preview printed the section — SA 701 does not apply to it.
    # An engagement with no pinned profile has UNKNOWN applicability, not
    # "nothing applies". Filtering on an empty flag set would hide every
    # gated clause and its fields — including the narrative a modified
    # opinion needs — and the user would see a workspace missing whole
    # documents with nothing saying why.
    applicable = applicable_flags(session, engagement) if engagement.profile_id else None

    def applies(clause: Clause) -> bool:
        return applicable is None or set(clause.requires) <= applicable

    gated = _gated_keys(clause_set, applicable)

    states = [
        state
        for state in field_states(session, engagement, clause_set, document=document)
        if state.key not in gated
    ]
    all_states = [
        state for state in field_states(session, engagement, clause_set) if state.key not in gated
    ]

    responses = engagement_answers(session, engagement.engagement_id)
    child_data = {
        clause.id: child_row_dicts(session, engagement.engagement_id, clause.repeating_block.entity)
        for clause in clause_set.for_document(document, engagement.fy_end)
        if clause.repeating_block is not None and applies(clause)
    }

    built = build_document(
        clause_set,
        document,
        engagement.fy_end,
        responses=responses,
        child_rows=child_data,
        context=signing_context(session, engagement, client, profile),
        applicable=applicable,
    )

    repeating = [
        (
            clause,
            clause.repeating_block,
            child_row_views(
                session,
                engagement.engagement_id,
                clause.repeating_block.entity,
                clause.repeating_block.columns,
            ),
        )
        for clause in clause_set.for_document(document, engagement.fy_end)
        if clause.repeating_block is not None
        and not clause.repeating_block.is_schedule
        and applies(clause)
    ]

    # A FIXED schedule is not a table you add rows to -- the rows are declared
    # and only the figures are typed -- so it is handed to the template
    # separately and rendered as one form (decision 73).
    schedules = [
        (
            clause,
            clause.repeating_block,
            schedule_state(
                session,
                engagement.engagement_id,
                clause.repeating_block.entity,
                clause.repeating_block,
            ),
        )
        for clause in clause_set.for_document(document, engagement.fy_end)
        if clause.repeating_block is not None
        and clause.repeating_block.is_schedule
        and applies(clause)
    ]

    index = page_index(states, clause_set)

    # Applicability the auditor has not stated yet (decision 75). CARO, IFC,
    # CSR, internal audit and secretarial audit are DECLARED -- the engine does
    # not infer them -- and until one is answered every clause that hangs off it
    # is silently absent from the document. The screen that answers them was
    # linked as "Applicability", which is not what someone hunting for "where do
    # I say CSR applies?" is reading for.
    awaiting: list[str] = []
    if profile is not None:
        awaiting = [
            view.label
            for view in flag_views(profile, engagement.fy_end, _rules_path())
            if view.is_declared and view.awaiting_answer
        ]

    firm = firm_for_client(session, client)
    governing = governing_flag(clause_set, document)
    # Derived from the file, never stored: a "this section is done" flag is a
    # second source of truth that drifts the moment an answer changes.
    section_list = sections(session, engagement, clause_set, applicable, gated)
    previous = prior_engagement(session, engagement)

    return {
        "documents": clause_set.documents,
        "current_document": document,
        "engagement": engagement,
        # The template must not offer to add or delete a computed block.
        "computed": is_computed,
        "client": client,
        "profile": profile,
        "states": states,
        "repeating": repeating,
        "schedules": schedules,
        "index": index,
        "awaiting_applicability": awaiting,
        "built": built,
        "document_html": render(built.document),
        "readiness": readiness(all_states),
        "letterhead": letterhead_for(clause_set.documents[document], firm, client, profile),
        # Only this client's firm's active signatories. Listing every partner
        # in the installation would offer one firm's member for another firm's
        # report (decision 50).
        "signing_partners": signing_partners(session, firm.firm_id) if firm else [],
        "stages": stages(engagement),
        "sections": section_list,
        "section_by_id": {section.id: section for section in section_list},
        # Why a clause is absent from the preview pane. Same reason as the
        # standalone preview: a document with every clause ruled out is a blank
        # page that looks broken.
        "exclusions": exclusion_reasons(
            profile,
            engagement.fy_end,
            get_settings().content_path / "applicability_rules.yaml",
        ),
        # The one question that decides whether this whole document exists
        # (decisions 30 and 34). Shown for CARO and Annexure B, because every
        # clause in each requires one flag. It writes the applicability
        # OVERRIDE, not a response row, so the document, the paragraph in the
        # auditor's report that refers to it and the engagement letter's scope
        # all move together and cannot disagree.
        "governing_flag": governing,
        "governing_question": flag_question(governing) if governing else "",
        "governing_state": (
            "computed"
            if governing is None or profile is None or not getattr(profile, f"{governing}_override")
            else ("applicable" if getattr(profile, governing) else "not_applicable")
        ),
        "governing_computed": bool(applicable is not None and governing in (applicable or ())),
        # Dropdowns on THIS document showing a clean default that was never
        # stored. Counted here rather than in the template so the offer to
        # accept them and the act of accepting them agree on what they cover.
        "unsaved_count": sum(
            1 for s in states if s.datatype == "select" and s.options and s.value is None
        ),
        "prior_fy": previous.fy_code if previous else None,
        "engagement_fields": ENGAGEMENT_FIELDS,
        "opinion_types": list(OpinionType),
        "going_concerns": list(GoingConcern),
        "error": error,
    }


@router.get("/{engagement_id}", response_class=HTMLResponse)
def workspace(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
    document: str = "auditors_report",
) -> HTMLResponse:
    try:
        context = _workspace_context(
            session, engagement_id, document, request_cookie=request.cookies.get(ACTIVE_FIRM_COOKIE)
        )
    except EngagementError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return templates.TemplateResponse(request=request, name="workspace.html", context=context)


def _redirect(engagement_id: int, document: str) -> RedirectResponse:
    return RedirectResponse(
        f"/engagements/{engagement_id}?document={document}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{engagement_id}/field", response_model=None)
def save_field(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
    field_key: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()],
    document: Annotated[str, Form()] = "auditors_report",
    value: Annotated[str, Form()] = "",
    wp_reference: Annotated[str, Form()] = "",
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    try:
        check_csrf(auditcraft_csrf, csrf_token)
        set_response(
            session,
            engagement_id,
            field_key,
            value,
            updated_by=LOCAL_ACTOR,
            wp_reference=wp_reference or None,
        )
        session.commit()
    except (CsrfError, EngagementError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="workspace.html",
            context=_workspace_context(
                session,
                engagement_id,
                document,
                error=str(exc),
                request_cookie=request.cookies.get(ACTIVE_FIRM_COOKIE),
            ),
            status_code=400,
        )
    return _redirect(engagement_id, document)


@router.post("/{engagement_id}/document-applicable", response_model=None)
def set_document_applicable(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
    document: Annotated[str, Form()],
    choice: Annotated[str, Form()] = "computed",
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """The single question that decides whether a whole document is prepared.

    Asked for CARO and for Annexure B (decisions 30 and 34), and for any
    document the repository later gates entirely behind one flag.

    Writes the applicability OVERRIDE, not an answer row. That is the point: the
    annexure, the paragraph in the auditor's report that refers to it and the
    engagement letter's scope all read the same flag, so answering the question
    here prepares the document and moves the rest with it. A separate response
    row would have let them disagree, which is the failure the applicability
    engine exists to prevent -- and which the partner met when the report said
    IFC applied and Annexure B came out empty.
    """
    try:
        check_csrf(auditcraft_csrf, csrf_token)
        engagement = get_engagement(session, engagement_id)
        flag = governing_flag(_clause_set(), document)
        if flag is None:
            raise EngagementError(f"{document!r} is not decided by a single applicability flag")
        profile = (
            session.get(ClientProfile, engagement.profile_id) if engagement.profile_id else None
        )
        if profile is None:
            raise EngagementError(
                "This engagement has no client profile, so applicability cannot be set"
            )
        set_override(
            session,
            profile,
            flag,
            choice,
            # A reason is required for anything but "computed", and rightly: the
            # log has to say why someone overruled the engine. Naming the
            # control lets a reviewer tell an answer given here from one argued
            # on the Applicability screen.
            reason=(
                ""
                if choice == "computed"
                else "Answered on the engagement workspace, in the document's own section"
            ),
        )
        session.commit()
    except (CsrfError, EngagementError, OverrideError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="workspace.html",
            context=_workspace_context(
                session,
                engagement_id,
                document,
                error=str(exc),
                request_cookie=request.cookies.get(ACTIVE_FIRM_COOKIE),
            ),
            status_code=400,
        )
    return _redirect(engagement_id, document)


@router.post("/{engagement_id}/accept-defaults", response_model=None)
def accept_defaults(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
    document: Annotated[str, Form()] = "auditors_report",
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Answer every unanswered dropdown in this document at its clean option.

    Scoped to the document on screen, not the whole engagement: a partner
    accepting the clean auditor's report has not thereby said anything about
    the Board's Report.
    """
    try:
        check_csrf(auditcraft_csrf, csrf_token)
        # The firm's master sheet first (decision 28), then the clean-first
        # option for anything it does not answer. In that order because a
        # standing answer the firm actually chose beats a convention about
        # option ordering.
        firm = active_firm(session, request.cookies.get(ACTIVE_FIRM_COOKIE))
        if firm is not None:
            apply_defaults(
                session,
                get_engagement(session, engagement_id),
                _clause_set(),
                firm.firm_id,
                applied_by=LOCAL_ACTOR,
            )
        accept_clean_defaults(
            session,
            engagement_id,
            _clause_set(),
            accepted_by=LOCAL_ACTOR,
            document=document,
        )
        session.commit()
    except (CsrfError, EngagementError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="workspace.html",
            context=_workspace_context(
                session,
                engagement_id,
                document,
                error=str(exc),
                request_cookie=request.cookies.get(ACTIVE_FIRM_COOKIE),
            ),
            status_code=400,
        )
    return _redirect(engagement_id, document)


@router.post("/{engagement_id}/confirm", response_model=None)
def confirm_field(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
    field_key: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()],
    document: Annotated[str, Form()] = "auditors_report",
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Confirm a carried-forward answer without changing it (§6.2)."""
    try:
        check_csrf(auditcraft_csrf, csrf_token)
        confirm_carry_forward(session, engagement_id, field_key, confirmed_by=LOCAL_ACTOR)
        session.commit()
    except (CsrfError, EngagementError) as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="workspace.html",
            context=_workspace_context(
                session,
                engagement_id,
                document,
                error=str(exc),
                request_cookie=request.cookies.get(ACTIVE_FIRM_COOKIE),
            ),
            status_code=400,
        )
    return _redirect(engagement_id, document)


@router.post("/{engagement_id}/rows/{entity}", response_model=None)
async def add_row(
    request: Request,
    engagement_id: int,
    entity: str,
    session: Annotated[Session, Depends(get_session)],
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Add a child record. Columns arrive as `col_<key>` form fields."""
    form = await request.form()
    document = str(form.get("document", "auditors_report"))
    try:
        check_csrf(auditcraft_csrf, str(form.get("csrf_token", "")))
        if entity not in CHILD_MODELS:
            raise EngagementError(f"unknown repeating entity {entity!r}")

        values = {
            key.removeprefix("col_"): str(value)
            for key, value in form.items()
            if key.startswith("col_") and str(value).strip()
        }
        if not values:
            raise EngagementError("Enter at least one value before adding a row")

        add_child_row(session, engagement_id, entity, values, added_by=LOCAL_ACTOR)
        session.commit()
    except (CsrfError, EngagementError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="workspace.html",
            context=_workspace_context(
                session,
                engagement_id,
                document,
                error=str(exc),
                request_cookie=request.cookies.get(ACTIVE_FIRM_COOKIE),
            ),
            status_code=400,
        )
    return _redirect(engagement_id, document)


@router.post("/{engagement_id}/schedule/{entity}", response_model=None)
async def save_fixed_schedule(
    request: Request,
    engagement_id: int,
    entity: str,
    session: Annotated[Session, Depends(get_session)],
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Save a whole fixed schedule at once. Figures arrive as `f_<row>_<column>`.

    One submit for the whole table, not one per row: the sub-totals are derived
    from every line, so saving a line at a time would leave the schedule
    briefly self-contradictory and give the auditor eight chances to stop
    half way.
    """
    form = await request.form()
    document = str(form.get("document", "directors_report"))
    try:
        check_csrf(auditcraft_csrf, str(form.get("csrf_token", "")))

        clause_set = _clause_set()
        block = next(
            (
                clause.repeating_block
                for clause in clause_set.clauses
                if clause.repeating_block is not None
                and clause.repeating_block.entity == entity
                and clause.repeating_block.is_schedule
            ),
            None,
        )
        if block is None:
            raise EngagementError(f"{entity!r} is not a fixed schedule")

        typed = {
            (row.key, column): str(form.get(f"f_{row.key}_{column}", ""))
            for row in block.fixed_rows
            for column in block.amount_columns
        }
        save_schedule(session, engagement_id, entity, block, typed, saved_by=LOCAL_ACTOR)
        session.commit()
    except (CsrfError, EngagementError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="workspace.html",
            context=_workspace_context(
                session,
                engagement_id,
                document,
                error=str(exc),
                request_cookie=request.cookies.get(ACTIVE_FIRM_COOKIE),
            ),
            status_code=400,
        )
    return _redirect(engagement_id, document)


@router.post("/{engagement_id}/rows/{entity}/{row_id}/delete", response_model=None)
def remove_row(
    request: Request,
    engagement_id: int,
    entity: str,
    row_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
    document: Annotated[str, Form()] = "auditors_report",
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    try:
        check_csrf(auditcraft_csrf, csrf_token)
        delete_child_row(session, engagement_id, entity, row_id, deleted_by=LOCAL_ACTOR)
        session.commit()
    except (CsrfError, EngagementError) as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="workspace.html",
            context=_workspace_context(
                session,
                engagement_id,
                document,
                error=str(exc),
                request_cookie=request.cookies.get(ACTIVE_FIRM_COOKIE),
            ),
            status_code=400,
        )
    return _redirect(engagement_id, document)


@router.post("/{engagement_id}/engagement-field", response_model=None)
def save_engagement_field(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
    field: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()],
    document: Annotated[str, Form()] = "auditors_report",
    value: Annotated[str, Form()] = "",
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Opinion, going concern, report date and place (§5.3)."""
    try:
        check_csrf(auditcraft_csrf, csrf_token)
        set_engagement_field(session, engagement_id, field, value, updated_by=LOCAL_ACTOR)
        session.commit()
    except (CsrfError, EngagementError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="workspace.html",
            context=_workspace_context(
                session,
                engagement_id,
                document,
                error=str(exc),
                request_cookie=request.cookies.get(ACTIVE_FIRM_COOKIE),
            ),
            status_code=400,
        )
    return _redirect(engagement_id, document)
