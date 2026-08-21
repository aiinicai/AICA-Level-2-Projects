"""Where an engagement has got to — stages and per-section completion.

Partner's request, 17 August 2026 (decisions 36 and 37): a step-by-step
workflow with a progress indicator, and a Not started / In progress / Completed
marker on every section.

Both are **derived from the file itself**, never stored. A stored "this section
is done" flag is a second source of truth that drifts the moment somebody
changes an answer, and the thing it would drift about — whether the document can
be signed — is the one thing that must not be guessed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import StrEnum

from sqlalchemy.orm import Session

from app.clauses.model import Clause, ClauseSet
from app.models.engagement import Engagement
from app.models.enums import EngagementStatus
from app.services.engagement import FieldState, field_states


class SectionState(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


SECTION_LABELS: dict[SectionState, str] = {
    SectionState.NOT_APPLICABLE: "Not applicable",
    SectionState.NOT_STARTED: "Not started",
    SectionState.IN_PROGRESS: "In progress",
    SectionState.COMPLETE: "Completed",
}


@dataclass(frozen=True, slots=True)
class Section:
    """One document, and how far through it the auditor is."""

    id: str
    title: str
    state: SectionState
    answered: int
    total: int

    @property
    def label(self) -> str:
        return SECTION_LABELS[self.state]

    @property
    def percent(self) -> int:
        if self.state is SectionState.NOT_APPLICABLE:
            return 100
        if not self.total:
            return 100
        return round(self.answered * 100 / self.total)


@dataclass(frozen=True, slots=True)
class Stage:
    """One step of the workflow bar."""

    key: str
    label: str
    done: bool
    current: bool


# The workflow the partner described. Deliberately five steps rather than the
# eight statuses behind them: "Prepared" and "Approved" are one thing to a
# person finishing a file, and a progress bar that names database states is a
# progress bar nobody reads.
STAGES: tuple[tuple[str, str, tuple[EngagementStatus, ...]], ...] = (
    ("profile", "Client profile", (EngagementStatus.NOT_STARTED,)),
    ("data", "Data collection", (EngagementStatus.DATA_COLLECTION,)),
    ("review", "Review", (EngagementStatus.PREPARED,)),
    ("reports", "Reports", (EngagementStatus.APPROVED,)),
    ("finalised", "Finalisation", (EngagementStatus.FINALISED, EngagementStatus.ARCHIVED)),
)


def stages(engagement: Engagement) -> list[Stage]:
    """The workflow bar for one engagement.

    `done` means the file has passed that step, not that every question in it
    was answered — the readiness percentage and the section markers say that,
    and one indicator claiming two different things is worse than two.
    """
    order = [key for key, _label, _statuses in STAGES]
    current_key = next(
        (key for key, _label, statuses in STAGES if engagement.status in statuses),
        "data",
    )
    position = order.index(current_key)
    return [
        Stage(key=key, label=label, done=index < position, current=index == position)
        for index, (key, label, _statuses) in enumerate(STAGES)
    ]


def sections(
    session: Session,
    engagement: Engagement,
    clause_set: ClauseSet,
    applicable: frozenset[str] | None,
    gated: set[str],
) -> list[Section]:
    """Every document, with how much of it is answered.

    `gated` is the workspace's own set of fields an applicability flag rules
    out, passed in rather than recomputed so that the marker and the form can
    never disagree about which fields count.
    """

    def ruled_out(document_id: str) -> bool:
        clauses = [c for c in clause_set.clauses if c.document == document_id]
        return (
            bool(clauses)
            and applicable is not None
            and all(not set(c.requires) <= applicable for c in clauses)
        )

    all_states: dict[str, list[FieldState]] = {}
    for document_id in clause_set.documents:
        all_states[document_id] = [
            state
            for state in field_states(session, engagement, clause_set, document=document_id)
            if state.key not in gated and state.mandatory
        ]

    out: list[Section] = []
    for document_id, document in clause_set.documents.items():
        if ruled_out(document_id):
            out.append(
                Section(
                    id=document_id,
                    title=document.title,
                    state=SectionState.NOT_APPLICABLE,
                    answered=0,
                    total=0,
                )
            )
            continue

        states = all_states[document_id]
        total = len(states)
        answered = sum(
            1 for s in states if s.value is not None and not s.is_unconfirmed_carry_forward
        )
        if total and answered == total:
            state = SectionState.COMPLETE
        elif answered:
            state = SectionState.IN_PROGRESS
        else:
            # A section with no mandatory fields at all is complete, not
            # "not started" — there is nothing for anyone to do in it.
            state = SectionState.NOT_STARTED if total else SectionState.COMPLETE
        out.append(
            Section(
                id=document_id,
                title=document.title,
                state=state,
                answered=answered,
                total=total,
            )
        )
    return out


def applies(clause: Clause, applicable: frozenset[str] | None) -> bool:
    return applicable is None or set(clause.requires) <= applicable


@dataclass(frozen=True, slots=True)
class IndexEntry:
    """One line of the in-page index (decision 75)."""

    clause_id: str
    title: str
    anchor: str
    outstanding: bool


def page_index(states: Sequence[FieldState], clause_set: ClauseSet) -> list[IndexEntry]:
    """An index of one document tab: one entry per clause, in page order.

    The Board's Report is 312 fields under 41 headings on a single page more
    than twenty screens tall. The firm's team reported the statutory auditors'
    term field as missing; it was 2,357 pixels down and rendering perfectly. A
    page nobody can traverse is a page whose fields do not exist, so the
    reports "I cannot find it" and "it is not there" are the same report and
    the fix is the same fix.

    `outstanding` marks a clause with a mandatory field still unanswered, so
    the index doubles as a worklist. It is derived from the states the page is
    rendering -- the same list, not a second count that could disagree with it.
    """
    entries: list[IndexEntry] = []
    seen: dict[str, int] = {}
    for state in states:
        unanswered = state.mandatory and state.value in (None, "")
        if state.clause_id in seen:
            if unanswered:
                position = seen[state.clause_id]
                entries[position] = replace(entries[position], outstanding=True)
            continue
        # `ClauseSet.get` RAISES on an unknown id rather than returning None.
        # An index that brings the page down because one clause was renamed is
        # worse than an index missing a title, and a field with no clause is
        # still a field sitting on the page.
        try:
            title = clause_set.get(state.clause_id).title
        except KeyError:
            title = state.clause_id
        seen[state.clause_id] = len(entries)
        entries.append(
            IndexEntry(
                clause_id=state.clause_id,
                title=title,
                anchor=f"field-{state.key}",
                outstanding=unanswered,
            )
        )
    return entries
