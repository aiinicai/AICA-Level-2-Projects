"""
TAX-CASH-001 — Cash Expenditure Disallowance Screen.

Legal provision: Section 40A(3) and 40A(3A), Income-tax Act, 1961.
Expenditure paid otherwise than by account-payee cheque/draft/
prescribed electronic mode, exceeding ₹10,000 to a single person in a
day, is disallowed (₹35,000 for payments to transport operators for
plying/hiring/leasing goods carriages — this transporter carve-out is
NOT automated here, see Limitation below). Rule 6DD carries further
exceptions (payments to banks/RBI/government where cash is mandated,
payments to agricultural/forest/dairy/fishery/cottage-industry
producers, payments in villages without bank service, employee
terminal benefits up to ₹50,000, and others) — none of these are
automatable from FinSight's data either.

Verification: VERIFIED (old Act, 1961) — primary source: "Prohibited
transaction in cash / limit on cash transactions" and Section 40A,
incometaxindia.gov.in (see documentation/stage10_tax_rule_catalogue_
proposal.md, TAX-CASH-001). Effective date of the current ₹10,000
figure: Finance Act 2017, AY 2018-19 onward. New Act 2025 forward
reference (UNVERIFIED, non-gating): Section 36 — cross-checked across
three independent secondary sources, consistent, but not itself
primary-confirmed; never used to decide whether this rule executes
(app/rules/tax/act_transition.py gates strictly on the old Act only).

FinSight Analytical Test — operationalizes Section 40A(3)/(3A), with a
threshold set by the Act itself (₹10,000/day/person), not by FinSight:
aggregate same-day cash-mode PAYMENTS ONLY (see Polarity below) per
counterparty across GL/BANK data (`is_cash_payment_mode()`, the same
normalizer Audit's AUD-CASH-010 already uses) and flag where the
aggregate EXCEEDS ₹10,000 (Round 3 correction — strictly greater than,
not "at or above"; an aggregate of exactly ₹10,000 does not trigger a
finding, only ₹10,000.01 or higher does). The IDENTIFICATION of which
rows are "cash" and which counterparty a payment belongs to is
FinSight's own operationalization — the rupee threshold itself is the
Act's.

Polarity (Round 2 correction — was previously `max(debit_amount,
credit_amount)`, which could count an incoming receipt as if it were an
expenditure payment): this rule reads `debit_amount` ONLY — the
payment/outflow side of a row, the same convention TAX-CASH-002 uses
for the receipt/`credit_amount` side, and TAX-LOAN-003/TAX-MSME-013
already establish (credit increases what is owed/received, debit is
the payment that reduces it). A row with only `credit_amount` populated
(a receipt) is correctly never counted by this expenditure screen.

Limitation: (1) the ₹35,000 transporter threshold is not applied — every
row uses the ₹10,000 general threshold, so a genuine transporter payment
between ₹10,000 and ₹35,000 may be flagged even though it is not
actually disallowable; the finding text says so. (2) None of the Rule
6DD exceptions are evaluated — every finding asks the reviewer to
confirm none apply. (3) Bank Statement rows have no Party Name field;
grouping for BANK rows uses the Description text as an approximate
counterparty proxy, which may under- or over-aggregate relative to GL's
Party Name-based grouping. (4) This is a same-day aggregate only — it
does not track a running "aggregate outstanding to one party across the
year" concept beyond single-day payments. (5) No deduplication across
GL and Bank Statement data: if both are uploaded and both record the
same underlying cash payment (e.g. a GL entry and its corresponding
bank debit), this rule has no reliable cross-source transaction-identity
field to detect that overlap, and will aggregate both rows as if they
were separate payments — this may overstate the aggregate for a given
counterparty/day. FinSight does not attempt to guess a deduplication
rule from the data available; this limitation is disclosed in every
finding rather than silently aggregated as if the sources were
independent. This rule never states a disallowance is confirmed — only
that the payment pattern warrants review against Section 40A(3)/(3A)
and Rule 6DD.

Insufficient data: no validated GL or Bank Statement data at all for
this engagement, or no row anywhere in that data has a Payment Mode
value populated.
"""
from __future__ import annotations

from collections import defaultdict

from app.rules import wording
from app.rules.accounting.shared_detectors import is_cash_payment_mode
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.rules.tax.act_transition import describe_act_era
from app.utils.currency import paise_to_display

RULE_ID = "TAX-CASH-001"
TOPIC = "Cash Expenditure Disallowance Screen"
PROVISION_REFERENCE = "Section 40A(3), Section 40A(3A), Income-tax Act, 1961"

CASH_THRESHOLD_PAISE = 1_000_000  # ₹10,000 — the Act's own figure, not FinSight's


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    gl_rows = dataset.get("GL", [])
    bank_rows = dataset.get("BANK", [])
    if not gl_rows and not bank_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped General Ledger or Bank Statement data is available for this engagement."
        )
        return outcome

    any_payment_mode = any(
        (row.values.get("payment_mode") or "").strip() for row in (gl_rows + bank_rows)
    )
    if not any_payment_mode:
        outcome.insufficient_data_reason = (
            "No row in this engagement's validated General Ledger or Bank Statement data has a Payment Mode value "
            "populated — cash payments cannot be identified without it."
        )
        return outcome

    # (counterparty_key, transaction_date) -> [amount_paise total, file_ids, dataset_types]
    groups: dict[tuple[str, str], dict] = defaultdict(lambda: {"amount": 0, "file_ids": set(), "count": 0, "dataset_types": set()})

    for dataset_type, rows in (("GL", gl_rows), ("BANK", bank_rows)):
        for row in rows:
            v = row.values
            if not is_cash_payment_mode(v.get("payment_mode")):
                continue
            txn_date = v.get("transaction_date")
            if not txn_date:
                continue
            # GL has party_name; BANK does not (FILE_TYPE_FIELD_SETS) — fall back to
            # Description as an approximate counterparty proxy for BANK rows, disclosed above.
            counterparty = (v.get("party_name") or v.get("description") or "").strip()
            if not counterparty:
                continue
            # Payment/outflow side only (Round 2 correction) — a receipt
            # (credit_amount only) must never be counted by an expenditure screen.
            amount = v.get("debit_amount") or 0
            if amount <= 0:
                continue
            outcome.evaluated_count += 1
            key = (counterparty, txn_date)
            groups[key]["amount"] += amount
            groups[key]["file_ids"].add(str(row.file_id))
            groups[key]["count"] += 1
            groups[key]["dataset_types"].add(dataset_type)

    era = describe_act_era(engagement.financial_year)
    for (counterparty, txn_date), info in groups.items():
        # Round 3 CRITICAL correction: strict "exceeds" (>), not "at or above" (>=).
        # An aggregate exactly equal to ₹10,000 does NOT cross the threshold; only
        # an aggregate strictly greater than ₹10,000 (₹10,000.01 or higher) does.
        if info["amount"] <= CASH_THRESHOLD_PAISE:
            continue
        proxy_note = (
            " (Bank Statement row(s) — counterparty identified from the Description text, an approximate proxy, "
            "not a Party Name field)" if "BANK" in info["dataset_types"] else ""
        )
        dedup_note = (
            " Both General Ledger and Bank Statement data contributed to this total, and FinSight cannot reliably "
            "detect whether they represent the same underlying payment recorded twice — the true amount may be "
            "lower than shown; please verify against source documents." if len(info["dataset_types"]) > 1 else ""
        )
        outcome.exceptions.append(ExceptionDraft(
            label=wording.POTENTIAL_TAX_ISSUE,
            area=TOPIC,
            trigger_condition=(
                f'Cash-mode payment(s) to "{counterparty}"{proxy_note} on {txn_date} total '
                f"{paise_to_display(info['amount'])}, which EXCEEDS the Section 40A(3) threshold of "
                f"{paise_to_display(CASH_THRESHOLD_PAISE)} (an aggregate exactly equal to the threshold does not "
                f"exceed it)."
            ),
            explanation=(
                f'{era}. Section 40A(3)/(3A) disallows expenditure paid otherwise than by account-payee cheque/'
                f'draft/prescribed electronic mode where the aggregate to one person in a day exceeds ₹10,000 '
                f'(₹35,000 for payments to transport operators, not distinguished here). FinSight identified '
                f'{info["count"]} cash-mode payment(s) to "{counterparty}" on {txn_date} totaling '
                f"{paise_to_display(info['amount'])}.{dedup_note} This does NOT establish that a disallowance "
                f"applies — Rule 6DD contains exceptions (payments to banks/government, agricultural producers, "
                f"employee terminal benefits, and others) that FinSight cannot evaluate from the data provided, "
                f"and the transporter carve-out is not applied. This is a potential issue for professional review, "
                f"not a confirmed disallowance."
            ),
            suggested_query=(
                f'Please confirm the mode of payment for the cash-mode transaction(s) to "{counterparty}" on '
                f"{txn_date}, and whether any Rule 6DD exception or the transporter carve-out applies."
            ),
            risk_level="MEDIUM",
            data_sources=sorted(info["file_ids"]),
            threshold_used={
                "cash_threshold_paise": CASH_THRESHOLD_PAISE,
                "threshold_is_statutory": True,
                "statutory_source": PROVISION_REFERENCE,
                "aggregate_amount_paise": info["amount"],
                "transporter_carveout_applied": False,
                "rule_6dd_exceptions_applied": False,
                "threshold_comparison_operator": "strictly greater than (exceeds)",
                "polarity": "debit_amount only (payment/outflow side)",
                "cross_source_deduplicated": False,
                "sources_contributing": sorted(info["dataset_types"]),
            },
            amount_paise=info["amount"],
        ))

    return outcome
