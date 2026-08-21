"""The What Changed screen. Build Prompt v2 §6.4.

Green unchanged, amber changed, red significant. "Significant" is not a
severity guess — it is a named list: an opinion modification, fraud, going
concern, or new material litigation. Those are the four a partner must not
be able to scroll past.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.applicability import Applicability
from app.core.formatting import DateStyle, format_date, group_indian
from app.models.engagement import Engagement, EngagementResponse, Litigation
from app.models.masters import Client, ClientProfile
from app.services.client import directors_in_office, kmp_in_office


class Severity(StrEnum):
    SAME = "same"
    CHANGED = "changed"
    SIGNIFICANT = "significant"


# Fields whose change is always significant (§6.4 red).
_SIGNIFICANT_FIELDS: frozenset[str] = frozenset(
    {
        "opinion_type",
        "going_concern",
    }
)

# Clause ids whose answers are significant when they move off a clean state.
_SIGNIFICANT_CLAUSES: frozenset[str] = frozenset(
    {
        "caro.xi.a",  # fraud by or on the company
        "caro.xi.b",  # ADT-4 filing
        "caro.xix",  # material uncertainty on meeting liabilities
        "rule11.a",  # pending litigations
    }
)


@dataclass(frozen=True, slots=True)
class Row:
    item: str
    previous: str
    current: str
    severity: Severity

    @property
    def changed(self) -> bool:
        return self.severity is not Severity.SAME


def _fmt(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if hasattr(value, "value"):  # enum
        return str(value.value).replace("_", " ")
    if isinstance(value, Decimal):
        # §12 — lakh and crore grouping. Without this the comparison screen
        # showed turnover as "186500000.00", which is the same defect §19
        # names for documents: a number a reader has to count digits on.
        # `str(Decimal)` was reaching the page directly.
        return group_indian(value)
    if isinstance(value, date):
        return format_date(value, DateStyle.LONG)
    return str(value)


def _row(item: str, previous: Any, current: Any, *, significant: bool = False) -> Row:
    before, after = _fmt(previous), _fmt(current)
    if before == after:
        return Row(item, before, after, Severity.SAME)
    return Row(
        item,
        before,
        after,
        Severity.SIGNIFICANT if significant else Severity.CHANGED,
    )


def compare(
    session: Session,
    previous: Engagement,
    current: Engagement,
    *,
    previous_applicability: Applicability | None = None,
    current_applicability: Applicability | None = None,
) -> list[Row]:
    """Every item §6.4 lists, in the order a reviewer reads them."""
    rows: list[Row] = []

    client = session.get(Client, current.client_id)
    old_profile = session.get(ClientProfile, previous.profile_id) if previous.profile_id else None
    new_profile = session.get(ClientProfile, current.profile_id) if current.profile_id else None

    # --- company details -------------------------------------------------
    rows.append(
        _row(
            "Company name",
            old_profile.company_name if old_profile else None,
            new_profile.company_name if new_profile else None,
        )
    )
    rows.append(
        _row(
            "Registered address",
            old_profile.registered_addr if old_profile else None,
            new_profile.registered_addr if new_profile else None,
        )
    )
    rows.append(
        _row(
            "Company type",
            old_profile.company_type if old_profile else None,
            new_profile.company_type if new_profile else None,
        )
    )
    rows.append(
        _row(
            "Framework",
            old_profile.framework if old_profile else None,
            new_profile.framework if new_profile else None,
        )
    )

    # --- directors and KMP ----------------------------------------------
    if client is not None:
        before = directors_in_office(session, client.client_id, previous.fy_end)
        after = directors_in_office(session, client.client_id, current.fy_end)
        rows.append(_row("Directors", len(before), len(after)))

        old_names = {d.name for d in before}
        new_names = {d.name for d in after}
        if old_names != new_names:
            joined = ", ".join(sorted(new_names - old_names)) or "—"
            left = ", ".join(sorted(old_names - new_names)) or "—"
            rows.append(Row("Directors appointed", "—", joined, Severity.CHANGED))
            rows.append(Row("Directors ceased", left, "—", Severity.CHANGED))

        old_kmp = {
            f"{k.role.value}: {k.name}"
            for k in kmp_in_office(session, client.client_id, previous.fy_end)
        }
        new_kmp = {
            f"{k.role.value}: {k.name}"
            for k in kmp_in_office(session, client.client_id, current.fy_end)
        }
        rows.append(
            _row("Key Managerial Personnel", "; ".join(sorted(old_kmp)), "; ".join(sorted(new_kmp)))
        )

    # --- the facts that decide paragraphs --------------------------------
    #
    # Four financial figures used to be compared here. They stopped driving
    # anything when applicability became declared (decision 61) and the columns
    # went with decision 62. What is worth showing between two years is what a
    # document prints or a determination reads -- a company that acquires a
    # subsidiary changes its Board's Report, and that is the change a reviewer
    # needs to see on this screen.
    for label, attribute in (
        ("Website", "website"),
        ("Has a subsidiary", "has_subsidiary"),
        ("Has an associate", "has_associate"),
        ("Has a joint venture", "has_joint_venture"),
        ("Cost records industry", "cost_records_industry"),
    ):
        rows.append(
            _row(
                label,
                getattr(old_profile, attribute, None),
                getattr(new_profile, attribute, None),
            )
        )

    # --- opinion and going concern (always red when they move) ----------
    rows.append(
        _row("Audit opinion", previous.opinion_type, current.opinion_type, significant=True)
    )
    rows.append(
        _row("Going concern", previous.going_concern, current.going_concern, significant=True)
    )
    rows.append(_row("Report date", previous.report_date, current.report_date))
    rows.append(_row("Dividend", None, None))

    # --- applicability ---------------------------------------------------
    if previous_applicability is not None and current_applicability is not None:
        for name in ("caro", "ifc", "s197", "csr"):
            rows.append(
                _row(
                    f"{name.upper()} applicability",
                    "applicable" if previous_applicability[name].value else "not applicable",
                    "applicable" if current_applicability[name].value else "not applicable",
                )
            )

    # --- clause answers --------------------------------------------------
    rows.extend(_answer_rows(session, previous, current))

    return [row for row in rows if row.item != "Dividend" or row.changed]


def _answer_rows(session: Session, previous: Engagement, current: Engagement) -> list[Row]:
    def answers(engagement_id: int) -> dict[str, Any]:
        return {
            row.field_key: (row.value_text or row.value_num or row.value_date)
            for row in session.scalars(
                select(EngagementResponse).where(EngagementResponse.engagement_id == engagement_id)
            )
        }

    before = answers(previous.engagement_id)
    after = answers(current.engagement_id)

    rows: list[Row] = []
    for key in sorted(set(before) | set(after)):
        if key.endswith(".narrative"):
            continue
        clause_id = key.rsplit(".status", 1)[0]
        significant = clause_id in _SIGNIFICANT_CLAUSES
        row = _row(key, before.get(key), after.get(key), significant=significant)
        if row.changed:
            rows.append(row)

    # New material litigation is significant (§6.4).
    def litigation_count(engagement_id: int) -> int:
        return len(
            session.scalars(
                select(Litigation).where(Litigation.engagement_id == engagement_id)
            ).all()
        )

    old_count = litigation_count(previous.engagement_id)
    new_count = litigation_count(current.engagement_id)
    if new_count > old_count:
        rows.append(Row("Litigation matters", str(old_count), str(new_count), Severity.SIGNIFICANT))
    elif new_count != old_count:
        rows.append(Row("Litigation matters", str(old_count), str(new_count), Severity.CHANGED))

    return rows


def summarise(rows: list[Row]) -> dict[str, int]:
    return {
        "same": sum(1 for r in rows if r.severity is Severity.SAME),
        "changed": sum(1 for r in rows if r.severity is Severity.CHANGED),
        "significant": sum(1 for r in rows if r.severity is Severity.SIGNIFICANT),
    }
