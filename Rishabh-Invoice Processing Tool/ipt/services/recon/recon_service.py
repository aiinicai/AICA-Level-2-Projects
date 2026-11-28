"""Runs and stores reconciliations; manual links, action status, ITC review, exceptions and export."""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from ipt.core import permissions as perms
from ipt.core.context import AppContext
from ipt.db.base import Database
from ipt.db.models import (Gstr2bRecord, Gstr2bUpload, Invoice, ItcAnalysis, PurchaseRegisterRecord,
                           PurchaseRegisterUpload, ReconRow, ReconRun, ReconSetting)
from ipt.services import audit_service
from ipt.services.recon.engine import (MODES, SOURCE_LABEL, STAGE_CONF, STATUS_ORDER, SUGGESTED_ACTION, Rec, Row,
                                       Settings, classify, reconcile)

ACTION_STATUSES = ("Pending", "Under Review", "Resolved", "Accepted", "Rejected")
ELIGIBILITY = ("Pending review", "Eligible", "Ineligible", "Blocked (Sec 17(5))", "Deferred", "Reversed")
IPT_DOC_TYPES = {"credit_note": "CRN", "debit_note": "DBN"}
ITC_BANNER = ("ITC figures are computed from the records; final eligibility needs professional review "
              "(Section 16 / 17 conditions, time limits, payment to supplier). IPT never decides it.")


class ReconError(Exception):
    pass


class ReconService:
    def __init__(self, db: Database, ctx: AppContext):
        self.db, self.ctx = db, ctx

    def _role(self):
        return self.ctx.user.role if self.ctx.user else None

    def _user(self) -> str:
        return self.ctx.user.username if self.ctx.user else ""

    # ---------------------------------------------------------------- settings
    def settings(self) -> Settings:
        with self.db.session() as s:
            row = s.scalar(select(ReconSetting).where(ReconSetting.company_id == self.ctx.company_id))
            if row is None:
                return Settings()
            return Settings(row.taxable_tol, row.tax_tol, row.total_tol, row.date_tol_days, row.similarity)

    def save_settings(self, st: Settings) -> None:
        perms.require(self._role(), "recon.run")
        if min(st.taxable_tol, st.tax_tol, st.total_tol) < 0 or st.date_tol_days < 0 or not (50 <= st.similarity <= 100):
            raise ReconError("Tolerances must be zero or more; similarity between 50 and 100")
        with self.db.session() as s:
            row = s.scalar(select(ReconSetting).where(ReconSetting.company_id == self.ctx.company_id))
            before = None
            if row is None:
                row = ReconSetting(company_id=self.ctx.company_id)
                s.add(row)
            else:
                before = {"taxable": str(row.taxable_tol), "tax": str(row.tax_tol), "total": str(row.total_tol),
                          "days": row.date_tol_days, "similarity": row.similarity}
            row.taxable_tol, row.tax_tol, row.total_tol = st.taxable_tol, st.tax_tol, st.total_tol
            row.date_tol_days, row.similarity = st.date_tol_days, st.similarity
            s.flush()
            audit_service.record(s, self.ctx.user, "recon.settings", "recon_setting", row.id, before,
                                 {"taxable": str(st.taxable_tol), "tax": str(st.tax_tol), "total": str(st.total_tol),
                                  "days": st.date_tol_days, "similarity": st.similarity},
                                 company_id=self.ctx.company_id)

    # ---------------------------------------------------------------- data
    def _load(self, s, start: date | None, end: date | None) -> dict[str, list[Rec]]:
        cid, fid = self.ctx.company_id, self.ctx.fy_id

        def in_range(d):
            return d is None or ((start is None or d >= start) and (end is None or d <= end))

        ipt = []
        for inv in s.scalars(select(Invoice).where(Invoice.company_id == cid, Invoice.fy_id == fid,
                                                   Invoice.status != "rejected")):
            if not in_range(inv.invoice_date):
                continue
            ipt.append(Rec("ipt", inv.id, inv.supplier_gstin or "", inv.invoice_no or "", inv.invoice_date,
                           inv.taxable_total, inv.igst, inv.cgst, inv.sgst, inv.cess, inv.invoice_total,
                           IPT_DOC_TYPES.get(inv.doc_type or "", "INV"), inv.supplier_name or ""))
        pr = []
        cur_pr = select(PurchaseRegisterUpload.id).where(PurchaseRegisterUpload.company_id == cid,
                                                         PurchaseRegisterUpload.fy_id == fid,
                                                         PurchaseRegisterUpload.is_current.is_(True))
        for p in s.scalars(select(PurchaseRegisterRecord).where(PurchaseRegisterRecord.upload_id.in_(cur_pr))):
            d = p.supplier_invoice_date or p.voucher_date
            if not in_range(p.voucher_date or d):
                continue
            if (p.narration or "").startswith("[RCM]"):
                continue           # reverse-charge entries are kept out of the reconciliation
            pr.append(Rec("pr", p.id, p.supplier_gstin, p.supplier_invoice_no, d, p.taxable_value, p.igst, p.cgst,
                          p.sgst, p.cess, p.invoice_total, p.doc_type, p.party_name))
        b2b = []
        q = select(Gstr2bUpload).where(Gstr2bUpload.company_id == cid, Gstr2bUpload.fy_id == fid,
                                       Gstr2bUpload.is_current.is_(True))
        up_ids = [u.id for u in s.scalars(q) if
                  (start is None or u.period >= f"{start:%Y-%m}") and (end is None or u.period <= f"{end:%Y-%m}")]
        for g in s.scalars(select(Gstr2bRecord).where(Gstr2bRecord.upload_id.in_(up_ids))):
            if g.doc_type in ("BOE", "ISD"):
                continue           # imports / ISD have no supplier invoice in the purchase register
            if g.reverse_charge:
                continue           # RCM supplies (GTA, legal ...) are not reconciled - tax is paid by the buyer
            b2b.append(Rec("2b", g.id, g.supplier_gstin, g.doc_no, g.doc_date, g.taxable_value, g.igst, g.cgst,
                           g.sgst, g.cess, g.invoice_value, g.doc_type, g.supplier_name, g.section,
                           g.original_doc_no, g.itc_available))
        return {"ipt": ipt, "pr": pr, "2b": b2b}

    def availability(self) -> dict[str, int]:
        with self.db.session() as s:
            d = self._load(s, None, None)
        return {k: len(v) for k, v in d.items()}

    # ---------------------------------------------------------------- run
    def latest_run(self) -> ReconRun | None:
        with self.db.session() as s:
            return s.scalar(select(ReconRun).where(ReconRun.company_id == self.ctx.company_id,
                                                   ReconRun.fy_id == self.ctx.fy_id, ReconRun.is_latest.is_(True))
                            .order_by(ReconRun.id.desc()))

    def run(self, mode: str, start: date | None = None, end: date | None = None) -> ReconRun:
        perms.require(self._role(), "recon.run")
        if mode not in MODES:
            raise ReconError(f"Unknown mode {mode}")
        st = self.settings()
        with self.db.session() as s:
            data = self._load(s, start, end)
            for src in MODES[mode]:
                if not data[src]:
                    raise ReconError(f"No {SOURCE_LABEL[src]} records for this period – load them first")
            prev = s.scalar(select(ReconRun).where(ReconRun.company_id == self.ctx.company_id,
                                                   ReconRun.fy_id == self.ctx.fy_id, ReconRun.is_latest.is_(True))
                            .order_by(ReconRun.id.desc()))
            links, carried = [], {}
            if prev is not None:
                for r in s.scalars(select(ReconRow).where(ReconRow.run_id == prev.id)):
                    ids = {k: v for k, v in (("ipt", r.ipt_invoice_id), ("pr", r.pr_record_id),
                                             ("2b", r.gstr2b_record_id)) if v}
                    if r.is_manual and prev.mode == mode:
                        links.append(ids)
                    if r.action_status != "Pending" or r.remarks:
                        carried[tuple(sorted(ids.items()))] = (r.action_status, r.remarks)
                prev.is_latest = False
            rows = reconcile(data, mode, st, manual_links=links)
            run = ReconRun(company_id=self.ctx.company_id, fy_id=self.ctx.fy_id, mode=mode, period_from=start,
                           period_to=end, run_by=self._user(),
                           settings_json=json.dumps({k: str(v) for k, v in asdict(st).items()}))
            counts: dict[str, int] = {}
            s.add(run)
            s.flush()
            for row in rows:
                counts[row.status] = counts.get(row.status, 0) + 1
                db_row = self._row_to_db(run, row)
                key = tuple(sorted({k: v for k, v in (("ipt", db_row.ipt_invoice_id), ("pr", db_row.pr_record_id),
                                                      ("2b", db_row.gstr2b_record_id)) if v}.items()))
                if key in carried:
                    db_row.action_status, db_row.remarks = carried[key]
                s.add(db_row)
            run.counts_json = json.dumps(counts)
            audit_service.record(s, self.ctx.user, "recon.run", "recon_run", run.id,
                                 after={"mode": mode, "from": str(start), "to": str(end), "counts": counts},
                                 company_id=self.ctx.company_id)
            s.flush()
            return run

    def _row_to_db(self, run: ReconRun, row: Row) -> ReconRow:
        recs = row.recs
        return ReconRow(run_id=run.id, company_id=run.company_id, fy_id=run.fy_id,
                        ipt_invoice_id=recs["ipt"].id if "ipt" in recs else None,
                        pr_record_id=recs["pr"].id if "pr" in recs else None,
                        gstr2b_record_id=recs["2b"].id if "2b" in recs else None,
                        supplier_gstin=row.gstin, supplier_name=str(row.first("name") or "")[:200],
                        doc_no=str(row.first("doc_no") or "")[:60], doc_date=row.first("doc_date"),
                        status=row.status, match_stage=row.stage, confidence=row.confidence,
                        reasons_json=json.dumps(row.reasons), differences_json=json.dumps(row.differences),
                        suggested_action=row.suggested_action, is_manual=row.is_manual)

    # ---------------------------------------------------------------- read
    def rows(self, run_id: int | None = None, status: str | None = None, text: str = "") -> list[ReconRow]:
        run = self.latest_run() if run_id is None else None
        rid = run_id or (run.id if run else None)
        if rid is None:
            return []
        with self.db.session() as s:
            q = select(ReconRow).where(ReconRow.run_id == rid, ReconRow.company_id == self.ctx.company_id)
            if status:
                q = q.where(ReconRow.status == status)
            out = list(s.scalars(q.order_by(ReconRow.id)))
        if text:
            t = text.lower()
            out = [r for r in out if t in f"{r.supplier_name} {r.supplier_gstin} {r.doc_no}".lower()]
        out.sort(key=lambda r: (STATUS_ORDER.index(r.status) if r.status in STATUS_ORDER else 99, r.supplier_gstin,
                                r.doc_no))
        return out

    def get_row(self, row_id: int) -> ReconRow | None:
        with self.db.session() as s:
            r = s.get(ReconRow, row_id)
            return r if r and r.company_id == self.ctx.company_id else None

    def sources_of(self, row: ReconRow) -> dict[str, dict]:
        """Full detail of the IPT invoice, books record and 2B record behind a row (for the compare view)."""
        out = {}
        with self.db.session() as s:
            if row.ipt_invoice_id and (inv := s.get(Invoice, row.ipt_invoice_id)):
                out["ipt"] = {"Supplier": inv.supplier_name, "GSTIN": inv.supplier_gstin, "Invoice no": inv.invoice_no,
                              "Date": inv.invoice_date, "Taxable": inv.taxable_total, "CGST": inv.cgst,
                              "SGST": inv.sgst, "IGST": inv.igst, "Cess": inv.cess, "Total": inv.invoice_total,
                              "Status": inv.status}
            if row.pr_record_id and (p := s.get(PurchaseRegisterRecord, row.pr_record_id)):
                out["pr"] = {"Supplier": p.party_name, "GSTIN": p.supplier_gstin, "Invoice no": p.supplier_invoice_no,
                             "Date": p.supplier_invoice_date, "Taxable": p.taxable_value, "CGST": p.cgst,
                             "SGST": p.sgst, "IGST": p.igst, "Cess": p.cess, "Total": p.invoice_total,
                             "Voucher": f"{p.voucher_type} {p.voucher_no} dt {p.voucher_date:%d-%m-%Y}"
                             if p.voucher_date else p.voucher_no}
            if row.gstr2b_record_id and (g := s.get(Gstr2bRecord, row.gstr2b_record_id)):
                out["2b"] = {"Supplier": g.supplier_name, "GSTIN": g.supplier_gstin, "Invoice no": g.doc_no,
                             "Date": g.doc_date, "Taxable": g.taxable_value, "CGST": g.cgst, "SGST": g.sgst,
                             "IGST": g.igst, "Cess": g.cess, "Total": g.invoice_value,
                             "Section": g.section, "ITC available": g.itc_available}
        return out

    # ---------------------------------------------------------------- user actions
    def update_action(self, row_id: int, action_status: str, remarks: str) -> None:
        perms.require(self._role(), "recon.edit")
        if action_status not in ACTION_STATUSES:
            raise ReconError("Unknown action status")
        with self.db.session() as s:
            r = s.get(ReconRow, row_id)
            if r is None or r.company_id != self.ctx.company_id:
                raise ReconError("Row not found")
            before = {"action_status": r.action_status, "remarks": r.remarks}
            r.action_status, r.remarks, r.updated_by = action_status, remarks, self._user()
            audit_service.record(s, self.ctx.user, "recon.action", "recon_row", r.id, before,
                                 {"action_status": action_status, "remarks": remarks}, company_id=r.company_id)

    def _row_recs(self, s, r: ReconRow) -> dict[str, Rec]:
        data = {}
        if r.ipt_invoice_id and (inv := s.get(Invoice, r.ipt_invoice_id)):
            data["ipt"] = Rec("ipt", inv.id, inv.supplier_gstin or "", inv.invoice_no or "", inv.invoice_date,
                              inv.taxable_total, inv.igst, inv.cgst, inv.sgst, inv.cess, inv.invoice_total,
                              IPT_DOC_TYPES.get(inv.doc_type or "", "INV"), inv.supplier_name or "")
        if r.pr_record_id and (p := s.get(PurchaseRegisterRecord, r.pr_record_id)):
            data["pr"] = Rec("pr", p.id, p.supplier_gstin, p.supplier_invoice_no,
                             p.supplier_invoice_date or p.voucher_date, p.taxable_value, p.igst, p.cgst, p.sgst,
                             p.cess, p.invoice_total, p.doc_type, p.party_name)
        if r.gstr2b_record_id and (g := s.get(Gstr2bRecord, r.gstr2b_record_id)):
            data["2b"] = Rec("2b", g.id, g.supplier_gstin, g.doc_no, g.doc_date, g.taxable_value, g.igst, g.cgst,
                             g.sgst, g.cess, g.invoice_value, g.doc_type, g.supplier_name, g.section,
                             g.original_doc_no, g.itc_available)
        return data

    def manual_link(self, row_ids: list[int], remark: str) -> ReconRow:
        """Join the records of several unmatched rows into one row. The differences are still shown."""
        perms.require(self._role(), "recon.edit")
        if not remark.strip():
            raise ReconError("A remark is required for a manual match")
        with self.db.session() as s:
            rows = [s.get(ReconRow, i) for i in row_ids]
            if len(rows) < 2 or any(r is None or r.company_id != self.ctx.company_id for r in rows):
                raise ReconError("Select at least two rows of this company")
            run = s.get(ReconRun, rows[0].run_id)
            if any(r.run_id != run.id for r in rows) or not run.is_latest:
                raise ReconError("Rows must come from the latest reconciliation run")
            recs: dict[str, Rec] = {}
            for r in rows:
                for src, rec in self._row_recs(s, r).items():
                    if src in recs:
                        raise ReconError(f"Two of the selected rows already have a {SOURCE_LABEL[src]} record")
                    recs[src] = rec
            if len(recs) < 2:
                raise ReconError("Nothing to link")
            new = classify(Row(recs=recs, stage="manual", confidence=STAGE_CONF["manual"], is_manual=True),
                           MODES[run.mode], self.settings())
            db_row = self._row_to_db(run, new)
            db_row.remarks, db_row.updated_by, db_row.action_status = remark, self._user(), "Under Review"
            before = [{"id": r.id, "status": r.status, "doc_no": r.doc_no} for r in rows]
            for r in rows:
                s.delete(r)
            s.add(db_row)
            s.flush()
            audit_service.record(s, self.ctx.user, "recon.manual_match", "recon_row", db_row.id, {"rows": before},
                                 {"status": db_row.status, "remark": remark}, company_id=db_row.company_id)
            return db_row

    def unlink(self, row_id: int, remark: str) -> list[ReconRow]:
        perms.require(self._role(), "recon.edit")
        if not remark.strip():
            raise ReconError("A remark is required to unmatch")
        with self.db.session() as s:
            r = s.get(ReconRow, row_id)
            if r is None or r.company_id != self.ctx.company_id:
                raise ReconError("Row not found")
            run = s.get(ReconRun, r.run_id)
            recs = self._row_recs(s, r)
            if len(recs) < 2:
                raise ReconError("This row has only one record")
            out = []
            for src, rec in recs.items():
                single = classify(Row(recs={src: rec}), MODES[run.mode], self.settings())
                db_row = self._row_to_db(run, single)
                db_row.remarks, db_row.updated_by = f"Unmatched: {remark}", self._user()
                s.add(db_row)
                out.append(db_row)
            before = {"status": r.status, "doc_no": r.doc_no, "manual": r.is_manual}
            s.delete(r)
            s.flush()
            audit_service.record(s, self.ctx.user, "recon.unmatch", "recon_row", row_id, before,
                                 {"rows": [x.id for x in out], "remark": remark}, company_id=run.company_id)
            return out

    # ---------------------------------------------------------------- exceptions & ITC
    def exceptions(self) -> list[ReconRow]:
        return [r for r in self.rows() if r.status != "MATCHED" and r.action_status not in ("Resolved", "Accepted")]

    def itc_rows(self) -> list[dict]:
        """ITC per document from the latest run: in books (Tally, else IPT) vs in GSTR-2B, with the user's review."""
        out = []
        with self.db.session() as s:
            reviews = {(a.supplier_gstin, a.doc_no_normalized, a.doc_type): a for a in s.scalars(
                select(ItcAnalysis).where(ItcAnalysis.company_id == self.ctx.company_id,
                                          ItcAnalysis.fy_id == self.ctx.fy_id))}
            for r in self.rows():
                recs = self._row_recs(s, r)
                book = recs.get("pr") or recs.get("ipt")
                b2 = recs.get("2b")
                itc_books = book.tax() if book else None
                itc_2b = b2.tax() if b2 else None
                any_rec = book or b2
                if any_rec is None:
                    continue          # its bill / records were deleted after this reconciliation ran
                key = (any_rec.gstin, any_rec.norm, any_rec.doc_type)
                timing = self._itc_timing(s, r, book, b2)
                rv = reviews.get(key)
                out.append({"row_id": r.id, "status": r.status, "supplier": r.supplier_name, "gstin": r.supplier_gstin,
                            "doc_no": r.doc_no, "doc_date": r.doc_date, "doc_type": any_rec.doc_type,
                            "itc_books": itc_books, "itc_2b": itc_2b,
                            "difference": (itc_2b or Decimal("0")) - (itc_books or Decimal("0")),
                            "itc_available_2b": b2.itc_available if b2 else "",
                            "eligibility": rv.eligibility if rv else "Pending review",
                            "reason": rv.reason if rv else "", "remarks": rv.remarks if rv else "",
                            "action_taken": rv.action_taken if rv else "", "reviewed_by": rv.reviewed_by if rv else "",
                            "timing": timing, "key": key})
        return out

    @staticmethod
    def _itc_timing(s, r: ReconRow, book, b2) -> str:
        """When the credit can be taken, from what GSTR-2B itself says (never a legal conclusion)."""
        if b2 is not None and r.gstr2b_record_id:
            g = s.get(Gstr2bRecord, r.gstr2b_record_id)
            up = s.get(Gstr2bUpload, g.upload_id) if g else None
            reason = (g.itc_reason or "") if g else ""
            if re.search(r"16\s*\(\s*4\s*\)", reason):
                return "Time-barred per 2B – Sec 16(4)"
            if g and (g.itc_available or "").lower().startswith("n"):
                return "2B: ITC not available" + (f" – {reason}" if reason else "")
            if g and up and g.doc_date:
                months = (int(up.period[:4]) - g.doc_date.year) * 12 + int(up.period[5:7]) - g.doc_date.month
                if months >= 1:
                    return f"Reported late: invoice {g.doc_date:%b-%y}, in 2B of {up.period[5:7]}-{up.period[:4]}"
            return ""
        if book is not None and b2 is None:
            return "Not in 2B yet – claim when it appears (check next months / follow up)"
        return ""

    def export_followup(self, target: Path) -> Path:
        """Supplier-wise list of bills in the books whose GSTR-2B entry is missing or different - to send to
        suppliers for correcting / filing their GSTR-1."""
        from openpyxl import Workbook
        from openpyxl.styles import Font
        perms.require(self._role(), "report.view")
        wanted = ("NOT_IN_2B", "AMOUNT_MISMATCH", "PARTIALLY_MATCHED", "GSTIN_MISMATCH")
        items = []
        with self.db.session() as s:
            for r in self.rows():
                if r.status not in wanted or r.action_status in ("Resolved", "Accepted"):
                    continue
                recs = self._row_recs(s, r)
                book, b2 = recs.get("pr") or recs.get("ipt"), recs.get("2b")
                if book is None:
                    continue
                items.append((r, book, b2))
        wb = Workbook()
        det = wb.active
        det.title = "Bills to follow up"
        head = ["Supplier", "GSTIN", "Invoice no", "Invoice date", "Taxable (books)", "Tax (books)", "Total (books)",
                "Tax in GSTR-2B", "Problem", "What to ask the supplier"]
        det.append(head)
        ask = {"NOT_IN_2B": "Please report this invoice in your GSTR-1 / IFF",
               "AMOUNT_MISMATCH": "Amount in your GSTR-1 differs from the invoice – please amend",
               "PARTIALLY_MATCHED": "Invoice number / date in your GSTR-1 differs – please check and amend",
               "GSTIN_MISMATCH": "Invoice reported under another GSTIN – please amend to ours"}
        f = lambda v: float(v) if v is not None else None  # noqa: E731
        summary: dict[tuple, list] = {}
        for r, book, b2 in sorted(items, key=lambda x: (x[0].supplier_name or "", x[0].doc_date or date.min)):
            det.append([r.supplier_name, r.supplier_gstin, r.doc_no, r.doc_date, f(book.taxable), f(book.tax()),
                        f(book.total), f(b2.tax()) if b2 else None, r.status.replace("_", " ").title(),
                        ask[r.status]])
            k = (r.supplier_name, r.supplier_gstin)
            sm = summary.setdefault(k, [0, Decimal("0")])
            sm[0] += 1
            sm[1] += (book.tax() or Decimal("0")) - ((b2.tax() or Decimal("0")) if b2 else Decimal("0"))
        tot = wb.create_sheet("Supplier summary", 0)
        tot.append(["Supplier", "GSTIN", "Bills", "ITC at stake"])
        for (name, g), (n, amt) in sorted(summary.items(), key=lambda x: -x[1][1]):
            tot.append([name, g, n, float(amt)])
        for ws in (tot, det):
            for c in ws[1]:
                c.font = Font(bold=True)
        wb.save(target)
        return target

    def gstr3b_periods(self) -> list[str]:
        """Return periods (YYYY-MM) with a current GSTR-2B, newest first."""
        with self.db.session() as s:
            return sorted({u.period for u in s.scalars(select(Gstr2bUpload).where(
                Gstr2bUpload.company_id == self.ctx.company_id, Gstr2bUpload.fy_id == self.ctx.fy_id,
                Gstr2bUpload.is_current.is_(True)))}, reverse=True)

    def gstr3b_working(self, period: str):
        from ipt.services.recon import gstr3b
        perms.require(self._role(), "report.view")
        try:
            with self.db.session() as s:
                return gstr3b.build(s, self.ctx.company_id, self.ctx.fy_id, period)
        except ValueError as e:
            raise ReconError(str(e)) from e

    def export_gstr3b(self, period: str, target: Path) -> Path:
        from ipt.db.models import Company
        from ipt.services.recon import gstr3b
        w = self.gstr3b_working(period)
        with self.db.session() as s:
            c = s.get(Company, self.ctx.company_id)
            name = c.name if c else ""
        return gstr3b.export_xlsx(w, name, target)

    def save_itc_review(self, row_id: int, eligibility: str, reason: str, remarks: str, action_taken: str) -> None:
        perms.require(self._role(), "recon.edit")
        if eligibility not in ELIGIBILITY:
            raise ReconError("Unknown eligibility")
        item = next((x for x in self.itc_rows() if x["row_id"] == row_id), None)
        if item is None:
            raise ReconError("Row not found in the latest reconciliation")
        g, norm, dt = item["key"]
        with self.db.session() as s:
            a = s.scalar(select(ItcAnalysis).where(ItcAnalysis.company_id == self.ctx.company_id,
                                                   ItcAnalysis.fy_id == self.ctx.fy_id, ItcAnalysis.supplier_gstin == g,
                                                   ItcAnalysis.doc_no_normalized == norm, ItcAnalysis.doc_type == dt))
            before = None
            if a is None:
                a = ItcAnalysis(company_id=self.ctx.company_id, fy_id=self.ctx.fy_id, supplier_gstin=g,
                                doc_no_normalized=norm, doc_type=dt)
                s.add(a)
            else:
                before = {"eligibility": a.eligibility, "reason": a.reason}
            a.itc_in_books, a.itc_in_2b, a.difference = item["itc_books"], item["itc_2b"], item["difference"]
            a.eligibility, a.reason, a.remarks, a.action_taken = eligibility, reason, remarks, action_taken
            a.reviewed_by, a.reviewed_at = self._user(), datetime.now()
            s.flush()
            audit_service.record(s, self.ctx.user, "itc.review", "itc_analysis", a.id, before,
                                 {"doc": item["doc_no"], "eligibility": eligibility, "reason": reason},
                                 company_id=self.ctx.company_id)

    # ---------------------------------------------------------------- export
    def export_xlsx(self, target: Path, rows: list[ReconRow] | None = None) -> Path:
        from openpyxl import Workbook
        from openpyxl.styles import Font
        perms.require(self._role(), "report.view")
        rows = self.rows() if rows is None else rows
        wb = Workbook()
        ws = wb.active
        ws.title = "Recon Details"
        head = ["Status", "Supplier", "GSTIN", "Invoice no", "Date"]
        for src in ("ipt", "pr", "2b"):
            head += [f"{SOURCE_LABEL[src]} {h}" for h in ("Invoice no", "Taxable", "CGST", "SGST", "IGST")]
        head += ["Match stage", "Confidence", "Reasons", "Suggested action", "Action status", "Remarks", "Manual"]
        ws.append(head)
        for c in ws[1]:
            c.font = Font(bold=True)

        def num(v):
            return float(v) if v not in (None, "None") else None

        for r in rows:
            diff = json.loads(r.differences_json or "{}")
            line = [r.status.replace("_", " ").title(), r.supplier_name, r.supplier_gstin, r.doc_no, r.doc_date]
            for src in ("ipt", "pr", "2b"):
                line += [diff.get("doc_no", {}).get(src)] + [num(diff.get(h, {}).get(src))
                                                             for h in ("taxable", "cgst", "sgst", "igst")]
            line += [r.match_stage, float(r.confidence) if r.confidence is not None else None,
                     "; ".join(json.loads(r.reasons_json or "[]")), r.suggested_action, r.action_status, r.remarks,
                     "Yes" if r.is_manual else ""]
            ws.append(line)
        summary = wb.create_sheet("Recon Summary", 0)
        summary.append(["Status", "Count", "Suggested action"])
        for c in summary[1]:
            c.font = Font(bold=True)
        counts: dict[str, int] = {}
        for r in rows:
            counts[r.status] = counts.get(r.status, 0) + 1
        for stt in STATUS_ORDER:
            if stt in counts:
                summary.append([stt.replace("_", " ").title(), counts[stt], SUGGESTED_ACTION.get(stt, "")])
        wb.save(target)
        return target
