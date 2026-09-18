"""
Reconciliation engine (Module 6 — Python).

Pure deterministic cross-checking logic.
Includes automatic detection of:
- Rate errors (e.g. June wrong fee percentage applied)
- Invoices computed on Total Revenue instead of Operating Revenue
- Counterparty fuzzy similarity matching
"""

import re
import difflib
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime

from extraction import ExtractedDoc

FUZZY_NAME_THRESHOLD = 0.80  # 80% similarity accounts for legal suffix variances
AMOUNT_TOLERANCE = 5.0       # Floating-point tolerance


@dataclass
class InvoiceFinding:
    invoice_filename: str
    severity: str  # "OK", "FLAG", "CRITICAL", "REVIEW"
    check: str
    detail: str


@dataclass
class InvoiceReconciliation:
    invoice: ExtractedDoc
    findings: List[InvoiceFinding] = field(default_factory=list)

    @property
    def status(self) -> str:
        if any(f.severity == "CRITICAL" for f in self.findings):
            return "CRITICAL"
        if any(f.severity == "FLAG" for f in self.findings):
            return "FLAG"
        if any(f.severity == "REVIEW" for f in self.findings):
            return "REVIEW"
        return "OK"


def _name_similarity(a: Optional[str], b: Optional[str]) -> float:
    if not a or not b:
        return 0.0
    norm = lambda s: re.sub(r"[^\w\s]", "", s).strip().lower()
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    for fmt in ("%d %B %Y", "%d %b %Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def _month_key(period_start: Optional[str]) -> Optional[str]:
    dt = _parse_date(period_start)
    return dt.strftime("%B %Y") if dt else None


def reconcile_invoice(invoice: ExtractedDoc, agreement: ExtractedDoc,
                       revenue_table: Dict[str, dict]) -> InvoiceReconciliation:
    result = InvoiceReconciliation(invoice=invoice)
    findings = result.findings

    # 0. Confidence review warnings
    if invoice.low_confidence_fields:
        findings.append(InvoiceFinding(
            invoice.filename, "REVIEW", "Extraction Confidence",
            f"Fields requiring manual verification: {', '.join(invoice.low_confidence_fields)}."
        ))

    # 1. Counterparty matching
    provider_sim = _name_similarity(invoice.provider_name, agreement.provider_name)
    if provider_sim < FUZZY_NAME_THRESHOLD:
        findings.append(InvoiceFinding(
            invoice.filename, "CRITICAL", "Counterparty Name Mismatch",
            f"Invoice provider '{invoice.provider_name}' does not match agreement Service Provider "
            f"'{agreement.provider_name}' (similarity: {provider_sim:.0%})."
        ))
    else:
        findings.append(InvoiceFinding(
            invoice.filename, "OK", "Counterparty Name Match",
            f"Provider name '{invoice.provider_name}' matches agreement (similarity: {provider_sim:.0%})."
        ))

    # 2. Currency check
    if agreement.currency and invoice.currency:
        if invoice.currency.upper() != agreement.currency.upper():
            findings.append(InvoiceFinding(
                invoice.filename, "CRITICAL", "Currency Mismatch",
                f"Invoice is denominated in {invoice.currency}, but agreement requires {agreement.currency}."
            ))
        else:
            findings.append(InvoiceFinding(
                invoice.filename, "OK", "Currency Match",
                f"Invoice currency ({invoice.currency}) matches agreement."
            ))

    # 3. Term check
    period_dt = _parse_date(invoice.period_start)
    term_start = _parse_date(agreement.period_start)
    term_end = _parse_date(agreement.period_end)
    if period_dt and term_start and term_end:
        if not (term_start <= period_dt <= term_end):
            findings.append(InvoiceFinding(
                invoice.filename, "CRITICAL", "Period Outside Agreement Term",
                f"Invoice period ({invoice.period_start}) is outside agreement term "
                f"({agreement.period_start} to {agreement.period_end})."
            ))
        else:
            findings.append(InvoiceFinding(
                invoice.filename, "OK", "Period Within Term",
                "Invoice period falls within effective term."
            ))

    # 4. Fee & Reference Schedule Verification
    month_key = _month_key(invoice.period_start)
    ref_ccy = agreement.currency or invoice.currency or "INR"

    if not month_key or month_key not in revenue_table:
        findings.append(InvoiceFinding(
            invoice.filename, "REVIEW", "No Reference Data",
            f"No Revenue Support Schedule supplied for {month_key or 'unknown month'}."
        ))
        return result

    rev = revenue_table[month_key]
    operating_revenue = rev.get("operating_revenue")
    extraordinary_income = rev.get("extraordinary_income") or 0.0
    total_revenue = rev.get("total_revenue")
    fee_pct = agreement.fee_percentage

    # 4a. Verify Referenced Revenue Base
    if invoice.referenced_revenue is not None and operating_revenue is not None:
        if abs(invoice.referenced_revenue - operating_revenue) > AMOUNT_TOLERANCE:
            if total_revenue is not None and abs(invoice.referenced_revenue - total_revenue) <= AMOUNT_TOLERANCE:
                findings.append(InvoiceFinding(
                    invoice.filename, "CRITICAL", "Fee Base Includes Extraordinary Income",
                    f"Invoice references revenue of {invoice.referenced_revenue:,.0f}, matching Total Revenue "
                    f"(Operating Revenue {operating_revenue:,.0f} + Extraordinary Income {extraordinary_income:,.0f}). "
                    f"Extraordinary income must be excluded per Clause 2."
                ))
            else:
                findings.append(InvoiceFinding(
                    invoice.filename, "FLAG", "Referenced Revenue Mismatch",
                    f"Invoice references revenue of {invoice.referenced_revenue:,.0f}, but Operating Revenue is "
                    f"{operating_revenue:,.0f} per schedule."
                ))

    # 4b. Mathematical Consistency & Diagnosis
    if fee_pct is not None and operating_revenue is not None and invoice.amount is not None:
        expected_fee = operating_revenue * (fee_pct / 100.0)
        diff = invoice.amount - expected_fee

        if abs(diff) <= AMOUNT_TOLERANCE:
            findings.append(InvoiceFinding(
                invoice.filename, "OK", "Fee Amount Match",
                f"Invoiced amount matches {fee_pct:.1f}% of {month_key} Operating Revenue ({ref_ccy} {expected_fee:,.0f})."
            ))
        else:
            # Check 1: Fee computed on Total Revenue base
            matches_total_basis = False
            if total_revenue is not None and extraordinary_income > 0:
                expected_fee_total = total_revenue * (fee_pct / 100.0)
                if abs(invoice.amount - expected_fee_total) <= AMOUNT_TOLERANCE:
                    matches_total_basis = True
                    overcharge = expected_fee_total - expected_fee
                    findings.append(InvoiceFinding(
                        invoice.filename, "CRITICAL", "Fee Computed on Total Revenue",
                        f"Invoiced amount ({ref_ccy} {invoice.amount:,.0f}) equals {fee_pct:.1f}% of Total Revenue "
                        f"({ref_ccy} {total_revenue:,.0f}). Includes extraordinary income of {ref_ccy} {extraordinary_income:,.0f}, "
                        f"causing an overcharge of {ref_ccy} {overcharge:,.0f}."
                    ))

            # Check 2: Fee rate error diagnosis (e.g. wrong % applied in June)
            if not matches_total_basis:
                implied_rate = (invoice.amount / operating_revenue) * 100.0 if operating_revenue > 0 else 0.0
                rate_str = f"{round(implied_rate)}%" if abs(implied_rate - round(implied_rate)) < 0.05 else f"{implied_rate:.2f}%"

                if abs(implied_rate - fee_pct) > 0.05:
                    findings.append(InvoiceFinding(
                        invoice.filename, "CRITICAL", "Incorrect Fee Percentage Applied",
                        f"Invoiced amount ({ref_ccy} {invoice.amount:,.0f}) reflects an effective rate of {rate_str} "
                        f"on Operating Revenue ({ref_ccy} {operating_revenue:,.0f}), instead of agreed rate of {fee_pct:.1f}%. "
                        f"Difference: {ref_ccy} {diff:,.0f} ({'overbilled' if diff > 0 else 'underbilled'})."
                    ))
                else:
                    findings.append(InvoiceFinding(
                        invoice.filename, "CRITICAL", "Fee Amount Mismatch",
                        f"Invoiced amount ({ref_ccy} {invoice.amount:,.0f}) does not match expected {fee_pct:.1f}% "
                        f"fee ({ref_ccy} {expected_fee:,.0f}). Difference: {ref_ccy} {diff:,.0f}."
                    ))

    return result


def reconcile_all(agreement: ExtractedDoc, invoices: List[ExtractedDoc],
                   revenue_schedule_docs: List[ExtractedDoc]) -> List[InvoiceReconciliation]:
    from extraction import build_operating_revenue_table
    revenue_table = build_operating_revenue_table(revenue_schedule_docs)
    return [reconcile_invoice(inv, agreement, revenue_table) for inv in invoices]