"""Rollover and the What Changed screen. Build Prompt v2 §6.3 and §6.4."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.clauses.model import ClauseSet
from app.config import get_settings
from app.core.applicability import Applicability, compute, facts_from_profile
from app.core.carryforward import RolloverError, roll_forward, unreviewed_carry_forwards
from app.core.comparison import compare, summarise
from app.core.permissions import LOCAL_ACTOR
from app.db import get_session
from app.models.engagement import Engagement
from app.models.masters import ClientProfile
from app.services.applicability import (
    OverrideError,
    flag_views,
    overridable,
    set_override,
)
from app.services.auth import CsrfError, check_csrf
from app.services.client import ACTIVE_FIRM_COOKIE, active_firm, change_profile, current_profile
from app.services.defaults import apply_defaults
from app.services.engagement import get_engagement, prior_engagement
from app.templating import build_templates

router = APIRouter(prefix="/engagements", tags=["rollover"])
templates = build_templates()

# Documents whose answers are never carried forward, with the reason.
NEVER_CARRIED: dict[str, str] = {
    # Gate C decision 18: a fresh engagement letter is issued every year, so
    # last year's answers must not be offered for reuse.
    "engagement_letter": "a fresh letter is issued every year",
}


def _clause_set() -> ClauseSet:
    from app.main import get_clause_set

    return get_clause_set()


def document_categories(clause_set: ClauseSet) -> tuple[tuple[str, str], ...]:
    """The documents a roll-forward can copy answers from.

    Derived from the clause repository rather than hard-coded. It WAS
    hard-coded, to the auditor's report and the CARO annexure alone, which
    silently overrode the per-clause `carry_forward` policies the register
    approved for the other four documents — 46 clauses marked `prompt` that
    could never be carried at all. A 32-clause representation letter was being
    re-answered from scratch every year as a result.

    A document added to the manifest now appears here automatically.
    """
    return tuple(
        (document_id, template.title)
        for document_id, template in clause_set.documents.items()
        if document_id not in NEVER_CARRIED
    )


# Figures that describe the year just audited, not the year being opened.
# Applicability turns on every one of them, so carrying them into a new
# engagement means CARO, IFC, CSR, internal audit and secretarial audit are
# all decided on last year's numbers until somebody happens to edit them.
# Gate C decision 1 (17 Aug 2026): the new year starts with them blank.
STALE_ON_ROLL_FORWARD: tuple[str, ...] = ()


def _profile_for_new_year(session: Session, client_id: int, fy_start: date) -> ClientProfile:
    """A profile version for the year being opened, financials cleared.

    Company name, address, type and framework carry over — those describe the
    company and rarely move. The figures do not: they are last year's, and the
    applicability engine cannot tell the difference between "unchanged" and
    "never entered for this year".

    If they are already blank there is nothing to change and the existing
    version is reused, so rolling forward twice does not stack empty versions.
    """
    existing = current_profile(session, client_id)
    if all(getattr(existing, field, None) is None for field in STALE_ON_ROLL_FORWARD):
        return existing
    return change_profile(
        session,
        client_id,
        dict.fromkeys(STALE_ON_ROLL_FORWARD),
        change_date=fy_start,
        changed_by=LOCAL_ACTOR,
        reason=(
            "Roll forward: financial figures cleared so applicability is not "
            "computed from the prior year's numbers"
        ),
    )


def _rules_path():
    return get_settings().content_path / "applicability_rules.yaml"


def _applicability(session: Session, engagement: Engagement) -> Applicability | None:
    profile = session.get(ClientProfile, engagement.profile_id) if engagement.profile_id else None
    if profile is None:
        return None
    return compute(facts_from_profile(profile), engagement.fy_end, _rules_path())


@router.get("/{engagement_id}/roll-forward", response_class=HTMLResponse)
def roll_forward_form(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> HTMLResponse:
    """The configurable carry-forward screen (§6.3)."""
    engagement = get_engagement(session, engagement_id)
    next_start = date(engagement.fy_end.year, 4, 1)
    next_end = date(next_start.year + 1, 3, 31)

    return templates.TemplateResponse(
        request=request,
        name="roll_forward.html",
        context={
            "documents": {},
            "engagement": engagement,
            "categories": document_categories(_clause_set()),
            "next_start": next_start,
            "next_end": next_end,
            "error": None,
        },
    )


@router.post("/{engagement_id}/roll-forward", response_model=None)
def do_roll_forward(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
    fy_start: Annotated[str, Form()],
    fy_end: Annotated[str, Form()],
    category: Annotated[list[str] | None, Form()] = None,
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    engagement = get_engagement(session, engagement_id)
    try:
        check_csrf(auditcraft_csrf, csrf_token)

        # No boxes ticked means "everything", not "nothing" — the checkbox
        # defaults in the form are all on.
        categories = set(category) if category else None

        # A new profile version with the prior year's figures cleared, so
        # applicability cannot be decided on stale numbers. Gate C decision 1.
        profile = _profile_for_new_year(session, engagement.client_id, date.fromisoformat(fy_start))
        target, report = roll_forward(
            session,
            engagement_id,
            fy_start=date.fromisoformat(fy_start),
            fy_end=date.fromisoformat(fy_end),
            profile_id=profile.profile_id,
            rolled_by=LOCAL_ACTOR,
            categories=categories,
        )
        # The firm's standing answers fill what carry-forward did not (decision
        # 28). Applied after the roll, and only to fields still unanswered, so a
        # carried-forward answer always wins over the master sheet: last year's
        # answer for this client is better evidence than the firm's general
        # position, and it is the one the auditor is being asked to confirm.
        firm = active_firm(session, request.cookies.get(ACTIVE_FIRM_COOKIE))
        if firm is not None:
            apply_defaults(session, target, _clause_set(), firm.firm_id, applied_by=LOCAL_ACTOR)
        session.commit()
    except (CsrfError, RolloverError, ValueError, ArithmeticError) as exc:
        session.rollback()
        next_start = date(engagement.fy_end.year, 4, 1)
        return templates.TemplateResponse(
            request=request,
            name="roll_forward.html",
            context={
                "documents": {},
                "engagement": engagement,
                "categories": document_categories(_clause_set()),
                "next_start": next_start,
                "next_end": date(next_start.year + 1, 3, 31),
                "error": str(exc),
            },
            status_code=400,
        )

    # The rollover report is recomputed on the What Changed screen from the
    # data itself, so nothing needs carrying across the redirect.
    return RedirectResponse(
        f"/engagements/{target.engagement_id}/what-changed?rolled={report.review_count}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/{engagement_id}/what-changed", response_class=HTMLResponse)
def what_changed(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> HTMLResponse:
    """§6.4 — available after rollover and at any time thereafter."""
    current = get_engagement(session, engagement_id)
    previous = prior_engagement(session, current)
    if previous is None:
        raise HTTPException(status_code=404, detail="There is no earlier financial year to compare")

    rows = compare(
        session,
        previous,
        current,
        previous_applicability=_applicability(session, previous),
        current_applicability=_applicability(session, current),
    )

    return templates.TemplateResponse(
        request=request,
        name="what_changed.html",
        context={
            "documents": {},
            "previous": previous,
            "current": current,
            "rows": rows,
            "summary": summarise(rows),
            "unreviewed": unreviewed_carry_forwards(session, engagement_id),
        },
    )


def _applicability_context(
    session: Session, engagement_id: int, error: str | None = None, saved: bool = False
) -> dict[str, object]:
    engagement = get_engagement(session, engagement_id)
    profile = session.get(ClientProfile, engagement.profile_id) if engagement.profile_id else None
    views = flag_views(profile, engagement.fy_end, _rules_path()) if profile is not None else []
    return {
        "documents": {},
        "engagement": engagement,
        "profile": profile,
        "views": views,
        "overridable": set(overridable(profile)) if profile is not None else set(),
        "error": error,
        "saved": saved,
    }


@router.get("/{engagement_id}/applicability", response_class=HTMLResponse)
def applicability_page(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
    saved: str = "",
) -> HTMLResponse:
    """Every flag with the reasoning that produced it, and a control to
    overrule it (§7)."""
    return templates.TemplateResponse(
        request=request,
        name="applicability.html",
        context=_applicability_context(session, engagement_id, saved=bool(saved)),
    )


@router.post("/{engagement_id}/applicability", response_model=None)
def save_applicability(
    request: Request,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
    flag: Annotated[str, Form()],
    choice: Annotated[str, Form()],
    reason: Annotated[str, Form()] = "",
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    try:
        check_csrf(auditcraft_csrf, csrf_token)
        engagement = get_engagement(session, engagement_id)
        if engagement.is_locked:
            raise OverrideError(
                f"FY {engagement.fy_code} is finalised and cannot be changed. "
                "Use Create Revision instead."
            )
        profile = (
            session.get(ClientProfile, engagement.profile_id) if engagement.profile_id else None
        )
        if profile is None:
            raise OverrideError("This engagement has no client profile pinned")

        set_override(session, profile, flag, choice, reason=reason)
        session.commit()
    except (CsrfError, OverrideError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="applicability.html",
            context=_applicability_context(session, engagement_id, error=str(exc)),
            status_code=400,
        )
    return RedirectResponse(
        f"/engagements/{engagement_id}/applicability?saved=1",
        status_code=status.HTTP_303_SEE_OTHER,
    )
