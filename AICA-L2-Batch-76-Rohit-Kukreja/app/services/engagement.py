"""Engagement workspace. Build Prompt v2 §5.3, §8.4, §8.6.

Responses are stored EAV, but *typed*: a date goes in `value_date`, an amount
in `value_num`. §19 — never store a formatted string.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import CarryForward, ClauseSet, RepeatingBlock
from app.core import arithmetic
from app.core.formatting import financial_year
from app.db import Base
from app.models.engagement import (
    BoardMeeting,
    DepositParticulars,
    EmployeeRemuneration,
    Engagement,
    EngagementResponse,
    FieldCatalog,
    FinancialSummary,
    ForexParticulars,
    IfcDeficiency,
    KeyAuditMatter,
    Litigation,
    Loan186,
    Mgt9BusinessActivity,
    Mgt9DirectorHolding,
    Mgt9Indebtedness,
    Mgt9PromoterHolding,
    Mgt9Shareholding,
    PoshComplaint,
    RelatedPartyContract,
    StatutoryDue,
    SubsidiaryChange,
    UncorrectedMisstatement,
)
from app.models.enums import EngagementStatus, GoingConcern, OpinionType, ResponseSource
from app.models.issuance import AuditLog
from app.models.masters import Client, Partner
from app.services.document import format_cell

# Child tables keyed by the `entity` named in a clause's repeating block.
CHILD_MODELS: dict[str, type[Any]] = {
    "litigation": Litigation,
    "statutory_due": StatutoryDue,
    "ifc_deficiency": IfcDeficiency,
    "board_meeting": BoardMeeting,
    # Added with the Phase 2 clause authoring. Every entity a clause declares
    # must appear here or the workspace raises on that document.
    "key_audit_matter": KeyAuditMatter,
    "uncorrected_misstatement": UncorrectedMisstatement,
    "financial_summary": FinancialSummary,
    "forex_particulars": ForexParticulars,
    "loan_186": Loan186,
    "related_party_contract": RelatedPartyContract,
    "subsidiary_change": SubsidiaryChange,
    "deposit_particulars": DepositParticulars,
    "employee_remuneration": EmployeeRemuneration,
    "posh_complaint": PoshComplaint,
    # MGT-9, attached on the firm's instruction of 20 Aug 2026. See the
    # annexure's clause files for the position taken on whether it is required.
    "mgt9_business_activity": Mgt9BusinessActivity,
    "mgt9_shareholding": Mgt9Shareholding,
    "mgt9_promoter_holding": Mgt9PromoterHolding,
    "mgt9_director_holding": Mgt9DirectorHolding,
    "mgt9_indebtedness": Mgt9Indebtedness,
}


class EngagementError(ValueError):
    """Message is safe to show a user."""


class LockedError(EngagementError):
    """A finalised engagement is read-only (§10, §18.7)."""


# --------------------------------------------------------------------------
# Typed coercion
# --------------------------------------------------------------------------

_NUMERIC = {"amount", "number"}
_TEXTUAL = {"select", "text", "longtext", "static", "computed"}

# Typed by an accountant, not a programmer. A loss is written in brackets and
# a rupee figure carries separators, so "(1,23,456)" has to mean -123456. The
# unicode minus arrives whenever a figure is pasted out of Word or a PDF.
_MINUSES = "−‒–—"  # noqa: RUF001 - these dashes are the point


def parse_amount(raw: str) -> Decimal:
    """A typed money figure as a Decimal, or `EngagementError` explaining why not.

    Every caller went through `Decimal(...)` directly before. `InvalidOperation`
    is an `ArithmeticError`, NOT a `ValueError`, so it passed straight through
    the routers' `except (CsrfError, EngagementError, ValueError)` and became an
    unhandled 500 -- which is what the firm's team saw as the tool closing on
    them. Bracketed negatives hit it on the first figure of any loss-making
    client.
    """
    text = raw.strip()
    for dash in _MINUSES:
        text = text.replace(dash, "-")
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative, text = True, text[1:-1].strip()
    if text.endswith("-"):  # trailing minus, as some ledgers print it
        negative, text = True, text[:-1].strip()
    text = text.replace(",", "").replace("₹", "").replace("Rs.", "").replace(" ", "")
    if text.startswith("-"):
        negative, text = True, text[1:]
    if not text:
        raise EngagementError(f"{raw!r} is not a valid amount")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise EngagementError(f"{raw!r} is not a valid amount") from exc
    if not value.is_finite():
        raise EngagementError(f"{raw!r} is not a valid amount")
    return -value if negative else value


def coerce(raw: str, datatype: str) -> tuple[str | None, Decimal | None, date | None]:
    """Split a submitted string into the one typed column that should hold it.

    Returns (value_text, value_num, value_date) with exactly one populated,
    or all three None for a cleared field.
    """
    value = raw.strip()
    if not value:
        return None, None, None

    if datatype in _NUMERIC:
        return None, parse_amount(value), None

    if datatype == "date":
        try:
            return None, None, date.fromisoformat(value)
        except ValueError as exc:
            raise EngagementError(f"{raw!r} is not a valid date (use YYYY-MM-DD)") from exc

    if datatype == "boolean":
        return ("true" if value.lower() in {"1", "true", "yes", "on"} else "false"), None, None

    if datatype in _TEXTUAL:
        return value, None, None

    raise EngagementError(f"unknown datatype {datatype!r}")


def response_value(row: EngagementResponse) -> Any:
    """The single populated column, whichever it is."""
    if row.value_num is not None:
        return row.value_num
    if row.value_date is not None:
        return row.value_date
    return row.value_text


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FieldState:
    """One field as the workspace needs to render it (§8.4)."""

    key: str
    label: str
    datatype: str
    clause_id: str
    clause_ref: str
    options: tuple[tuple[str, str], ...]
    mandatory: bool
    carry_forward: CarryForward
    value: Any
    reviewed: bool
    source: ResponseSource | None
    wp_reference: str
    prior_value: Any = None

    @property
    def raw(self) -> str:
        """The value as a form control should show it — never pre-formatted."""
        if self.value is None:
            return ""
        if isinstance(self.value, date):
            return self.value.isoformat()
        return str(self.value)

    @property
    def is_unconfirmed_carry_forward(self) -> bool:
        """Carried forward but not yet confirmed for this year (§6.2).

        The distinction between "same as last year" and "verified for the
        current year" is exactly this flag.
        """
        return self.source is ResponseSource.CARRIED_FORWARD and not self.reviewed

    @property
    def changed_from_prior(self) -> bool:
        return self.prior_value is not None and self.prior_value != self.value


def get_engagement(session: Session, engagement_id: int) -> Engagement:
    engagement = session.get(Engagement, engagement_id)
    if engagement is None:
        raise EngagementError(f"Engagement {engagement_id} not found")
    return engagement


def responses_for(session: Session, engagement_id: int) -> dict[str, EngagementResponse]:
    rows = session.scalars(
        select(EngagementResponse).where(EngagementResponse.engagement_id == engagement_id)
    ).all()
    return {row.field_key: row for row in rows}


def answer_map(session: Session, engagement_id: int) -> dict[str, Any]:
    """`{field_key: value}` — what the renderer consumes."""
    return {key: response_value(row) for key, row in responses_for(session, engagement_id).items()}


def prior_engagement(session: Session, engagement: Engagement) -> Engagement | None:
    """The immediately preceding year, for the inline prior-year column."""
    return session.scalar(
        select(Engagement)
        .where(
            Engagement.client_id == engagement.client_id,
            Engagement.fy_end < engagement.fy_end,
        )
        .order_by(Engagement.fy_end.desc())
        .limit(1)
    )


def field_states(
    session: Session,
    engagement: Engagement,
    clause_set: ClauseSet,
    document: str | None = None,
) -> list[FieldState]:
    """Every catalogued field in force for this year, with its answer."""
    catalog = session.scalars(
        select(FieldCatalog).order_by(FieldCatalog.document, FieldCatalog.sort_order)
    ).all()
    answers = responses_for(session, engagement.engagement_id)

    previous = prior_engagement(session, engagement)
    prior_answers = answer_map(session, previous.engagement_id) if previous is not None else {}

    # NOTE: a runtime filter here — skipping catalogue rows the repository no
    # longer backs — was tried and reverted on 17 Aug 2026. It dropped the
    # narrative fields with it and could not be diagnosed inside the session.
    # A stale row is instead cleared where it is created: `scripts/seed.py`
    # rebuilds the catalogue from the repository, and removing a question now
    # requires re-running it. If the filter is retried, note that a narrative
    # is catalogued as `<clause id>.narrative`, not under the input key.

    states: list[FieldState] = []
    for entry in catalog:
        if document is not None and entry.document != document:
            continue
        if entry.effective_from and engagement.fy_end < entry.effective_from:
            continue
        if entry.effective_to and engagement.fy_end > entry.effective_to:
            continue

        row = answers.get(entry.field_key)
        states.append(
            FieldState(
                key=entry.field_key,
                label=entry.label,
                datatype=entry.datatype,
                clause_id=entry.clause_id,
                clause_ref=entry.clause_ref,
                options=tuple(
                    (o["value"], o.get("label") or o["value"])
                    for o in json.loads(entry.options_json or "[]")
                ),
                mandatory=entry.is_mandatory,
                carry_forward=entry.carry_forward,
                value=response_value(row) if row else None,
                reviewed=row.reviewed if row else False,
                source=row.source if row else None,
                wp_reference=row.wp_reference if row else "",
                prior_value=prior_answers.get(entry.field_key),
            )
        )
    return states


def readiness(states: list[FieldState]) -> int:
    """Audit Readiness: confirmed mandatory fields over total (§8.4)."""
    mandatory = [s for s in states if s.mandatory]
    if not mandatory:
        return 100
    done = sum(1 for s in mandatory if s.value is not None and not s.is_unconfirmed_carry_forward)
    return round(done * 100 / len(mandatory))


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------


def _guard_unlocked(engagement: Engagement) -> None:
    if engagement.is_locked:
        raise LockedError(
            f"FY {engagement.fy_code} is {engagement.status.value} and cannot be edited. "
            "Use Create Revision instead."
        )


def set_response(
    session: Session,
    engagement_id: int,
    field_key: str,
    raw: str,
    *,
    updated_by: str,
    wp_reference: str | None = None,
) -> EngagementResponse:
    """Save one answer. Editing an answer confirms it for the current year."""
    engagement = get_engagement(session, engagement_id)
    _guard_unlocked(engagement)

    entry = session.get(FieldCatalog, field_key)
    if entry is None:
        raise EngagementError(f"{field_key!r} is not a catalogued field")

    if entry.datatype == "select" and raw.strip():
        allowed = {o["value"] for o in json.loads(entry.options_json or "[]")}
        if raw.strip() not in allowed:
            raise EngagementError(f"{raw!r} is not an option for this field")

    text, num, day = coerce(raw, entry.datatype)

    row = session.get(EngagementResponse, (engagement_id, field_key))
    before = response_value(row) if row else None

    if row is None:
        row = EngagementResponse(engagement_id=engagement_id, field_key=field_key)
        session.add(row)

    row.value_text, row.value_num, row.value_date = text, num, day
    row.source = ResponseSource.USER
    # A human touched it this year, so it is verified, not merely inherited.
    row.reviewed = True
    row.reviewed_by = updated_by
    row.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    row.updated_by = updated_by
    if wp_reference is not None:
        row.wp_reference = wp_reference

    session.add(
        AuditLog(
            entity="engagement_response",
            entity_id=f"{engagement_id}:{field_key}",
            action="update",
            field=field_key,
            before_json=json.dumps(str(before) if before is not None else None),
            after_json=json.dumps(raw or None),
            actor=updated_by,
        )
    )
    session.flush()
    return row


def confirm_carry_forward(
    session: Session, engagement_id: int, field_key: str, *, confirmed_by: str
) -> None:
    """Mark an inherited answer as verified for this year without editing it."""
    _guard_unlocked(get_engagement(session, engagement_id))
    row = session.get(EngagementResponse, (engagement_id, field_key))
    if row is None:
        raise EngagementError(f"{field_key!r} has no answer to confirm")
    row.reviewed = True
    row.reviewed_by = confirmed_by
    row.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    session.add(
        AuditLog(
            entity="engagement_response",
            entity_id=f"{engagement_id}:{field_key}",
            action="confirm",
            field=field_key,
            actor=confirmed_by,
        )
    )
    session.flush()


def accept_clean_defaults(
    session: Session,
    engagement_id: int,
    clause_set: ClauseSet,
    *,
    accepted_by: str,
    document: str | None = None,
) -> list[str]:
    """Store the clean answer for every select that has none. Returns the keys.

    **Why this exists.** Decision 24 preselects each dropdown's clean option,
    and decision 24 also holds that a default is not a stored answer — nothing
    is written until the field is saved. Those two are correct together and
    were unusable together: the workspace autosaves on `change`, an untouched
    dropdown never fires one, so 106 fields showed the right answer, stored
    nothing, and went on blocking export with no visible reason why.

    This is the deliberate act that closes the gap. It is a POST the auditor
    makes, not something that happens on page load — the answers are attributed
    to them, logged, and count towards readiness, because the auditor asserting
    a clean report is exactly what the stored answer means. A default that
    saved itself would let an engagement nobody opened export as clean.

    Only **unanswered selects** are touched. An existing answer is never
    overwritten, including one carried forward and not yet confirmed: changing
    an answer the auditor has not looked at is the opposite of what this is for.
    """
    engagement = get_engagement(session, engagement_id)
    _guard_unlocked(engagement)

    accepted: list[str] = []
    for state in field_states(session, engagement, clause_set, document):
        if state.datatype != "select" or not state.options or state.value is not None:
            continue
        set_response(
            session,
            engagement_id,
            state.key,
            state.options[0][0],
            updated_by=accepted_by,
        )
        accepted.append(state.key)
    return accepted


# --------------------------------------------------------------------------
# Child records
# --------------------------------------------------------------------------


def child_rows(session: Session, engagement_id: int, entity: str) -> list[Any]:
    model = CHILD_MODELS.get(entity)
    if model is None:
        raise EngagementError(f"unknown repeating entity {entity!r}")
    return list(
        session.scalars(
            select(model).where(model.engagement_id == engagement_id).order_by(model.row_index)
        ).all()
    )


@dataclass(frozen=True, slots=True)
class ChildRowView:
    """A child record ready to render: its primary key and display cells.

    The primary-key column is named differently on every child model, so the
    template must not have to guess it.
    """

    pk: int
    cells: tuple[str, ...]


def _primary_key(model: type[Any], row: Any) -> int:
    (pk_column,) = model.__mapper__.primary_key
    return int(getattr(row, pk_column.key))


def child_row_views(
    session: Session, engagement_id: int, entity: str, columns: tuple[Any, ...]
) -> list[ChildRowView]:
    if entity in COMPUTED_CHILD_ROWS:
        engagement = get_engagement(session, engagement_id)
        return [
            ChildRowView(
                pk=0,  # nothing to delete: the register is the source
                cells=tuple(
                    format_cell(row.get(column.key), column.datatype) for column in columns
                ),
            )
            for row in COMPUTED_CHILD_ROWS[entity](session, engagement)
        ]
    model = CHILD_MODELS.get(entity)
    if model is None:
        raise EngagementError(f"unknown repeating entity {entity!r}")
    views: list[ChildRowView] = []
    for row in child_rows(session, engagement_id, entity):
        cells: list[str] = []
        for column in columns:
            # Formatted the same way the document renderer formats the same
            # value (§12). This was `str(value)`, so the workspace showed a
            # litigation amount as "4260000.00" while the annexure printed
            # "42,60,000" — the same figure, two screens, two answers.
            cells.append(format_cell(getattr(row, column.key, None), column.datatype))
        views.append(ChildRowView(pk=_primary_key(model, row), cells=tuple(cells)))
    return views


def child_row_dicts(session: Session, engagement_id: int, entity: str) -> list[dict[str, Any]]:
    """Child rows as plain dicts, for the renderer."""
    if entity in COMPUTED_CHILD_ROWS:
        return COMPUTED_CHILD_ROWS[entity](session, get_engagement(session, engagement_id))
    model = CHILD_MODELS.get(entity)
    if model is None:
        raise EngagementError(
            f"unknown repeating entity {entity!r} — a clause declares it but no "
            "model backs it; see CHILD_MODELS"
        )
    columns = [c.key for c in model.__mapper__.column_attrs]
    return [
        {c: getattr(row, c) for c in columns} for row in child_rows(session, engagement_id, entity)
    ]


def add_child_row(
    session: Session, engagement_id: int, entity: str, values: dict[str, Any], *, added_by: str
) -> Any:
    engagement = get_engagement(session, engagement_id)
    _guard_unlocked(engagement)

    model = CHILD_MODELS.get(entity)
    if model is None:
        raise EngagementError(f"unknown repeating entity {entity!r}")

    columns = {c.key for c in model.__mapper__.column_attrs}
    unknown = set(values) - columns
    if unknown:
        raise EngagementError(f"unknown column(s) for {entity}: {', '.join(sorted(unknown))}")

    existing = child_rows(session, engagement_id, entity)
    row = model(
        engagement_id=engagement_id,
        row_index=len(existing),
        source=ResponseSource.USER,
        reviewed=True,
        **_coerce_child(model, values),
    )
    session.add(row)
    session.add(
        AuditLog(
            entity=entity,
            entity_id=str(engagement_id),
            action="insert",
            after_json=json.dumps({k: str(v) for k, v in values.items()}),
            actor=added_by,
        )
    )
    session.flush()
    return row


def _coerce_child(model: type[Any], values: dict[str, Any]) -> dict[str, Any]:
    """Amounts and dates become Decimal and date, never strings (§19)."""
    out: dict[str, Any] = {}
    for key, raw in values.items():
        column = model.__mapper__.columns[key]
        python_type = getattr(column.type, "python_type", str)
        text = str(raw).strip()
        if not text:
            continue
        if python_type is Decimal:
            out[key] = parse_amount(text)
        elif python_type is date:
            try:
                out[key] = date.fromisoformat(text)
            except ValueError as exc:
                raise EngagementError(f"{raw!r} is not a valid date (use YYYY-MM-DD)") from exc
        elif python_type is int:
            try:
                out[key] = int(text)
            except ValueError as exc:
                raise EngagementError(f"{raw!r} is not a whole number") from exc
        else:
            out[key] = text
    return out


def save_schedule(
    session: Session,
    engagement_id: int,
    entity: str,
    block: RepeatingBlock,
    typed: dict[tuple[str, str], str],
    *,
    saved_by: str,
) -> None:
    """Rewrite a FIXED schedule from the figures typed against it (decision 73).

    `typed` is keyed by (row key, column key). Rows the schedule computes are
    ignored if they arrive -- a sub-total is derived here, every time the
    schedule is saved, so it cannot be left disagreeing with the lines above
    it. The rows are replaced wholesale rather than patched, so the stored
    schedule always matches the declared one, including after the declaration
    changes.
    """
    engagement = get_engagement(session, engagement_id)
    _guard_unlocked(engagement)

    model = CHILD_MODELS.get(entity)
    if model is None:
        raise EngagementError(f"unknown repeating entity {entity!r}")
    if not block.is_schedule:
        raise EngagementError(f"{entity!r} is not a fixed schedule")

    columns = block.amount_columns

    # Column by column, top to bottom: a sub-total may only refer to rows above
    # it, which the loader has already enforced, so one pass is enough.
    figures: dict[str, dict[str, Decimal | None]] = {column: {} for column in columns}
    for row in block.fixed_rows:
        for column in columns:
            if row.is_computed:
                assert row.computed is not None
                figures[column][row.key] = arithmetic.evaluate(row.computed, figures[column])
                continue
            raw = typed.get((row.key, column), "").strip()
            figures[column][row.key] = parse_amount(raw) if raw else None

    for stale in child_rows(session, engagement_id, entity):
        session.delete(stale)
    session.flush()

    for index, row in enumerate(block.fixed_rows):
        session.add(
            model(
                engagement_id=engagement_id,
                row_index=index,
                source=ResponseSource.USER,
                reviewed=True,
                particulars=row.particulars,
                **{column: figures[column][row.key] for column in columns},
            )
        )

    session.add(
        AuditLog(
            entity=entity,
            entity_id=str(engagement_id),
            action="update",
            after_json=json.dumps(
                {
                    f"{key}.{column}": (None if value is None else str(value))
                    for column, values in figures.items()
                    for key, value in values.items()
                }
            ),
            actor=saved_by,
        )
    )
    session.flush()


def schedule_state(
    session: Session, engagement_id: int, entity: str, block: RepeatingBlock
) -> list[dict[str, Any]]:
    """The schedule as the workspace renders it: one entry per declared row.

    Built from the DECLARATION and filled in from storage, never the other way
    round, so a row added to the schedule appears immediately on every existing
    engagement instead of only on new ones.
    """
    stored = {row.particulars: row for row in child_rows(session, engagement_id, entity)}
    out: list[dict[str, Any]] = []
    for row in block.fixed_rows:
        saved = stored.get(row.particulars)
        out.append(
            {
                "key": row.key,
                "particulars": row.particulars,
                "computed": row.is_computed,
                "values": {
                    column: (getattr(saved, column, None) if saved is not None else None)
                    for column in block.amount_columns
                },
            }
        )
    return out


def delete_child_row(
    session: Session, engagement_id: int, entity: str, row_id: int, *, deleted_by: str
) -> None:
    _guard_unlocked(get_engagement(session, engagement_id))
    model = CHILD_MODELS[entity]
    row = session.get(model, row_id)
    if row is None or row.engagement_id != engagement_id:
        raise EngagementError("Row not found on this engagement")
    session.delete(row)
    session.add(
        AuditLog(
            entity=entity,
            entity_id=str(engagement_id),
            action="delete",
            before_json=json.dumps({"row_id": row_id}),
            actor=deleted_by,
        )
    )
    session.flush()
    # Keep row_index contiguous so the rendered table numbers correctly.
    for index, remaining in enumerate(child_rows(session, engagement_id, entity)):
        remaining.row_index = index
    session.flush()


# --------------------------------------------------------------------------
# Creation
# --------------------------------------------------------------------------


def create_engagement(
    session: Session,
    client_id: int,
    fy_start: date,
    fy_end: date,
    *,
    profile_id: int | None,
    created_by: str,
) -> Engagement:
    fy_code = financial_year(fy_end).removeprefix("FY ")
    existing = session.scalar(
        select(Engagement).where(Engagement.client_id == client_id, Engagement.fy_code == fy_code)
    )
    if existing is not None:
        raise EngagementError(f"FY {fy_code} already exists for this client")

    # The client's usual signing partner, copied in rather than looked up
    # later (decision 67). Copied, because the engagement's own partner is what
    # a signed report names: changing the client's default next year must not
    # move the name on a report already issued. Still overridable here.
    client = session.get(Client, client_id)
    default_partner = getattr(client, "default_partner_id", None) if client else None

    engagement = Engagement(
        client_id=client_id,
        fy_code=fy_code,
        fy_start=fy_start,
        fy_end=fy_end,
        profile_id=profile_id,
        partner_id=default_partner,
        status=EngagementStatus.DATA_COLLECTION,
    )
    session.add(engagement)
    session.flush()
    session.add(
        AuditLog(
            entity="engagement",
            entity_id=str(engagement.engagement_id),
            action="create",
            after_json=json.dumps({"fy_code": fy_code}),
            actor=created_by,
        )
    )
    session.flush()
    return engagement


# --------------------------------------------------------------------------
# Engagement-level fields
# --------------------------------------------------------------------------

# Columns on `engagement` itself rather than in the EAV catalogue. They are
# year-specific by definition and none of them carries forward (§6.1
# `never`): the opinion, the going-concern conclusion, the report date and
# the place of signature must all be reached afresh each year.
ENGAGEMENT_FIELDS: tuple[str, ...] = (
    "opinion_type",
    "going_concern",
    "report_date",
    "place",
    # Who signs this engagement. The column existed from the start and nothing
    # read or set it, so in a firm with two signatories every report was signed
    # by whichever partner sorted first (decision 50).
    "partner_id",
)

_ENGAGEMENT_ENUMS: dict[str, type[Any]] = {
    "opinion_type": OpinionType,
    "going_concern": GoingConcern,
}


def set_engagement_field(
    session: Session, engagement_id: int, field: str, raw: str, *, updated_by: str
) -> Engagement:
    """Set one engagement-level field, with the same lock and audit rules."""
    engagement = get_engagement(session, engagement_id)
    _guard_unlocked(engagement)

    if field not in ENGAGEMENT_FIELDS:
        raise EngagementError(f"{field!r} is not an editable engagement field")

    before = getattr(engagement, field)
    value = raw.strip()

    if field in _ENGAGEMENT_ENUMS:
        enum_cls = _ENGAGEMENT_ENUMS[field]
        if not value:
            parsed: Any = None
        else:
            try:
                parsed = enum_cls(value)
            except ValueError as exc:
                allowed = ", ".join(m.value for m in enum_cls)
                raise EngagementError(f"{raw!r} is not one of ({allowed})") from exc
    elif field == "partner_id":
        if not value:
            parsed = None
        else:
            try:
                parsed = int(value)
            except ValueError as exc:
                raise EngagementError(f"{raw!r} is not a partner") from exc
            partner = session.get(Partner, parsed)
            if partner is None:
                raise EngagementError("That partner no longer exists")
            # The partner must belong to the practice that holds this client.
            # Without this an engagement could name one firm's member over
            # another firm's letterhead, which is the sort of thing that is
            # only noticed after a report has gone out.
            client = session.get(Client, engagement.client_id)
            if client is None or partner.firm_id != client.firm_id:
                raise EngagementError("That partner belongs to a different firm")
            if not partner.active:
                raise EngagementError(f"{partner.partner_name} is no longer an active partner")
    elif field == "report_date":
        if not value:
            parsed = None
        else:
            try:
                parsed = date.fromisoformat(value)
            except ValueError as exc:
                raise EngagementError(f"{raw!r} is not a valid date") from exc
            if parsed < engagement.fy_end:
                raise EngagementError("The report date cannot precede the financial year end")
    else:
        parsed = value

    setattr(engagement, field, parsed)
    session.add(
        AuditLog(
            entity="engagement",
            entity_id=str(engagement_id),
            action="update",
            field=field,
            before_json=json.dumps(str(before) if before is not None else None),
            after_json=json.dumps(value or None),
            actor=updated_by,
        )
    )
    session.flush()
    return engagement


# --------------------------------------------------------------------------
# Computed child rows. §18.8 — directors are computed from the client's
# register, never typed into a document.
#
# `bdr.directors.kmp` first wrote to a typed table, which meant the Board's
# Report could name a director the register did not have, or miss one it did.
# These entities have no table: the rows are derived on every render, so the
# two cannot disagree.
# --------------------------------------------------------------------------


def _director_changes_in_year(session: Session, engagement: Engagement) -> list[dict[str, Any]]:
    """Directors appointed or ceased during the financial year.

    Column keys match `bdr.directors.kmp`'s declared block. A director who
    resigned in October appears even though they are gone by the year end,
    which is the whole point of the Rule 8(5)(iii) disclosure.
    """
    from app.services.client import directors_during_fy

    rows: list[dict[str, Any]] = []
    for director in directors_during_fy(
        session, engagement.client_id, engagement.fy_start, engagement.fy_end
    ):
        designation = director.designation.value.replace("_", " ")
        if engagement.fy_start <= director.appointment_date <= engagement.fy_end:
            rows.append(
                {
                    "name": director.name,
                    "din": director.din,
                    "designation": designation,
                    "change": "Appointed",
                    "change_date": director.appointment_date,
                }
            )
        if director.cessation_date and (
            engagement.fy_start <= director.cessation_date <= engagement.fy_end
        ):
            rows.append(
                {
                    "name": director.name,
                    "din": director.din,
                    "designation": designation,
                    "change": "Resigned",
                    "change_date": director.cessation_date,
                }
            )
    return sorted(rows, key=lambda r: (r["change_date"], r["name"]))


ComputedRows = Callable[[Session, Engagement], list[dict[str, Any]]]

COMPUTED_CHILD_ROWS: dict[str, ComputedRows] = {
    "director_changes_in_year": _director_changes_in_year,
}


def is_computed(entity: str) -> bool:
    """Computed entities are read-only: there is nothing for a user to add or
    delete, and the workspace must not offer to."""
    return entity in COMPUTED_CHILD_ROWS


def delete_engagement(session: Session, engagement_id: int, *, deleted_by: str) -> str:
    """Delete one financial year and everything recorded against it.

    Partner's request, 17 August 2026: a way to remove a client's data for a
    given year -- a file opened by mistake, a trial run, a duplicate.

    **A finalised or archived year cannot be deleted.** Documents have been
    issued from it and its snapshots are what make a reprint byte-identical;
    destroying that would leave a signed report with nothing behind it. Those
    are corrected through Create Revision, which is the whole reason §18.7
    exists. This is the one guard that must not be relaxed for convenience.

    Everything else goes: answers, child-table rows, generated documents,
    review comments and the workflow history. The CLIENT is untouched --- its
    profile versions, directors and other years all survive, because deleting a
    year is not deleting a client.

    Returns the FY code, so the caller can say what it removed rather than
    reporting a bare success.
    """
    engagement = get_engagement(session, engagement_id)
    if engagement.status in (EngagementStatus.FINALISED, EngagementStatus.ARCHIVED):
        raise LockedError(
            f"FY {engagement.fy_code} is {engagement.status.value} and cannot be deleted. "
            "Documents have been issued from it. Use Create Revision instead."
        )

    fy_code = engagement.fy_code

    # Every table that points at an engagement, discovered rather than listed.
    # A hand-written list is how a new child table survives a delete and then
    # fails the foreign key months later -- ten of them were missing from
    # CHILD_MODELS as recently as this week.
    for table in reversed(Base.metadata.sorted_tables):
        if table.name != "engagement" and "engagement_id" in table.c:
            session.execute(
                table.delete().where(table.c.engagement_id == engagement_id)  # type: ignore[arg-type]
            )

    session.delete(engagement)
    session.add(
        AuditLog(
            entity="engagement",
            entity_id=str(engagement_id),
            action="delete",
            before_json=json.dumps({"fy_code": fy_code, "client_id": engagement.client_id}),
            actor=deleted_by,
        )
    )
    session.flush()
    return fy_code
