"""Accounting–tax bridge per lease (Ind AS 12 support; not a tax-compliance engine)."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ..db.models import Company, Lease
from ..engine.calendar_utils import fy_of
from ..engine.decimal_utils import D, to_jsonable
from ..engine.tax import TaxSettings, deferred_tax_rows, income_tax_computation_adjustments
from .lease_service import reporting_run
from .report_service import period_ns
from .settings_service import get_settings


def tax_view(db: Session, lease: Lease, as_of: date) -> dict:
    comp = db.get(Company, lease.company_id)
    t = {**get_settings(comp)["tax"], **(lease.tax_settings or {})}
    run = reporting_run(db, lease)
    if not run or not run.summary.get("periods"):
        return {"available": False, "note": "No capitalised lease calculation available."}
    periods = [period_ns(r) for r in run.summary["periods"]]
    ts = TaxSettings(D(t["tax_rate_pct"]), D(t.get("rou_tax_base") or 0), D(t.get("liability_tax_base") or 0),
                     bool(t.get("dta_recoverable", True)), bool(t.get("offset_permitted", True)))
    rows = deferred_tax_rows(periods, ts)
    fy_s, fy_e = fy_of(as_of, comp.fy_start_month or 4)
    fy_ends = {fy_of(p.period_end, comp.fy_start_month or 4)[1] for p in periods}
    year_rows = [r for r in rows if r["period_end"] in fy_ends or r["period_end"] == periods[-1].period_end]
    adj = income_tax_computation_adjustments(periods, fy_s, fy_e)
    return to_jsonable({"available": True, "settings": t, "year_end_rows": year_rows, "fy": [fy_s, fy_e],
                        "computation_adjustments": adj,
                        "disclaimer": "Accounting-support module: tax bases default to nil (rent claimed on payment/accrual basis). "
                                      "Confirm the tax treatment, rates and recoverability with the tax team; this is not a "
                                      "tax-compliance computation."})
