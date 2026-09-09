"""
TAX-MSME-013 — MSME Delayed-Payment Review Screen.

Legal provision: Section 43B, clause (h) (some sources currently label
it (g) after a 43B renumbering; the labeling ambiguity does not affect
the substance), Income-tax Act, 1961 — inserted by the Finance Act,
2023, effective FY 2023-24 (AY 2024-25) onward. Disallows any sum
payable to a Micro or Small enterprise (registered under Section 7(1)
of the MSMED Act, 2006 — Medium enterprises are explicitly EXCLUDED)
for goods/services, unless paid within the time limit under Section 15
of the MSMED Act, 2006 (the period agreed in writing, capped at 45
days, or 15 days if no written agreement). Unpaid-in-time amounts are
disallowed in the year of accrual and allowed only in the year of
actual payment — the general Section 43B "paid before return due date"
grace period does NOT apply to this clause.

Verification: VERIFIED (old Act, 1961) — primary source: Section 43B,
incometaxindia.gov.in, full text fetched directly, including this
clause (see documentation/stage10_tax_rule_catalogue_proposal.md,
TAX-MSME-013). New Act 2025 forward reference (UNVERIFIED, non-gating):
reported as Section 37(2)(g) by a single secondary source, not
cross-checked; never used to decide executability.

FinSight Analytical Test — a FinSight-designed heuristic screen for
Section 43B(h), not itself a figure the Act specifies (the 45-DAY CAP
is the Act's own, via MSMED Act Section 15; FinSight's role is only to
approximate elapsed days from Accounts Payable data): computes, per AP
counterparty, the net outstanding balance as of financial year end and
the days elapsed since that party's last recorded movement — the same
ageing-approximation pattern AUD-LOB-012 already established — and
flags counterparties whose outstanding balance has aged beyond 45 days.

CRITICAL wording requirement (Stage 10, Decision 4 — approved): this
rule's finding NEVER states that a tax disallowance exists merely
because a payment exceeded 45 days. FinSight has no field anywhere
recording a supplier's MSME (Micro/Small) registration status (Decision
5 — no new field added this stage) — the vast majority of AP
counterparties aged beyond 45 days will NOT be MSME-registered at all,
so an aged balance is only ever the first of two conditions Section
43B(h) actually requires. Every finding uses the label "Potential MSME
Payment Review" and explicitly asks the reviewer to confirm (a) MSME
Micro/Small registration and (b) the actual agreed payment terms,
before any disallowance conclusion is possible.

Limitation: (1) no MSME-registration data exists in FinSight — this is
a candidate list of aged AP balances, not a list of confirmed MSME
dues. (2) Ageing is approximated as "days since the party's last
recorded movement" (no invoice-date/due-date field exists in the
approved schema — the same limitation AUD-LOB-012 already discloses for
its own ageing), not true per-invoice ageing against the actual agreed
MSMED Act Section 15 payment term, which may be shorter than 45 days if
agreed in writing.

Insufficient data: no validated Accounts Payable data at all for this
engagement, or the engagement's financial year cannot be parsed.
"""
from __future__ import annotations

from datetime import date

from app.rules import wording
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.rules.period_utils import financial_year_bounds
from app.rules.tax.act_transition import describe_act_era
from app.utils.currency import paise_to_display

RULE_ID = "TAX-MSME-013"
TOPIC = "MSME Delayed-Payment Review Screen"
PROVISION_REFERENCE = "Section 43B(h), Income-tax Act, 1961, read with Section 15, MSMED Act, 2006"

MSME_PAYMENT_WINDOW_DAYS = 45  # the Act's own cap (via MSMED Act Section 15), not FinSight's
MINIMUM_OUTSTANDING_PAISE = 100_000  # ~₹1,000 — a FinSight noise floor, not a statutory figure


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    ap_rows = dataset.get("AP", [])
    if not ap_rows:
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Accounts Payable data is available for this engagement."
        )
        return outcome

    bounds = financial_year_bounds(engagement.financial_year)
    if bounds is None:
        outcome.insufficient_data_reason = (
            f"The engagement's financial year (\"{engagement.financial_year}\") could not be parsed into "
            f"calendar bounds."
        )
        return outcome
    _fy_start, fy_end = bounds

    # party_name -> {balance, last_date, file_ids} — same aggregation shape as
    # AUD-LOB-012's ageing detector (a disclosed, deliberate reuse of that pattern,
    # not shared_detectors code, since AP-only single-ledger polarity needs no
    # AR/AP dual-polarity handling AUD-LOB-012's own helper carries).
    parties: dict[str, dict] = {}
    for row in ap_rows:
        v = row.values
        party_name = (v.get("party_name") or "").strip()
        raw_date = v.get("transaction_date")
        if not party_name or not raw_date:
            outcome.partial_insufficient_data_notes.append(
                f"AP row (file {row.file_id}, row {row.row_index + 1}): no Party Name or no Transaction Date — "
                f"could not be included in the MSME ageing computation."
            )
            continue
        try:
            txn_date = date.fromisoformat(raw_date)
        except ValueError:
            outcome.partial_insufficient_data_notes.append(
                f"AP row (file {row.file_id}, row {row.row_index + 1}): Transaction Date could not be parsed."
            )
            continue
        if txn_date > fy_end:
            continue

        credit = v.get("credit_amount") or 0
        debit = v.get("debit_amount") or 0
        entry = parties.setdefault(party_name, {"balance": 0, "last_date": None, "file_ids": set()})
        entry["balance"] += credit - debit  # AP polarity: credit increases payable, debit (payment) reduces it
        entry["file_ids"].add(str(row.file_id))
        if entry["last_date"] is None or txn_date > entry["last_date"]:
            entry["last_date"] = txn_date

    outcome.evaluated_count = len(parties)
    era = describe_act_era(engagement.financial_year)

    for party_name, entry in parties.items():
        balance = entry["balance"]
        last_date = entry["last_date"]
        if balance <= 0 or last_date is None or balance < MINIMUM_OUTSTANDING_PAISE:
            continue

        ageing_days = (fy_end - last_date).days
        if ageing_days < MSME_PAYMENT_WINDOW_DAYS:
            continue

        outcome.exceptions.append(ExceptionDraft(
            label=wording.POTENTIAL_MSME_PAYMENT_REVIEW,
            area=TOPIC,
            trigger_condition=(
                f'Net payable to "{party_name}" of {paise_to_display(balance)} has no recorded movement for '
                f"{ageing_days} day(s) as of financial year end ({fy_end.isoformat()})."
            ),
            explanation=(
                f'{era}. Section 43B(h) disallows a sum payable to a Micro or Small enterprise (not Medium) '
                f'unless paid within the MSMED Act Section 15 time limit (agreed terms, capped at 45 days). '
                f'FinSight identified a net payable to "{party_name}" of {paise_to_display(balance)}, with no '
                f"recorded movement for {ageing_days} day(s) — an ageing approximation (days since last recorded "
                f"movement, not true per-invoice ageing against an actual agreed term; no due-date field exists "
                f"in FinSight's schema). FinSight has NO record of whether \"{party_name}\" is registered as a "
                f"Micro or Small enterprise — most aged payables will NOT be MSME suppliers at all. This finding "
                f"does NOT state that a Section 43B(h) disallowance exists — it flags this balance for the "
                f"reviewer to confirm MSME registration and the actual agreed payment terms before any "
                f"disallowance conclusion is possible."
            ),
            suggested_query=(
                f'Please confirm whether "{party_name}" is registered as a Micro or Small Enterprise under the '
                f"MSMED Act, 2006, the agreed payment term (in writing, if any), and the actual payment date for "
                f"this outstanding balance."
            ),
            risk_level="MEDIUM",
            data_sources=sorted(entry["file_ids"]),
            threshold_used={
                "msme_payment_window_days": MSME_PAYMENT_WINDOW_DAYS,
                "threshold_is_statutory": True,
                "statutory_source": PROVISION_REFERENCE,
                "minimum_outstanding_paise": MINIMUM_OUTSTANDING_PAISE,
                "ageing_days": ageing_days,
                "ageing_is_approximated_not_per_invoice": True,
                "msme_registration_status_known": False,
                "candidate_only_not_a_disallowance": True,
            },
            amount_paise=balance,
        ))

    return outcome
