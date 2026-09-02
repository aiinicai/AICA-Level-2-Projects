"""
AS15-EB-008 / INDAS19-EB-008 — Employee Benefit Provisions
(presence/absence advisory).

Framework: AS 15 (Employee Benefits) / Ind AS 19 (Employee Benefits).
Already downgraded in the Stage 3 blueprint review to a low-confidence
advisory presence/absence check — not a computation of what the
provision *should* be (that needs an actuarial valuation, which is
never part of any uploaded accounting file). Stage 8 Round 2
(correction #9's "only strong rules should be active" principle)
downgrades it further to `is_active=False` — "Future / Not currently
executable" — since a coarse presence/absence keyword check is exactly
the class of weak signal that instruction says should not be activated
merely to reach a rule count. The blueprint's own text already flagged
this as "recommend revisiting in a later version if HR data becomes an
available input" — this module is kept, coded and ready, for that
future reactivation, but does not run today.

What data is required: ledger-style rows (TB/GL/JE) with `account_name`
values.
What can actually be established: whether an account resembling a
common employee-benefit provision (gratuity, leave encashment,
compensated absences) is present at all in the trial balance / general
ledger.
What cannot be established: whether any such provision, if present, is
adequate — that requires an actuarial valuation never available from
uploaded ledger data. Equally, absence of a matching account name does
not establish that no provision exists (it could be worded differently,
or bundled into a broader "provisions" line) — the finding text says so
explicitly and is always advisory/LOW risk, never phrased as a
deficiency.
Insufficient data: no ledger-style data (TB/GL/JE) is available at all
for this engagement.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.base_rule import ExceptionDraft, RuleOutcome

FRAMEWORK_RULE_IDS = {"AS": "AS15-EB-008", "IND_AS": "INDAS19-EB-008"}
TOPIC = "Employee Benefit Provisions — Presence Check"
_BENEFIT_KEYWORDS = ("gratuity", "leave encashment", "compensated absence", "leave salary", "pf contribution", "provident fund")
_LEDGER_TYPES = ("TB", "GL", "JE")


def evaluate(engagement, dataset: dict[str, list], framework: str) -> RuleOutcome:
    rule_id = FRAMEWORK_RULE_IDS.get(framework, FRAMEWORK_RULE_IDS["AS"])
    outcome = RuleOutcome(rule_id=rule_id)

    ledger_rows = [row for t in _LEDGER_TYPES for row in dataset.get(t, [])]
    if not ledger_rows:
        outcome.insufficient_data_reason = (
            "No validated Trial Balance, General Ledger, or Journal Entry data is available for this engagement."
        )
        return outcome

    outcome.evaluated_count = 1
    matched_accounts = sorted({
        (row.values.get("account_name") or "").strip()
        for row in ledger_rows
        if any(k in (row.values.get("account_name") or "").lower() for k in _BENEFIT_KEYWORDS)
    })

    if matched_accounts:
        return outcome  # provision-like accounts found — nothing flagged; adequacy is not something this can assess

    outcome.exceptions.append(ExceptionDraft(
        label=wording.REVIEW_REQUIRED,
        area=TOPIC,
        trigger_condition=(
            "No ledger account matching common employee-benefit provision keywords (gratuity, leave encashment, "
            "compensated absences, provident fund) was found in the validated Trial Balance/General Ledger/Journal "
            "Entry data."
        ),
        explanation=(
            "No account resembling a typical employee-benefit provision was found by name in this engagement's "
            "validated ledger data. This does not establish that no such provision exists or is required — the "
            "account may be worded differently, bundled into a broader provisions line, or the entity may "
            "genuinely have no employee-benefit obligation requiring a provision. This is a low-confidence "
            "presence check only, not an assessment of adequacy, which would require an actuarial valuation not "
            "available from uploaded ledger data."
        ),
        suggested_query=(
            "Please confirm whether provisions for employee benefits (e.g. gratuity, leave encashment) exist, "
            "and if so, where they appear in the trial balance/general ledger."
        ),
        risk_level="LOW",
        data_sources=[str(row.file_id) for row in ledger_rows[:1]],
        threshold_used={"matched_account_count": 0},
    ))

    return outcome
