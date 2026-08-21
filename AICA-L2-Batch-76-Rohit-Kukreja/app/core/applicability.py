"""The single applicability engine. Build Prompt v2 §7.

One pure function. Every document generator reads from its result, so a
company type can never mean one thing in the auditor's report and another in
the Directors' Report — the prototype defect that told listed companies they
were private.

Thresholds live in `content/applicability_rules.yaml`, never here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

FLAGS: tuple[str, ...] = (
    "caro",
    "ifc",
    "s197",
    "csr",
    "cost_records",
    "internal_audit",
    "secretarial_audit",
    "kam",
    "abridged_board_report",
    # The strict inverse of the flag above, so a clause can require the FULL
    # report the way every other clause requires a flag -- `requires` is a
    # set-inclusion test and has no way to say "not". Derived, never computed
    # separately: Rule 8(6) and Rule 8A divide every company between them, and
    # two independent determinations could drift apart and produce a report
    # that is neither.
    "full_board_report",
    "cfs_required",
)


# Flags whose value is computed FROM another flag rather than from the profile.
# They have no stored column and cannot be overridden on their own: overriding
# the flag they derive from moves them, which is the point. Overriding both
# independently is what would let a company be determined abridged and still
# print the Rule 8 paragraphs.
DERIVED_FLAGS: frozenset[str] = frozenset({"full_board_report"})

# Flags the AUDITOR states, rather than the engine inferring them from the
# profile's figures. Partner's instruction of 20 Aug 2026: ask the plain
# question and do not link it to turnover or borrowings.
#
# Why, beyond the instruction: both exemptions turn on facts the figures do not
# carry. CARO's private-company limb is lost outright if the company is a
# subsidiary or holding company of a public company; the s.143(3)(i) exemption
# under G.S.R. 583(E) is lost if the company has defaulted in filing under s.92
# or s.137, which no column records. An engine reading only turnover and
# borrowings will be confidently wrong in both directions, and the auditor has
# to check the position anyway.
DECLARED_FLAGS: frozenset[str] = frozenset(
    {"caro", "ifc", "csr", "internal_audit", "secretarial_audit"}
)


class ApplicabilityError(ValueError):
    """The rules file is malformed. Message is safe to show a user."""


@dataclass(frozen=True, slots=True)
class Flag:
    """One determination, with the reasoning shown in the UI tooltip (§7)."""

    value: bool
    basis: str
    overridden: bool = False
    # False only for a declared flag nobody has answered yet. `value` is then
    # False as the safe reading, but it is an absence of an answer rather than
    # an answer of "no" -- the completeness gate blocks export until it is one.
    decided: bool = True


@dataclass(frozen=True, slots=True)
class Applicability:
    caro: Flag
    ifc: Flag
    s197: Flag
    csr: Flag
    cost_records: Flag
    internal_audit: Flag
    secretarial_audit: Flag
    kam: Flag
    abridged_board_report: Flag
    full_board_report: Flag
    cfs_required: Flag

    def __getitem__(self, name: str) -> Flag:
        if name not in FLAGS:
            raise KeyError(f"{name!r} is not an applicability flag")
        return getattr(self, name)  # type: ignore[no-any-return]

    def as_dict(self) -> dict[str, Flag]:
        return {name: self[name] for name in FLAGS}

    @property
    def active(self) -> tuple[str, ...]:
        return tuple(name for name in FLAGS if self[name].value)


@dataclass(frozen=True, slots=True)
class ProfileFacts:
    """What the engine is allowed to look at.

    Deliberately a narrow value object rather than the ORM row: the engine
    is pure and testable, and it cannot quietly start depending on something
    that is not a stated input.
    """

    company_type: str
    cost_records_industry: bool | None = None

    # NO FINANCIAL FIGURES. Every flag that read one is now declared by the
    # auditor (20 Aug 2026), so paid-up capital, turnover, borrowings, net
    # worth, net profit, reserves and deposits are no longer inputs to
    # anything. They were removed rather than left unread: an input the engine
    # ignores is an invitation to wonder why the answer did not change when it
    # was corrected.

    # s.129(3) reaches associates and joint ventures, not subsidiaries alone.
    has_subsidiary: bool | None = None
    has_associate: bool | None = None
    has_joint_venture: bool | None = None

    # Rule 6 exemption from preparing consolidated financial statements.
    is_wholly_owned_or_unopposed_partially_owned: bool = False
    not_listed_or_in_process_of_listing: bool = False
    parent_files_compliant_cfs: bool = False

    @property
    def is_listed(self) -> bool:
        return self.company_type == "pub_listed"

    @property
    def is_private(self) -> bool:
        return self.company_type in {"pvt", "opc", "small"}


# --------------------------------------------------------------------------
# Rules file
# --------------------------------------------------------------------------


@lru_cache(maxsize=4)
def load_rules(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ApplicabilityError(f"{path}: applicability_rules.yaml not found")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict) or "rules" not in data:
        raise ApplicabilityError(f"{path}: expected a mapping with a `rules` key")
    rules: dict[str, Any] = data["rules"]
    missing = [name for name in FLAGS if name not in rules]
    if missing:
        raise ApplicabilityError(f"{path}: no rule for {', '.join(missing)}")
    return rules


def _in_force(rule: dict[str, Any], fy_end: date) -> bool:
    raw = rule.get("effective_from")
    if raw is None:
        return True
    start = raw if isinstance(raw, date) else date.fromisoformat(str(raw))
    return fy_end >= start


def _amount(value: Decimal | None) -> Decimal:
    return Decimal(0) if value is None else value


def _crore(value: Any) -> str:
    """Render a threshold the way a reviewer will recognise it."""
    return f"Rs. {Decimal(str(value)) / 10000000:.10g} crore"


# --------------------------------------------------------------------------
# Individual determinations
# --------------------------------------------------------------------------


def _by_company_type(facts: ProfileFacts, rule: dict[str, Any], label: str) -> Flag:
    allowed = rule.get("company_types", [])
    if facts.company_type in allowed:
        return Flag(True, f"{label} applies to {facts.company_type} companies")
    return Flag(False, f"{label} does not apply to {facts.company_type} companies")


def _cost_records(facts: ProfileFacts, _rule: dict[str, Any]) -> Flag:
    if facts.cost_records_industry is None:
        # Industry-driven, and the profile does not say. Refusing to guess is
        # the point: a silent False would omit CARO (vii) and Rule 8(5)(ix).
        return Flag(
            False,
            "industry not recorded — cost records applicability must be set on the client",
        )
    if facts.cost_records_industry:
        return Flag(True, "client is in a prescribed industry")
    return Flag(False, "client is not in a prescribed industry")


def _cfs(facts: ProfileFacts, rule: dict[str, Any]) -> Flag:
    """s.129(3) plus the Rule 6 exemption.

    Subsidiaries alone are not the test - associates and joint ventures count
    too - and a company that has them may still be exempt under Rule 6. Both
    halves rest on profile facts the engine cannot infer.
    """
    holdings = {
        "subsidiary": facts.has_subsidiary,
        "associate": facts.has_associate,
        "joint venture": facts.has_joint_venture,
    }
    if all(value is None for value in holdings.values()):
        return Flag(
            False,
            "subsidiary, associate and joint-venture status not recorded - "
            "set them on the client profile",
        )

    held = [name for name, value in holdings.items() if value]
    if not held:
        return Flag(False, "no subsidiary, associate or joint venture")

    required = (rule.get("rule_6_exemption") or {}).get("requires_all", [])
    if required and all(getattr(facts, name, False) for name in required):
        return Flag(
            False,
            f"has {', '.join(held)} but exempt under Rule 6 "
            "(wholly owned or unopposed, unlisted, parent files compliant CFS)",
        )

    return Flag(True, f"company has {', '.join(held)}")


# --------------------------------------------------------------------------
# The one public function (§7)
# --------------------------------------------------------------------------


def compute(
    facts: ProfileFacts,
    fy_end: date,
    rules_path: Path,
    overrides: dict[str, bool] | None = None,
) -> Applicability:
    """Determine every flag for one engagement.

    Pure: same inputs, same result, no database and no clock. An override
    replaces the computed value, sets `overridden` and keeps the computed
    basis visible so a reviewer can see what was overruled.
    """
    rules = load_rules(rules_path)
    overrides = overrides or {}

    computed: dict[str, Flag] = {}
    for name in FLAGS:
        rule = rules[name]
        if not _in_force(rule, fy_end):
            computed[name] = Flag(False, f"not in force for a year ending {fy_end}")
            continue

        if name in DECLARED_FLAGS:
            # Not inferred. The override carries the auditor's answer, and the
            # loop below replaces this placeholder when one exists.
            computed[name] = Flag(
                False,
                "to be stated by the auditor",
                decided=False,
            )
            continue

        match name:
            case "cost_records":
                flag = _cost_records(facts, rule)
            case "cfs_required":
                flag = _cfs(facts, rule)
            case _:
                flag = _by_company_type(facts, rule, rules[name].get("label", name))
        computed[name] = flag

    for name, value in overrides.items():
        if name not in FLAGS:
            raise ApplicabilityError(f"{name!r} is not an applicability flag")
        original = computed[name]
        if name in DECLARED_FLAGS:
            computed[name] = Flag(
                value=value,
                basis="stated by the auditor",
                overridden=False,
                decided=True,
            )
            continue
        computed[name] = Flag(
            value=value,
            basis=f"overridden (computed: {original.value} — {original.basis})",
            overridden=True,
        )

    # Derived last, so it inverts the abridged flag AFTER any override. A firm
    # that overrides one company onto the full report gets the Rule 8 clauses
    # in the same movement, rather than an abridged determination and a full
    # set of paragraphs.
    abridged = computed["abridged_board_report"]
    computed["full_board_report"] = Flag(
        value=not abridged.value,
        basis=(
            "Rule 8 does not apply — Rule 8(6)"
            if abridged.value
            else f"Rule 8 applies: {abridged.basis}"
        ),
        overridden=abridged.overridden,
    )

    return Applicability(**computed)


def facts_from_profile(profile: Any) -> ProfileFacts:
    """Adapt a `client_profile` row to the engine's inputs.

    Every field the engine reads now has a column, so nothing here defaults
    silently. A flag that still reports "not recorded" means the profile
    genuinely has not been filled in — which is the honest answer.

    **No amount is read.** Paid-up capital, turnover, borrowings, net worth,
    net profit, reserves and deposits are still columns on the profile, holding
    what was entered before, and the engine no longer looks at any of them: the
    flags that used to turn on them are stated by the auditor. Passing them here
    would make them look like inputs, which is how a figure ends up corrected in
    the belief that a determination will move.
    """
    return ProfileFacts(
        company_type=profile.company_type.value,
        has_subsidiary=profile.has_subsidiary,
        has_associate=profile.has_associate,
        has_joint_venture=profile.has_joint_venture,
        is_wholly_owned_or_unopposed_partially_owned=(
            profile.is_wholly_owned_or_unopposed_partially_owned
        ),
        not_listed_or_in_process_of_listing=profile.not_listed_or_in_process_of_listing,
        parent_files_compliant_cfs=profile.parent_files_compliant_cfs,
        cost_records_industry=profile.cost_records_industry,
    )
