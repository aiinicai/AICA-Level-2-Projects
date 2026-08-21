"""The firm's standing answers to clause questions (decision 28, 17 Aug 2026).

Set once at **Admin -> Default Answers**, applied to every engagement created
afterwards, and overridable on any individual engagement by changing the
dropdown as usual.

Three rules hold this together, and each of them is there because the obvious
alternative is worse:

1. **The default is copied onto the engagement, not read through it.** An
   engagement's answers are its own rows in `engagement_response`, written at
   creation and marked `ResponseSource.DEFAULT`. Editing the master sheet
   therefore cannot alter a file already in progress, and every answer that
   contributed to a signed report is recorded against that report rather than
   inferred from settings as they stand today.

2. **A copied default counts as answered** -- the partner's instruction of
   17 August 2026, so that a clean file can be finalised without repeating the
   same selections for every client. It is a real professional assertion, made
   once deliberately, not a machine guess. The consequence, accepted: an
   engagement nobody has opened reads 100% ready and will export on the
   strength of the standing answers alone. `source` stays `DEFAULT` so the
   audit trail can always separate "the firm's standing answer" from "someone
   looked at this client's file", which readiness alone can no longer show.

3. **Only questions the repository still asks can hold a default.** Values are
   validated against `field_catalog` on the way in, and a default whose option
   has since been withdrawn is reported rather than quietly kept -- eleven
   questions were removed from the auditor's report on 17 August 2026 alone.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import ClauseSet
from app.models.engagement import Engagement, FieldCatalog
from app.models.enums import ResponseSource
from app.models.issuance import AuditLog
from app.models.masters import FieldDefault
from app.services.engagement import EngagementError, field_states, set_response


def default_map(session: Session, firm_id: int) -> dict[str, str]:
    """Every standing answer this firm has set, keyed by field."""
    rows = session.scalars(select(FieldDefault).where(FieldDefault.firm_id == firm_id)).all()
    return {row.field_key: row.value for row in rows}


def selectable_fields(session: Session, clause_set: ClauseSet) -> list[FieldCatalog]:
    """The catalogue rows a default can be set on: dropdowns, in force, in a
    document the repository still builds.

    Effective dates are deliberately NOT filtered here. The master sheet is not
    tied to a financial year, so a question that only applies from FY 2023-24
    still needs an answer on it -- filtering by today's date would hide it and
    filtering by an engagement's date would make the sheet client-specific,
    which is the thing this screen exists to avoid.
    """
    rows = session.scalars(
        select(FieldCatalog).order_by(FieldCatalog.document, FieldCatalog.sort_order)
    ).all()
    return [
        row
        for row in rows
        if row.datatype == "select"
        and row.options_json
        and json.loads(row.options_json)
        and row.document in clause_set.documents
    ]


def set_defaults(
    session: Session,
    firm_id: int,
    values: dict[str, str],
    *,
    updated_by: str,
) -> tuple[int, int]:
    """Save the master sheet. Returns (saved, cleared).

    An empty value clears the default rather than storing a blank: "the firm
    has no standing answer to this" and "the firm's standing answer is the empty
    string" are different things, and only the first is meaningful.
    """
    saved = cleared = 0
    now = datetime.now(UTC).replace(tzinfo=None)

    for field_key, raw in values.items():
        entry = session.get(FieldCatalog, field_key)
        if entry is None:
            raise EngagementError(f"{field_key!r} is not a catalogued field")

        value = raw.strip()
        row = session.get(FieldDefault, (firm_id, field_key))

        if not value:
            if row is not None:
                session.delete(row)
                cleared += 1
            continue

        allowed = {option["value"] for option in json.loads(entry.options_json or "[]")}
        if value not in allowed:
            raise EngagementError(f"{value!r} is not an option for {entry.label or field_key!r}")

        if row is None:
            session.add(
                FieldDefault(
                    firm_id=firm_id,
                    field_key=field_key,
                    value=value,
                    updated_by=updated_by,
                    updated_at=now,
                )
            )
        else:
            row.value = value
            row.updated_by = updated_by
            row.updated_at = now
        saved += 1

    session.add(
        AuditLog(
            entity="field_default",
            entity_id=str(firm_id),
            action="update",
            after_json=json.dumps({"saved": saved, "cleared": cleared}),
            actor=updated_by,
        )
    )
    session.flush()
    return saved, cleared


def stale_defaults(session: Session, firm_id: int) -> list[str]:
    """Defaults the clause repository no longer accepts.

    Either the question is gone or the option was withdrawn. Reported on the
    screen rather than deleted: a firm that answered a question deliberately
    should be told the question has changed, not have the record removed for
    them. This is the counterpart of the eleven questions withdrawn from the
    auditor's report on 17 August 2026.
    """
    stale: list[str] = []
    for field_key, value in default_map(session, firm_id).items():
        entry = session.get(FieldCatalog, field_key)
        if entry is None:
            stale.append(field_key)
            continue
        allowed = {option["value"] for option in json.loads(entry.options_json or "[]")}
        if value not in allowed:
            stale.append(field_key)
    return stale


def apply_defaults(
    session: Session,
    engagement: Engagement,
    clause_set: ClauseSet,
    firm_id: int,
    *,
    applied_by: str,
) -> list[str]:
    """Write this firm's standing answers onto one engagement. Returns the keys.

    Called when an engagement is created, and again from the workspace button
    for engagements that already existed when the master sheet was first filled
    in.

    **Never overwrites an answer that is already there**, including one carried
    forward and not yet confirmed. A standing answer is a starting point, not a
    correction to something the auditor has entered for this client.
    """
    defaults = default_map(session, firm_id)
    if not defaults:
        return []

    applied: list[str] = []
    for state in field_states(session, engagement, clause_set):
        if state.value is not None:
            continue
        value = defaults.get(state.key)
        if value is None or value not in {option for option, _ in state.options}:
            continue
        row = set_response(
            session,
            engagement.engagement_id,
            state.key,
            value,
            updated_by=applied_by,
        )
        # `set_response` marks an edited answer USER and reviewed, which is
        # right for a person typing and wrong here: nobody has looked at this
        # client's file yet. The value counts (decision 28), but the trail must
        # still say where it came from.
        row.source = ResponseSource.DEFAULT
        applied.append(state.key)

    session.flush()
    return applied
