"""Dashboard, client register and the master-data editor. §8.2 and §8.3."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import LOCAL_ACTOR
from app.core.validators import ValidationError, validate_frn
from app.db import get_session
from app.models.enums import CompanyType, Designation, Framework, KmpRole
from app.models.issuance import AuditLog
from app.models.masters import Client, Firm, Partner
from app.services.auth import CsrfError, check_csrf
from app.services.client import (
    ACTIVE_FIRM_COOKIE,
    ChangeScope,
    ProfileError,
    active_firm,
    add_director,
    add_kmp,
    add_partner,
    all_firms,
    change_history,
    change_profile,
    create_client,
    create_firm,
    current_profile,
    delete_firm,
    delete_partner,
    directors_during_fy,
    directors_in_office,
    end_director,
    end_kmp,
    engagements_for,
    firm_blockers,
    kmp_in_office,
    partner_blockers,
    profile_versions,
    signing_partners,
    update_partner,
)
from app.services.defaults import (
    apply_defaults,
    default_map,
    selectable_fields,
    set_defaults,
    stale_defaults,
)
from app.services.engagement import (
    EngagementError,
    create_engagement,
    delete_engagement,
    get_engagement,
)
from app.services.register import (
    dashboard_tiles,
    recent_changes,
    recent_engagements,
    search_clients,
)
from app.templating import build_templates

router = APIRouter(tags=["clients"])
templates = build_templates()

#
# The columns remain on `client_profile`, holding whatever was entered before.
# Dropping them is a one-way loss of data the firm typed, so it waits on the
# partner rather than riding along with a behaviour change.
#
# The master-data form, as sections rather than a flat list (decision 62).
#
# Every field here is read by something: a document prints it, or an
# applicability flag turns on it. Fifteen that were read by nothing came out at
# the same review, and eight that ARE read had no capture point at all -- the
# group-structure flags, the consolidation exemption and the cost-records
# industry were settable on no screen, so they sat at their column defaults for
# the life of a client and quietly decided paragraphs.
#
# `kind` picks the control. `tristate` exists because those columns are
# `bool | None` and the third state is not decoration: the applicability engine
# says "not recorded" and means it, which is a different statement from "no".
PROFILE_SECTIONS: tuple[dict[str, Any], ...] = (
    {
        "title": "Company",
        "note": "Printed on the letterhead of every document the company issues.",
        "fields": (
            {"name": "company_name", "label": "Company name", "kind": "text"},
            {
                "name": "registered_addr",
                "label": "Registered office address",
                "kind": "textarea",
                "help": "Appears on the company's letterhead and in Form MGT-9.",
            },
            {"name": "company_type", "label": "Company class", "kind": "choice"},
            {"name": "framework", "label": "Reporting framework", "kind": "choice"},
            {
                "name": "website",
                "label": "Website",
                "kind": "text",
                "help": (
                    "Where the annual return is placed. Left blank, the Board's Report "
                    "states that the company has no website instead of giving a web address."
                ),
            },
        ),
    },
    {
        "title": "Group structure",
        "note": (
            "Decides the subsidiaries paragraph in the Board's Report and whether "
            "consolidated financial statements arise under section 129(3)."
        ),
        "fields": (
            {"name": "has_subsidiary", "label": "Has a subsidiary", "kind": "tristate"},
            {"name": "has_associate", "label": "Has an associate", "kind": "tristate"},
            {"name": "has_joint_venture", "label": "Has a joint venture", "kind": "tristate"},
        ),
    },
    {
        "title": "Exemption from consolidation",
        "note": (
            "Rule 6 of the Companies (Accounts) Rules, 2014. All three must hold for "
            "the exemption. Only relevant where the company has a group company above."
        ),
        "only_if_group": True,
        "fields": (
            {
                "name": "is_wholly_owned_or_unopposed_partially_owned",
                "label": "Wholly owned, or partially owned with no member objecting",
                "kind": "toggle",
            },
            {
                "name": "not_listed_or_in_process_of_listing",
                "label": "Not listed, and not in the process of listing",
                "kind": "toggle",
            },
            {
                "name": "parent_files_compliant_cfs",
                "label": "Parent files compliant consolidated statements",
                "kind": "toggle",
            },
        ),
    },
    {
        "title": "Cost records",
        "note": (
            "Whether the company operates in an industry for which the Central "
            "Government has specified cost records under section 148(1)."
        ),
        "fields": (
            {
                "name": "cost_records_industry",
                "label": "In a specified industry",
                "kind": "tristate",
            },
        ),
    },
)

# Flattened once, so the handler and the form cannot drift apart about what is
# editable.
EDITABLE_FIELDS: tuple[str, ...] = tuple(
    field["name"] for section in PROFILE_SECTIONS for field in section["fields"]
)

TRISTATE_FIELDS: frozenset[str] = frozenset(
    field["name"]
    for section in PROFILE_SECTIONS
    for field in section["fields"]
    if field["kind"] == "tristate"
)

TOGGLE_FIELDS: frozenset[str] = frozenset(
    field["name"]
    for section in PROFILE_SECTIONS
    for field in section["fields"]
    if field["kind"] == "toggle"
)

GROUP_FIELDS: tuple[str, ...] = ("has_subsidiary", "has_associate", "has_joint_venture")


# How each company class is named on screen. The enum values are database
# tokens -- a form offering "pvt" and "opc" asks the user to know the schema.
# The firm's team asked to classify a company as a Small Company, an OPC, or a
# private company other than a small one; those are the words used here.
COMPANY_TYPE_LABELS: dict[str, str] = {
    "small": "Small Company (s.2(85))",
    "opc": "One Person Company",
    "pvt": "Private Limited (other than a Small Company)",
    "pub_unlisted": "Public Limited (unlisted)",
    "pub_listed": "Public Limited (listed)",
    "sec8": "Section 8 Company",
    "nidhi": "Nidhi Company",
}

# The tool covers Indian GAAP only -- confirmed by the partner on 20 August
# 2026. Ind AS remains in the clause repository but is not offered, because a
# framework the tool does not support is a control that produces a wrong
# document: the team's own test client was set to Ind AS, and that is what
# produced two of their eleven observations.
FRAMEWORK_LABELS: dict[str, str] = {
    "igaap": "Indian GAAP (Accounting Standards, s.133)",
}

# Faces a signed document may be set in. Every one ships with Windows and with
# Word, so a document opened on a colleague's machine sets in the face it was
# written in -- a font the recipient lacks is silently substituted, and the page
# breaks of a signed report move with it.
#
# Serif faces only, and Times New Roman first: this is a statutory report, not a
# newsletter, and the firm's own precedents are set in Times.
# The ICAI Chartered Accountant logo, shipped with the application. The firm's
# team asked for it to be the mark used wherever a logo appears.
#
# It is offered as the DEFAULT, not fixed. Two reasons. Decision 20 makes the
# installation usable by any practice, and a firm with its own artwork must not
# be overruled by ours. And the mark is ICAI's, not this tool's: its use is
# governed by ICAI's guidelines for members, and whether it appears over a
# particular firm's name on a particular document is that firm's professional
# judgement to exercise, not a default this software should impose silently.
ICAI_CA_LOGO = "/static/Firm_logo.png"

DOCUMENT_FONTS: tuple[str, ...] = (
    "Times New Roman",
    "Cambria",
    "Garamond",
    "Georgia",
    "Book Antiqua",
    "Calibri",
    "Arial",
)


def _chrome(session: Session | None = None, firm: Firm | None = None) -> dict[str, object]:
    """Shared sidebar context.

    `firms` and `active_firm` drive the firm picker. Several firms may share an
    installation and there is no login, so the picker is a working filter and
    not access control — see docs/GATE_A_DECISIONS.md, decision 20.
    """
    return {
        "documents": {},
        "firms": all_firms(session) if session is not None else [],
        "active_firm": firm,
    }


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    auditcraft_firm: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    firm = active_firm(session, auditcraft_firm)
    firm_id = firm.firm_id if firm else None
    recent = recent_engagements(session, firm_id=firm_id)
    open_now = [(e, name) for e, name in recent if not e.is_locked]
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            **_chrome(session, firm),
            "tiles": dashboard_tiles(session, firm_id=firm_id),
            "recent": recent,
            # "Continue audit" needs somewhere to go. The most recently touched
            # engagement that is still open — a finalised one is not something
            # to continue, and offering it would be a dead action.
            "continue_target": open_now[0][0] if open_now else None,
            "continue_name": open_now[0][1] if open_now else "",
            "changes": recent_changes(session),
        },
    )


@router.get("/clients", response_class=HTMLResponse)
def client_register(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    q: str = "",
    type: str = "",
    page: int = 1,
    auditcraft_firm: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    company_type = None
    if type:
        try:
            company_type = CompanyType(type)
        except ValueError:
            company_type = None

    firm = active_firm(session, auditcraft_firm)
    return templates.TemplateResponse(
        request=request,
        name="clients.html",
        context={
            **_chrome(session, firm),
            "page": search_clients(
                session,
                query=q,
                company_type=company_type,
                page=page,
                firm_id=firm.firm_id if firm else None,
            ),
            "q": q,
            "selected_type": type,
            "company_types": list(CompanyType),
        },
    )


def _load_client(session: Session, client_id: int) -> Client:
    client = session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def _profile_sections(profile: Any) -> list[dict[str, Any]]:
    """The master-data form with every field's current value attached.

    The old form was a field picker: choose one field from a dropdown, type a
    value, submit, repeat. It showed no current values at all, so the only way
    to see what a profile held was to change something and look at the version
    history.
    """
    has_group = bool(profile and any(getattr(profile, name) for name in GROUP_FIELDS))

    out: list[dict[str, Any]] = []
    for section in PROFILE_SECTIONS:
        if section.get("only_if_group") and not has_group:
            continue
        fields = []
        for spec in section["fields"]:
            value = getattr(profile, spec["name"], None) if profile else None
            if spec["name"] in ("company_type", "framework") and value is not None:
                value = value.value
            options: list[tuple[str, str]] = []
            if spec["name"] == "company_type":
                options = list(COMPANY_TYPE_LABELS.items())
            elif spec["name"] == "framework":
                options = list(FRAMEWORK_LABELS.items())
            fields.append({**spec, "value": value, "options": options})
        out.append({**section, "fields": fields})
    return out


def _detail_context(
    session: Session,
    client_id: int,
    tab: str,
    as_on: str,
    error: str | None = None,
) -> dict[str, object]:
    client = _load_client(session, client_id)

    # Directors are always shown "as on" a date, never as a stored list —
    # the register plus a date is the single source of truth (§18.8).
    try:
        as_on_date = date.fromisoformat(as_on) if as_on else date.today()
    except ValueError:
        as_on_date = date.today()

    fy_start = (
        date(as_on_date.year - 1, 4, 1) if as_on_date.month <= 3 else date(as_on_date.year, 4, 1)
    )
    fy_end = date(fy_start.year + 1, 3, 31)

    return {
        **_chrome(session, active_firm(session)),
        "client": client,
        "profile": current_profile(session, client_id),
        "tab": tab,
        "as_on": as_on_date,
        "fy_start": fy_start,
        "fy_end": fy_end,
        "versions": profile_versions(session, client_id),
        "directors": directors_in_office(session, client_id, as_on_date),
        "directors_year": directors_during_fy(session, client_id, fy_start, fy_end),
        "kmps": kmp_in_office(session, client_id, as_on_date),
        "engagements": engagements_for(session, client_id),
        "history": change_history(session, client_id),
        # The form, section by section, each field carrying its current value
        # so the page shows what is stored rather than making the user guess.
        "profile_sections": _profile_sections(current_profile(session, client_id)),
        # Who usually signs for this client. Offered on the Financial Years tab,
        # because that is where a year is opened and the default is used.
        "signing_choices": (
            signing_partners(session, client.firm_id) if client is not None else []
        ),
        "company_types": list(CompanyType),
        "company_type_labels": COMPANY_TYPE_LABELS,
        # For the appointment forms on the Directors tab (decision 74).
        "designations": list(Designation),
        "kmp_roles": list(KmpRole),
        "scopes": list(ChangeScope),
        "error": error,
    }


# --------------------------------------------------------------------------
# New client. Added 17 August 2026 — there was no way to create one.
#
# One long form, on the partner's instruction: master data, financials,
# directors and KMP together. The obvious risk is that a validation failure
# throws away everything typed, so every handler below re-renders the form
# with `submitted` and the template puts the values back.
# --------------------------------------------------------------------------

# (form field, profile column). Amounts are coerced; blanks stay NULL so the
# applicability engine can tell "not entered" from "nil".
# Text fields the client profile actually needs (decision 35).
#
# **Six were removed on 17 August 2026 because nothing consumed them**:
# corporate address, phone, email, industry, nature of business and
# "amounts in". No clause interpolated them, the applicability engine did not
# read them, and no document printed them -- they were asked on the new-client
# form and never used again. The columns are left in place; only the questions
# are gone, so a firm that filled them in has not lost the data.
#
# `website` stays: the Board's Report cites the annual-return web address under
# s.134(3)(a), which is the paragraph that replaced Form MGT-9.
NEW_CLIENT_TEXT: tuple[tuple[str, str], ...] = (
    ("company_name", "Company name"),
    ("registered_addr", "Registered address"),
    ("website", "Website (annual return address, for the Board's Report)"),
)

# Facts the applicability engine reads that NOTHING could set (decision 35).
#
# They were captured here from that decision onward, and still could not be
# CORRECTED afterwards -- the master-data editor did not carry them, so a
# mis-ticked box at onboarding was permanent. Decision 62 put them on the
# master-data form as well, which is where a fact discovered mid-audit is
# actually entered.
#
# The two public-company relationship flags that used to sit here went with
# CARO's inference: nothing reads them now that the auditor states CARO.
# and what writes it.
NEW_CLIENT_FACTS: tuple[tuple[str, str, str], ...] = (
    (
        "has_subsidiary",
        "Has one or more subsidiaries",
        "Drives whether consolidated financial statements are required under s.129(3).",
    ),
    (
        "has_associate",
        "Has one or more associates",
        "Counted with subsidiaries and joint ventures for the consolidation requirement.",
    ),
    (
        "has_joint_venture",
        "Has one or more joint ventures",
        "Counted with subsidiaries and associates for the consolidation requirement.",
    ),
    (
        "is_wholly_owned_or_unopposed_partially_owned",
        "Wholly owned, or partially owned with no shareholder objecting",
        "First limb of the Rule 6 exemption from preparing consolidated financial statements.",
    ),
    (
        "not_listed_or_in_process_of_listing",
        "Not listed and not in the process of listing",
        "Second limb of the Rule 6 consolidation exemption.",
    ),
    (
        "parent_files_compliant_cfs",
        "Parent files compliant consolidated financial statements",
        "Third limb of the Rule 6 consolidation exemption.",
    ),
    (
        "cost_records_industry",
        "Operates in an industry prescribed for cost records",
        "Cost records under s.148(1) apply only to the industries listed in the Companies "
        "(Cost Records and Audit) Rules, 2014.",
    ),
)


DIRECTOR_ROW_FIELDS = ("name", "din", "designation", "appointment_date", "cessation_date")
KMP_ROW_FIELDS = ("name", "role", "appointment_date")


def _new_client_context(
    session: Session,
    submitted: dict[str, Any],
    error: str = "",
    rows: dict[str, list[dict[str, str]]] | None = None,
) -> dict:
    return {
        "director_rows": (rows or {}).get("director", []),
        "kmp_rows": (rows or {}).get("kmp", []),
        "nav": "clients",
        "firms": list(session.scalars(select(Firm).order_by(Firm.firm_name))),
        "text_fields": NEW_CLIENT_TEXT,
        "fact_fields": NEW_CLIENT_FACTS,
        "company_types": list(CompanyType),
        "company_type_labels": COMPANY_TYPE_LABELS,
        "framework_labels": FRAMEWORK_LABELS,
        "frameworks": list(Framework),
        "designations": list(Designation),
        "kmp_roles": list(KmpRole),
        "submitted": submitted,
        "error": error,
    }


@router.get("/clients/new", response_class=HTMLResponse)
def new_client_form(
    request: Request, session: Annotated[Session, Depends(get_session)]
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request, name="client_new.html", context=_new_client_context(session, {})
    )


def _optional_date(raw: str, label: str) -> date | None:
    text = raw.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ProfileError(f"{label} must be a date, not {raw!r}") from exc


def _required_date(raw: str, label: str) -> date:
    """As above, but the field is not allowed to be blank.

    An appointment or a cessation without its date is not a record of anything:
    the whole register is read "as on" a date, and a row with no date would
    never appear in office and never appear to have left.
    """
    value = _optional_date(raw, label)
    if value is None:
        raise ProfileError(f"{label} is required")
    return value


def _officer_rows(form: Any, prefix: str, fields: tuple[str, ...]) -> list[dict[str, Any]]:
    """Rows from a repeated-name form, skipping the spare blank ones.

    Presence is decided by `fields[0]` — the name — and nothing else. Testing
    whether *any* field is filled does not work: every row carries a
    `<select>` for designation or role, and a select always posts a value, so
    all four blank director rows counted as filled and the form refused itself
    with "Director row is missing name, din, appointment_date".
    """
    values = {field: form.getlist(f"{prefix}_{field}") for field in fields}
    count = max((len(v) for v in values.values()), default=0)
    key = fields[0]
    rows: list[dict[str, Any]] = []
    for index in range(count):
        row = {
            field: (values[field][index] if index < len(values[field]) else "") for field in fields
        }
        if str(row[key]).strip():
            rows.append(row)
    return rows


@router.post("/clients/new", response_model=None)
async def create_client_route(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    form = await request.form()
    submitted = {k: v for k, v in form.multi_items() if isinstance(v, str)}
    # `submitted` collapses repeated names to their last value, so the officer
    # tables need their rows kept separately or they come back blank on a
    # validation failure — which, in a form this long, is the whole cost of
    # having chosen one long form.
    entered_rows = {
        "director": _officer_rows(form, "director", DIRECTOR_ROW_FIELDS),
        "kmp": _officer_rows(form, "kmp", KMP_ROW_FIELDS),
    }
    try:
        check_csrf(auditcraft_csrf, str(form.get("csrf_token", "")))

        firm_id = int(str(form.get("firm_id") or 0))
        if not firm_id:
            raise ProfileError("Choose the firm this client belongs to")

        profile: dict[str, Any] = {
            column: str(form.get(column, "")).strip() for column, _ in NEW_CLIENT_TEXT
        }
        profile["company_type"] = CompanyType(str(form.get("company_type")))
        profile["framework"] = Framework(str(form.get("framework")))
        # The engine's own facts. A checkbox that is not ticked posts nothing,
        # so absence is False here -- which is the right reading for every one
        # of them ("has a subsidiary", "is listed"): unticked means no.
        for column, _label, _help in NEW_CLIENT_FACTS:
            profile[column] = form.get(column) is not None

        directors = [
            {
                "name": row["name"].strip(),
                "din": row["din"].strip(),
                "designation": Designation(row["designation"]),
                "appointment_date": _optional_date(row["appointment_date"], "Appointment date"),
                "cessation_date": _optional_date(row["cessation_date"], "Cessation date"),
                "is_active": not row["cessation_date"].strip(),
            }
            for row in entered_rows["director"]
        ]
        kmps = [
            {
                "name": row["name"].strip(),
                "role": KmpRole(row["role"]),
                "appointment_date": _optional_date(row["appointment_date"], "Appointment date"),
            }
            for row in entered_rows["kmp"]
        ]

        client = create_client(
            session,
            firm_id=firm_id,
            client_code=str(form.get("client_code", "")),
            cin=str(form.get("cin", "")),
            pan=str(form.get("pan", "")),
            date_of_incorp=_optional_date(
                str(form.get("date_of_incorp", "")), "Date of incorporation"
            ),
            profile=profile,
            directors=directors,
            kmps=kmps,
        )
        session.commit()
    except (CsrfError, ProfileError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="client_new.html",
            context=_new_client_context(session, submitted, str(exc), entered_rows),
            status_code=400,
        )

    return RedirectResponse(f"/clients/{client.client_id}", status_code=status.HTTP_303_SEE_OTHER)


# NOTE: every literal path under /clients must be declared above the
# `/clients/{client_id}` route below. FastAPI matches in declaration
# order, so a literal placed after it is never reached — `/clients/new`
# returned 422 trying to read "new" as an integer id.
@router.get("/clients/{client_id}", response_class=HTMLResponse)
def client_detail(
    request: Request,
    client_id: int,
    session: Annotated[Session, Depends(get_session)],
    tab: str = "overview",
    as_on: str = "",
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="client_detail.html",
        context=_detail_context(session, client_id, tab, as_on),
    )


def _submitted_changes(form: Mapping[str, Any], profile: Any) -> dict[str, Any]:
    """Read the whole form and return only what actually differs.

    Every field is posted on every save, so without this comparison a change
    reason of "corrected the address" would open a new profile version
    recording eleven fields as changed. `change_profile` returns the existing
    row unchanged when the result is empty, so a save that alters nothing is
    not an error -- it is a no-op, which is what the user meant by it.
    """
    changes: dict[str, Any] = {}
    for name in EDITABLE_FIELDS:
        raw = form.get(f"f_{name}")
        if not isinstance(raw, str):
            continue

        if name in TRISTATE_FIELDS:
            # "" is "not recorded", which is a real answer and not the same as
            # "no" -- the applicability engine reports it differently.
            new: Any = None if raw == "" else raw == "yes"
        elif name in TOGGLE_FIELDS:
            new = raw == "yes"
        else:
            new = raw.strip()

        current = getattr(profile, name, None)
        if current is not None and hasattr(current, "value"):
            current = current.value
        if new != current:
            changes[name] = new
    return changes


@router.post("/clients/{client_id}/master-data", response_model=None)
async def edit_master_data(
    request: Request,
    client_id: int,
    session: Annotated[Session, Depends(get_session)],
    effective_date: Annotated[str, Form()],
    scope: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()],
    # `reason` is accepted empty so that the domain layer produces a readable
    # message (§8.10) instead of FastAPI's 422 blob.
    reason: Annotated[str, Form()] = "",
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Version the profile. §8.3 — the only path that changes master data.

    The whole form is submitted at once (decision 62). It used to take one
    field per submit, chosen from a dropdown, which meant three round trips to
    correct three things and a change reason typed three times.
    """
    try:
        check_csrf(auditcraft_csrf, csrf_token)

        form = await request.form()
        changes = _submitted_changes(form, current_profile(session, client_id))

        change_profile(
            session,
            client_id,
            changes,
            change_date=date.fromisoformat(effective_date),
            changed_by=LOCAL_ACTOR,
            reason=reason,
            scope=ChangeScope(scope),
        )
        session.commit()
    except (CsrfError, ProfileError, ValueError, ArithmeticError) as exc:
        session.rollback()
        # §8.10 — a message the user can act on, never a stack trace.
        return templates.TemplateResponse(
            request=request,
            name="client_detail.html",
            context=_detail_context(session, client_id, "master-data", "", error=str(exc)),
            status_code=400,
        )

    return RedirectResponse(
        f"/clients/{client_id}?tab=master-data", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/clients/{client_id}/signing-partner", response_model=None)
async def set_default_signing_partner(
    request: Request,
    client_id: int,
    session: Annotated[Session, Depends(get_session)],
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Who usually signs for this client (decision 67).

    Changing it moves nothing that already exists. It is copied onto an
    engagement when the year is opened, and the engagement's own partner is
    what a report names — so a client reassigned this year leaves last year's
    signed report naming the partner who signed it.
    """
    form = await request.form()
    try:
        check_csrf(auditcraft_csrf, str(form.get("csrf_token", "")))
        client = session.get(Client, client_id)
        if client is None:
            raise ProfileError(f"No client with id {client_id}")

        raw = str(form.get("partner_id", "")).strip()
        chosen: int | None = int(raw) if raw else None
        if chosen is not None:
            allowed = {p.partner_id for p in signing_partners(session, client.firm_id)}
            if chosen not in allowed:
                raise ProfileError("That partner is not an active signatory of this client's firm")

        before = client.default_partner_id
        client.default_partner_id = chosen
        session.add(
            AuditLog(
                entity="client",
                entity_id=str(client_id),
                action="update",
                field="default_partner_id",
                before_json=json.dumps({"default_partner_id": before}),
                after_json=json.dumps({"default_partner_id": chosen}),
                reason="Default signing partner set",
                actor=LOCAL_ACTOR,
            )
        )
        session.commit()
    except (CsrfError, ProfileError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="client_detail.html",
            context=_detail_context(session, client_id, "financial-years", "", error=str(exc)),
            status_code=400,
        )
    return RedirectResponse(
        f"/clients/{client_id}?tab=financial-years", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/clients/{client_id}/directors", response_class=HTMLResponse)
def directors_as_on(
    request: Request,
    client_id: int,
    session: Annotated[Session, Depends(get_session)],
    as_on: str = "",
) -> HTMLResponse:
    """Directors in office on a date. Recomputed, never stored."""
    return client_detail(request, client_id, session, tab="directors", as_on=as_on)


# --------------------------------------------------------------------------
# Maintaining the registers. Decision 74.
#
# There was no route here at all: directors and KMP were written once by the
# new-client form and never touched again, so a resignation during the year
# could not be recorded. `bdr.directors.kmp` derives the Board's Report
# disclosure from this register, so the paragraph the directors sign could only
# say "no change" whatever had happened.
#
# Every handler re-renders the tab with the message rather than returning a
# bare 400, the same as every other form on this screen (§8.10).
# --------------------------------------------------------------------------


def _register_error(
    request: Request, session: Session, client_id: int, message: str
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="client_detail.html",
        context=_detail_context(session, client_id, "directors", "", error=message),
        status_code=400,
    )


@router.post("/clients/{client_id}/directors", response_model=None)
def appoint_director(
    request: Request,
    client_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
    name: Annotated[str, Form()] = "",
    din: Annotated[str, Form()] = "",
    designation: Annotated[str, Form()] = "",
    appointment_date: Annotated[str, Form()] = "",
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Record an appointment."""
    try:
        check_csrf(auditcraft_csrf, csrf_token)
        add_director(
            session,
            client_id,
            name=name,
            din=din,
            designation=Designation(designation),
            appointment_date=_required_date(appointment_date, "Appointment date"),
        )
        session.commit()
    except (CsrfError, ProfileError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return _register_error(request, session, client_id, str(exc))
    return RedirectResponse(
        f"/clients/{client_id}?tab=directors", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/clients/{client_id}/directors/{director_id}/cease", response_model=None)
def cease_director(
    request: Request,
    client_id: int,
    director_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
    cessation_date: Annotated[str, Form()] = "",
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Record a resignation or other cessation.

    The row is kept and dated, never deleted: last year's signed report names
    the people who held office then, and it has to go on naming them.
    """
    try:
        check_csrf(auditcraft_csrf, csrf_token)
        end_director(
            session,
            client_id,
            director_id,
            cessation_date=_required_date(cessation_date, "Cessation date"),
        )
        session.commit()
    except (CsrfError, ProfileError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return _register_error(request, session, client_id, str(exc))
    return RedirectResponse(
        f"/clients/{client_id}?tab=directors", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/clients/{client_id}/kmp", response_model=None)
def appoint_kmp(
    request: Request,
    client_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
    name: Annotated[str, Form()] = "",
    role: Annotated[str, Form()] = "",
    pan: Annotated[str, Form()] = "",
    appointment_date: Annotated[str, Form()] = "",
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    try:
        check_csrf(auditcraft_csrf, csrf_token)
        add_kmp(
            session,
            client_id,
            name=name,
            role=KmpRole(role),
            pan=pan,
            appointment_date=_required_date(appointment_date, "Appointment date"),
        )
        session.commit()
    except (CsrfError, ProfileError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return _register_error(request, session, client_id, str(exc))
    return RedirectResponse(
        f"/clients/{client_id}?tab=directors", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/clients/{client_id}/kmp/{kmp_id}/cease", response_model=None)
def cease_kmp(
    request: Request,
    client_id: int,
    kmp_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
    cessation_date: Annotated[str, Form()] = "",
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    try:
        check_csrf(auditcraft_csrf, csrf_token)
        end_kmp(
            session,
            client_id,
            kmp_id,
            cessation_date=_required_date(cessation_date, "Cessation date"),
        )
        session.commit()
    except (CsrfError, ProfileError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return _register_error(request, session, client_id, str(exc))
    return RedirectResponse(
        f"/clients/{client_id}?tab=directors", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/admin/needs-review", response_class=HTMLResponse)
def needs_review(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> HTMLResponse:
    """The needs-review clause list is a deliverable (§20), not a log line."""
    from app.main import get_clause_set

    return templates.TemplateResponse(
        request=request,
        name="needs_review.html",
        context={
            **_chrome(session, active_firm(session)),
            "clauses": get_clause_set().needs_review,
        },
    )


@router.get("/admin/audit-log", response_class=HTMLResponse)
def audit_log(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="audit_log.html",
        context={
            **_chrome(session, active_firm(session)),
            "entries": recent_changes(session, limit=200),
        },
    )


@router.get("/clients/lookup/{client_code}", response_model=None)
def lookup(
    client_code: str,
    session: Annotated[Session, Depends(get_session)],
) -> RedirectResponse:
    client = session.scalar(select(Client).where(Client.client_code == client_code))
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return RedirectResponse(f"/clients/{client.client_id}", status_code=303)


# --------------------------------------------------------------------------
# Admin — firm and partners
# --------------------------------------------------------------------------

FIRM_FIELDS: tuple[tuple[str, str], ...] = (
    ("firm_name", "Firm name"),
    ("frn", "Firm Registration Number"),
    ("address", "Firm address"),
    ("default_place", "Default place of signature"),
    ("logo_path", "Letterhead logo"),
    ("doc_font", "Document font"),
    ("doc_header", "Document header"),
    ("doc_footer", "Document footer"),
)


def _firm_page(
    request: Request,
    session: Session,
    *,
    error: str | None = None,
    saved: bool = False,
    status_code: int = 200,
) -> HTMLResponse:
    # The ACTIVE firm, not the first one. With several firms sharing the
    # installation, `select(Firm)` would have this screen silently editing
    # somebody else's details and listing their partners.
    firm = active_firm(session, request.cookies.get(ACTIVE_FIRM_COOKIE))
    firms = all_firms(session)
    counts = dict(
        session.execute(select(Client.firm_id, func.count()).group_by(Client.firm_id)).all()
    )
    for row in firms:
        row.client_count = counts.get(row.firm_id, 0)  # type: ignore[attr-defined]
        # What holds this firm, so the page can say why rather than showing a
        # button that will only refuse.
        row.blockers = firm_blockers(session, row.firm_id)  # type: ignore[attr-defined]

    partners = (
        list(
            session.scalars(
                select(Partner).where(Partner.firm_id == firm.firm_id).order_by(Partner.partner_id)
            )
        )
        if firm
        else []
    )
    for person in partners:
        person.blockers = partner_blockers(session, person.partner_id)  # type: ignore[attr-defined]

    return templates.TemplateResponse(
        request=request,
        name="firm.html",
        context={
            **_chrome(session, firm),
            "firm": firm,
            "firms": firms,
            "partners": partners,
            "removed": request.query_params.get("removed", ""),
            "fields": FIRM_FIELDS,
            "document_fonts": DOCUMENT_FONTS,
            "icai_logo": ICAI_CA_LOGO,
            "saved": saved,
            "error": error,
        },
        status_code=status_code,
    )


@router.post("/clients/{client_id}/engagements", response_model=None)
def add_engagement(
    request: Request,
    client_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
    fy_start: Annotated[str, Form()],
    fy_end: Annotated[str, Form()],
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Open a financial year for a client that has none.

    **This was missing, and it made decision 28 unreachable for the case that
    matters most.** A client created at Clients -> New client had no engagement
    and no way to be given one: the only path to a new financial year was rolling
    an existing one forward, so a brand-new client was a dead end reading "No
    financial years yet". The firm's standing answers are applied here, which for
    a first year means the whole file arrives answered.
    """
    from app.main import get_clause_set

    try:
        check_csrf(auditcraft_csrf, csrf_token)
        profile = current_profile(session, client_id)
        engagement = create_engagement(
            session,
            client_id,
            date.fromisoformat(fy_start),
            date.fromisoformat(fy_end),
            profile_id=profile.profile_id if profile else None,
            created_by=LOCAL_ACTOR,
        )
        firm = active_firm(session, request.cookies.get(ACTIVE_FIRM_COOKIE))
        if firm is not None:
            apply_defaults(
                session, engagement, get_clause_set(), firm.firm_id, applied_by=LOCAL_ACTOR
            )
        session.commit()
    except (CsrfError, EngagementError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="client_detail.html",
            context=_detail_context(session, client_id, "financial-years", "", error=str(exc)),
            status_code=400,
        )
    return RedirectResponse(
        f"/engagements/{engagement.engagement_id}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/clients/{client_id}/engagements/{engagement_id}/delete", response_model=None)
def delete_financial_year(
    request: Request,
    client_id: int,
    engagement_id: int,
    session: Annotated[Session, Depends(get_session)],
    csrf_token: Annotated[str, Form()],
    confirm_fy: Annotated[str, Form()] = "",
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Delete one financial year and everything recorded against it.

    **Typing the FY code is required.** This destroys answers, tables, generated
    documents and history for that year and cannot be undone; a bare button next
    to a list of years is one misclick away from a year's work. The confirmation
    is the FY code itself rather than a yes/no, so the row being destroyed has to
    be read before it goes.
    """
    try:
        check_csrf(auditcraft_csrf, csrf_token)
        engagement = get_engagement(session, engagement_id)
        if engagement.client_id != client_id:
            raise EngagementError("That financial year belongs to a different client")
        if confirm_fy.strip() != engagement.fy_code:
            raise EngagementError(
                f"Type {engagement.fy_code} exactly to confirm deletion of that year"
            )
        delete_engagement(session, engagement_id, deleted_by=LOCAL_ACTOR)
        session.commit()
    except (CsrfError, EngagementError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="client_detail.html",
            context=_detail_context(session, client_id, "financial-years", "", error=str(exc)),
            status_code=400,
        )
    return RedirectResponse(
        f"/clients/{client_id}?tab=financial-years", status_code=status.HTTP_303_SEE_OTHER
    )


def _defaults_page(
    request: Request,
    session: Session,
    *,
    saved: str = "",
    error: str | None = None,
) -> HTMLResponse:
    firm = active_firm(session, request.cookies.get(ACTIVE_FIRM_COOKIE))
    if firm is None:
        raise HTTPException(status_code=404, detail="No firm is set up yet")

    # Deferred: `app.main` imports this router, so a module-level import here
    # would be circular.
    from app.main import get_clause_set

    clause_set = get_clause_set()
    current = default_map(session, firm.firm_id)
    stale = set(stale_defaults(session, firm.firm_id))

    # Grouped by document so the sheet reads in the order the documents do,
    # rather than as one list of 220 questions.
    groups: list[dict[str, Any]] = []
    for document_id, document in clause_set.documents.items():
        fields = [
            {
                "key": entry.field_key,
                "label": entry.label or entry.field_key,
                "clause_ref": entry.clause_ref,
                "options": json.loads(entry.options_json or "[]"),
                "value": current.get(entry.field_key, ""),
                "stale": entry.field_key in stale,
            }
            for entry in selectable_fields(session, clause_set)
            if entry.document == document_id
        ]
        if fields:
            groups.append(
                {
                    "id": document_id,
                    "title": document.title,
                    "fields": fields,
                    "set_count": sum(1 for f in fields if f["value"]),
                }
            )

    total = sum(len(group["fields"]) for group in groups)
    return templates.TemplateResponse(
        request=request,
        name="defaults.html",
        context={
            "firm": firm,
            "groups": groups,
            "total": total,
            "set_count": sum(group["set_count"] for group in groups),
            # Defaults whose question or option the repository dropped. Listed
            # rather than deleted: the firm answered deliberately and should be
            # told the question changed.
            "orphaned": sorted(stale - {f["key"] for g in groups for f in g["fields"]}),
            "saved": saved,
            "error": error,
        },
        status_code=400 if error else 200,
    )


@router.get("/admin/defaults", response_class=HTMLResponse)
def default_answers(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    saved: str = "",
) -> HTMLResponse:
    """The firm's master answer sheet (decision 28).

    Every dropdown in every document, answered once for the whole practice.
    New engagements start from these; any engagement can override any of them by
    changing the dropdown in its own workspace.
    """
    return _defaults_page(request, session, saved=saved)


@router.post("/admin/defaults", response_model=None)
async def save_default_answers(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    form = await request.form()
    firm = active_firm(session, request.cookies.get(ACTIVE_FIRM_COOKIE))
    if firm is None:
        raise HTTPException(status_code=404, detail="No firm is set up yet")
    try:
        check_csrf(auditcraft_csrf, str(form.get("csrf_token") or ""))
        # Every field on the sheet is posted, including the ones left blank, so
        # that clearing a default is possible. A field absent from the form is
        # therefore left alone rather than treated as cleared.
        values = {
            key.removeprefix("default:"): str(value)
            for key, value in form.multi_items()
            if key.startswith("default:")
        }
        saved, cleared = set_defaults(session, firm.firm_id, values, updated_by=LOCAL_ACTOR)
        session.commit()
    except (CsrfError, EngagementError) as exc:
        session.rollback()
        return _defaults_page(request, session, error=str(exc))
    return RedirectResponse(
        f"/admin/defaults?saved={saved}-{cleared}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/admin/firm", response_class=HTMLResponse)
def firm_settings(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    saved: str = "",
) -> HTMLResponse:
    """Firm details. Nothing about the firm is hard-coded anywhere else.

    Any CA firm can point this tool at its own name, FRN, address, signing
    partner and logo without touching code.
    """
    return _firm_page(request, session, saved=bool(saved))


@router.post("/admin/firm", response_model=None)
async def save_firm(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    form = await request.form()
    firm = active_firm(session, request.cookies.get(ACTIVE_FIRM_COOKIE))
    try:
        check_csrf(auditcraft_csrf, str(form.get("csrf_token", "")))
        if firm is None:
            raise ProfileError("No firm record exists — run scripts/seed.py first")

        before = {name: getattr(firm, name) for name, _ in FIRM_FIELDS}
        for name, _label in FIRM_FIELDS:
            if name in form:
                setattr(firm, name, str(form[name]).strip())

        if not firm.firm_name.strip():
            raise ProfileError("The firm name cannot be blank")
        if firm.frn.strip():
            firm.frn = validate_frn(firm.frn)

        changed = {
            name: (before[name], getattr(firm, name))
            for name, _ in FIRM_FIELDS
            if before[name] != getattr(firm, name)
        }
        if changed:
            session.add(
                AuditLog(
                    entity="firm",
                    entity_id=str(firm.firm_id),
                    action="update",
                    field=",".join(changed),
                    before_json=json.dumps({k: str(v[0]) for k, v in changed.items()}),
                    after_json=json.dumps({k: str(v[1]) for k, v in changed.items()}),
                    actor=LOCAL_ACTOR,
                )
            )
        session.commit()
    except (CsrfError, ProfileError, ValidationError) as exc:
        session.rollback()
        return templates.TemplateResponse(
            request=request,
            name="firm.html",
            context={
                **_chrome(session, active_firm(session)),
                "firm": firm,
                "partners": list(session.scalars(select(Partner))),
                "fields": FIRM_FIELDS,
                "saved": False,
                "error": str(exc),
            },
            status_code=400,
        )
    return RedirectResponse("/admin/firm?saved=1", status_code=status.HTTP_303_SEE_OTHER)


# --------------------------------------------------------------------------
# Partners. Added 17 August 2026 — the screen listed them and offered no way
# to record one.
# --------------------------------------------------------------------------


@router.post("/admin/partners", response_model=None)
async def add_partner_route(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    form = await request.form()
    try:
        check_csrf(auditcraft_csrf, str(form.get("csrf_token", "")))
        firm = active_firm(session, request.cookies.get(ACTIVE_FIRM_COOKIE))
        if firm is None:
            raise ProfileError("No firm record exists — run scripts/seed.py first")
        add_partner(
            session,
            firm_id=firm.firm_id,
            partner_name=str(form.get("partner_name", "")),
            membership_no=str(form.get("membership_no", "")),
            is_signing=str(form.get("is_signing", "")) == "on",
        )
        session.commit()
    except (CsrfError, ProfileError, ValidationError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return _firm_page(request, session, error=str(exc), status_code=400)
    return RedirectResponse("/admin/firm", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/partners/{partner_id}", response_model=None)
async def update_partner_route(
    request: Request,
    partner_id: int,
    session: Annotated[Session, Depends(get_session)],
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Edit one partner, or retire them.

    There is no delete. A partner named on a document already issued must
    remain findable, so leaving the firm sets `active = False`.
    """
    form = await request.form()
    try:
        check_csrf(auditcraft_csrf, str(form.get("csrf_token", "")))
        changes: dict[str, Any] = {
            "partner_name": str(form.get("partner_name", "")),
            "membership_no": str(form.get("membership_no", "")),
            "is_signing": str(form.get("is_signing", "")) == "on",
            "active": str(form.get("active", "")) == "on",
        }
        update_partner(session, partner_id, changes)
        session.commit()
    except (CsrfError, ProfileError, ValidationError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return _firm_page(request, session, error=str(exc), status_code=400)
    return RedirectResponse("/admin/firm", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/partners/{partner_id}/delete", response_model=None)
async def delete_partner_route(
    request: Request,
    partner_id: int,
    session: Annotated[Session, Depends(get_session)],
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Remove a partner nothing points at.

    Typed confirmation, not a modal: the name has to be entered to match. A
    partner is one row in a short list and the rows look alike, so an
    "are you sure?" on the wrong line is confirmed just as readily as on the
    right one.
    """
    form = await request.form()
    try:
        check_csrf(auditcraft_csrf, str(form.get("csrf_token", "")))
        partner = session.get(Partner, partner_id)
        if partner is None:
            raise ProfileError(f"No partner with id {partner_id}")

        typed = str(form.get("confirm_name", "")).strip()
        if typed.casefold() != partner.partner_name.strip().casefold():
            raise ProfileError(
                f"Type the partner's name exactly — {partner.partner_name!r} — to confirm."
            )

        removed = delete_partner(session, partner_id, deleted_by=LOCAL_ACTOR)
        session.commit()
    except (CsrfError, ProfileError, ValidationError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return _firm_page(request, session, error=str(exc), status_code=400)
    return RedirectResponse(
        f"/admin/firm?removed={quote(removed)}", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/admin/firms/{firm_id}/delete", response_model=None)
async def delete_firm_route(
    request: Request,
    firm_id: int,
    session: Annotated[Session, Depends(get_session)],
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Remove a firm that holds no clients, with its partners and defaults.

    The active-firm cookie is cleared on the way out. Left pointing at a row
    that no longer exists, every screen would fall back to "no firm" and read
    as though the installation had been wiped rather than one firm removed.
    """
    form = await request.form()
    try:
        check_csrf(auditcraft_csrf, str(form.get("csrf_token", "")))
        firm = session.get(Firm, firm_id)
        if firm is None:
            raise ProfileError(f"No firm with id {firm_id}")

        typed = str(form.get("confirm_name", "")).strip()
        if typed.casefold() != firm.firm_name.strip().casefold():
            raise ProfileError(f"Type the firm's name exactly — {firm.firm_name!r} — to confirm.")

        removed = delete_firm(session, firm_id, deleted_by=LOCAL_ACTOR)
        session.commit()
    except (CsrfError, ProfileError, ValidationError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return _firm_page(request, session, error=str(exc), status_code=400)

    response = RedirectResponse(
        f"/admin/firm?removed={quote(removed)}", status_code=status.HTTP_303_SEE_OTHER
    )
    response.delete_cookie(ACTIVE_FIRM_COOKIE)
    return response


# --------------------------------------------------------------------------
# Firms. Several may share one installation (decision 20, 17 Aug 2026).
# --------------------------------------------------------------------------


@router.post("/admin/firms", response_model=None)
async def add_firm_route(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    form = await request.form()
    try:
        check_csrf(auditcraft_csrf, str(form.get("csrf_token", "")))
        firm = create_firm(
            session,
            firm_name=str(form.get("firm_name", "")),
            frn=str(form.get("frn", "")),
            address=str(form.get("address", "")),
            default_place=str(form.get("default_place", "")),
        )
        session.commit()
    except (CsrfError, ProfileError, ValidationError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return _firm_page(request, session, error=str(exc), status_code=400)

    # Switch to the firm just created, which is almost always what was wanted.
    response = RedirectResponse("/admin/firm", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(ACTIVE_FIRM_COOKIE, str(firm.firm_id), httponly=True, samesite="strict")
    return response


@router.post("/admin/firms/switch", response_model=None)
async def switch_firm(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    auditcraft_csrf: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse | RedirectResponse:
    """Choose which firm to work as.

    A cookie, not a session: there is no login. This selects a working context
    and grants nothing — every firm remains visible to whoever opens the app.
    """
    form = await request.form()
    try:
        check_csrf(auditcraft_csrf, str(form.get("csrf_token", "")))
        chosen = active_firm(session, str(form.get("firm_id", "")))
        if chosen is None:
            raise ProfileError("No firm to switch to")
    except (CsrfError, ProfileError, ValueError, ArithmeticError) as exc:
        session.rollback()
        return _firm_page(request, session, error=str(exc), status_code=400)

    response = RedirectResponse(
        str(form.get("next") or "/clients"), status_code=status.HTTP_303_SEE_OTHER
    )
    response.set_cookie(ACTIVE_FIRM_COOKIE, str(chosen.firm_id), httponly=True, samesite="strict")
    return response
