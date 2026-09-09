"""
TAX-GST-009 — GST Invoice Reconciliation.

Legal provision: none — this is a data-reconciliation check (matching
the same invoice across Sales Register / Purchase Register / GST
dataset by `invoice_number`), not a legal test. Carried forward
unchanged in substance from the original v0.2 Tax Rule Verification
Register, where it was already classified VERIFIED for exactly this
reason ("logic-only rule; no statutory citation to verify").

Stage 10 research context (see documentation/stage10_tax_rule_
catalogue_proposal.md, TAX-GST-009): no Income-tax Act provision (old
or new) statutorily mandates reconciling GST turnover against
income-tax turnover — a 2020 government clarification stated GST
turnover shown in Form 26AS is "for information only." This
reconciliation is standard professional practice, not a codified
compliance requirement — its value is audit-quality/risk-based.

FinSight Analytical Test: for each `invoice_number` appearing in more
than one of the Sales Register / Purchase Register / GST source
datasets, compares the recorded taxable value and total tax (CGST +
SGST + IGST) across those sources; flags a mismatch beyond a small
FinSight-configurable tolerance. The tolerance itself is FinSight's
own, not a statutory figure (there being no statute to set one).

Limitation: purely an internal consistency check of data already in
FinSight — it does not verify actual GST return filing, correctness of
the filed return, or reconciliation with the GSTN portal. It also does
not flag an invoice_number present in only one source as an error by
itself (e.g. many Purchase Register lines legitimately have no GST
counterpart if the vendor is unregistered) — only genuine value
mismatches on a shared invoice_number are flagged.

Insufficient data: no validated Sales Register, Purchase Register, or
GST data at all for this engagement, or no invoice_number appears in
more than one of those sources.
"""
from __future__ import annotations

from collections import defaultdict

from app.rules import wording
from app.rules.base_rule import ExceptionDraft, RuleOutcome
from app.rules.tax.act_transition import describe_act_era
from app.utils.currency import paise_to_display

RULE_ID = "TAX-GST-009"
TOPIC = "GST Invoice Reconciliation"

RECONCILIATION_TOLERANCE_PAISE = 100  # ~₹1 — FinSight's own, no statutory basis
_SOURCE_TYPES = ("SALES", "PURCHASE", "GST")


def _row_taxable_and_tax(row) -> tuple[int, int]:
    v = row.values
    taxable = v.get("taxable_value_paise") or 0
    tax = (v.get("cgst_paise") or 0) + (v.get("sgst_paise") or 0) + (v.get("igst_paise") or 0)
    return taxable, tax


def evaluate(engagement, dataset: dict[str, list]) -> RuleOutcome:
    outcome = RuleOutcome(rule_id=RULE_ID)

    rows_by_type = {dt: dataset.get(dt, []) for dt in _SOURCE_TYPES}
    if not any(rows_by_type.values()):
        outcome.insufficient_data_reason = (
            "No validated, confirmed-mapped Sales Register, Purchase Register, or GST Data is available for this "
            "engagement."
        )
        return outcome

    # invoice_number -> [(dataset_type, row), ...]
    by_invoice: dict[str, list] = defaultdict(list)
    for dataset_type, rows in rows_by_type.items():
        for row in rows:
            invoice_number = (row.values.get("invoice_number") or "").strip()
            if invoice_number:
                by_invoice[invoice_number].append((dataset_type, row))

    multi_source = {inv: entries for inv, entries in by_invoice.items() if len({dt for dt, _ in entries}) > 1}
    outcome.evaluated_count = len(multi_source)
    if not multi_source:
        outcome.insufficient_data_reason = (
            "No invoice_number appears in more than one of the Sales Register / Purchase Register / GST sources "
            "for this engagement — reconciliation requires the same invoice recorded in at least two of them."
        )
        return outcome

    era = describe_act_era(engagement.financial_year)
    for invoice_number, entries in multi_source.items():
        values = [(dt, row, *_row_taxable_and_tax(row)) for dt, row in entries]
        taxable_values = {taxable for _dt, _row, taxable, _tax in values}
        tax_values = {tax for _dt, _row, _taxable, tax in values}
        taxable_mismatch = max(taxable_values) - min(taxable_values) > RECONCILIATION_TOLERANCE_PAISE
        tax_mismatch = max(tax_values) - min(tax_values) > RECONCILIATION_TOLERANCE_PAISE
        if not (taxable_mismatch or tax_mismatch):
            continue

        detail = "; ".join(
            f"{dt} (file {row.file_id}): taxable {paise_to_display(taxable)}, tax {paise_to_display(tax)}"
            for dt, row, taxable, tax in values
        )
        outcome.exceptions.append(ExceptionDraft(
            label=wording.TAX_REVIEW_REQUIRED,
            area=TOPIC,
            trigger_condition=(
                f'Invoice "{invoice_number}" has mismatched figures across its sources: {detail}.'
            ),
            explanation=(
                f'{era}. FinSight reconciles the same invoice across Sales Register, Purchase Register, and GST '
                f'data as a data-quality/audit-risk check (not a statutory requirement — see this rule\'s '
                f'Limitation). Invoice "{invoice_number}" shows different taxable value and/or tax figures across '
                f"its sources: {detail}. This does NOT establish that the GST return was incorrectly filed — the "
                f"discrepancy may be a data entry difference between registers. This is a potential issue for "
                f"review, not a confirmed filing error."
            ),
            suggested_query=(
                f'Please explain the discrepancy between the Sales/Purchase register and GST figures for invoice '
                f'"{invoice_number}", and confirm which figure is correct.'
            ),
            risk_level="LOW",
            data_sources=sorted({str(row.file_id) for _dt, row, _t, _x in values}),
            threshold_used={
                "reconciliation_tolerance_paise": RECONCILIATION_TOLERANCE_PAISE,
                "threshold_is_statutory": False,
                "statutory_source": None,
                "taxable_value_mismatch": taxable_mismatch,
                "tax_amount_mismatch": tax_mismatch,
            },
            amount_paise=max(taxable_values) - min(taxable_values) if taxable_mismatch else None,
        ))

    return outcome
