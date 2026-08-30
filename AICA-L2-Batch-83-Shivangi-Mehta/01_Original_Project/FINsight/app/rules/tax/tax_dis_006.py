"""
TAX-DIS-006 — Statutory Dues Payment-Basis Timing Test.

Legal provision: Section 43B(a)-(f), Income-tax Act, 1961. Deduction
for certain expenses (tax/duty/cess, employer PF/ESI/gratuity/welfare-
fund contributions, bonus/commission under Section 36(1)(ii), interest
on specified institutional/NBFC/bank loans, leave encashment) is
allowed only in the year of ACTUAL PAYMENT, not accrual — subject to a
proviso allowing payment up to the return-filing due date to still
count for that year (Section 43B(h), the MSME 45-day rule, is a
separate provision with NO such grace-period proviso — see
TAX-MSME-013, not this rule).

Verification: VERIFIED (old Act, 1961) — primary source: Section 43B,
incometaxindia.gov.in, full clause text fetched directly (see
documentation/stage10_tax_rule_catalogue_proposal.md, TAX-DIS-006).
New Act 2025 forward reference (UNVERIFIED, non-gating): Section 37 —
cross-checked across two independent sources, consistent, but not
itself primary-confirmed; never used to decide executability.

FinSight Analytical Test — a FinSight-designed heuristic screen for
Section 43B(a)-(f), not itself a figure the Act specifies: identifies
GL/JE/TB accounts whose name or description matches a statutory-dues
keyword list (provident fund, ESI, gratuity, leave encashment, bonus
payable, professional tax, excise/customs duty, cess payable — FinSight
has no dedicated statutory-dues classification field, Decision 5), and
computes each matched account's net credit balance as of financial year
end. A positive net credit balance (accrued but not fully offset by a
matching debit/payment entry) is flagged as a potential 43B timing
issue for review — never a computed disallowance.

Limitation: (1) keyword matching is FinSight's own approximation of
"statutory dues" — it will both miss dues under unclear account names
and may flag unrelated accounts that happen to contain a matched word.
(2) FinSight compares only the net balance as of financial year end; it
does not track whether a payment was actually made by the return-filing
due date (the proviso's actual test) — the finding asks the reviewer to
confirm the payment date rather than computing this itself, since
FinSight has no reliable "return filing due date" input per engagement.
(3) A GL/JE/TB clearing entry does not necessarily represent an actual
cash/bank payment (it could be a further accrual or reclassification) —
FinSight cannot distinguish these from account movement alone.

Insufficient data: no validated GL, JE, or Trial Balance data at all
for this engagement.
"""
from __future__ import annotations

from app.rules import wording
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.rules.tax.act_transition import describe_act_era
from app.utils.currency import paise_to_display

RULE_ID = "TAX-DIS-006"
TOPIC = "Statutory Dues Payment-Basis Timing Test"
PROVISION_REFERENCE = "Section 43B(a)-(f), Income-tax Act, 1961"

_STATUTORY_DUE_KEYWORDS = (
    "provident fund", "pf payable", "esi", "employee state insurance", "gratuity",
    "leave encashment", "bonus payable", "statutory due", "professional tax",
    "excise duty", "customs duty", "cess payable",
)
_LEDGER_TYPES = ("GL", "JE", "TB")
# A small noise floor, FinSight's own — not a statutory figure — to avoid flagging
# immaterial rounding-level balances. Mirrors AUD-LOB-012's MINIMUM_OUTSTANDING_PAISE.
NOISE_FLOOR_PAISE = 100_000  # ~₹1,000


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    ledger_rows = [row for dt in _LEDGER_TYPES for row in dataset.get(dt, [])]
    if not ledger_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped General Ledger, Journal Entries, or Trial Balance data is available "
            "for this engagement."
        )
        return outcome

    # account_name -> {balance, file_ids} — a custom aggregator (not shared_detectors.
    # net_balance_by_account(), which returns balances only, no file_id) so this rule's
    # findings can cite the same per-row Data Used (file IDs) traceability every other
    # rule in FinSight provides.
    accounts: dict[str, dict] = {}
    for row in ledger_rows:
        v = row.values
        account_name = (v.get("account_name") or "").strip()
        description = (v.get("description") or "").strip()
        haystack = f"{account_name} {description}".strip().lower()
        if not haystack or not any(k in haystack for k in _STATUTORY_DUE_KEYWORDS):
            continue
        debit = v.get("debit_amount") or 0
        credit = v.get("credit_amount") or 0
        key = account_name or description
        entry = accounts.setdefault(key, {"balance": 0, "file_ids": set()})
        entry["balance"] += credit - debit
        entry["file_ids"].add(str(row.file_id))

    outcome.evaluated_count = len(accounts)
    era = describe_act_era(engagement.financial_year)

    for account_name, info in accounts.items():
        balance = info["balance"]
        if balance < NOISE_FLOOR_PAISE:
            continue

        outcome.exceptions.append(ExceptionDraft(
            label=wording.TAX_REVIEW_REQUIRED,
            area=TOPIC,
            trigger_condition=(
                f'Statutory-dues-type account "{account_name}" carries a net credit (unpaid) balance of '
                f"{paise_to_display(balance)} as of financial year end."
            ),
            explanation=(
                f'{era}. Section 43B(a)-(f) allows deduction of certain statutory dues only in the year of actual '
                f'payment (with a grace period up to the return-filing due date, per the general 43B proviso). '
                f'FinSight identified account "{account_name}" (matched via a statutory-dues keyword, FinSight\'s '
                f"own heuristic — not a verified data field) with a net credit balance of "
                f"{paise_to_display(balance)} as of financial year end, suggesting the amount may not have been "
                f"paid. This does NOT establish that Section 43B disallows this amount — the account may not "
                f"actually be a Section 43B due, and payment may have been made before the return-filing due date "
                f"in a way this data does not show. This is a potential issue for professional review, not a "
                f"confirmed disallowance."
            ),
            suggested_query=(
                f'Please confirm the nature of "{account_name}" and, if it is a Section 43B statutory due, its '
                f"actual payment date relative to the return-filing due date."
            ),
            risk_level="MEDIUM",
            data_sources=sorted(info["file_ids"]),
            threshold_used={
                "noise_floor_paise": NOISE_FLOOR_PAISE,
                "threshold_is_statutory": False,
                "statutory_source": PROVISION_REFERENCE,
                "identification_method": "FinSight statutory-dues keyword heuristic",
                "net_credit_balance_paise": balance,
            },
            amount_paise=balance,
        ))

    return outcome
