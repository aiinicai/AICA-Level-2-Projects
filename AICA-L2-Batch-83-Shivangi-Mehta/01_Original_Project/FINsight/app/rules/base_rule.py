"""
Shared result shapes every rule module returns, and the auto-discovery
registry that finds them — referenced by `app/rules/__init__.py`'s
docstring since Stage 2/3 ("added in Stage 3/8 once there are model
classes to register against"). Function-based, not class-based: every
rule module in `app/rules/accounting/` is just a Python module exposing
a module-level `RULE_ID` and an `evaluate(engagement, dataset) ->
RuleOutcome` function — no base class to subclass, matching this
codebase's existing function-oriented service style rather than
introducing OOP where nothing else in the project uses it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from app.rules import wording


@dataclass
class ExceptionDraft:
    """One potential finding a rule wants to raise. Never persisted
    directly — `app/services/accounting_review_service.py` turns this
    into a real `ExceptionRecord` (+ a linked `QueryRecord`), which is
    where amounts/labels/JSON encoding actually happen. Kept as a plain
    draft here so rule modules stay free of any SQLAlchemy/session
    concerns."""

    label: str  # one of wording.POTENTIAL_EXCEPTION / REVIEW_REQUIRED / POTENTIAL_INCONSISTENCY
    area: str  # topic, e.g. "Fixed Assets — Depreciation"
    trigger_condition: str  # the Trigger — what specifically fired
    explanation: str  # the Explanation — human-readable paragraph
    suggested_query: str  # the Suggested Query, with placeholders already filled in
    risk_level: str  # LOW / MEDIUM / HIGH
    data_sources: list[str] = field(default_factory=list)  # file_ids as strings, or dataset_type labels
    threshold_used: dict | None = None  # the Result — structured snapshot of the comparison
    amount_paise: int | None = None
    related_transaction_id: int | None = None

    def __post_init__(self):
        wording.assert_non_definitive(self.explanation)
        wording.assert_non_definitive(self.trigger_condition)


@dataclass
class RuleOutcome:
    """What running one rule against one engagement produced."""

    rule_id: str
    evaluated_count: int = 0  # how many individual items (assets/rows/etc.) were actually testable
    exceptions: list[ExceptionDraft] = field(default_factory=list)
    insufficient_data_reason: str | None = None  # set when the RULE AS A WHOLE could not run at all
    partial_insufficient_data_notes: list[str] = field(default_factory=list)  # per-item gaps, rule still ran


# module_name -> (RULE_ID, evaluate callable) — populated by
# app/rules/accounting/__init__.py at import time.
AccountingRuleModule = Callable[..., RuleOutcome]
