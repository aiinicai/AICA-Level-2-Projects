"""
TAX-CASH-002 — Large Cash Receipt Restriction Screen.

Legal provision: Section 269ST, Income-tax Act, 1961. No person shall
receive ₹2,00,000 or more in cash (a) in aggregate from a person in a
day, (b) in respect of a single transaction, or (c) in respect of
transactions relating to one event or occasion from a person.
Exceptions: receipts by Government, banking company, post office
savings bank, co-operative bank; transactions already covered by
Section 269SS; and other Central-Government-notified receipts.

Verification: VERIFIED (old Act, 1961) — primary source: Section 269ST
and the consolidated cash-transaction-threshold page, incometaxindia.
gov.in (see documentation/stage10_tax_rule_catalogue_proposal.md,
TAX-CASH-002). Effective 1 April 2017 (Finance Act 2017). New Act 2025
forward reference (UNVERIFIED, non-gating): Section 186 — cross-checked
across multiple independent sources, consistent, but not itself
primary-confirmed; never used to decide executability.

FinSight Analytical Test — operationalizes Section 269ST, with a
threshold set by the Act itself (₹2,00,000), not by FinSight: covers
limb (a) same-day aggregate per counterparty, via GL/BANK/SALES/AR
data (`is_cash_payment_mode()`), and limb (b) any single transaction
at or above ₹2,00,000, RECEIPTS ONLY (see Polarity below). Limb (c) —
transactions "relating to one event or occasion" — is NOT implemented
(see Limitation): FinSight has no event/occasion grouping key in its
data model.

Polarity (Round 2 correction — was previously `max(debit_amount,
credit_amount)`, which could count an outgoing payment as if it were
an incoming receipt): this rule reads `credit_amount` ONLY — the
receipt/inflow side of a row, the same convention TAX-CASH-001 uses
for the payment/`debit_amount` side. A row with only `debit_amount`
populated (a payment) is correctly never counted by this receipt
screen.

Limitation: (1) limb (c) is not covered — a series of cash receipts
tied to one event but spread across different days/parties in the data
will not be flagged by this rule. (2) None of the Section 269ST
exceptions (Government, banks, post office savings bank, co-operative
bank, or receipts already covered by Section 269SS) are evaluated —
every finding asks the reviewer to confirm none apply, and specifically
to check whether Section 269SS (a loan/deposit, see TAX-LOAN-003)
already covers the same receipt, since 269ST and 269SS are mutually
exclusive for the same transaction. (3) Bank Statement rows have no
Party Name field; grouping for BANK rows uses the Description text as
an approximate counterparty proxy. (4) No deduplication across data
sources: if GL, Bank Statement, Sales Register, and/or Accounts
Receivable all record the same underlying cash receipt, this rule has
no reliable cross-source transaction-identity field to detect that
overlap and will aggregate every source's row as if it were a separate
receipt — this may overstate the same-day aggregate; disclosed in each
finding where more than one source contributed, never silently
corrected. This rule never states a violation is confirmed — only that
the receipt pattern warrants review against Section 269ST.

Insufficient data: no validated GL, Bank Statement, Sales Register, or
Accounts Receivable data at all for this engagement, or no row anywhere
in that data has a Payment Mode value populated.
"""
from __future__ import annotations

from collections import defaultdict

from app.rules import wording
from app.rules.accounting.shared_detectors import is_cash_payment_mode
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.rules.tax.act_transition import describe_act_era
from app.utils.currency import paise_to_display

RULE_ID = "TAX-CASH-002"
TOPIC = "Large Cash Receipt Restriction Screen"
PROVISION_REFERENCE = "Section 269ST, Income-tax Act, 1961"

RECEIPT_THRESHOLD_PAISE = 20_000_000  # ₹2,00,000 — the Act's own figure, not FinSight's
_RECEIPT_DATASET_TYPES = ("GL", "BANK", "SALES", "AR")


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    rows_by_type = {dt: dataset.get(dt, []) for dt in _RECEIPT_DATASET_TYPES}
    if not any(rows_by_type.values()):
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped General Ledger, Bank Statement, Sales Register, or Accounts "
            "Receivable data is available for this engagement."
        )
        return outcome

    all_rows = [row for rows in rows_by_type.values() for row in rows]
    if not any((row.values.get("payment_mode") or "").strip() for row in all_rows):
        outcome.insufficient_data_reason = (
            "No row in this engagement's validated data has a Payment Mode value populated — cash receipts "
            "cannot be identified without it."
        )
        return outcome

    groups: dict[tuple[str, str], dict] = defaultdict(lambda: {"amount": 0, "file_ids": set(), "count": 0, "max_single": 0, "dataset_types": set()})

    for dataset_type, rows in rows_by_type.items():
        for row in rows:
            v = row.values
            if not is_cash_payment_mode(v.get("payment_mode")):
                continue
            txn_date = v.get("transaction_date")
            if not txn_date:
                continue
            counterparty = (v.get("party_name") or v.get("description") or "").strip()
            if not counterparty:
                continue
            # Receipt/inflow side only (Round 2 correction) — a payment
            # (debit_amount only) must never be counted by a receipt screen.
            amount = v.get("credit_amount") or 0
            if amount <= 0:
                continue
            outcome.evaluated_count += 1
            key = (counterparty, txn_date)
            g = groups[key]
            g["amount"] += amount
            g["file_ids"].add(str(row.file_id))
            g["count"] += 1
            g["max_single"] = max(g["max_single"], amount)
            g["dataset_types"].add(dataset_type)

    era = describe_act_era(engagement.financial_year)
    for (counterparty, txn_date), info in groups.items():
        limb_a = info["amount"] >= RECEIPT_THRESHOLD_PAISE  # same-day aggregate
        limb_b = info["max_single"] >= RECEIPT_THRESHOLD_PAISE  # single transaction
        if not (limb_a or limb_b):
            continue

        limb_text = []
        if limb_a:
            limb_text.append(f"same-day aggregate of {paise_to_display(info['amount'])}")
        if limb_b:
            limb_text.append(f"a single transaction of {paise_to_display(info['max_single'])}")
        proxy_note = (
            " (counterparty identified from Description text, an approximate proxy)"
            if "BANK" in info["dataset_types"] else ""
        )
        dedup_note = (
            " More than one data source (among GL/Bank Statement/Sales Register/Accounts Receivable) contributed "
            "to this total, and FinSight cannot reliably detect whether they represent the same underlying "
            "receipt recorded twice — the true amount may be lower than shown; please verify against source "
            "documents." if len(info["dataset_types"]) > 1 else ""
        )

        outcome.exceptions.append(ExceptionDraft(
            label=wording.POTENTIAL_TAX_ISSUE,
            area=TOPIC,
            trigger_condition=(
                f'Cash-mode receipt(s) from "{counterparty}"{proxy_note} on {txn_date} — {" and ".join(limb_text)} '
                f"— at or above the Section 269ST threshold of {paise_to_display(RECEIPT_THRESHOLD_PAISE)}."
            ),
            explanation=(
                f'{era}. Section 269ST restricts a person from receiving ₹2,00,000 or more in cash, whether in '
                f'aggregate from one person in a day, or in a single transaction, or across transactions relating '
                f'to one event/occasion (this third limb is not evaluated by FinSight — see this rule\'s '
                f'Limitation). FinSight identified {" and ".join(limb_text)} from "{counterparty}" on '
                f"{txn_date}.{dedup_note} This does NOT establish that Section 269ST was contravened — receipts "
                f"by Government, banking companies, post office savings banks, co-operative banks, or amounts "
                f"already covered by Section 269SS are excluded, and FinSight cannot evaluate these exceptions "
                f"from the data provided. This is a potential issue for professional review, not a determination "
                f"that a violation occurred."
            ),
            suggested_query=(
                f'Please confirm the mode of receipt from "{counterparty}" on {txn_date}, whether any Section '
                f"269ST exception applies, and whether this receipt is already covered under Section 269SS."
            ),
            risk_level="MEDIUM",
            data_sources=sorted(info["file_ids"]),
            threshold_used={
                "receipt_threshold_paise": RECEIPT_THRESHOLD_PAISE,
                "threshold_is_statutory": True,
                "statutory_source": PROVISION_REFERENCE,
                "same_day_aggregate_paise": info["amount"],
                "max_single_transaction_paise": info["max_single"],
                "limb_a_same_day_aggregate": limb_a,
                "limb_b_single_transaction": limb_b,
                "limb_c_event_occasion_evaluated": False,
                "polarity": "credit_amount only (receipt/inflow side)",
                "cross_source_deduplicated": False,
                "sources_contributing": sorted(info["dataset_types"]),
            },
            amount_paise=max(info["amount"], info["max_single"]),
        ))

    return outcome
