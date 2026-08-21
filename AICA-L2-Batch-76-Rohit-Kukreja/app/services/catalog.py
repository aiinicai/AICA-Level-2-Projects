"""`field_catalog`, kept in step with the clause repository (§5.3).

Never hand-maintained. This is what makes acceptance criterion 12 work: a new
clause needs a YAML file and nothing else.

**It lives in the application, not in `scripts/seed.py`, because a packaged
installation never runs that script.** A colleague opening the .exe got a
database with an empty catalogue, so `field_states` returned nothing and the
workspace rendered **zero dropdowns** — every clause present in the repository,
none of them askable. The seed script now calls this too, so there is one
implementation rather than a development one and a shipped one that drift.
"""

from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clauses.model import CarryForward, ClauseSet
from app.models.engagement import EngagementResponse, FieldCatalog


def sync_field_catalog(session: Session, clause_set: ClauseSet, *, prune: bool = True) -> int:
    """Bring the catalogue in line with the repository. Returns the field count.

    `prune=False` keeps rows the repository no longer backs. Used on startup:
    see `prune_orphans` for why deleting them there is not always safe.
    """
    existing = {row.field_key: row for row in session.scalars(select(FieldCatalog))}
    seen: set[str] = set()

    for clause in clause_set.clauses:
        if clause.input is not None:
            key = clause.input.key
            seen.add(key)
            row = existing.get(key) or FieldCatalog(field_key=key)
            row.document = clause.document
            row.clause_id = clause.id
            row.clause_ref = clause.clause_ref
            row.label = clause.input.label or clause.title
            row.datatype = clause.input.datatype.value
            row.options_json = json.dumps(
                [{"value": o.value, "label": o.label} for o in clause.input.options]
            )
            row.carry_forward = clause.input.carry_forward
            row.is_mandatory = clause.input.mandatory
            row.effective_from = clause.effective_from
            row.effective_to = clause.effective_to
            row.sort_order = clause.order
            session.add(row)

        # A variant that demands an explanation needs somewhere to put it.
        # Narratives are always year-specific, so they never carry forward.
        #
        # Built for EVERY such clause, not only those that also ask a question.
        # A clause whose variant is chosen by the engagement's own data --
        # `bdr.auditor.remarks` follows the opinion type -- has no `input`, and
        # while this sat inside the `input` branch that clause could demand the
        # Board's explanation of a qualification with nowhere on any screen to
        # type it: the export stayed blocked and no field existed to unblock it.
        if any(v.requires_narrative for v in clause.variants):
            narrative_key = f"{clause.id}.narrative"
            seen.add(narrative_key)
            narrative = existing.get(narrative_key) or FieldCatalog(field_key=narrative_key)
            narrative.document = clause.document
            narrative.clause_id = clause.id
            narrative.clause_ref = clause.clause_ref
            prompt = clause.input.label if clause.input is not None else ""
            narrative.label = f"{prompt or clause.title} — explanation"
            narrative.datatype = "longtext"
            narrative.options_json = "[]"
            narrative.carry_forward = CarryForward.NEVER
            narrative.is_mandatory = False
            narrative.effective_from = clause.effective_from
            narrative.effective_to = clause.effective_to
            narrative.sort_order = clause.order + 1
            session.add(narrative)

    if prune:
        # A field the YAML no longer declares is orphaned. §13's startup
        # self-check looks for these; deleting them keeps the two in step.
        for key, row in existing.items():
            if key not in seen:
                session.delete(row)

    return len(seen)


def prune_orphans(session: Session, clause_set: ClauseSet) -> list[str]:
    """Delete catalogue rows the repository dropped, **unless answered**.

    Startup cannot simply delete them. A row with responses is protected by a
    foreign key, so deleting it fails outright and would stop the application
    from opening at all; and even if it were possible, a question that has been
    answered on a live engagement is evidence, not litter. Those are cleared
    deliberately by re-running `scripts/seed.py`, where the operator can see
    what is being discarded.

    Returns the keys kept, so a caller can say what is stale rather than
    leaving a phantom question on the workspace with no explanation.
    """
    live = {clause.input.key for clause in clause_set.clauses if clause.input is not None}
    live |= {f"{clause.id}.narrative" for clause in clause_set.clauses}

    answered = {
        key
        for (key,) in session.execute(
            select(EngagementResponse.field_key).group_by(EngagementResponse.field_key)
        )
    }
    kept: list[str] = []
    for row in list(session.scalars(select(FieldCatalog))):
        if row.field_key in live:
            continue
        if row.field_key in answered:
            kept.append(row.field_key)
            continue
        session.delete(row)
    return kept


def catalogue_size(session: Session) -> int:
    return int(session.scalar(select(func.count()).select_from(FieldCatalog)) or 0)
