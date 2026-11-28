"""MIS reports and dashboard figures. Every number comes from stored records; the dashboard, MIS reports and
the Export Centre all use these functions, so their totals always agree.

Two purchase sources:
- 'books': the current purchase register (fetched from Tally or imported) - the statutory figures;
- 'ipt'  : invoices processed in IPT (all except rejected).
"""
from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ipt.core import permissions as perms
from ipt.core.context import AppContext
from ipt.db.base import Database
from ipt.db.models import (Invoice, MappingRule, PurchaseRegisterRecord, PurchaseRegisterUpload, Supplier,
                           TallyImport)
from ipt.services.recon.engine import SOURCE_LABEL, STATUS_ORDER

Z = Decimal("0.00")
SLABS = [Decimal(x) for x in ("0", "0.25", "1.5", "3", "5", "12", "18", "28", "40")]
REPORTS = OrderedDict([
    ("supplier", "Supplier-wise purchases"),
    ("monthly", "Monthly purchases"),
    ("ledger", "Ledger-wise purchases"),
    ("rate", "GST rate summary"),
    ("hsn", "HSN summary (IPT invoice items)"),
    ("recon_summary", "Reconciliation summary"),
    ("recon_details", "Reconciliation details"),
    ("exceptions", "Exception report"),
    ("itc", "ITC analysis"),
    ("import_log", "Tally import log"),
])
MONEY_COLS = {"Taxable", "CGST", "SGST", "IGST", "Cess", "Tax", "Total", "ITC in books", "ITC in 2B", "Difference",
              "Taxable (Tally)", "Taxable (2B)"}


@dataclass
class Report:
    key: str
    title: str
    headers: list[str]
    rows: list[list] = field(default_factory=list)
    totals: list | None = None
    note: str = ""

    def money_columns(self) -> list[int]:
        return [i for i, h in enumerate(self.headers) if h in MONEY_COLS]


@dataclass
class Doc:
    """A purchase document from either source, reduced to what the reports need."""
    supplier: str
    gstin: str
    doc_no: str
    doc_date: date | None
    doc_type: str
    taxable: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    cess: Decimal
    total: Decimal
    ledger: str = ""
    status: str = ""
    items: list = field(default_factory=list)

    @property
    def tax(self) -> Decimal:
        return self.cgst + self.sgst + self.igst + self.cess

    @property
    def sign(self) -> int:
        return -1 if self.doc_type in ("CRN", "credit_note") else 1


def _z(v) -> Decimal:
    return v if v is not None else Z


def _slab(taxable: Decimal, tax: Decimal) -> str:
    if not taxable:
        return "Unknown"
    pct = tax * 100 / taxable
    best = min(SLABS, key=lambda s: abs(s - pct))
    return f"{best.normalize():f}%" if abs(best - pct) <= Decimal("0.25") else "Mixed / other"


class ReportService:
    def __init__(self, db: Database, ctx: AppContext, recon=None, imports=None):
        self.db, self.ctx, self.recon, self.imports = db, ctx, recon, imports

    # ---------------------------------------------------------------- documents
    def documents(self, source: str = "books", start: date | None = None, end: date | None = None,
                  supplier: str = "") -> list[Doc]:
        if not self.ctx.company_id or not self.ctx.fy_id:
            return []
        out: list[Doc] = []
        t = supplier.strip().lower()
        with self.db.session() as s:
            if source == "ipt":
                q = select(Invoice).where(Invoice.company_id == self.ctx.company_id, Invoice.fy_id == self.ctx.fy_id,
                                          Invoice.status != "rejected").options(selectinload(Invoice.items))
                for i in s.scalars(q):
                    out.append(Doc(i.supplier_name or "", i.supplier_gstin or "", i.invoice_no or "", i.invoice_date,
                                   i.doc_type or "tax_invoice", _z(i.taxable_total), _z(i.cgst), _z(i.sgst), _z(i.igst),
                                   _z(i.cess), _z(i.invoice_total), status=i.status, items=list(i.items)))
            else:
                cur = select(PurchaseRegisterUpload.id).where(
                    PurchaseRegisterUpload.company_id == self.ctx.company_id,
                    PurchaseRegisterUpload.fy_id == self.ctx.fy_id, PurchaseRegisterUpload.is_current.is_(True))
                for p in s.scalars(select(PurchaseRegisterRecord).where(PurchaseRegisterRecord.upload_id.in_(cur))):
                    out.append(Doc(p.party_name, p.supplier_gstin, p.supplier_invoice_no,
                                   p.voucher_date or p.supplier_invoice_date, p.doc_type, _z(p.taxable_value), _z(p.cgst),
                                   _z(p.sgst), _z(p.igst), _z(p.cess), _z(p.invoice_total),
                                   ledger=p.purchase_ledger or "Not classified"))
        return [d for d in out if (start is None or (d.doc_date and d.doc_date >= start))
                and (end is None or (d.doc_date and d.doc_date <= end))
                and (not t or t in f"{d.supplier} {d.gstin}".lower())]

    # ---------------------------------------------------------------- dashboard
    def kpis(self, source: str = "books", start: date | None = None, end: date | None = None,
             supplier: str = "") -> dict:
        docs = self.documents(source, start, end, supplier)
        net = lambda attr: sum((getattr(d, attr) * d.sign for d in docs), Z)  # noqa: E731
        months: dict[str, list[Decimal]] = OrderedDict()
        for d in sorted((d for d in docs if d.doc_date), key=lambda d: d.doc_date):
            k = f"{d.doc_date:%b %y}"
            months.setdefault(k, [Z, Z])
            months[k][0] += d.taxable * d.sign
            months[k][1] += d.tax * d.sign
        sup: dict[str, Decimal] = {}
        for d in docs:
            sup[d.supplier or d.gstin or "Unknown"] = sup.get(d.supplier or d.gstin or "Unknown", Z) + d.taxable * d.sign
        top = sorted(sup.items(), key=lambda kv: -kv[1])[:5]
        statuses: dict[str, int] = {}
        if source == "ipt":
            for d in docs:
                statuses[d.status] = statuses.get(d.status, 0) + 1
        recon_counts: dict[str, int] = {}
        if self.recon is not None:
            for r in self.recon.rows():
                recon_counts[r.status] = recon_counts.get(r.status, 0) + 1
        itc_books = itc_2b = Z
        if self.recon is not None:
            for x in self.recon.itc_rows():
                itc_books += _z(x["itc_books"])
                itc_2b += _z(x["itc_2b"])
        return {"documents": len(docs), "suppliers": len({d.gstin or d.supplier for d in docs}),
                "taxable": net("taxable"), "tax": net("cgst") + net("sgst") + net("igst") + net("cess"),
                "total": net("total"), "months": months, "top_suppliers": top, "invoice_status": statuses,
                "recon": {k: recon_counts[k] for k in STATUS_ORDER if k in recon_counts},
                "itc_books": itc_books, "itc_2b": itc_2b}

    # ---------------------------------------------------------------- reports
    def report(self, key: str, source: str = "books", start: date | None = None, end: date | None = None,
               supplier: str = "") -> Report:
        perms.require(self.ctx.user.role if self.ctx.user else None, "report.view")
        fn = getattr(self, f"_r_{key}", None)
        if fn is None:
            raise ValueError(f"Unknown report {key}")
        rep = fn(source, start, end, supplier)
        rep.title = REPORTS[key] + ("" if key.startswith(("recon", "exceptions", "itc", "import")) else
                                    f" – {'Tally books' if source == 'books' else 'IPT invoices'}")
        return rep

    def _sum_rows(self, rep: Report, label_cols: int) -> None:
        if not rep.rows:
            rep.totals = None
            return
        tot = ["Total"] + [""] * (label_cols - 1)
        for c in range(label_cols, len(rep.headers)):
            vals = [r[c] for r in rep.rows if isinstance(r[c], (int, Decimal))]
            tot.append(sum(vals, Z if any(isinstance(v, Decimal) for v in vals) else 0) if vals else "")
        rep.totals = tot

    def _grouped(self, docs: list[Doc], key) -> dict:
        g: dict = OrderedDict()
        for d in docs:
            k = key(d)
            a = g.setdefault(k, [0, Z, Z, Z, Z, Z, Z])
            a[0] += 1
            for i, attr in enumerate(("taxable", "cgst", "sgst", "igst", "cess", "total"), 1):
                a[i] += getattr(d, attr) * d.sign
        return g

    def _r_supplier(self, source, start, end, supplier) -> Report:
        docs = self.documents(source, start, end, supplier)
        g = self._grouped(docs, lambda d: (d.supplier or "Unknown", d.gstin))
        rep = Report("supplier", "", ["Supplier", "GSTIN", "Documents", "Taxable", "CGST", "SGST", "IGST", "Cess",
                                      "Total"],
                     [[k[0], k[1]] + v for k, v in sorted(g.items(), key=lambda kv: -kv[1][1])],
                     note="Credit notes are subtracted.")
        self._sum_rows(rep, 2)
        return rep

    def _r_monthly(self, source, start, end, supplier) -> Report:
        docs = sorted((d for d in self.documents(source, start, end, supplier) if d.doc_date), key=lambda d: d.doc_date)
        g = self._grouped(docs, lambda d: f"{d.doc_date:%Y-%m}")
        rep = Report("monthly", "", ["Month", "Documents", "Taxable", "CGST", "SGST", "IGST", "Cess", "Total"],
                     [[date(int(k[:4]), int(k[5:]), 1).strftime("%b %Y")] + v for k, v in g.items()])
        self._sum_rows(rep, 1)
        return rep

    def _r_ledger(self, source, start, end, supplier) -> Report:
        docs = self.documents(source, start, end, supplier)
        if source == "ipt":
            with self.db.session() as s:
                rules = {r.source_key: r.tally_name for r in s.scalars(select(MappingRule).where(
                    MappingRule.company_id == self.ctx.company_id, MappingRule.entity == "purchase_ledger"))}
            for d in docs:
                intra = (d.gstin[:2] if d.gstin else "") and (d.igst == 0)
                d.ledger = rules.get("intra" if intra else "inter", "Not mapped")
        g = self._grouped(docs, lambda d: d.ledger or "Not classified")
        rep = Report("ledger", "", ["Purchase ledger", "Documents", "Taxable", "CGST", "SGST", "IGST", "Cess", "Total"],
                     [[k] + v for k, v in g.items()],
                     note="Tally books: the purchase ledger(s) of each voucher. IPT: the approved purchase-ledger mapping.")
        self._sum_rows(rep, 1)
        return rep

    def _r_rate(self, source, start, end, supplier) -> Report:
        docs = self.documents(source, start, end, supplier)
        g: dict = OrderedDict()
        for d in docs:
            parts = ([(it.gst_rate, _z(it.taxable_value), _z(it.cgst) + _z(it.sgst) + _z(it.igst) + _z(it.cess))
                      for it in d.items] if source == "ipt" and d.items else [(None, d.taxable, d.tax)])
            for rate, tx, tax in parts:
                if rate is None and source == "ipt" and d.items:
                    k = "Unknown"
                else:
                    k = f"{Decimal(rate).normalize():f}%" if rate is not None else _slab(tx, tax)
                a = g.setdefault(k, [Z, Z])
                a[0] += tx * d.sign
                a[1] += tax * d.sign
        rows = [[k, v[0], v[1]] for k, v in sorted(g.items())]
        rep = Report("rate", "", ["GST rate", "Taxable", "Tax"], rows,
                     note="Tally books have no item rates, so the rate is worked out as tax ÷ taxable value; "
                          "vouchers with several rates show as 'Mixed / other'." if source == "books" else
                     "From IPT invoice items; item tax is used where it was extracted.")
        self._sum_rows(rep, 1)
        return rep

    def _r_hsn(self, source, start, end, supplier) -> Report:
        docs = self.documents("ipt", start, end, supplier)
        g: dict = OrderedDict()
        for d in docs:
            for it in d.items:
                k = it.hsn_sac or "Not given"
                a = g.setdefault(k, [it.description or "", Decimal("0"), Z, Z, Z, Z, Z])
                a[1] += it.qty or 0
                for i, attr in enumerate(("taxable_value", "cgst", "sgst", "igst", "cess"), 2):
                    a[i] += _z(getattr(it, attr)) * d.sign
        rep = Report("hsn", "", ["HSN/SAC", "Description", "Quantity", "Taxable", "CGST", "SGST", "IGST", "Cess"],
                     [[k] + v for k, v in sorted(g.items())], note="Only IPT invoice items carry HSN codes.")
        self._sum_rows(rep, 2)
        if rep.totals:
            rep.totals[2] = ""     # quantities of different units are not added up
        return rep

    def _r_recon_summary(self, source, start, end, supplier) -> Report:
        rows = self.recon.rows() if self.recon else []
        counts: dict[str, list] = {}
        for r in rows:
            d = json.loads(r.differences_json or "{}")
            a = counts.setdefault(r.status, [0, Z, Z])
            a[0] += 1
            for i, src in ((1, "pr"), (2, "2b")):
                v = d.get("taxable", {}).get(src)
                a[i] += Decimal(v) if v not in (None, "None") else Z
        from ipt.services.recon.engine import SUGGESTED_ACTION
        rep = Report("recon_summary", "", ["Status", "Documents", "Taxable (Tally)", "Taxable (2B)",
                                           "Suggested action"],
                     [[k.replace("_", " ").title(), *counts[k], SUGGESTED_ACTION.get(k, "")]
                      for k in STATUS_ORDER if k in counts])
        self._sum_rows(rep, 1)
        if rep.totals:
            rep.totals[-1] = ""
        return rep

    def _r_recon_details(self, source, start, end, supplier) -> Report:
        rows = self.recon.rows(text=supplier) if self.recon else []
        out = []
        for r in rows:
            d = json.loads(r.differences_json or "{}")
            num = lambda h, s: Decimal(d[h][s]) if d.get(h, {}).get(s) not in (None, "None") else None  # noqa: E731
            out.append([r.status.replace("_", " ").title(), r.supplier_name, r.supplier_gstin, r.doc_no, r.doc_date,
                        num("taxable", "pr"), num("taxable", "2b"),
                        "; ".join(json.loads(r.reasons_json or "[]")), r.action_status, r.remarks])
        return Report("recon_details", "", ["Status", "Supplier", "GSTIN", "Invoice no", "Date", "Taxable (Tally)",
                                            "Taxable (2B)", "Reasons", "Action status", "Remarks"], out)

    def _r_exceptions(self, source, start, end, supplier) -> Report:
        rows = self.recon.exceptions() if self.recon else []
        return Report("exceptions", "", ["Status", "Supplier", "GSTIN", "Invoice no", "Main reason",
                                         "Suggested action", "Action status", "Remarks"],
                      [[r.status.replace("_", " ").title(), r.supplier_name, r.supplier_gstin, r.doc_no,
                        (json.loads(r.reasons_json or "[]") or [""])[0], r.suggested_action, r.action_status,
                        r.remarks] for r in rows],
                      note="Reconciliation differences not yet Resolved or Accepted.")

    def _r_itc(self, source, start, end, supplier) -> Report:
        items = self.recon.itc_rows() if self.recon else []
        rep = Report("itc", "", ["Supplier", "GSTIN", "Document", "Date", "Recon status", "ITC in books", "ITC in 2B",
                                 "Difference", "Eligibility", "Reason", "Reviewed by"],
                     [[x["supplier"], x["gstin"], x["doc_no"], x["doc_date"], x["status"].replace("_", " ").title(),
                       x["itc_books"], x["itc_2b"], x["difference"], x["eligibility"], x["reason"], x["reviewed_by"]]
                      for x in items],
                     note="Final ITC eligibility needs professional review; IPT never decides it.")
        self._sum_rows(rep, 5)
        if rep.totals:
            rep.totals[8:] = ["", "", ""]
        return rep

    def _r_import_log(self, source, start, end, supplier) -> Report:
        if not self.ctx.company_id:
            return Report("import_log", "", [])
        with self.db.session() as s:
            imps = list(s.scalars(select(TallyImport).where(TallyImport.company_id == self.ctx.company_id)
                                  .order_by(TallyImport.id)))
            invs = {i.id: i for i in s.scalars(select(Invoice).where(Invoice.id.in_([x.invoice_id for x in imps
                                                                                       if x.invoice_id])))}
        from ipt.core.timefmt import local
        return Report("import_log", "", ["When", "Invoice", "Supplier", "Tally company", "Status", "Created", "Errors",
                                         "Tally ID", "User"],
                      [[local(x.at), invs[x.invoice_id].invoice_no if x.invoice_id in invs else "",
                        invs[x.invoice_id].supplier_name if x.invoice_id in invs else "", x.tally_company, x.status,
                        x.created, x.errors, x.tally_master_id, x.username] for x in imps])

    # ---------------------------------------------------------------- masters for the workbook
    def supplier_master(self) -> Report:
        with self.db.session() as s:
            sups = list(s.scalars(select(Supplier).where(Supplier.company_id == self.ctx.company_id)
                                  .order_by(Supplier.name)))
        return Report("suppliers", "Supplier Master", ["Name", "GSTIN", "PAN", "State", "Tally ledger", "Address"],
                      [[x.name, x.gstin, x.pan, x.state_code, x.tally_ledger_name, x.address] for x in sups])

    def mapping_report(self, entity: str, title: str) -> Report:
        with self.db.session() as s:
            rules = list(s.scalars(select(MappingRule).where(MappingRule.company_id == self.ctx.company_id,
                                                             MappingRule.entity.in_(entity.split(",")))
                                   .order_by(MappingRule.entity, MappingRule.source_key)))
        return Report(entity, title, ["What", "From invoice", "Tally master", "Times used", "Approved by"],
                      [[r.entity.replace("_", " "), r.source_key, r.tally_name, r.times_used, r.approved_by]
                       for r in rules])

    def source_label(self, source: str) -> str:
        return {"books": SOURCE_LABEL["pr"], "ipt": SOURCE_LABEL["ipt"]}.get(source, source)
