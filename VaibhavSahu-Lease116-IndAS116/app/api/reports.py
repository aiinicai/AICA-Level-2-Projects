"""Dashboard, reports, disclosures and journals (portfolio level)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.base import get_db
from ..db.models import Company, JournalEntry, User
from ..engine.calendar_utils import fy_of, month_end, parse_date
from ..engine.decimal_utils import to_jsonable
from ..services import audit
from ..services.export_service import disclosure_xlsx, table_csv, table_pdf, table_xlsx
from ..services.journal_service import export_csv, export_sap, export_tally, period_journals, post_period
from ..services.lease_service import ServiceError, company_of
from ..services.report_service import REPORTS, accessible_leases, dashboard, disclosures, run_report
from ..services.settings_service import get_settings
from .deps import require

router = APIRouter(prefix="/api", tags=["reports"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/dashboard")
def get_dashboard(as_of: Optional[str] = None, entity_id: Optional[int] = None, db: Session = Depends(get_db),
                  user: User = Depends(require("report.read"))):
    return dashboard(db, user, parse_date(as_of) or date.today(), entity_id)


@router.get("/reports")
def list_reports(user: User = Depends(require("report.read"))):
    return [{"code": k, "title": v} for k, v in REPORTS.items()]


@router.get("/reports/{code}")
def get_report(code: str, request: Request, db: Session = Depends(get_db), user: User = Depends(require("report.read"))):
    if code == "audit_trail":
        from ..services.security import has_perm
        if not has_perm(user.role.code, "audit.read"):
            raise HTTPException(403, "Audit trail requires audit.read permission")
    try:
        return run_report(db, user, code, dict(request.query_params))
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.get("/reports/{code}/export")
def export_report(code: str, request: Request, format: str = "xlsx", db: Session = Depends(get_db),
                  user: User = Depends(require("export"))):
    rep = run_report(db, user, code, dict(request.query_params))
    comp = company_of(db)
    meta = {"Company": comp.name, "Filters": ", ".join(f"{k}={v}" for k, v in rep["filters"].items() if v),
            "Generated": f"{datetime.now():%d-%b-%Y %H:%M} by {user.full_name}"}
    audit.log(db, user, "EXPORT", "Report", code, rep["title"], "format", None, format)
    db.commit()
    fn = f"{rep['title'].replace(' ', '_').replace('/', '-')}_{date.today():%Y%m%d}"
    if format == "csv":
        return Response(table_csv(rep["columns"], rep["rows"]), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{fn}.csv"'})
    if format == "pdf":
        return Response(table_pdf(rep["title"], rep["columns"], rep["rows"], meta, rep.get("totals")), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{fn}.pdf"'})
    return Response(table_xlsx(rep["title"], rep["columns"], rep["rows"], meta, rep.get("totals")), media_type=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="{fn}.xlsx"'})


@router.get("/disclosures")
def get_disclosures(start: Optional[str] = None, end: Optional[str] = None, entity_id: Optional[int] = None,
                    db: Session = Depends(get_db), user: User = Depends(require("disclosure.read"))):
    comp = company_of(db)
    e = parse_date(end) or date.today()
    s = parse_date(start) or fy_of(e, comp.fy_start_month or 4)[0]
    return disclosures(db, user, s, e, entity_id)


@router.get("/disclosures/export")
def export_disclosures(start: Optional[str] = None, end: Optional[str] = None, entity_id: Optional[int] = None,
                       db: Session = Depends(get_db), user: User = Depends(require("export"))):
    comp = company_of(db)
    e = parse_date(end) or date.today()
    s = parse_date(start) or fy_of(e, comp.fy_start_month or 4)[0]
    d = disclosures(db, user, s, e, entity_id)
    audit.log(db, user, "EXPORT", "Disclosure", None, f"{s} to {e}", "format", None, "xlsx")
    db.commit()
    return Response(disclosure_xlsx(d, comp.name), media_type=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="Lease_note_{e:%Y%m%d}.xlsx"'})


@router.get("/payments")
def payments_calendar(start: Optional[str] = None, end: Optional[str] = None, entity_id: Optional[int] = None,
                      db: Session = Depends(get_db), user: User = Depends(require("lease.read"))):
    """Portfolio payment calendar: scheduled lease payments (after approved/draft events) within a date window."""
    from ..engine.calendar_utils import add_months
    from ..engine.decimal_utils import D
    from ..services.lease_service import reporting_run
    s = parse_date(start) or date.today().replace(day=1)
    e = parse_date(end) or month_end(add_months(s, 2))
    rows = []
    for l in accessible_leases(db, user, entity_id):
        run = reporting_run(db, l)
        lines = (run.summary.get("payments") if run else None)
        if lines is None:
            lines = [{"date": p.payment_date.isoformat(), "period_start": p.period_start.isoformat() if p.period_start else None,
                      "period_end": p.period_end.isoformat() if p.period_end else None, "lease_amount": str(p.lease_amount or 0),
                      "non_lease_amount": str(p.non_lease_amount or 0), "category": p.category, "description": p.description,
                      "included": None, "inclusion_reason": ("Exempt lease — expensed" if l.lease_type in ("SHORT_TERM", "LOW_VALUE")
                                                             else "Lessor receipt" if l.role == "LESSOR" else "Not calculated")}
                     for p in l.payments]
        for p in lines:
            d = parse_date(p["date"])
            if d is None or not (s <= d <= e):
                continue
            la, nl = D(p.get("lease_amount") or 0), D(p.get("non_lease_amount") or 0)
            rows.append({"lease_id": l.id, "lease_code": l.lease_code, "description": l.description,
                         "counterparty": l.counterparty.name if l.counterparty else "", "entity": l.entity.code if l.entity else "",
                         "currency": l.currency, "role": l.role, "lease_type": l.lease_type, "status": l.status,
                         "date": d.isoformat(), "period_start": p.get("period_start"), "period_end": p.get("period_end"),
                         "category": p.get("category"), "line_description": p.get("description"), "lease_amount": str(la),
                         "non_lease_amount": str(nl), "total": str(la + nl), "included": p.get("included"),
                         "inclusion_reason": p.get("inclusion_reason"),
                         "direction": "Receipt" if l.role == "LESSOR" or l.lease_type == "SUBLEASE" else "Payment"})
    rows.sort(key=lambda r: (r["date"], r["lease_code"]))
    return {"start": s.isoformat(), "end": e.isoformat(), "rows": rows}


@router.get("/events")
def events_list(event_type: str = "", entity_id: Optional[int] = None, db: Session = Depends(get_db),
                user: User = Depends(require("lease.read"))):
    """All lease events (modifications, reassessments, terminations, impairments ...) across accessible leases."""
    from ..services.lease_service import reporting_run
    types = [t for t in event_type.split(",") if t]
    out = []
    for l in accessible_leases(db, user, entity_id, include_archived=True):
        run = reporting_run(db, l)
        res_by_ref = {e.get("ref"): e for e in (run.summary.get("events", []) if run else [])}
        for ev in l.events:
            if types and ev.event_type not in types:
                continue
            r = ev.result or res_by_ref.get(f"EV-{ev.id}") or {}
            out.append({"id": ev.id, "lease_id": l.id, "lease_code": l.lease_code, "lease_description": l.description,
                        "lease_status": l.status, "event_type": ev.event_type, "subtype": ev.subtype,
                        "effective_date": ev.effective_date, "description": ev.description, "status": ev.status,
                        "liability_before": r.get("liability_before"), "liability_after": r.get("liability_after"),
                        "rou_before": r.get("rou_before"), "rou_after": r.get("rou_after"), "gain_loss": r.get("gain_loss"),
                        "rate_after_pct": r.get("rate_after_pct"), "separate_lease": r.get("separate_lease"),
                        "role": l.role, "balance_label": r.get("balance_label"), "balance_before": r.get("balance_before"),
                        "balance_after": r.get("balance_after"), "classification_after": r.get("classification_after"),
                        "created_at": ev.created_at, "approved_at": ev.approved_at})
    out.sort(key=lambda x: (str(x["effective_date"]), x["lease_code"]), reverse=True)
    return to_jsonable(out)


@router.get("/journals")
def get_journals(start: Optional[str] = None, end: Optional[str] = None, entity_id: Optional[int] = None, summarise: bool = False,
                 db: Session = Depends(get_db), user: User = Depends(require("journal.read"))):
    e = parse_date(end) or month_end(date.today())
    s = parse_date(start) or date(e.year, e.month, 1)
    leases = accessible_leases(db, user, entity_id)
    js = period_journals(db, leases, s, e, summarise)
    posted = {(p.lease_id, p.period_end.isoformat()) for p in db.scalars(select(JournalEntry)).all()}
    for j in js:
        j["posted"] = (j.get("lease_id"), j["period_end"]) in posted
    return js


@router.get("/journals/export")
def journals_export(format: str = "csv", start: Optional[str] = None, end: Optional[str] = None, entity_id: Optional[int] = None,
                    summarise: bool = False, db: Session = Depends(get_db), user: User = Depends(require("export"))):
    e = parse_date(end) or month_end(date.today())
    s = parse_date(start) or date(e.year, e.month, 1)
    comp = company_of(db)
    js = period_journals(db, accessible_leases(db, user, entity_id), s, e, summarise)
    audit.log(db, user, "EXPORT", "Journals", None, f"{s} to {e}", "format", None, format)
    db.commit()
    fn = f"Lease_journals_{s:%Y%m%d}_{e:%Y%m%d}"
    if format == "tally":
        name = get_settings(comp)["journal"].get("tally_company") or comp.name
        return Response(export_tally(js, name), media_type="application/xml", headers={"Content-Disposition": f'attachment; filename="{fn}_Tally.xml"'})
    if format == "sap":
        return Response(export_sap(js), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{fn}_SAP.csv"'})
    if format == "xlsx":
        cols = [{"key": k, "label": l, "type": t} for k, l, t in (("je_ref", "JE ref", "text"), ("date", "Date", "date"),
                                                                    ("lease_code", "Lease", "text"), ("event_label", "Event", "text"),
                                                                    ("account_code", "Account", "text"), ("account_name", "Account name", "text"),
                                                                    ("debit", "Debit", "money"), ("credit", "Credit", "money"),
                                                                    ("narration", "Narration", "text"))]
        rows = [{**{k: j[k] for k in ("je_ref", "date", "lease_code", "event_label", "narration")}, **{k: l[k] for k in
                                                                                                        ("account_code", "account_name", "debit", "credit")}}
                for j in js for l in j["lines"]]
        return Response(table_xlsx("Lease journals", cols, rows, {"Period": f"{s} to {e}"}, {"debit": 1, "credit": 1}),
                        media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{fn}.xlsx"'})
    return Response(export_csv(js), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{fn}.csv"'})


@router.post("/journals/post")
def journals_post(payload: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(require("journal.post"))):
    pe = parse_date(payload.get("period_end"))
    if pe is None or pe != month_end(pe):
        raise HTTPException(400, "period_end must be a month-end date")
    leases = accessible_leases(db, user, payload.get("entity_id"))
    try:
        res = post_period(db, leases, pe, user)
    except ServiceError as exc:
        db.rollback()
        raise HTTPException(exc.status, exc.message)
    db.commit()
    return res
