"""Dashboard, 19 standard reports and disclosure builder (reads approved calculation runs)."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import (AuditLog, CalcRun, Company, Document, GLBalance, JournalEntry, Lease, LeaseEventRow,
                         ReportingPeriod)
from ..engine.calendar_utils import add_months, fy_of, month_end, parse_date, prev_day
from ..engine.decimal_utils import D, ZERO, q, to_jsonable
from ..engine.disclosures import LeaseForDisclosure, build_disclosures
from ..engine.journals import ROLE_CATALOG
from ..engine.lessor import aggregate_lessor_disclosures, position_at
from ..engine.models import Framework
from .lease_service import reporting_run
from .journal_service import resolver

DEC_FIELDS_PERIOD = ("liab_open", "liab_additions", "interest", "payments", "liab_remeasurement", "liab_modification",
                     "liab_derecognised", "liab_close", "liab_current", "liab_noncurrent", "rounding_trueup", "rou_open",
                     "rou_additions", "depreciation", "impairment", "rou_remeasurement", "rou_modification", "rou_derecognised",
                     "rou_close", "rou_cost_close", "rou_accdep_close", "rou_accimp_close", "gain_loss", "remeasurement_pl",
                     "variable_expense", "non_lease_expense", "cash_outflow", "prov_open", "prov_additions", "prov_unwinding",
                     "prov_revision", "prov_settled", "prov_close", "dep_open", "dep_additions", "dep_interest", "dep_refund",
                     "dep_close", "rate_pct")


def period_ns(r: dict) -> SimpleNamespace:
    d = dict(r)
    d["liab_fx"] = D(d.get("liab_fx") or 0)
    for k in DEC_FIELDS_PERIOD:
        if k in d:
            d[k] = D(d[k] or 0)
    d["period_start"] = parse_date(d["period_start"])
    d["period_end"] = parse_date(d["period_end"])
    d["maturity"] = {k: D(v) for k, v in (d.get("maturity") or {}).items()}
    return SimpleNamespace(**d)


def functional_summary(summary: dict) -> dict:
    """For foreign-currency leases, restate period rows in functional currency: liability at closing rates (monetary),
    ROU at historical rates (non-monetary), P&L at average rates, exchange differences shown separately."""
    fx = summary.get("fx_periods")
    if not fx or not summary.get("periods"):
        return summary
    out = dict(summary)
    rows = []
    by_pe = {f["period_end"]: f for f in fx}
    for r in summary["periods"]:
        f = by_pe.get(r["period_end"])
        if f is None:
            continue
        lc_close = D(r["liab_close"])
        close = D(f["liab_close"])
        cur = (close * D(r["liab_current"]) / lc_close).quantize(Decimal("0.01")) if lc_close else ZERO
        avg = D(f["avg_rate"])
        clos = D(f["closing_rate"])
        rou_open, rou_add, rou_adj = D(f["rou_open"]), D(f["rou_additions"]), D(f["rou_adjustments"])
        dep, rou_close = D(f["depreciation"]), D(f["rou_close"])
        other = rou_open + rou_add + rou_adj - dep - rou_close
        imp = other if D(r["impairment"]) != 0 else ZERO
        der = other - imp
        n = dict(r)
        n.update({"liab_open": f["liab_open"], "liab_additions": f["liab_additions"], "interest": f["interest"],
                  "payments": f["payments"], "liab_remeasurement": f["adjustments"], "liab_modification": "0",
                  "liab_derecognised": f["derecognised"], "liab_fx": f["fx_difference"], "liab_close": f["liab_close"],
                  "liab_current": str(cur), "liab_noncurrent": str(close - cur), "rou_open": f["rou_open"],
                  "rou_additions": f["rou_additions"], "depreciation": f["depreciation"], "impairment": str(imp),
                  "rou_remeasurement": f["rou_adjustments"], "rou_modification": "0", "rou_derecognised": str(der),
                  "rou_close": f["rou_close"], "rou_cost_close": f["rou_cost_close"], "rou_accdep_close": f["rou_accdep_close"],
                  "rou_accimp_close": str(D(f["rou_cost_close"]) - D(f["rou_accdep_close"]) - D(f["rou_close"])),
                  "gain_loss": f["gain_loss"], "variable_expense": str(q(D(r["variable_expense"]) * avg)),
                  "non_lease_expense": str(q(D(r["non_lease_expense"]) * avg)), "cash_outflow": str(q(D(r["cash_outflow"]) * avg)),
                  "maturity": {k: str(q(D(v) * clos)) for k, v in (r.get("maturity") or {}).items()},
                  "dep_interest": str(q(D(r.get("dep_interest") or 0) * avg)), "prov_unwinding": str(q(D(r.get("prov_unwinding") or 0) * avg))})
        rows.append(n)
    out["periods"] = rows
    init = dict(summary.get("initial") or {})
    if fx:
        init["liability"] = fx[0]["liab_additions"]
        init["rou"] = fx[0]["rou_additions"]
    out["initial"] = init
    out["functional_view"] = True
    return out


def result_view(summary: dict) -> SimpleNamespace:
    init = summary.get("initial") or {}
    return SimpleNamespace(
        periods=[period_ns(r) for r in summary.get("periods", [])],
        initial=SimpleNamespace(liability=D(init.get("liability") or 0), measurement_date=parse_date(init.get("measurement_date"))),
        payments=[SimpleNamespace(included=p.get("included"), date=parse_date(p["date"]), lease_amount=D(p.get("lease_amount") or 0))
                  for p in summary.get("payments", [])])


def row_at(summary: dict, as_of: date) -> Optional[dict]:
    rows = [r for r in summary.get("periods", []) if parse_date(r["period_end"]) <= as_of]
    return rows[-1] if rows else None


def accessible_leases(db: Session, user, entity_id: Optional[int] = None, include_archived: bool = False) -> list[Lease]:
    from ..db.models import UserEntityAccess
    stmt = select(Lease)
    if not include_archived:
        stmt = stmt.where(Lease.status != "Archived")
    if entity_id:
        stmt = stmt.where(Lease.entity_id == entity_id)
    leases = db.scalars(stmt.order_by(Lease.lease_code)).all()
    if user is not None and not user.all_entities and user.role.code != "ADMIN":
        allowed = set(db.scalars(select(UserEntityAccess.entity_id).where(UserEntityAccess.user_id == user.id)).all())
        leases = [l for l in leases if l.entity_id in allowed]
    return leases


# --------------------------------------------------------------------------- dashboard
def dashboard(db: Session, user, as_of: date, entity_id: Optional[int] = None) -> dict:
    leases = accessible_leases(db, user, entity_id)
    comp = db.scalar(select(Company))
    fy_start, fy_end = fy_of(as_of, comp.fy_start_month or 4)
    k = defaultdict(lambda: ZERO)
    maturity = defaultdict(lambda: ZERO)
    rou_class = defaultdict(lambda: ZERO)
    liab_entity = defaultdict(lambda: ZERO)
    liab_ccy = defaultdict(lambda: ZERO)
    pay_month = defaultdict(lambda: ZERO)
    expiring = {"3": [], "6": [], "12": []}
    renewals, missing_rates, missing_contracts, unapproved, exceptions, exempt = [], [], [], [], [], 0
    active = 0
    horizon = [month_end(add_months(as_of, i)) for i in range(-11, 13)]
    docs = set(db.scalars(select(Document.lease_id).where(Document.lease_id.is_not(None))).all())
    for l in leases:
        run = reporting_run(db, l)
        if l.discount_rate_pct in (None, "") and l.lease_type in ("STANDARD", "SALE_LEASEBACK", None) and l.role == "LESSEE":
            missing_rates.append({"lease_code": l.lease_code, "id": l.id, "description": l.description})
        if l.id not in docs:
            missing_contracts.append({"lease_code": l.lease_code, "id": l.id, "description": l.description})
        if run is None or run.status not in ("Approved", "Posted"):
            unapproved.append({"lease_code": l.lease_code, "id": l.id, "status": run.status if run else "Not calculated"})
        if run is None:
            continue
        s = functional_summary(run.summary)
        issues = [i for i in (s.get("issues") or []) if i.get("severity") in ("ERROR", "WARNING")]
        if issues:
            exceptions.append({"lease_code": l.lease_code, "id": l.id, "count": len(issues), "first": issues[0].get("message")})
        if s.get("kind") == "EXEMPT":
            exempt += 1
            for r in s.get("rows", []):
                pe = parse_date(r["period_end"])
                if pe in horizon:
                    pay_month[pe.isoformat()] += D(r["cash_paid"])
            continue
        if s.get("kind") not in ("LESSEE", None) and "periods" not in s:
            continue
        r = row_at(s, as_of)
        term_end = parse_date((s.get("term") or {}).get("term_end")) if s.get("term") else l.contract_end
        comm = l.commencement_date
        if comm and comm <= as_of and (term_end is None or term_end >= as_of) and l.status != "Terminated":
            active += 1
        if r:
            k["liability"] += D(r["liab_close"])
            k["current"] += D(r["liab_current"])
            k["noncurrent"] += D(r["liab_noncurrent"])
            k["rou"] += D(r["rou_close"])
            for b, v in (r.get("maturity") or {}).items():
                maturity[b] += D(v)
            rou_class[l.asset_class.name if l.asset_class else "Other"] += D(r["rou_close"])
            liab_entity[l.entity.code if l.entity else "-"] += D(r["liab_close"])
            liab_ccy[l.currency or "INR"] += D(r["liab_close"])
        for p in s.get("periods", []):
            pe = parse_date(p["period_end"])
            if fy_start <= pe <= as_of:
                k["interest_ytd"] += D(p["interest"])
                k["depreciation_ytd"] += D(p["depreciation"])
            if pe == month_end(as_of):
                k["payments_month"] += D(p["cash_outflow"])
            if pe in horizon:
                pay_month[pe.isoformat()] += D(p["cash_outflow"])
        if term_end and as_of <= term_end:
            for m in ("3", "6", "12"):
                if term_end <= add_months(as_of, int(m)):
                    expiring[m].append({"lease_code": l.lease_code, "id": l.id, "term_end": term_end.isoformat(),
                                        "description": l.description})
                    break
        for o in l.options:
            if o.kind == "EXTENSION" and o.exercise_date and as_of <= o.exercise_date <= add_months(as_of, 12):
                renewals.append({"lease_code": l.lease_code, "id": l.id, "exercise_date": o.exercise_date.isoformat(),
                                 "reasonably_certain": o.reasonably_certain, "description": o.description})
    upcoming = [{"lease_code": e_l.lease_code, "id": e_l.id, "event": e.event_type, "effective_date": e.effective_date.isoformat(),
                 "status": e.status}
                for e_l in leases for e in e_l.events if e.status in ("Draft", "Submitted")]
    lessor = lessor_dashboard(db, leases, as_of, fy_start, horizon)
    return to_jsonable({
        "as_of": as_of, "fy": [fy_start, fy_end],
        "kpis": {"active_leases": active, "total_leases": len(leases), "exempt_leases": exempt,
                 "total_liability": q(k["liability"]), "current_liability": q(k["current"]), "noncurrent_liability": q(k["noncurrent"]),
                 "total_rou": q(k["rou"]), "payments_this_month": q(k["payments_month"]), "interest_ytd": q(k["interest_ytd"]),
                 "depreciation_ytd": q(k["depreciation_ytd"])},
        "alerts": {"expiring": expiring, "renewals_due": renewals, "upcoming_modifications": upcoming,
                   "missing_contracts": missing_contracts, "missing_discount_rates": missing_rates,
                   "unapproved": unapproved, "exceptions": exceptions},
        "charts": {"maturity": {k2: q(v) for k2, v in maturity.items()}, "rou_by_class": {k2: q(v) for k2, v in rou_class.items()},
                   "liability_by_entity": {k2: q(v) for k2, v in liab_entity.items()},
                   "liability_by_currency": {k2: q(v) for k2, v in liab_ccy.items()},
                   "payments_by_month": {k2: q(v) for k2, v in sorted(pay_month.items())}},
        "lessor": lessor,
    })


def lessor_entries(db: Session, leases: list[Lease], include_subleases: bool = True) -> list[dict]:
    """Calculated lessor positions (lessor leases and, as intermediate lessor, subleases)."""
    out = []
    for l in leases:
        is_lessor = l.role == "LESSOR" and (l.lease_type or "STANDARD") != "SUBLEASE"
        is_sub = (l.lease_type or "") == "SUBLEASE"
        if not (is_lessor or (include_subleases and is_sub)):
            continue
        run = reporting_run(db, l)
        if not run or run.summary.get("kind") not in ("LESSOR", "SUBLEASE"):
            continue
        if not is_current_lessor_run(run.summary):
            continue          # produced by the pre-v1.1 lessor engine — listed in the exception report until recalculated
        out.append({"lease": l, "lease_code": l.lease_code, "asset_class": l.asset_class.name if l.asset_class else "",
                    "kind": run.summary.get("kind"), "summary": run.summary, "run": run})
    return out


def is_current_lessor_run(summary: dict) -> bool:
    """True when a lessor / sublease result carries the lessor-engine 2.x structure (segments and full schedule rows)."""
    rows = summary.get("rows") or []
    return summary.get("segments") is not None and (not rows or "ni_close" in rows[0])


def lessor_dashboard(db: Session, leases: list[Lease], as_of: date, fy_start: date, horizon: list) -> dict:
    ents = lessor_entries(db, leases)
    k = defaultdict(lambda: ZERO)
    for key in ("net_investment", "ni_current", "loss_allowance", "accrued_income", "deposits_received", "finance_income_ytd",
                "operating_income_ytd", "variable_income_ytd", "receipts_this_month"):
        k[key] = ZERO
    maturity = defaultdict(lambda: ZERO)
    income_month = defaultdict(lambda: ZERO)
    by_class = defaultdict(lambda: ZERO)
    active = 0
    n_fin = n_op = 0
    for e in ents:
        s = e["summary"]
        pos = position_at(s, as_of)
        cls = pos["classification"]
        if cls in ("FINANCE", "OPERATING"):
            active += 1
            n_fin += cls == "FINANCE"
            n_op += cls == "OPERATING"
        k["net_investment"] += D(pos["ni_close"])
        k["ni_current"] += D(pos["ni_current"])
        k["loss_allowance"] += D(pos["loss_allowance"])
        k["accrued_income"] += D(pos["accrued_lease_income"])
        k["deposits_received"] += D(pos["deposit_carrying"])
        for m in pos["maturity"]:
            maturity[m["bucket"]] += D(m["amount"])
        for r in s.get("rows") or []:
            pe = parse_date(r["period_end"])
            inc = D(r.get("finance_income") or 0) + D(r.get("lease_income") or 0) + D(r.get("variable_income") or 0)
            if fy_start <= pe <= as_of:
                k["finance_income_ytd"] += D(r.get("finance_income") or 0)
                k["operating_income_ytd"] += D(r.get("lease_income") or 0)
                k["variable_income_ytd"] += D(r.get("variable_income") or 0)
            if pe == month_end(as_of):
                k["receipts_this_month"] += D(r.get("receipts") or 0)
            if pe in horizon:
                income_month[pe.isoformat()] += inc
        by_class[e["asset_class"] or "Other"] += D(pos["ni_close"]) if cls == "FINANCE" else ZERO
    return to_jsonable({
        "count": len(ents), "active": active, "finance_leases": n_fin, "operating_leases": n_op,
        "kpis": {kk: q(v) for kk, v in k.items()},
        "maturity": [{"bucket": b, "amount": q(maturity.get(b, ZERO))}
                     for b in [f"Year {i}" for i in range(1, 6)] + ["Later than five years"]] if maturity else [],
        "income_by_month": {kk: q(v) for kk, v in sorted(income_month.items())},
    })


# --------------------------------------------------------------------------- disclosures
def disclosures(db: Session, user, start: date, end: date, entity_id: Optional[int] = None) -> dict:
    comp = db.scalar(select(Company))
    items = []
    for l in accessible_leases(db, user, entity_id):
        run = reporting_run(db, l)
        if run is None:
            continue
        s = functional_summary(run.summary)
        if s.get("kind") == "EXEMPT":
            rows = [{"period_end": parse_date(r["period_end"]), "expense": D(r["expense"]), "variable_expense": D(r["variable_expense"]),
                     "cash_paid": D(r["cash_paid"])} for r in s.get("rows", [])]
            items.append(LeaseForDisclosure(l.lease_code, l.entity.name, l.asset_class.name if l.asset_class else "Other",
                                            exempt_type=l.lease_type, exempt_rows=rows))
        elif s.get("kind") in ("LESSEE",) or (s.get("kind") is None and s.get("periods")):
            view = result_view(s)
            opt = ZERO
            for p in s.get("payments", []):
                if not p.get("included") and "optional period" in (p.get("inclusion_reason") or "").lower():
                    opt += D(p.get("lease_amount") or 0)
            slb_gain = D((s.get("slb") or {}).get("gain_rights_transferred") or 0)
            items.append(LeaseForDisclosure(l.lease_code, l.entity.name, l.asset_class.name if l.asset_class else "Other", view,
                                            option_exposure=opt, slb_gain=slb_gain,
                                            slb_date=l.commencement_date if s.get("slb") else None))
        elif s.get("kind") == "SUBLEASE" or s.get("kind") == "LESSOR":
            rows = [{"period_end": parse_date(r["period_end"]), "lease_income": D(r.get("lease_income") or 0),
                     "finance_income": D(r.get("finance_income") or 0)} for r in s.get("rows", [])]
            if s.get("kind") == "SUBLEASE":
                items.append(LeaseForDisclosure(l.lease_code, l.entity.name, "Sublease", sublease_income_rows=rows))
    pol = comp.settings.get("policies", {}) if comp.settings else {}
    d = build_disclosures(items, start, end, Framework(comp.framework or "IND_AS_116"),
                          buckets=tuple(pol.get("maturity_buckets") or (1, 2, 3, 4, 5)))
    d["lessor"] = lessor_disclosures(db, user, start, end, entity_id)
    return to_jsonable(d)


def lessor_disclosures(db: Session, user, start: date, end: date, entity_id=None) -> dict:
    """Lessor note (Ind AS 116.89–97) for lessor leases and, as intermediate lessor, subleases."""
    ents = lessor_entries(db, accessible_leases(db, user, entity_id))
    out = aggregate_lessor_disclosures([{k: e[k] for k in ("lease_code", "asset_class", "kind", "summary")} for e in ents], start, end)
    inc = out["income"]
    # legacy keys kept for existing consumers
    out.update({"finance_income": inc["finance_income"], "operating_lease_income": inc["operating_income"],
                "selling_profit": inc["selling_profit"],
                "includes_subleases": any(e["kind"] == "SUBLEASE" for e in ents)})
    return to_jsonable(out)


# --------------------------------------------------------------------------- reports
REPORTS = {
    "lease_register": "Lease Register", "liability_schedule": "Lease Liability Schedule", "rou_schedule": "ROU Asset Schedule",
    "combined_schedule": "Combined Lease Schedule", "journal_report": "Journal Report", "gl_reconciliation": "GL Reconciliation",
    "maturity_analysis": "Maturity Analysis", "disclosure_report": "Disclosure Report", "expiry_report": "Lease Expiry Report",
    "renewal_options": "Renewal Option Report", "modification_report": "Modification Report", "deposit_report": "Security Deposit Report",
    "fx_report": "FX Report", "impairment_report": "Impairment Report", "exemption_report": "Exemption Report",
    "audit_trail": "Audit Trail", "exceptions": "Missing Data / Exception Report",
    "lessor_schedule": "Lessor Income & Net Investment Schedule", "lessor_maturity": "Lessor Maturity Analysis & Reconciliation",
}


def _col(key, label, typ="text"):
    return {"key": key, "label": label, "type": typ}


def run_report(db: Session, user, code: str, f: dict) -> dict:
    as_of = parse_date(f.get("as_of")) or date.today()
    start = parse_date(f.get("start")) or fy_of(as_of)[0]
    end = parse_date(f.get("end")) or as_of
    entity_id = int(f["entity_id"]) if f.get("entity_id") else None
    leases = accessible_leases(db, user, entity_id)
    if f.get("lease_id"):
        leases = [l for l in leases if l.id == int(f["lease_id"])]
    if f.get("asset_class"):
        leases = [l for l in leases if l.asset_class and l.asset_class.name == f["asset_class"]]
    if f.get("currency"):
        leases = [l for l in leases if l.currency == f["currency"]]
    if f.get("status"):
        leases = [l for l in leases if l.status == f["status"]]
    if f.get("location"):
        leases = [l for l in leases if (l.location or "").lower().find(f["location"].lower()) >= 0]
    if f.get("cost_centre"):
        leases = [l for l in leases if (l.cost_centre or "") == f["cost_centre"]]
    title = REPORTS.get(code, code)
    cols, rows, totals = [], [], None

    if code == "lease_register":
        if f.get("role"):
            leases = [l for l in leases if (l.role or "LESSEE") == f["role"].upper()]
        cols = [_col("lease_code", "Lease ID"), _col("entity", "Entity"), _col("description", "Description"), _col("role", "Role"),
                _col("lessor", "Counterparty"), _col("asset_class", "Asset class"), _col("location", "Location"),
                _col("cost_centre", "Cost centre"), _col("lease_type", "Type"), _col("classification", "Lessor classification"),
                _col("commencement_date", "Commencement", "date"), _col("term_end", "Lease term end", "date"),
                _col("currency", "Ccy"), _col("discount_rate_pct", "Rate %", "pct"), _col("initial_liability", "Initial liability", "money"),
                _col("liability", f"Liability {as_of} (functional ccy)", "money"), _col("rou", f"ROU {as_of} (functional ccy)", "money"),
                _col("net_investment", f"Net investment {as_of} (lessor)", "money"),
                _col("accrued_income", f"Accrued / (deferred) lease income {as_of}", "money"), _col("status", "Status")]
        for l in leases:
            run = reporting_run(db, l)
            s = functional_summary(run.summary) if run else {}
            r = row_at(s, as_of) if s.get("periods") else None
            pos = position_at(s, as_of) if s.get("kind") in ("LESSOR", "SUBLEASE") else None
            rows.append({"lease_code": l.lease_code, "entity": l.entity.code, "description": l.description, "role": (l.role or "LESSEE").title(),
                         "lessor": l.counterparty.name if l.counterparty else "", "asset_class": l.asset_class.name if l.asset_class else "",
                         "location": l.location, "cost_centre": l.cost_centre, "lease_type": l.lease_type,
                         "classification": pos["classification"].title() if pos else None,
                         "commencement_date": l.commencement_date, "term_end": (s.get("term") or {}).get("term_end") or l.contract_end,
                         "currency": l.currency, "discount_rate_pct": l.discount_rate_pct if (l.role or "LESSEE") == "LESSEE" else s.get("implicit_rate_pct"),
                         "initial_liability": (s.get("initial") or {}).get("liability"), "liability": r["liab_close"] if r else None,
                         "rou": r["rou_close"] if r else None, "net_investment": pos["ni_close"] if pos else None,
                         "accrued_income": pos["accrued_lease_income"] if pos else None, "status": l.status})
        totals = {"initial_liability": sum((D(r["initial_liability"] or 0) for r in rows), ZERO),
                  "liability": sum((D(r["liability"] or 0) for r in rows), ZERO), "rou": sum((D(r["rou"] or 0) for r in rows), ZERO),
                  "net_investment": sum((D(r["net_investment"] or 0) for r in rows), ZERO),
                  "accrued_income": sum((D(r["accrued_income"] or 0) for r in rows), ZERO)}

    elif code in ("liability_schedule", "rou_schedule", "combined_schedule"):
        base = [_col("lease_code", "Lease ID"), _col("period_end", "Period end", "date")]
        liab = [_col("liab_open", "Opening liability", "money"), _col("liab_additions", "Additions", "money"),
                _col("interest", "Interest", "money"), _col("payments", "Payments", "money"),
                _col("liab_remeasurement", "Remeasurement", "money"), _col("liab_modification", "Modification", "money"),
                _col("liab_derecognised", "Derecognised", "money"), _col("liab_close", "Closing liability", "money"),
                _col("liab_current", "Current", "money"), _col("liab_noncurrent", "Non-current", "money")]
        rou = [_col("rou_open", "Opening ROU", "money"), _col("rou_additions", "Additions", "money"),
               _col("depreciation", "Depreciation", "money"), _col("impairment", "Impairment", "money"),
               _col("rou_remeasurement", "Remeasurement", "money"), _col("rou_modification", "Modification", "money"),
               _col("rou_derecognised", "Derecognised", "money"), _col("rou_close", "Closing ROU", "money")]
        cols = base + (liab if code == "liability_schedule" else rou if code == "rou_schedule" else liab + rou)
        keys = [c["key"] for c in cols if c["type"] == "money"]
        totals = defaultdict(lambda: ZERO)
        for l in leases:
            run = reporting_run(db, l)
            if not run:
                continue
            for r in functional_summary(run.summary).get("periods", []):
                pe = parse_date(r["period_end"])
                if start <= pe <= end:
                    row = {"lease_code": l.lease_code, "period_end": r["period_end"]}
                    row.update({k: r.get(k) for k in keys})
                    rows.append(row)
                    for k in keys:
                        if k not in ("liab_open", "liab_close", "liab_current", "liab_noncurrent", "rou_open", "rou_close"):
                            totals[k] += D(r.get(k) or 0)
        totals = dict(totals)

    elif code == "journal_report":
        from .journal_service import period_journals
        cols = [_col("je_ref", "JE ref"), _col("date", "Date", "date"), _col("lease_code", "Lease"), _col("event_label", "Event"),
                _col("account_code", "Account"), _col("account_name", "Account name"), _col("debit", "Debit", "money"),
                _col("credit", "Credit", "money"), _col("narration", "Narration")]
        for j in period_journals(db, leases, start, end):
            for ln in j["lines"]:
                rows.append({"je_ref": j["je_ref"], "date": j["date"], "lease_code": j["lease_code"], "event_label": j["event_label"],
                             "account_code": ln["account_code"], "account_name": ln["account_name"], "debit": ln["debit"],
                             "credit": ln["credit"], "narration": j["narration"]})
        totals = {"debit": sum((D(r["debit"]) for r in rows), ZERO), "credit": sum((D(r["credit"]) for r in rows), ZERO)}

    elif code == "gl_reconciliation":
        resolve = resolver(db, leases[0].company_id) if leases else None
        app_bal = defaultdict(lambda: ZERO)
        role_names = {}
        for l in leases:
            run = reporting_run(db, l)
            if not run:
                continue
            for p in run.summary.get("postings", []):
                if parse_date(p["date"]) <= as_of:
                    for ln in p["lines"]:
                        code_, name = resolve(ln["role"], l)
                        app_bal[code_] += D(ln["debit"]) - D(ln["credit"])
                        role_names[code_] = name
        gl = defaultdict(lambda: ZERO)
        for b in db.scalars(select(GLBalance).where(GLBalance.as_of == as_of)).all():
            if entity_id and b.entity_id != entity_id:
                continue
            gl[b.account_code] += D(b.balance)
        cols = [_col("account_code", "Account"), _col("account_name", "Account name"), _col("app_balance", "Lease116 balance (Dr+/Cr−)", "money"),
                _col("gl_balance", "GL balance (Dr+/Cr−)", "money"), _col("difference", "Difference", "money"), _col("status", "Status")]
        bs_codes = {ROLE_CATALOG[r][0] for r in ("ROU_ASSET", "ROU_ACC_DEP", "ROU_ACC_IMP", "LEASE_LIABILITY", "SECURITY_DEPOSIT",
                                                  "RESTORATION_PROVISION", "NET_INVESTMENT_LEASE", "NET_INVESTMENT_SUBLEASE",
                                                  "ACCRUED_LEASE_INCOME", "SECURITY_DEPOSIT_RECEIVED", "LESSOR_IDC_ASSET",
                                                  "LOSS_ALLOWANCE_LEASE_RECEIVABLES")}
        for c in sorted(set(app_bal) | set(gl)):
            a, g = q(app_bal.get(c, ZERO)), q(gl.get(c, ZERO))
            if c not in gl and c not in bs_codes and not f.get("all_accounts"):
                continue
            rows.append({"account_code": c, "account_name": role_names.get(c, ""), "app_balance": a,
                         "gl_balance": g if c in gl else None, "difference": a - g if c in gl else None,
                         "status": ("No GL balance imported" if c not in gl else "Reconciled" if a == g else "EXCEPTION")})

    elif code == "maturity_analysis":
        cols = [_col("lease_code", "Lease ID")]
        bucket_keys = None
        for l in leases:
            run = reporting_run(db, l)
            if not run:
                continue
            fs = functional_summary(run.summary)
            r = row_at(fs, as_of) if fs.get("periods") else None
            if not r:
                continue
            m = r.get("maturity") or {}
            if bucket_keys is None:
                bucket_keys = list(m.keys())
                cols += [_col(k, _bucket_title(k), "money") for k in bucket_keys] + [_col("total", "Total undiscounted", "money"),
                                                                                     _col("carrying", "Carrying amount", "money")]
            row = {"lease_code": l.lease_code, **m}
            row["total"] = sum((D(v) for v in m.values()), ZERO)
            row["carrying"] = r["liab_close"]
            rows.append(row)
        if bucket_keys:
            totals = {k: sum((D(r.get(k) or 0) for r in rows), ZERO) for k in bucket_keys + ["total", "carrying"]}

    elif code == "disclosure_report":
        d = disclosures(db, user, start, end, entity_id)
        cols = [_col("ref", "Ind AS 116 ref"), _col("item", "Disclosure item"), _col("amount", "Amount", "money")]
        rows = [{"ref": x["ref"], "item": x["item"], "amount": x["amount"]} for x in d["para53"]]
        ld = d.get("lessor") or {}
        if ld.get("count"):
            rows.append({"ref": "89–97", "item": "LESSOR DISCLOSURES" + (" (incl. subleases — intermediate lessor)" if ld.get("includes_subleases") else ""),
                         "amount": None})
            rows += [{"ref": x["ref"], "item": x["item"], "amount": x["amount"]} for x in ld["income_table"]]
            mv = ld["net_investment_movement"]
            for key, label in (("opening", "Net investment in finance leases — opening"), ("additions", "Additions (new finance leases)"),
                               ("finance_income", "Finance income"), ("receipts", "Lease payments received / receivable"),
                               ("residual_returned", "Unguaranteed residual realised (asset returned)"),
                               ("remeasurement", "Remeasurements / modifications"), ("derecognised", "Derecognised (terminations / reclassification)"),
                               ("closing", "Net investment in finance leases — closing (gross)")):
                rows.append({"ref": "93", "item": label, "amount": mv[key]})
            for m in ld["maturity_finance"]:
                rows.append({"ref": "94", "item": f"Finance lease receipts (undiscounted) — {m['bucket']}", "amount": m["amount"]})
            rc = ld.get("reconciliation")
            if rc:
                rows += [{"ref": "94", "item": "Total undiscounted lease payments receivable", "amount": rc["undiscounted_lease_payments"]},
                         {"ref": "94", "item": "Less: unearned finance income", "amount": rc["unearned_finance_income"]},
                         {"ref": "94", "item": "Add: discounted unguaranteed residual value", "amount": rc["discounted_unguaranteed_residual"]},
                         {"ref": "94", "item": "Net investment in finance leases", "amount": rc["net_investment"]},
                         {"ref": "Ind AS 109", "item": "Less: loss allowance", "amount": rc["loss_allowance"]}]
            for m in ld["maturity_operating"]:
                rows.append({"ref": "97", "item": f"Operating lease receipts (undiscounted) — {m['bucket']}", "amount": m["amount"]})

    elif code == "expiry_report":
        cols = [_col("lease_code", "Lease ID"), _col("description", "Description"), _col("contract_end", "Contract end", "date"),
                _col("term_end", "Accounting term end", "date"), _col("months_left", "Months left", "num"), _col("status", "Status")]
        for l in leases:
            run = reporting_run(db, l)
            te = parse_date((run.summary.get("term") or {}).get("term_end")) if run and run.summary.get("term") else l.contract_end
            if te and te >= as_of:
                months = (te.year - as_of.year) * 12 + te.month - as_of.month
                rows.append({"lease_code": l.lease_code, "description": l.description, "contract_end": l.contract_end,
                             "term_end": te, "months_left": months, "status": l.status})
        rows.sort(key=lambda r: r["term_end"])

    elif code == "renewal_options":
        cols = [_col("lease_code", "Lease ID"), _col("kind", "Option"), _col("holder", "Holder"), _col("exercise_date", "Exercise / start", "date"),
                _col("extension_end_date", "Extension end", "date"), _col("reasonably_certain", "Reasonably certain"),
                _col("rationale", "Rationale"), _col("last_reassessment_date", "Last reassessed", "date")]
        for l in leases:
            for o in l.options:
                rows.append({"lease_code": l.lease_code, "kind": o.kind, "holder": o.holder, "exercise_date": o.exercise_date,
                             "extension_end_date": o.extension_end_date,
                             "reasonably_certain": {True: "Yes", False: "No", None: "Not assessed"}[o.reasonably_certain],
                             "rationale": o.rationale, "last_reassessment_date": o.last_reassessment_date})

    elif code in ("modification_report", "impairment_report"):
        types = ("MODIFICATION", "REASSESSMENT", "TERMINATION") if code == "modification_report" else ("IMPAIRMENT",)
        cols = [_col("lease_code", "Lease ID"), _col("event_type", "Event"), _col("subtype", "Type"),
                _col("effective_date", "Effective", "date"), _col("description", "Description"), _col("status", "Status"),
                _col("liability_before", "Liability before", "money"), _col("liability_after", "Liability after", "money"),
                _col("rou_before", "ROU before", "money"), _col("rou_after", "ROU after", "money"),
                _col("lessor_balance", "Lessor balance (NI / accrued income)"), _col("lessor_before", "Lessor balance before", "money"),
                _col("lessor_after", "Lessor balance after", "money"), _col("gain_loss", "Gain/(loss)", "money")]
        if code == "modification_report":
            types = types + ("UGR_REVISION",)
        else:
            types = types + ("ECL",)
        for l in leases:
            run = reporting_run(db, l)
            res_by_ref = {e.get("ref"): e for e in (run.summary.get("events", []) if run else [])}
            for e in l.events:
                if e.event_type not in types:
                    continue
                r = e.result or res_by_ref.get(f"EV-{e.id}") or {}
                rows.append({"lease_code": l.lease_code, "event_type": e.event_type, "subtype": e.subtype,
                             "effective_date": e.effective_date, "description": e.description, "status": e.status,
                             "liability_before": r.get("liability_before"), "liability_after": r.get("liability_after"),
                             "rou_before": r.get("rou_before"), "rou_after": r.get("rou_after"),
                             "lessor_balance": r.get("balance_label"), "lessor_before": r.get("balance_before"),
                             "lessor_after": r.get("balance_after"), "gain_loss": r.get("gain_loss")})

    elif code == "deposit_report":
        cols = [_col("lease_code", "Lease ID"), _col("direction", "Deposit"), _col("amount_paid", "Amount paid / (received)", "money"),
                _col("payment_date", "Paid / received on", "date"), _col("refund_date", "Refund date", "date"),
                _col("market_rate_pct", "Market rate %", "pct"), _col("initial_fair_value", "Initial fair value", "money"),
                _col("difference_prepaid_rent", "Difference (lessee: prepaid rent to ROU; lessor: lease payment in advance)", "money"),
                _col("carrying", f"Carrying amount {as_of}", "money"),
                _col("interest_ytd", "Interest income / (unwinding expense) — period", "money")]
        for l in leases:
            run = reporting_run(db, l)
            if not run or not run.summary.get("deposit"):
                continue
            dsum = run.summary["deposit"]
            if run.summary.get("kind") == "LESSOR":
                lrows = run.summary.get("rows") or []
                at = [x for x in lrows if parse_date(x["period_end"]) <= as_of]
                unw = sum((D(x.get("dep_unwinding") or 0) for x in lrows if start <= parse_date(x["period_end"]) <= end), ZERO)
                rows.append({"lease_code": l.lease_code, "direction": "Received (lessor)", "amount_paid": -D(dsum.get("amount_received") or 0),
                             "payment_date": dsum.get("receipt_date"), "refund_date": dsum.get("refund_date"),
                             "market_rate_pct": dsum.get("market_rate_pct"), "initial_fair_value": dsum.get("initial_fair_value"),
                             "difference_prepaid_rent": dsum.get("lease_payment_element"),
                             "carrying": (-D(at[-1].get("dep_close") or 0)) if at else None, "interest_ytd": -unw})
                continue
            r = row_at(run.summary, as_of)
            ytd = sum((D(p["dep_interest"]) for p in run.summary.get("periods", []) if start <= parse_date(p["period_end"]) <= end), ZERO)
            rows.append({"lease_code": l.lease_code, "direction": "Paid (lessee)", **{k: dsum.get(k) for k in ("amount_paid", "payment_date", "refund_date",
                                                                                                          "market_rate_pct", "initial_fair_value",
                                                                                                          "difference_prepaid_rent")},
                         "carrying": r["dep_close"] if r else None, "interest_ytd": ytd})

    elif code == "fx_report":
        cols = [_col("lease_code", "Lease ID"), _col("currency", "Ccy"), _col("period_end", "Period end", "date"),
                _col("closing_rate", "Closing rate", "rate"), _col("liab_close", "Liability (functional)", "money"),
                _col("fx_difference", "FX (gain)/loss", "money"), _col("rou_close", "ROU (historical)", "money")]
        for l in leases:
            run = reporting_run(db, l)
            for fr in (run.summary.get("fx_periods") or []) if run else []:
                if start <= parse_date(fr["period_end"]) <= end:
                    rows.append({"lease_code": l.lease_code, "currency": l.currency, "period_end": fr["period_end"],
                                 "closing_rate": fr["closing_rate"], "liab_close": fr["liab_close"],
                                 "fx_difference": fr["fx_difference"], "rou_close": fr["rou_close"]})

    elif code == "exemption_report":
        cols = [_col("lease_code", "Lease ID"), _col("description", "Description"), _col("exemption", "Exemption"),
                _col("valid", "Validation"), _col("basis", "Basis"), _col("expense", "Expense (period)", "money"),
                _col("asset_class", "Class")]
        for l in leases:
            if l.lease_type not in ("SHORT_TERM", "LOW_VALUE"):
                continue
            run = reporting_run(db, l)
            s = functional_summary(run.summary) if run else {}
            exp = sum((D(r["expense"]) for r in s.get("rows", []) if start <= parse_date(r["period_end"]) <= end), ZERO)
            rows.append({"lease_code": l.lease_code, "description": l.description, "exemption": l.lease_type,
                         "valid": "Passed" if s.get("valid") else "FAILED", "basis": "; ".join(s.get("reasons") or []),
                         "expense": exp, "asset_class": l.asset_class.name if l.asset_class else ""})

    elif code == "audit_trail":
        cols = [_col("at", "Timestamp"), _col("username", "User"), _col("action", "Action"), _col("object_type", "Object"),
                _col("object_label", "Reference"), _col("field", "Field"), _col("old_value", "Old value"), _col("new_value", "New value"),
                _col("reason", "Reason"), _col("approval_status", "Approval status")]
        stmt = select(AuditLog).order_by(AuditLog.at.desc()).limit(int(f.get("limit") or 2000))
        for a in db.scalars(stmt).all():
            rows.append({"at": a.at.strftime("%d-%b-%Y %H:%M:%S"), "username": a.username, "action": a.action, "object_type": a.object_type,
                         "object_label": a.object_label, "field": a.field, "old_value": a.old_value, "new_value": a.new_value,
                         "reason": a.reason, "approval_status": a.approval_status})

    elif code == "exceptions":
        cols = [_col("lease_code", "Lease ID"), _col("severity", "Severity"), _col("category", "Category"), _col("message", "Message")]
        docs = set(db.scalars(select(Document.lease_id).where(Document.lease_id.is_not(None))).all())
        for l in leases:
            run = reporting_run(db, l)
            if l.id not in docs:
                rows.append({"lease_code": l.lease_code, "severity": "WARNING", "category": "Missing contract",
                             "message": "No lease agreement attached."})
            if l.role == "LESSEE" and l.lease_type in ("STANDARD", "SALE_LEASEBACK") and l.discount_rate_pct in (None, ""):
                rows.append({"lease_code": l.lease_code, "severity": "ERROR", "category": "Missing discount rate",
                             "message": "Discount rate required (Ind AS 116.26)."})
            if l.role == "LESSOR" and (l.lease_type or "STANDARD") != "SUBLEASE":
                det = l.lessor_details or {}
                if not det.get("classification_override") and (not det.get("fair_value") or not det.get("economic_life_months")):
                    rows.append({"lease_code": l.lease_code, "severity": "ERROR", "category": "Lessor classification inputs",
                                 "message": "Fair value and economic life of the asset (or a documented classification) are required to "
                                            "classify the lease (Ind AS 116.61–66)."})
                if l.deposits and l.deposits[0].market_rate_pct in (None, "") and not l.deposits[0].interest_bearing:
                    rows.append({"lease_code": l.lease_code, "severity": "ERROR", "category": "Deposit market rate",
                                 "message": "Market rate required to fair-value the interest-free deposit received (Ind AS 109)."})
            for o in l.options:
                if o.reasonably_certain is None:
                    rows.append({"lease_code": l.lease_code, "severity": "ERROR", "category": "Judgment pending",
                                 "message": f"{o.kind.title()} option not assessed (reasonably certain?)."})
            if run is None:
                rows.append({"lease_code": l.lease_code, "severity": "WARNING", "category": "Not calculated", "message": "No calculation run."})
                continue
            if run.status not in ("Approved", "Posted"):
                rows.append({"lease_code": l.lease_code, "severity": "INFO", "category": "Unapproved",
                             "message": f"Calculation run {run.run_no} is {run.status}."})
            if run.summary.get("kind") in ("LESSOR", "SUBLEASE") and not is_current_lessor_run(run.summary):
                rows.append({"lease_code": l.lease_code, "severity": "ERROR", "category": "Recalculate (lessor engine)",
                             "message": "Calculated with the previous lessor engine — excluded from the lessor note, dashboard and "
                                        "lessor reports until recalculated (reopen if approved)."})
            for i in run.summary.get("issues") or []:
                rows.append({"lease_code": l.lease_code, "severity": i.get("severity"), "category": i.get("code"), "message": i.get("message")})
    elif code == "lessor_schedule":
        cols = [_col("lease_code", "Lease ID"), _col("period_end", "Period end", "date"), _col("classification", "Classification"),
                _col("ni_open", "Opening net investment", "money"), _col("ni_additions", "Additions", "money"),
                _col("finance_income", "Finance income", "money"), _col("ni_receipts", "Receipts applied", "money"),
                _col("ni_remeasurement", "Remeasurement", "money"), _col("ni_derecognised", "Derecognised", "money"),
                _col("ni_close", "Closing net investment", "money"), _col("lease_income", "Operating lease income", "money"),
                _col("variable_income", "Variable lease income", "money"), _col("receipts", "Lease payments billed", "money"),
                _col("accrued_close", "Accrued / (deferred) lease income", "money"), _col("dep_close", "Deposit received (carrying)", "money"),
                _col("dep_unwinding", "Deposit unwinding", "money"), _col("idc_amortisation", "IDC amortisation", "money"),
                _col("ecl_charge", "ECL charge", "money"), _col("gain_loss", "Gain / (loss) on events", "money")]
        flows = ("ni_additions", "finance_income", "ni_receipts", "ni_remeasurement", "ni_derecognised", "lease_income", "variable_income",
                 "receipts", "dep_unwinding", "idc_amortisation", "ecl_charge", "gain_loss")
        totals = defaultdict(lambda: ZERO)
        for e in lessor_entries(db, leases):
            for r in e["summary"].get("rows") or []:
                pe = parse_date(r["period_end"])
                if start <= pe <= end:
                    row = {"lease_code": e["lease_code"], "period_end": r["period_end"], "classification": (r.get("classification") or "").title()}
                    row.update({c["key"]: r.get(c["key"]) for c in cols if c["type"] == "money"})
                    rows.append(row)
                    for k_ in flows:
                        totals[k_] += D(r.get(k_) or 0)
        totals = dict(totals)

    elif code == "lessor_maturity":
        buckets = [f"Year {i}" for i in range(1, 6)] + ["Later than five years"]
        cols = [_col("lease_code", "Lease ID"), _col("classification", "Classification")] + \
               [_col(b, b, "money") for b in buckets] + \
               [_col("total", "Total undiscounted", "money"), _col("unearned", "Unearned finance income", "money"),
                _col("pv_ugr", "Discounted unguaranteed residual", "money"), _col("net_investment", "Net investment", "money"),
                _col("loss_allowance", "Loss allowance", "money"), _col("check", "Check vs schedule", "money")]
        totals = defaultdict(lambda: ZERO)
        for e in lessor_entries(db, leases):
            pos = position_at(e["summary"], as_of)
            if pos["classification"] not in ("FINANCE", "OPERATING"):
                continue
            row = {"lease_code": e["lease_code"], "classification": pos["classification"].title(), "total": pos["total_undiscounted"],
                   "loss_allowance": pos["loss_allowance"]}
            for m in pos["maturity"]:
                row[m["bucket"]] = m["amount"]
            rc = pos.get("reconciliation")
            if rc:
                row.update({"unearned": rc["unearned_finance_income"], "pv_ugr": rc["discounted_unguaranteed_residual"],
                            "net_investment": rc["net_investment"], "check": rc.get("difference")})
            rows.append(row)
            for k_ in buckets + ["total", "unearned", "pv_ugr", "net_investment", "loss_allowance"]:
                totals[k_] += D(row.get(k_) or 0)
        totals = dict(totals)

    else:
        raise ValueError(f"Unknown report {code}")
    return to_jsonable({"code": code, "title": title, "columns": cols, "rows": rows, "totals": totals,
                        "filters": {"as_of": as_of, "start": start, "end": end, "entity_id": entity_id}})


def _bucket_title(k: str) -> str:
    if k.startswith(">"):
        return f"> {k[1:]} yrs"
    a, b = k.split("-")
    return f"{a}–{b} yrs"
