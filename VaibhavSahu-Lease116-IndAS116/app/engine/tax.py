"""Accounting-tax bridge (Ind AS 12) — accounting-support module, NOT a tax-compliance engine.

Default assumption (editable): under Indian income-tax law lease rentals are generally
claimed as business expenditure when paid/accrued, so the tax base of both the ROU asset
and the lease liability is nil. The ROU asset then gives a taxable temporary difference
(DTL) and the lease liability a deductible temporary difference (DTA). Following the
Ind AS 12 amendment effective 1 April 2023, the initial recognition exemption does not
apply to transactions giving rise to equal taxable and deductible temporary differences.
DTA recognition (probable taxable profit) and offsetting (legally enforceable right, same
authority) are judgments captured as inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .decimal_utils import D, ZERO, q
from .references import ref


@dataclass
class TaxSettings:
    tax_rate_pct: Decimal = Decimal("25.168")   # e.g. concessional corporate regime incl. surcharge & cess — confirm per entity
    rou_tax_base: Decimal = ZERO
    liability_tax_base: Decimal = ZERO
    dta_recoverable: bool = True
    offset_permitted: bool = True


def deferred_tax_rows(periods: list, settings: TaxSettings, decimals: int = 2) -> list[dict]:
    rate = D(settings.tax_rate_pct) / 100
    out = []
    prev_net = ZERO
    for r in periods:
        ttd = D(r.rou_close) - D(settings.rou_tax_base)
        dtd_liab = D(r.liab_close) - D(settings.liability_tax_base)
        dtd_prov = D(getattr(r, "prov_close", 0))
        dtl = q(ttd * rate, decimals) if ttd > 0 else ZERO
        dta_gross = q((dtd_liab + dtd_prov) * rate, decimals)
        dta = dta_gross if settings.dta_recoverable else ZERO
        net = dta - dtl
        out.append({"period_end": r.period_end, "rou_carrying": r.rou_close, "rou_tax_base": q(settings.rou_tax_base, decimals),
                    "taxable_temp_diff": q(ttd, decimals), "liability_carrying": r.liab_close,
                    "liability_tax_base": q(settings.liability_tax_base, decimals), "provision_carrying": q(dtd_prov, decimals),
                    "deductible_temp_diff": q(dtd_liab + dtd_prov, decimals), "dtl": dtl, "dta": dta,
                    "net_dta_dtl": net, "movement_pl": net - prev_net,
                    "presentation": "Offset (net)" if settings.offset_permitted else "Gross (no offset)"})
        prev_net = net
    return out


def income_tax_computation_adjustments(periods: list, fy_start, fy_end, decimals: int = 2) -> dict:
    """Items typically adjusted in the computation of business income for a lessee (for review)."""
    rows = [r for r in periods if fy_start <= r.period_end <= fy_end]
    dep = sum((D(r.depreciation) for r in rows), ZERO)
    interest = sum((D(r.interest) for r in rows), ZERO)
    unwind = sum((D(getattr(r, "prov_unwinding", 0)) for r in rows), ZERO)
    gains = sum((D(r.gain_loss) + D(r.remeasurement_pl) for r in rows), ZERO)
    paid = sum((D(r.payments) for r in rows), ZERO)
    return {
        "add_back_rou_depreciation": q(dep, decimals),
        "add_back_interest_on_lease_liability": q(interest, decimals),
        "add_back_provision_unwinding": q(unwind, decimals),
        "less_gain_on_modification_or_termination": q(gains, decimals),
        "less_lease_rent_paid_or_payable": q(paid, decimals),
        "net_adjustment": q(dep + interest + unwind - gains - paid, decimals),
        "note": ("Accounting-support computation only. Deductibility of rent, treatment of Ind AS adjustments and applicable "
                 "section references (Income-tax Act) must be confirmed by the tax team."),
        "reference": ref("DEFERRED_TAX"),
    }
