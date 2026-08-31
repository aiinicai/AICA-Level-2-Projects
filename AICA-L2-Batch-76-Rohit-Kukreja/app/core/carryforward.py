"""Rollover. Build Prompt v2 §6 — the defining feature.

The firm's requirement: master data stays the same every year until someone
chooses to change it, *without corrupting documents already issued*.

Two rules do the work:
  · a `never` field is not copied at all;
  · a copied field is only marked reviewed if its policy is `always`.

Everything else follows from those, including the §6.2 never-blind-copy
register, which is enforced by giving those fields a `prompt` policy in the
clause YAML rather than by a second list in Python.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clauses.model import CarryForward, ClauseSet
from app.core.formatting import financial_year
from app.models.engagement import (
    Engagement,
    EngagementResponse,
    FieldCatalog,
    Litigation,
    Mgt9BusinessActivity,
    Mgt9DirectorHolding,
    Mgt9Indebtedness,
    Mgt9PromoterHolding,
    Mgt9Shareholding,
    StatutoryDue,
)
from app.models.enums import EngagementStatus, ResponseSource
from app.models.issuance import AuditLog

# Child entities that roll forward. Board meetings and director changes are
# recomputed from the register each year, so they are deliberately absent.
#
# The MGT-9 tables were added on 21 August 2026 (decision 67). Six tables of
# shareholding, indebtedness and business activity were retyped from scratch
# every year for every client, and in a private company the shareholding
# rarely moves at all. Every carried row arrives flagged for review, exactly
# as litigation does -- carrying is not the same as confirming, and the export
# gate holds until each one is looked at.
ROLLED_CHILD_MODELS: dict[str, type] = {
    "litigation": Litigation,
    "statutory_due": StatutoryDue,
    "mgt9_business_activity": Mgt9BusinessActivity,
    "mgt9_shareholding": Mgt9Shareholding,
    "mgt9_promoter_holding": Mgt9PromoterHolding,
    "mgt9_director_holding": Mgt9DirectorHolding,
    "mgt9_indebtedness": Mgt9Indebtedness,
}


class RolloverError(ValueError):
    """Message is safe to show a user."""


@dataclass(frozen=True, slots=True)
class RolloverReport:
    """What §6.3 step 5 requires. Do not omit it."""

    engagement_id: int
    fy_code: str
    carried: tuple[str, ...] = ()
    requires_review: tuple[str, ...] = ()
    newly_in_force: tuple[str, ...] = ()
    retired: tuple[str, ...] = ()
    child_rows_carried: dict[str, int] = field(default_factory=dict)
    blanked: tuple[str, ...] = ()

    @property
    def review_count(self) -> int:
        return len(self.requires_review)


def _in_force(entry: FieldCatalog, fy_end: date) -> bool:
    if entry.effective_from and fy_end < entry.effective_from:
        return False
    return not (entry.effective_to and fy_end > entry.effective_to)


def roll_forward(
    session: Session,
    source_id: int,
    *,
    fy_start: date,
    fy_end: date,
    profile_id: int | None,
    rolled_by: str,
    categories: set[str] | None = None,
) -> tuple[Engagement, RolloverReport]:
    """Create next year's engagement from this one.

    `categories` optionally restricts which documents are copied, matching
    the configurable carry-forward screen in §6.3.
    """
    source = session.get(Engagement, source_id)
    if source is None:
        raise RolloverError(f"Engagement {source_id} not found")

    fy_code = financial_year(fy_end).removeprefix("FY ")
    if session.scalar(
        select(Engagement).where(
            Engagement.client_id == source.client_id, Engagement.fy_code == fy_code
        )
    ):
        raise RolloverError(f"FY {fy_code} already exists for this client")

    target = Engagement(
        client_id=source.client_id,
        fy_code=fy_code,
        fy_start=fy_start,
        fy_end=fy_end,
        # The client's *current* profile, not the source engagement's (§6.3).
        profile_id=profile_id,
        partner_id=source.partner_id,
        manager_id=source.manager_id,
        rolled_from=source.engagement_id,
        status=EngagementStatus.DATA_COLLECTION,
    )
    session.add(target)
    session.flush()

    catalog = {entry.field_key: entry for entry in session.scalars(select(FieldCatalog))}
    previous = {
        row.field_key: row
        for row in session.scalars(
            select(EngagementResponse).where(EngagementResponse.engagement_id == source_id)
        )
    }

    carried: list[str] = []
    requires_review: list[str] = []
    blanked: list[str] = []

    for key, row in previous.items():
        entry = catalog.get(key)
        if entry is None:
            continue
        if categories is not None and entry.document not in categories:
            continue

        # A clause that has since been retired must not be carried into a
        # year in which it does not exist.
        if not _in_force(entry, fy_end):
            continue

        if entry.carry_forward is CarryForward.NEVER:
            blanked.append(key)
            continue

        reviewed = entry.carry_forward is CarryForward.ALWAYS
        session.add(
            EngagementResponse(
                engagement_id=target.engagement_id,
                field_key=key,
                value_text=row.value_text,
                value_num=row.value_num,
                value_date=row.value_date,
                source=ResponseSource.CARRIED_FORWARD,
                reviewed=reviewed,
                wp_reference=row.wp_reference,
                updated_by=rolled_by,
            )
        )
        carried.append(key)
        if not reviewed:
            requires_review.append(key)

    child_counts = _roll_child_rows(session, source_id, target.engagement_id, rolled_by)

    newly, retired = _clause_movements(catalog, source.fy_end, fy_end)

    session.add(
        AuditLog(
            entity="engagement",
            entity_id=str(target.engagement_id),
            action="roll_forward",
            field=f"from:{source.fy_code}",
            reason=f"Rolled forward from FY {source.fy_code}",
            actor=rolled_by,
        )
    )
    session.flush()

    return target, RolloverReport(
        engagement_id=target.engagement_id,
        fy_code=fy_code,
        carried=tuple(sorted(carried)),
        requires_review=tuple(sorted(requires_review)),
        newly_in_force=newly,
        retired=retired,
        child_rows_carried=child_counts,
        blanked=tuple(sorted(blanked)),
    )


def _roll_child_rows(
    session: Session, source_id: int, target_id: int, rolled_by: str
) -> dict[str, int]:
    """Copy child records, every row flagged for review.

    Litigation status changes constantly and disputed dues get settled, so
    no carried row is ever presented as verified (§6.2).
    """
    counts: dict[str, int] = {}
    for entity, model in ROLLED_CHILD_MODELS.items():
        # `model` is a mapped class chosen at runtime, so the ORM attributes
        # are invisible to the type checker. Kept local and explicit rather
        # than loosening the whole module.
        mapped: Any = model
        rows: list[Any] = list(
            session.scalars(
                select(mapped).where(mapped.engagement_id == source_id).order_by(mapped.row_index)
            ).all()
        )
        copied = 0
        skip = {
            "engagement_id",
            "source",
            "reviewed",
            *(column.key for column in mapped.__mapper__.primary_key),
        }
        for row in rows:
            values = {
                column.key: getattr(row, column.key)
                for column in mapped.__mapper__.column_attrs
                if column.key not in skip
            }
            session.add(
                mapped(
                    engagement_id=target_id,
                    source=ResponseSource.CARRIED_FORWARD,
                    reviewed=False,
                    **values,
                )
            )
            copied += 1
        if copied:
            counts[entity] = copied
            session.add(
                AuditLog(
                    entity=entity,
                    entity_id=str(target_id),
                    action="carry_forward",
                    reason=f"{copied} row(s) carried forward for review",
                    actor=rolled_by,
                )
            )
    session.flush()
    return counts


def _clause_movements(
    catalog: dict[str, FieldCatalog], source_fy_end: date, target_fy_end: date
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Clauses newly in force this year, and clauses retired.

    §6.3 step 5: "this is what makes the design amendment-proof. Do not omit
    it." Without it, a clause that came into force this year would simply be
    absent and unanswered, with nothing telling anyone to look.
    """
    newly: list[str] = []
    retired: list[str] = []
    for key, entry in catalog.items():
        was = _in_force(entry, source_fy_end)
        now = _in_force(entry, target_fy_end)
        if now and not was:
            newly.append(key)
        elif was and not now:
            retired.append(key)
    return tuple(sorted(newly)), tuple(sorted(retired))


def unreviewed_carry_forwards(session: Session, engagement_id: int) -> list[str]:
    """Fields inherited but not yet confirmed. Export is blocked while any
    remain (§6.1)."""
    rows = session.scalars(
        select(EngagementResponse).where(
            EngagementResponse.engagement_id == engagement_id,
            EngagementResponse.source == ResponseSource.CARRIED_FORWARD,
            EngagementResponse.reviewed.is_(False),
        )
    ).all()
    return sorted(row.field_key for row in rows)


def catalog_policies(clause_set: ClauseSet) -> dict[str, CarryForward]:
    """Policy per field, straight from the clause YAML (§6.1).

    Policy is set in the YAML, never in Python — this only reads it back so
    tests can assert the two agree.
    """
    return {
        clause.input.key: clause.input.carry_forward
        for clause in clause_set.clauses
        if clause.input is not None
    }
