"""Applicability overrides. Build Prompt v2 §7.

The engine computes every flag from the client profile. Sometimes the firm
knows better — the profile is incomplete, an exemption turns on a fact the
engine cannot see, or the partner simply takes a different view.

§7: "An override requires a reason, sets `overridden = True`, and appears in
the UI and audit log." All three are enforced here, and the computed value
and its reasoning stay visible beside the override so a reviewer can see
exactly what was overruled and why.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.clauses.model import ClauseSet
from app.config import get_settings
from app.core.applicability import (
    DECLARED_FLAGS,
    DERIVED_FLAGS,
    FLAGS,
    Applicability,
    Flag,
    compute,
    facts_from_profile,
)
from app.core.permissions import LOCAL_ACTOR
from app.models.engagement import Engagement
from app.models.issuance import AuditLog
from app.models.masters import ClientProfile

# Each flag is stored as a value column plus an `_override` boolean, so the
# profile records both what the firm chose and that it was a choice.
#
# Built by name rather than by `hasattr`. The old form quietly dropped any
# flag whose column was missing, which is how secretarial_audit,
# abridged_board_report and cfs_required went unoverridable without anyone
# noticing — a missing column produced a shorter list, not an error. Migration
# 0004 added the columns; `_assert_every_flag_has_columns` below now makes the
# next omission fail at import instead.
# Derived flags are excluded: they have no column because they have no
# independent value to store.
STORED_FLAGS: tuple[str, ...] = tuple(f for f in FLAGS if f not in DERIVED_FLAGS)
VALUE_COLUMNS: dict[str, str] = {name: name for name in STORED_FLAGS}
OVERRIDE_COLUMNS: dict[str, str] = {name: f"{name}_override" for name in STORED_FLAGS}


def _assert_every_flag_has_columns() -> None:
    """§7 — every applicability flag is overridable, with a reason."""
    missing = [
        column
        for column in (*VALUE_COLUMNS.values(), *OVERRIDE_COLUMNS.values())
        if not hasattr(ClientProfile, column)
    ]
    if missing:
        raise RuntimeError(
            f"ClientProfile is missing applicability columns {missing}; add them in a "
            "migration or the override screen cannot reach those flags"
        )


_assert_every_flag_has_columns()


class OverrideError(ValueError):
    """Message is safe to show a user."""


@dataclass(frozen=True, slots=True)
class FlagView:
    """One flag as the applicability screen needs it."""

    name: str
    label: str
    effective: Flag
    computed: Flag

    @property
    def is_declared(self) -> bool:
        """Stated by the auditor rather than inferred from the profile."""
        return self.name in DECLARED_FLAGS

    @property
    def awaiting_answer(self) -> bool:
        return not self.effective.decided

    @property
    def is_overridden(self) -> bool:
        return self.effective.overridden

    @property
    def differs_from_computed(self) -> bool:
        return self.effective.value != self.computed.value


def stored_overrides(profile: ClientProfile) -> dict[str, bool]:
    """Overrides recorded on the profile, as `compute()` wants them."""
    return {
        name: bool(getattr(profile, VALUE_COLUMNS[name]))
        for name, column in OVERRIDE_COLUMNS.items()
        if getattr(profile, column, False) and name in VALUE_COLUMNS
    }


def overridable(profile: ClientProfile) -> tuple[str, ...]:
    """Flags this profile can carry an override for — all of them.

    It used to be a subset by accident: three flags had no columns and dropped
    out silently. Migration 0004 added them and `_assert_every_flag_has_columns`
    stops that returning.

    It is a subset again, deliberately. A DERIVED flag has no column because it
    has no independent value — `full_board_report` is the inverse of
    `abridged_board_report` — so offering a control for it would either write
    nowhere or let one company be abridged by the engine and full on the page.
    Overriding the flag it derives from moves it, which is the supported path.
    """
    return STORED_FLAGS


def resolve(
    profile: ClientProfile, fy_end: date, rules_path: Path
) -> tuple[Applicability, Applicability]:
    """Return (effective, computed).

    The computed result is kept so the screen can show what the engine would
    have said. An override that agrees with the engine is still worth seeing:
    it tells a reviewer someone looked.
    """
    facts = facts_from_profile(profile)
    computed = compute(facts, fy_end, rules_path)
    effective = compute(facts, fy_end, rules_path, overrides=stored_overrides(profile))
    return effective, computed


def flag_views(profile: ClientProfile, fy_end: date, rules_path: Path) -> list[FlagView]:
    effective, computed = resolve(profile, fy_end, rules_path)
    labels = {
        "caro": "CARO 2020",
        "ifc": "Internal financial controls (s.143(3)(i))",
        "s197": "Managerial remuneration (s.197)",
        "csr": "Corporate social responsibility (s.135)",
        "cost_records": "Cost records (s.148(1))",
        "internal_audit": "Internal audit (s.138)",
        "secretarial_audit": "Secretarial audit (s.204)",
        "kam": "Key Audit Matters (SA 701)",
        "abridged_board_report": "Abridged Board's Report",
        "cfs_required": "Consolidated financial statements",
    }
    return [
        FlagView(
            name=name,
            label=labels.get(name, name),
            effective=effective[name],
            computed=computed[name],
        )
        for name in FLAGS
    ]


def set_override(
    session: Session,
    profile: ClientProfile,
    flag: str,
    choice: str,
    *,
    reason: str,
    actor: str = LOCAL_ACTOR,
) -> None:
    """Record or clear an override.

    `choice` is "computed", "applicable" or "not_applicable". A reason is
    required for the two that overrule the engine — without one the audit log
    would record that someone disagreed but not why, which is the part a
    reviewer actually needs.
    """
    if flag not in OVERRIDE_COLUMNS:
        if flag in DERIVED_FLAGS:
            raise OverrideError(
                f"{flag!r} is derived from another flag and cannot be set on its own — "
                "override the flag it derives from instead"
            )
        raise OverrideError(f"{flag!r} cannot be overridden")
    if choice not in {"computed", "applicable", "not_applicable"}:
        raise OverrideError(f"{choice!r} is not a valid choice")

    override_column = OVERRIDE_COLUMNS[flag]
    value_column = VALUE_COLUMNS[flag]
    before = (getattr(profile, value_column), getattr(profile, override_column))

    if choice == "computed":
        setattr(profile, override_column, False)
    else:
        # A declared flag has no computed answer to overrule -- the auditor's
        # choice IS the determination -- so no reason is demanded for it.
        if flag not in DECLARED_FLAGS and not reason.strip():
            raise OverrideError("A reason is required to override the computed answer")
        setattr(profile, override_column, True)
        setattr(profile, value_column, choice == "applicable")

    session.add(
        AuditLog(
            entity="client_profile",
            entity_id=str(profile.client_id),
            action="applicability_override",
            field=flag,
            before_json=json.dumps({"value": bool(before[0]), "overridden": bool(before[1])}),
            after_json=json.dumps(
                {
                    "value": bool(getattr(profile, value_column)),
                    "overridden": bool(getattr(profile, override_column)),
                    "choice": choice,
                }
            ),
            reason=reason.strip(),
            actor=actor,
        )
    )
    session.flush()


def applicable_flags(session: Session, engagement: Engagement) -> frozenset[str]:
    """The applicability flags that are true for one engagement (§7).

    `build_document` skips any clause requiring a flag absent from this set,
    which is what keeps a Key Audit Matters section out of an unlisted
    private company's report and the CARO annexure out of an exempt one.

    An engagement with no pinned profile yields an empty set. That is the
    conservative reading — an unanswered profile is not evidence that a
    requirement applies — and it shows up in the preview as a list of
    clauses skipped for want of applicability, not as a silent omission.
    """
    profile = session.get(ClientProfile, engagement.profile_id) if engagement.profile_id else None
    if profile is None:
        return frozenset()
    rules_path = get_settings().content_path / "applicability_rules.yaml"
    effective, _ = resolve(profile, engagement.fy_end, rules_path)
    return frozenset(name for name in FLAGS if effective[name].value)


def exclusion_reasons(
    profile: ClientProfile | None, fy_end: date, rules_path: Path
) -> dict[str, tuple[str, str]]:
    """Flag name -> (label, basis) for every flag that is currently FALSE.

    So a document the engine ruled out can say which determination ruled it out
    and on what figures, instead of rendering as a blank page. The basis text is
    the engine's own, not a second explanation written next to it that could
    drift from what the rule actually did.
    """
    if profile is None:
        return {}
    return {
        view.name: (view.label, view.effective.basis)
        for view in flag_views(profile, fy_end, rules_path)
        if not view.effective.value
    }


def governing_flag(clause_set: ClauseSet, document_id: str) -> str | None:
    """The single applicability flag that decides whether a document exists.

    A document is governed by a flag when **every** clause in it requires that
    one flag: CARO's 51 clauses all require `caro`, Annexure B's 11 all require
    `ifc`. Nothing else qualifies -- the auditor's report has one gated clause
    (KAM) out of 34, so it is not governed by anything and gets no question.

    Derived rather than listed, so a document added to the repository is picked
    up without a code change, and so a document that stops being wholly gated
    stops offering a question that would no longer be true.
    """
    clauses = [clause for clause in clause_set.clauses if clause.document == document_id]
    if not clauses:
        return None
    flags = {flag for clause in clauses for flag in clause.requires}
    if len(flags) != 1:
        return None
    only = next(iter(flags))
    if not all(only in clause.requires for clause in clauses):
        return None
    return only if only in OVERRIDE_COLUMNS else None


FLAG_QUESTIONS: dict[str, str] = {
    "caro": "Does CARO 2020 reporting apply to this company?",
    "ifc": "Is the Internal Financial Controls report applicable?",
}


def flag_question(flag: str) -> str:
    """The question to ask for a flag, in the auditor's words rather than the
    engine's. Falls back to the flag's own label so a new flag is askable
    immediately, if clumsily, instead of silently unaskable."""
    return FLAG_QUESTIONS.get(flag, f"Does {flag.replace('_', ' ')} apply to this company?")
