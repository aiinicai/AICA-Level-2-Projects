"""Subleases — intermediate lessor accounting (Ind AS 116.B58, 68).

The sublease is classified by reference to the right-of-use asset arising from the
head lease, not by reference to the underlying asset. If the head lease is a
short-term lease accounted for under para 6, the sublease is an operating lease.

Finance sublease: derecognise the ROU asset (portion transferred), recognise the net
investment in the sublease, recognise any difference in profit or loss and retain
the head-lease liability. Operating sublease: retain the ROU asset and recognise
sublease income on a straight-line basis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from .calendar_utils import months_between_frac, next_day
from .decimal_utils import D, ONE, ZERO, engine_context, q
from .lessor import LessorLeaseInput, calculate_lessor
from .models import JudgmentFlag, PaymentLine, Policy, Posting
from .rates import Discounter, TimeBasis, effective_annual_rate, present_value
from .references import ref


@dataclass
class SubleaseInput:
    sublease_id: str
    head_lease_id: str
    commencement: date
    term_end: date
    payments: list[PaymentLine]
    head_rou_carrying_amount: Decimal          # NBV of head-lease ROU at sublease commencement (portion subleased)
    head_lease_term_end: date                   # remaining head-lease term
    head_lease_discount_rate_pct: Decimal       # para 68: may be used if sublease implicit rate not determinable
    portion_subleased: Decimal = ONE            # fraction of the head-lease ROU subleased (e.g. area)
    head_lease_short_term: bool = False         # B58(a)
    implicit_rate_pct: Optional[Decimal] = None
    classification_override: Optional[str] = None
    override_rationale: str = ""
    policy: Policy = field(default_factory=Policy)


@dataclass
class SubleaseResult:
    classification: str
    explanation: list[str]
    rate_pct: Decimal
    net_investment: Decimal
    rou_derecognised: Decimal
    gain_loss: Decimal
    rows: list[dict]
    postings: list[Posting]
    flags: list[JudgmentFlag]
    term_ratio_pct: Decimal
    pv_ratio_pct: Optional[Decimal]
    lessor: Optional[object] = None          # underlying lessor-engine result (rows, segments, rate basis)


@engine_context
def calculate_sublease(inp: SubleaseInput) -> SubleaseResult:
    c = inp.commencement
    expl = []
    dp = inp.policy.currency_decimals
    rate = D(inp.implicit_rate_pct) if inp.implicit_rate_pct is not None else D(inp.head_lease_discount_rate_pct)
    if inp.implicit_rate_pct is None:
        expl.append(f"Sublease implicit rate not readily determinable — head-lease discount rate {rate}% used (Ind AS 116.68).")
    disc = Discounter(effective_annual_rate(rate, inp.policy.rate_convention), TimeBasis(c, inp.policy.daycount))
    pv = present_value([(p.date, D(p.lease_amount)) for p in inp.payments], disc, c)
    remaining_head = months_between_frac(c, next_day(inp.head_lease_term_end))
    sub_term = months_between_frac(c, next_day(inp.term_end))
    term_ratio = (sub_term / remaining_head * 100) if remaining_head else Decimal(0)
    rou_portion = D(inp.head_rou_carrying_amount) * D(inp.portion_subleased)
    pv_ratio = (pv / rou_portion * 100) if rou_portion else None
    if inp.head_lease_short_term:
        suggested = "OPERATING"
        expl.append("Head lease is a short-term lease accounted for under para 6 — sublease classified as operating (B58(a)).")
    else:
        suggested = "FINANCE" if term_ratio >= Decimal("75") else "OPERATING"
        expl.append(f"Sublease term {q(sub_term, 2)} months vs remaining head-lease term {q(remaining_head, 2)} months "
                    f"({q(term_ratio, 2)}%) — classification by reference to the ROU asset (B58(b)).")
        if pv_ratio is not None:
            expl.append(f"PV of sublease payments {q(pv)} vs ROU carrying amount subleased {q(rou_portion)} ({q(pv_ratio, 2)}%).")
    final = inp.classification_override or suggested
    if inp.classification_override:
        expl.append(f"Classification overridden to {final}: {inp.override_rationale or 'rationale not documented'}.")
    postings: list[Posting] = []
    rows: list[dict] = []
    gain = ZERO
    ni = ZERO
    derecog = ZERO
    if final == "FINANCE":
        lres = calculate_lessor(LessorLeaseInput(inp.sublease_id, c, inp.term_end, inp.payments, fair_value=pv, carrying_amount=pv,
                                                 implicit_rate_pct=rate, classification_override="FINANCE",
                                                 override_rationale="Classified by reference to the head-lease right-of-use asset (B58)",
                                                 policy=inp.policy, ni_role="NET_INVESTMENT_SUBLEASE"))
        ni = lres.net_investment                      # PV of sublease payments not yet received (para 70)
        day1 = lres.receivable_at_commencement        # sublease payments due at / before commencement
        derecog = q(rou_portion, dp)
        gain = ni + day1 - derecog
        lines = [("NET_INVESTMENT_SUBLEASE", ni, ZERO), ("LESSEE_RECEIVABLE", day1, ZERO), ("ROU_ASSET_SUBLEASED", ZERO, derecog)]
        if gain > 0:
            lines.append(("GAIN_LOSS_SUBLEASE", ZERO, gain))
        elif gain < 0:
            lines.append(("GAIN_LOSS_SUBLEASE", -gain, ZERO))
        postings.append(Posting(c, "SUBLEASE_COMMENCEMENT", "Finance sublease: derecognise ROU (portion), recognise net investment "
                                                            "(Ind AS 116.B58, 67); head-lease liability retained",
                                [l for l in lines if l[1] or l[2]]))
        rows = lres.rows
        postings += [p for p in lres.postings if p.event != "LESSOR_COMMENCEMENT"]
    else:
        lres = calculate_lessor(LessorLeaseInput(inp.sublease_id, c, inp.term_end, inp.payments, fair_value=pv or ONE,
                                                 implicit_rate_pct=rate, classification_override="OPERATING",
                                                 override_rationale="Classified by reference to the head-lease right-of-use asset (B58)",
                                                 policy=inp.policy, ni_role="NET_INVESTMENT_SUBLEASE"))
        rows = lres.rows
        postings += lres.postings
        expl.append("Operating sublease: head-lease ROU asset retained and depreciated; sublease income recognised straight-line (para 81).")
    flags = [JudgmentFlag("SUBLEASE", "Sublease classification", "Classify by reference to the head-lease ROU asset; reviewer attention.",
                          ref("SUBLEASE"))]
    out = SubleaseResult(final, expl, rate, ni, derecog, gain, rows, postings, flags, q(term_ratio, 2),
                         None if pv_ratio is None else q(pv_ratio, 2))
    out.lessor = lres
    return out
