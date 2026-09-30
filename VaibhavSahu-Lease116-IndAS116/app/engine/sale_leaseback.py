"""Sale and leaseback (Ind AS 116.98–103, 102A).

Step 1 — Is the transfer a sale? Determined under Ind AS 115 (control transfer).
         This is an assessment input (checklist + conclusion), never inferred.
Step 2 — If a sale (para 100):
         * off-market adjustments (101–102): consideration above fair value is additional
           financing; below fair value is a prepayment of lease payments;
         * ROU asset = carrying amount x (PV of leaseback payments attributable to the
           lease [+ prepayment]) / fair value;
         * gain/loss recognised only for the rights transferred to the buyer-lessor.
         Subsequent measurement follows para 102A (no gain/loss on the right of use
         retained) — policy for variable payments is flagged for judgment.
Step 3 — If not a sale (para 103): seller-lessee keeps the asset and recognises a
         financial liability (Ind AS 109) equal to the transfer proceeds.

Benchmarked in the test-suite to IFRS 16 Illustrative Example 24 (seller-lessee:
ROU 699,555; gain on rights transferred 240,355; financial liability 1,459,200).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from .decimal_utils import D, ZERO, engine_context, q
from .models import JudgmentFlag, PaymentLine, Policy, Posting
from .rates import Discounter, TimeBasis, effective_annual_rate, present_value
from .references import ref


@dataclass
class SaleLeasebackInput:
    transaction_id: str
    date: date
    asset_description: str
    carrying_amount: Decimal
    sale_consideration: Decimal
    fair_value: Decimal
    leaseback_payments: list[PaymentLine]
    discount_rate_pct: Decimal
    is_sale_ind_as_115: Optional[bool] = None      # assessment conclusion (required)
    sale_assessment_notes: str = ""
    control_indicators: dict = field(default_factory=dict)
    policy: Policy = field(default_factory=Policy)


@dataclass
class SaleLeasebackResult:
    is_sale: bool
    steps: list[tuple[str, Decimal, str]]
    rou_asset: Decimal
    financial_liability_total: Decimal
    lease_liability_portion: Decimal
    additional_financing: Decimal
    prepayment: Decimal
    gain_total: Decimal
    gain_rights_transferred: Decimal
    gain_rights_retained_not_recognised: Decimal
    postings: list[Posting]
    flags: list[JudgmentFlag]
    buyer_lessor: dict


@engine_context
def calculate_sale_leaseback(inp: SaleLeasebackInput) -> SaleLeasebackResult:
    if inp.is_sale_ind_as_115 is None:
        raise ValueError("Ind AS 115 sale assessment conclusion is required before accounting for a sale and leaseback (para 99).")
    dp = inp.policy.currency_decimals
    d = inp.date
    CA, SC, FV = D(inp.carrying_amount), D(inp.sale_consideration), D(inp.fair_value)
    disc = Discounter(effective_annual_rate(inp.discount_rate_pct, inp.policy.rate_convention), TimeBasis(d, inp.policy.daycount))
    pv = present_value([(p.date, D(p.lease_amount)) for p in inp.leaseback_payments], disc, d)
    pv_r = q(pv, dp)
    flags = [JudgmentFlag("SLB", "Sale and leaseback — reviewer attention",
                          "Ind AS 115 sale assessment, fair value, off-market terms and para 102A policy require review.",
                          ref("SLB"), assumptions=[inp.sale_assessment_notes or "Sale assessment notes not documented"])]
    if not inp.is_sale_ind_as_115:
        postings = [Posting(d, "SLB_FAILED_SALE", "Transfer is not a sale — asset retained; proceeds recognised as financial liability "
                                                  "(Ind AS 116.103(a); Ind AS 109)",
                            [("BANK", q(SC, dp), ZERO), ("SLB_FINANCIAL_LIABILITY", ZERO, q(SC, dp))])]
        steps = [("Transfer is not a sale under Ind AS 115", ZERO, "para 103"),
                 ("Financial liability = transfer proceeds", q(SC, dp), "Ind AS 109")]
        return SaleLeasebackResult(False, steps, ZERO, q(SC, dp), ZERO, ZERO, ZERO, ZERO, ZERO, ZERO, postings, flags,
                                   {"note": "Buyer-lessor recognises a financial asset equal to the transfer proceeds (para 103(b))."})
    additional_financing = SC - FV if SC > FV else ZERO
    prepayment = FV - SC if SC < FV else ZERO
    lease_pv = pv - additional_financing
    retained_ratio = (lease_pv + prepayment) / FV
    rou = CA * retained_ratio
    gain_total = FV - CA
    gain_retained = gain_total * retained_ratio
    gain_transferred = gain_total - gain_retained
    rou_r = q(rou, dp)
    # journal (balanced by construction: gain line is the balancing figure)
    # The leaseback liability is measured by the lessee engine at the PV of the leaseback payments; it is credited to the
    # lease-liability account so that subsequent interest and payment postings run through the same ledger account.
    lines = [("BANK", q(SC, dp), ZERO), ("ROU_ASSET", rou_r, ZERO), ("ASSET_SOLD", ZERO, q(CA, dp)),
             ("LEASE_LIABILITY", ZERO, pv_r)]
    bal = sum(l[1] for l in lines) - sum(l[2] for l in lines)
    gain_je = bal
    lines.append(("GAIN_SLB_RIGHTS_TRANSFERRED", ZERO, bal) if bal >= 0 else ("GAIN_SLB_RIGHTS_TRANSFERRED", -bal, ZERO))
    postings = [Posting(d, "SLB_COMMENCEMENT", "Sale and leaseback — derecognise asset, recognise ROU retained and gain on rights "
                                                "transferred (Ind AS 116.100)", lines)]
    steps = [
        ("Carrying amount of asset", q(CA, dp), ""),
        ("Sale consideration", q(SC, dp), ""),
        ("Fair value of asset", q(FV, dp), ""),
        ("Additional financing (consideration above fair value)", q(additional_financing, dp), "para 101(b)"),
        ("Prepayment of lease payments (consideration below fair value)", q(prepayment, dp), "para 101(a)"),
        ("PV of leaseback payments", pv_r, f"at {inp.discount_rate_pct}% p.a."),
        ("PV attributable to the lease", q(lease_pv, dp), "PV − additional financing"),
        ("Right of use retained (proportion)", q(retained_ratio, 6), "(lease PV + prepayment) ÷ fair value"),
        ("ROU asset = carrying amount × proportion retained", rou_r, "para 100(a)"),
        ("Total gain on sale (fair value − carrying amount)", q(gain_total, dp), ""),
        ("Gain relating to right of use retained (not recognised)", q(gain_retained, dp), "para 100(a)"),
        ("Gain on rights transferred to buyer-lessor (recognised)", q(gain_transferred, dp), "para 100(a)"),
        ("Gain per journal (balancing, after rounding)", q(gain_je, dp), ""),
    ]
    if additional_financing > 0:
        flags.append(JudgmentFlag("SLB_ADDITIONAL_FINANCING", "Additional financing within the leaseback liability",
                                  f"Consideration exceeds fair value by {q(additional_financing, dp)}. That portion is additional "
                                  "financing provided by the buyer-lessor and is a financial liability under Ind AS 109 (para 101(b)); "
                                  "it is included in the lease-liability ledger account here — reclassify for presentation and "
                                  "disclosure.", ref("SLB")))
    flags.append(JudgmentFlag("SLB_102A", "Subsequent measurement — para 102A",
                              "Determine 'lease payments' / 'revised lease payments' so that no gain or loss is recognised on the "
                              "right of use retained. Document the policy for variable payments.", ref("SLB_102A")))
    buyer = {"asset_recognised_at": q(FV, dp), "financial_asset_additional_financing": q(additional_financing, dp),
             "note": "Buyer-lessor accounts for the purchase applying applicable standards and the leaseback applying lessor "
                     "requirements; above-market consideration is a financial asset (Ind AS 109)."}
    return SaleLeasebackResult(True, steps, rou_r, pv_r, q(lease_pv, dp), q(additional_financing, dp), q(prepayment, dp),
                               q(gain_total, dp), q(gain_transferred, dp), q(gain_retained, dp), postings, flags, buyer)
