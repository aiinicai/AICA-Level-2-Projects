"""
clock45.engine
==============
Ties classification and rules together into an immutable, reproducible run.

A `ComputationRun` records the rule pack version, the statute applied, the
acceptance-date policy and the operator. Re-running it next year must
reproduce the number that went into a signed audit report — that requirement
is why nothing here reads a "current" value from anywhere.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from .classify import UdyamRecord, assess_coverage, Coverage, exclusion_summary
from .rules import (
    RULE_PACK_VERSION, statute_for, fy_bounds, assess_invoice, Verdict,
    bank_rate_on, msmed_rate_on, DISALLOWED, ALLOWED_LATE_INTEREST_ONLY,
)

# Acceptance-date policies. There is no acceptance date in any Indian ledger,
# so we do not invent one — the user picks a policy and it is PRINTED in the
# working paper for the partner to sign.
ACC_INVOICE_DATE = "INVOICE_DATE"
ACC_GRN_DATE = "GRN_DATE"
ACC_INVOICE_PLUS = "INVOICE_DATE_PLUS_N"

ACC_POLICY_TEXT = {
    ACC_INVOICE_DATE:
        "Date of acceptance has been taken as the invoice date. This is the "
        "conservative basis and may overstate exposure where goods were "
        "accepted later. Discussed with management.",
    ACC_GRN_DATE:
        "Date of acceptance has been taken as the goods receipt note date "
        "where available, and the invoice date otherwise. Discussed with "
        "management.",
    ACC_INVOICE_PLUS:
        "Date of acceptance has been taken as the invoice date plus an agreed "
        "inspection period. The period is a management representation and has "
        "not been independently verified.",
}


@dataclass
class PurchaseLine:
    invoice_id: str
    vendor_id: str
    vendor_name_as_written: str
    invoice_date: date
    amount: Decimal
    grn_date: Optional[date] = None
    agreement_days: Optional[int] = None


@dataclass
class PaymentLine:
    invoice_id: str
    payment_date: date
    amount: Decimal


@dataclass
class Finding:
    invoice_id: str
    vendor_id: str
    vendor_name: str
    invoice_date: date
    acceptance_date: date
    amount: Decimal
    status: str
    reason: str
    gate_failed: Optional[str]
    disallowance: Decimal
    interest: Decimal
    due_date: Optional[date]
    appointed_day: Optional[date]
    evidence_strength: int
    # For EXCLUDED lines: what WOULD have been disallowed had the gate not
    # applied. This is the number that matters on the Exclusion Register --
    # gross turnover with a trader is irrelevant; the amount another tool
    # would have wrongly added back is the whole point.
    counterfactual_disallowance: Decimal = Decimal("0.00")


@dataclass
class ComputationRun:
    entity_name: str
    fy: str
    operator: str
    acceptance_policy: str
    run_at: datetime = field(default_factory=datetime.now)
    rule_pack_version: str = RULE_PACK_VERSION
    findings: list[Finding] = field(default_factory=list)
    control_totals: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def statute(self) -> dict:
        return statute_for(self.fy)

    @property
    def disallowance_total(self) -> Decimal:
        return sum((f.disallowance for f in self.findings), Decimal("0"))

    @property
    def interest_total(self) -> Decimal:
        return sum((f.interest for f in self.findings), Decimal("0"))

    @property
    def excluded_total(self) -> Decimal:
        """Amount a tool without the coverage gates would have wrongly
        disallowed. This is the Exclusion Register headline."""
        return sum(
            (f.counterfactual_disallowance for f in self.findings if f.gate_failed),
            Decimal("0"),
        )

    def run_hash(self) -> str:
        payload = {
            "entity": self.entity_name, "fy": self.fy,
            "rule_pack": self.rule_pack_version,
            "policy": self.acceptance_policy,
            "disallowance": str(self.disallowance_total),
            "interest": str(self.interest_total),
            "lines": len(self.findings),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()[:16]


def _acceptance_date(line: PurchaseLine, policy: str, plus_days: int = 0) -> date:
    from .rules import days_add

    if policy == ACC_GRN_DATE and line.grn_date:
        return line.grn_date
    if policy == ACC_INVOICE_PLUS:
        return days_add(line.invoice_date, plus_days)
    return line.invoice_date


def run_assessment(
    *,
    entity_name: str,
    fy: str,
    operator: str,
    purchases: list[PurchaseLine],
    payments: list[PaymentLine],
    udyam: dict[str, UdyamRecord],
    acceptance_policy: str = ACC_INVOICE_DATE,
    acceptance_plus_days: int = 0,
) -> ComputationRun:
    fy_start, fy_end = fy_bounds(fy)
    run = ComputationRun(entity_name, fy, operator, acceptance_policy)

    by_invoice: dict[str, list[tuple[date, Decimal]]] = {}
    for p in payments:
        by_invoice.setdefault(p.invoice_id, []).append((p.payment_date, p.amount))

    source_total = sum((line.amount for line in purchases), Decimal("0"))
    out_of_period = [
        line for line in purchases if not (fy_start <= line.invoice_date <= fy_end)
    ]
    out_of_period_total = sum((line.amount for line in out_of_period), Decimal("0"))
    ledger_total = Decimal("0")
    unconfirmed_vendors: set[str] = set()
    coverages: list[Coverage] = []

    for line in purchases:
        if not (fy_start <= line.invoice_date <= fy_end):
            continue
        ledger_total += line.amount

        acc_date = _acceptance_date(line, acceptance_policy, acceptance_plus_days)
        rec = udyam.get(line.vendor_id) or UdyamRecord(vendor_id=line.vendor_id)
        cov = assess_coverage(rec, acc_date)
        coverages.append(cov)
        if cov.needs_human_confirmation:
            unconfirmed_vendors.add(line.vendor_id)

        if not cov.covered:
            counterfactual = assess_invoice(
                amount=line.amount, acceptance_date=acc_date,
                agreement_days=line.agreement_days,
                payments=by_invoice.get(line.invoice_id, []), fy=fy,
            )
            run.findings.append(Finding(
                line.invoice_id, line.vendor_id, line.vendor_name_as_written,
                line.invoice_date, acc_date, line.amount,
                "EXCLUDED", cov.reason, cov.gate_failed,
                Decimal("0.00"), Decimal("0.00"), None, None,
                cov.evidence_strength,
                counterfactual_disallowance=counterfactual.disallowance,
            ))
            continue

        v: Verdict = assess_invoice(
            amount=line.amount,
            acceptance_date=acc_date,
            agreement_days=line.agreement_days,
            payments=by_invoice.get(line.invoice_id, []),
            fy=fy,
        )
        run.findings.append(Finding(
            line.invoice_id, line.vendor_id, line.vendor_name_as_written,
            line.invoice_date, acc_date, line.amount,
            v.status, v.reason, None, v.disallowance, v.interest,
            v.due_date, v.appointed_day, cov.evidence_strength,
        ))

    accounted = sum((f.amount for f in run.findings), Decimal("0"))
    run.control_totals = {
        "source_purchase_lines": len(purchases),
        "source_purchase_value": source_total,
        "ledger_lines_in_year": len(run.findings),
        "ledger_value": ledger_total,
        "out_of_period_lines": len(out_of_period),
        "out_of_period_value": out_of_period_total,
        "value_accounted_for": accounted,
        "scope_reconciles": source_total == ledger_total + out_of_period_total,
        "ties": (
            ledger_total == accounted
            and source_total == ledger_total + out_of_period_total
        ),
        "bank_rate_at_year_end_pct": bank_rate_on(fy_end),
        "msmed_rate_at_year_end_pct": msmed_rate_on(fy_end),
        "exclusions_by_gate": exclusion_summary(coverages),
    }

    if not run.control_totals["ties"]:
        run.warnings.append(
            "CONTROL TOTALS DO NOT TIE. Refusing to certify this run."
        )
    if out_of_period:
        run.warnings.append(
            f"{len(out_of_period)} purchase line(s) totalling {out_of_period_total} "
            f"fall outside FY {fy} and were excluded from the statutory computation."
        )
    if unconfirmed_vendors:
        run.warnings.append(
            f"{len(unconfirmed_vendors)} vendor(s) classified on weak or no "
            f"evidence. Confirm before sign-off — these must not enter a "
            f"signed audit report unconfirmed."
        )
    return run


def action_list(run: ComputationRun, top_n: int = 25) -> list[dict]:
    """
    The 31 March Action List, ranked by money saved. This is the output that
    turns a September audit observation into a January prevention.
    """
    agg: dict[str, dict] = {}
    for f in run.findings:
        if f.status != DISALLOWED:
            continue
        a = agg.setdefault(f.vendor_id, {
            "vendor": f.vendor_name, "invoices": 0,
            "pay_now": Decimal("0"), "disallowance_saved": Decimal("0"),
            "interest_exposure": Decimal("0"), "earliest_due": f.due_date,
        })
        a["invoices"] += 1
        a["pay_now"] += f.disallowance
        a["disallowance_saved"] += f.disallowance
        a["interest_exposure"] += f.interest
        if f.due_date and (a["earliest_due"] is None or f.due_date < a["earliest_due"]):
            a["earliest_due"] = f.due_date

    rows = sorted(agg.values(), key=lambda r: -r["pay_now"])
    return rows[:top_n]


def exclusion_register(run: ComputationRun) -> list[dict]:
    """Vendors NOT disallowed, with the gate that failed. The credibility slide."""
    agg: dict[str, dict] = {}
    for f in run.findings:
        if not f.gate_failed:
            continue
        a = agg.setdefault(f.vendor_id, {
            "vendor": f.vendor_name, "gate": f.gate_failed,
            "reason": f.reason, "invoices": 0,
            "turnover": Decimal("0"), "wrongly_disallowable": Decimal("0"),
            "evidence_strength": f.evidence_strength,
        })
        a["invoices"] += 1
        a["turnover"] += f.amount
        a["wrongly_disallowable"] += f.counterfactual_disallowance
    return sorted(agg.values(), key=lambda r: -r["wrongly_disallowable"])


def interest_only_register(run: ComputationRun) -> list[dict]:
    """Paid late but within the year: no disallowance, but s.16 interest bites.
    Almost every competing tool misses this entirely."""
    agg: dict[str, dict] = {}
    for f in run.findings:
        if f.status != ALLOWED_LATE_INTEREST_ONLY:
            continue
        a = agg.setdefault(f.vendor_id, {
            "vendor": f.vendor_name, "invoices": 0,
            "value": Decimal("0"), "interest": Decimal("0"),
        })
        a["invoices"] += 1
        a["value"] += f.amount
        a["interest"] += f.interest
    return sorted(agg.values(), key=lambda r: -r["interest"])
