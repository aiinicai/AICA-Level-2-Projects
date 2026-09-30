"""Journal generation, GL resolution, posting and ERP-friendly exports (CSV, Excel, Tally XML, SAP-style)."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal
from typing import Callable, Optional
from xml.sax.saxutils import escape

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import CalcRun, Company, GLMapping, JournalEntry, JournalLine, Lease
from ..engine.calendar_utils import month_end, parse_date
from ..engine.decimal_utils import D, ZERO, q
from ..engine.journals import EVENT_LABELS, ROLE_CATALOG
from . import audit
from .lease_service import ServiceError, reporting_run
from .settings_service import get_settings


def resolver(db: Session, company_id: int) -> Callable[[str, Lease], tuple[str, str]]:
    maps = db.scalars(select(GLMapping).where(GLMapping.company_id == company_id)).all()
    by_role: dict[str, list[GLMapping]] = {}
    for m in maps:
        by_role.setdefault(m.role, []).append(m)

    def resolve(role: str, lease: Lease) -> tuple[str, str]:
        best, score = None, -1
        for m in by_role.get(role, []):
            s = 0
            ok = True
            for attr, val in (("entity_id", lease.entity_id), ("asset_class_id", lease.asset_class_id),
                              ("cost_centre", lease.cost_centre), ("lease_type", lease.lease_type)):
                mv = getattr(m, attr)
                if mv in (None, ""):
                    continue
                if mv == val:
                    s += 1
                else:
                    ok = False
                    break
            if ok and s > score:
                best, score = m, s
        if best is not None:
            return best.account_code, best.account_name or ROLE_CATALOG.get(role, ("", role, ""))[1]
        code, name, _ = ROLE_CATALOG.get(role, ("99999", role.replace("_", " ").title(), ""))
        return code, name
    comp = db.get(Company, company_id)
    resolve.payment_role = (get_settings(comp)["journal"].get("payment_credit_role") or "LESSOR_PAYABLE") if comp else "LESSOR_PAYABLE"
    return resolve


def lease_journals(db: Session, lease: Lease, run: CalcRun, resolve=None, start: date | None = None,
                   end: date | None = None) -> list[dict]:
    resolve = resolve or resolver(db, lease.company_id)
    out = []
    for n, p in enumerate(run.summary.get("postings", []), start=1):
        pe = parse_date(p.get("period_end") or p["date"])
        jd = parse_date(p["date"])
        rpe = month_end(pe)
        if start and rpe < start:
            continue
        if end and jd > end:
            continue
        lines = []
        pay_role = getattr(resolve, "payment_role", "LESSOR_PAYABLE")
        for i, l in enumerate(p["lines"], start=1):
            role = pay_role if (l["role"] == "LESSOR_PAYABLE" and pay_role != "LESSOR_PAYABLE") else l["role"]
            code, name = resolve(role, lease)
            lines.append({"line": i, "role": role, "account_code": code, "account_name": name, "debit": str(q(D(l["debit"]))),
                          "credit": str(q(D(l["credit"]))), "cost_centre": lease.cost_centre or ""})
        dr = sum((D(x["debit"]) for x in lines), ZERO)
        cr = sum((D(x["credit"]) for x in lines), ZERO)
        out.append({"je_ref": f"{lease.lease_code}/{n:04d}", "date": jd.isoformat(), "period_end": rpe.isoformat(),
                    "event": p["event"], "event_label": EVENT_LABELS.get(p["event"], p["event"].title()), "narration": p["narration"],
                    "lease_code": lease.lease_code, "lease_id": lease.id, "entity": lease.entity.code if lease.entity else "",
                    "currency": lease.currency, "run_no": run.run_no, "run_status": run.status, "lines": lines,
                    "total_debit": str(q(dr)), "total_credit": str(q(cr)), "balanced": dr == cr, "ref": p.get("ref") or ""})
    return out


def period_journals(db: Session, leases: list[Lease], start: date, end: date, summarise: bool = False) -> list[dict]:
    if not leases:
        return []
    resolve = resolver(db, leases[0].company_id)
    out = []
    for lease in leases:
        run = reporting_run(db, lease)
        if not run:
            continue
        out += lease_journals(db, lease, run, resolve, start, end)
    out.sort(key=lambda j: (j["date"], j["lease_code"], j["je_ref"]))
    if not summarise:
        return out
    agg: dict = {}
    for j in out:
        key = (j["period_end"], j["event"])
        a = agg.setdefault(key, {"je_ref": f"SUM/{j['period_end']}/{j['event']}", "date": j["period_end"], "period_end": j["period_end"],
                                 "event": j["event"], "event_label": j["event_label"],
                                 "narration": f"{j['event_label']} — all leases (summarised)", "lease_code": "ALL", "entity": "",
                                 "currency": j["currency"], "lines": {}, "run_status": "", "balanced": True})
        for l in j["lines"]:
            k = (l["account_code"], l["account_name"], l["role"])
            cur = a["lines"].setdefault(k, [ZERO, ZERO])
            cur[0] += D(l["debit"])
            cur[1] += D(l["credit"])
    res = []
    for a in agg.values():
        lines = []
        for i, ((code, name, role), (dr, cr)) in enumerate(sorted(a["lines"].items()), start=1):
            net = dr - cr
            lines.append({"line": i, "role": role, "account_code": code, "account_name": name,
                          "debit": str(q(net)) if net > 0 else "0.00", "credit": str(q(-net)) if net < 0 else "0.00", "cost_centre": ""})
        a["lines"] = lines
        a["total_debit"] = str(q(sum((D(x["debit"]) for x in lines), ZERO)))
        a["total_credit"] = str(q(sum((D(x["credit"]) for x in lines), ZERO)))
        a["balanced"] = a["total_debit"] == a["total_credit"]
        res.append(a)
    return sorted(res, key=lambda x: (x["date"], x["event"]))


def post_period(db: Session, leases: list[Lease], period_end: date, user) -> dict:
    from .workflow_service import is_locked
    start = date(period_end.year, period_end.month, 1)
    posted, skipped = 0, []
    resolve = resolver(db, leases[0].company_id) if leases else None
    for lease in leases:
        run = db.scalar(select(CalcRun).where(CalcRun.lease_id == lease.id, CalcRun.status.in_(["Approved", "Posted"]))
                        .order_by(CalcRun.run_no.desc()))
        if run is None:
            skipped.append(f"{lease.lease_code}: no approved calculation")
            continue
        exists = db.scalar(select(JournalEntry.id).where(JournalEntry.lease_id == lease.id, JournalEntry.period_end == period_end))
        if exists:
            skipped.append(f"{lease.lease_code}: already posted for {period_end}")
            continue
        jes = lease_journals(db, lease, run, resolve, start, period_end)
        for j in jes:
            if not j["balanced"]:
                raise ServiceError(f"Unbalanced journal {j['je_ref']} — posting stopped.")
            je = JournalEntry(company_id=lease.company_id, entity_id=lease.entity_id, lease_id=lease.id, calc_run_id=run.id,
                              je_number=j["je_ref"], je_date=parse_date(j["date"]), period_end=period_end, event=j["event"],
                              narration=j["narration"], status="Posted", currency=lease.currency, reference=j["ref"],
                              posted_by=user.id)
            for l in j["lines"]:
                je.lines.append(JournalLine(line_no=l["line"], role=l["role"], account_code=l["account_code"],
                                            account_name=l["account_name"], debit=D(l["debit"]), credit=D(l["credit"]),
                                            cost_centre=l["cost_centre"]))
            db.add(je)
            posted += 1
        if jes and lease.status == "Approved":
            lease.status = "Posted"
        run.status = "Posted"
    audit.log(db, user, "POST_JOURNALS", "ReportingPeriod", period_end, str(period_end), "journals", None,
              f"{posted} journal(s) posted", approval_status="Posted")
    return {"posted": posted, "skipped": skipped}


# --------------------------------------------------------------------------- exports
def export_csv(journals: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["JE Ref", "Date", "Period End", "Lease", "Entity", "Event", "Narration", "Line", "Account Code", "Account Name",
                "Debit", "Credit", "Cost Centre", "Currency", "Calc Status"])
    for j in journals:
        for l in j["lines"]:
            w.writerow([j["je_ref"], j["date"], j["period_end"], j["lease_code"], j["entity"], j["event_label"], j["narration"],
                        l["line"], l["account_code"], l["account_name"], l["debit"], l["credit"], l["cost_centre"], j["currency"],
                        j.get("run_status", "")])
    return buf.getvalue().encode("utf-8-sig")


def export_sap(journals: list[dict], company_code: str = "1000") -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["CompanyCode", "DocumentDate", "PostingDate", "DocumentType", "Reference", "HeaderText", "LineItem",
                "PostingKey", "GLAccount", "Amount", "Currency", "CostCenter", "ItemText"])
    for j in journals:
        d = parse_date(j["date"]).strftime("%d.%m.%Y")
        for l in j["lines"]:
            dr, cr = D(l["debit"]), D(l["credit"])
            amt, key = (dr, "40") if dr else (cr, "50")
            if not amt:
                continue
            w.writerow([company_code, d, d, "SA", j["je_ref"][:16], j["narration"][:25], l["line"], key, l["account_code"],
                        f"{amt:.2f}", j["currency"], l["cost_centre"], j["narration"][:50]])
    return buf.getvalue().encode("utf-8-sig")


def export_tally(journals: list[dict], company_name: str) -> bytes:
    """Tally Prime / ERP 9 XML (Import Data → Vouchers). Ledger names must exist in Tally."""
    parts = ["<ENVELOPE>", "<HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>", "<BODY><IMPORTDATA>",
             "<REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME><STATICVARIABLES>"
             f"<SVCURRENTCOMPANY>{escape(company_name)}</SVCURRENTCOMPANY></STATICVARIABLES></REQUESTDESC>", "<REQUESTDATA>"]
    for j in journals:
        d = parse_date(j["date"]).strftime("%Y%m%d")
        parts.append('<TALLYMESSAGE xmlns:UDF="TallyUDF"><VOUCHER VCHTYPE="Journal" ACTION="Create" OBJVIEW="Accounting Voucher View">')
        parts.append(f"<DATE>{d}</DATE><EFFECTIVEDATE>{d}</EFFECTIVEDATE><VOUCHERTYPENAME>Journal</VOUCHERTYPENAME>")
        parts.append(f"<VOUCHERNUMBER>{escape(j['je_ref'])}</VOUCHERNUMBER><PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>")
        parts.append(f"<NARRATION>{escape(j['narration'] + ' [' + j['lease_code'] + ']')}</NARRATION>")
        for l in j["lines"]:
            dr, cr = D(l["debit"]), D(l["credit"])
            if dr:
                parts.append(f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{escape(l['account_name'])}</LEDGERNAME>"
                             f"<ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-{dr:.2f}</AMOUNT></ALLLEDGERENTRIES.LIST>")
            if cr:
                parts.append(f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{escape(l['account_name'])}</LEDGERNAME>"
                             f"<ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>{cr:.2f}</AMOUNT></ALLLEDGERENTRIES.LIST>")
        parts.append("</VOUCHER></TALLYMESSAGE>")
    parts += ["</REQUESTDATA>", "</IMPORTDATA></BODY>", "</ENVELOPE>"]
    return "\n".join(parts).encode("utf-8")
