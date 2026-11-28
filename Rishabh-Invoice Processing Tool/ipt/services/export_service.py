"""Export Centre: Excel (one report or the 12-sheet workbook), CSV, PDF and a Tally XML batch."""
from __future__ import annotations

import csv
import html
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from ipt.core import permissions as perms
from ipt.core.context import AppContext
from ipt.core.money import format_inr
from ipt.db.base import Database
from ipt.services import audit_service
from ipt.services.reports_service import Report, ReportService

WORKBOOK_SHEETS = ["Invoice Summary", "Item Details", "Supplier Master", "Purchase Register", "GST Summary",
                   "HSN Summary", "Ledger Mapping", "Stock Item Mapping", "Recon Summary", "Recon Details",
                   "Exception Report", "ITC Analysis"]


def _cell(v):
    if isinstance(v, Decimal):
        return float(v)
    return v


def _text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, Decimal):
        return format_inr(v)
    if isinstance(v, datetime):
        return v.strftime("%d-%m-%Y %H:%M")
    if isinstance(v, date):
        return v.strftime("%d-%m-%Y")
    return str(v)


def write_sheet(ws, rep: Report) -> None:
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    ws.append(rep.headers)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="DBEAFE")
    money = set(rep.money_columns())
    for row in rep.rows:
        ws.append([_cell(v) for v in row])
    if rep.totals:
        ws.append([_cell(v) for v in rep.totals])
        for c in ws[ws.max_row]:
            c.font = Font(bold=True)
    for r in ws.iter_rows(min_row=2):
        for c in r:
            if c.column - 1 in money:
                c.number_format = "#,##,##0.00"
            elif isinstance(c.value, (date, datetime)):
                c.number_format = "DD-MM-YYYY"
    for i, h in enumerate(rep.headers, 1):
        width = max([len(str(h))] + [len(_text(r[i - 1])) for r in rep.rows[:200] if i - 1 < len(r)])
        ws.column_dimensions[get_column_letter(i)].width = min(max(10, width + 2), 60)
    ws.freeze_panes = "A2"
    if rep.note:
        ws.append([])
        ws.append([rep.note])


class ExportService:
    def __init__(self, db: Database, ctx: AppContext, reports: ReportService, invoices=None, vouchers=None):
        self.db, self.ctx, self.reports, self.invoices, self.vouchers = db, ctx, reports, invoices, vouchers

    def _require(self):
        perms.require(self.ctx.user.role if self.ctx.user else None, "export.run")

    def _audit(self, kind: str, target: Path, extra: dict | None = None):
        with self.db.session() as s:
            audit_service.record(s, self.ctx.user, "export." + kind, "export", "",
                                 after={"file": str(target), **(extra or {})}, company_id=self.ctx.company_id)

    # ---------------------------------------------------------------- single report
    def report_xlsx(self, rep: Report, target: Path) -> Path:
        from openpyxl import Workbook
        self._require()
        wb = Workbook()
        ws = wb.active
        ws.title = re.sub(r"[\\/*?:\[\]]", "", rep.title)[:31] or "Report"
        write_sheet(ws, rep)
        wb.save(target)
        self._audit("xlsx", target, {"report": rep.key})
        return target

    def report_csv(self, rep: Report, target: Path) -> Path:
        self._require()
        with open(target, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(rep.headers)
            for row in rep.rows + ([rep.totals] if rep.totals else []):
                w.writerow(["" if v is None else (f"{v:.2f}" if isinstance(v, Decimal) else
                                                  v.strftime("%d-%m-%Y") if isinstance(v, date) else v) for v in row])
        self._audit("csv", target, {"report": rep.key})
        return target

    def report_pdf(self, rep: Report, target: Path, company: str = "", period: str = "") -> Path:
        """PDF through PyMuPDF (already used for invoices) - landscape A4, header repeated on each page."""
        import pymupdf
        self._require()
        money = set(rep.money_columns())
        head = "".join(f"<th>{html.escape(h)}</th>" for h in rep.headers)

        def tr(row, bold=False):
            cells = "".join(f"<td class='{'n' if i in money else ''}'>{html.escape(_text(v))}</td>"
                            for i, v in enumerate(row))
            return f"<tr class='{'t' if bold else ''}'>{cells}</tr>"

        body = "".join(tr(r) for r in rep.rows) + (tr(rep.totals, True) if rep.totals else "")
        doc_html = (f"<h2>{html.escape(rep.title)}</h2><p>{html.escape(company)} {html.escape(period)} · generated "
                    f"{datetime.now():%d-%m-%Y %H:%M}</p><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody>"
                    f"</table><p>{html.escape(rep.note)}</p>")
        css = ("* {font-family: sans-serif; font-size: 8pt;} h2 {font-size: 13pt;} table {border-collapse: collapse;}"
               "th {background: #dbeafe; text-align: left;} th, td {border: 0.5px solid #999; padding: 2px 4px;}"
               "td.n {text-align: right;} tr.t td {font-weight: bold;}")
        story = pymupdf.Story(html=doc_html, user_css=css)
        writer = pymupdf.DocumentWriter(str(target))
        page = pymupdf.paper_rect("a4-l")
        where = page + (28, 28, -28, -28)
        more = True
        while more:
            dev = writer.begin_page(page)
            more, _ = story.place(where)
            story.draw(dev)
            writer.end_page()
        writer.close()
        self._audit("pdf", target, {"report": rep.key})
        return target

    # ---------------------------------------------------------------- workbook
    def workbook(self, target: Path, source: str = "books", start: date | None = None, end: date | None = None,
                 progress=None) -> Path:
        """The 12-sheet workbook. Sheets with no data still appear with their headers."""
        from openpyxl import Workbook
        self._require()
        r = self.reports
        wb = Workbook()
        wb.remove(wb.active)
        inv_summary, items = self._invoice_sheets(start, end)
        books = r.documents("books", start, end)
        pr = Report("pr", "Purchase Register", ["Date", "Supplier", "GSTIN", "Supplier inv no", "Type", "Ledger",
                                                "Taxable", "CGST", "SGST", "IGST", "Cess", "Total"],
                    [[d.doc_date, d.supplier, d.gstin, d.doc_no, d.doc_type, d.ledger, d.taxable, d.cgst, d.sgst,
                      d.igst, d.cess, d.total] for d in books])
        r._sum_rows(pr, 6)
        sheets = [inv_summary, items, r.supplier_master(), pr, r.report("rate", source, start, end),
                  r.report("hsn", "ipt", start, end),
                  r.mapping_report("party,purchase_ledger,tax_ledger,charge_ledger,round_off,voucher_type",
                                   "Ledger Mapping"),
                  r.mapping_report("stock_item,godown", "Stock Item Mapping"), r.report("recon_summary"),
                  r.report("recon_details"), r.report("exceptions"), r.report("itc")]
        for name, rep in zip(WORKBOOK_SHEETS, sheets):
            if progress:
                progress(f"Writing {name}")
            write_sheet(wb.create_sheet(name), rep)
        wb.save(target)
        self._audit("workbook", target, {"source": source, "from": str(start), "to": str(end)})
        return target

    def _invoice_sheets(self, start, end) -> tuple[Report, Report]:
        invs = [i for i in (self.invoices.list_invoices() if self.invoices else []) if i.status != "rejected"
                and (start is None or (i.invoice_date and i.invoice_date >= start))
                and (end is None or (i.invoice_date and i.invoice_date <= end))]
        summary = Report("invoices", "Invoice Summary",
                         ["Supplier", "GSTIN", "Invoice no", "Date", "Type", "Status", "Taxable", "CGST", "SGST",
                          "IGST", "Cess", "Total"],
                         [[i.supplier_name, i.supplier_gstin, i.invoice_no, i.invoice_date,
                           (i.doc_type or "").replace("_", " "), i.status, i.taxable_total, i.cgst, i.sgst, i.igst,
                           i.cess, i.invoice_total] for i in invs])
        self.reports._sum_rows(summary, 6)
        items = Report("items", "Item Details", ["Invoice no", "Line", "Description", "HSN/SAC", "Qty", "Unit", "Rate",
                                                 "Taxable", "GST %", "CGST", "SGST", "IGST", "Cess", "Total"],
                       [[i.invoice_no, it.line_no, it.description, it.hsn_sac, it.qty, it.unit, it.rate,
                         it.taxable_value, it.gst_rate, it.cgst, it.sgst, it.igst, it.cess, it.total]
                        for i in invs for it in i.items])
        return summary, items

    # ---------------------------------------------------------------- Tally XML batch
    def tally_xml_batch(self, invoice_ids: list[int], target: Path, mode: str = "inventory") -> tuple[int, list[str]]:
        """One import file with the vouchers of several approved invoices. Returns (vouchers written, skipped)."""
        self._require()
        if self.vouchers is None:
            raise ValueError("Voucher service not available")
        messages, skipped, company = [], [], ""
        for iid in invoice_ids:
            built = self.vouchers.build(iid, mode)
            inv = self.invoices.get(iid) if self.invoices else None
            label = (inv.invoice_no or f"IPT #{iid}") if inv else f"IPT #{iid}"
            if not built.ok:
                skipped.append(f"{label}: {'; '.join(built.blockers)}")
                continue
            m = re.search(r"<TALLYMESSAGE[^>]*>.*?</TALLYMESSAGE>", built.xml, re.S)
            c = re.search(r"<SVCURRENTCOMPANY>(.*?)</SVCURRENTCOMPANY>", built.xml)
            if not m:
                skipped.append(f"{label}: voucher XML not found")
                continue
            company = company or (c.group(1) if c else "")
            messages.append(m.group(0))
        if not messages:
            raise ValueError("None of the selected invoices is ready for Tally:\n" + "\n".join(skipped))
        xml = ("<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC>"
               "<REPORTNAME>Vouchers</REPORTNAME><STATICVARIABLES>"
               f"<SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY></STATICVARIABLES></REQUESTDESC><REQUESTDATA>"
               + "".join(messages) + "</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>")
        Path(target).write_text(xml, encoding="utf-8")
        self._audit("tally_xml_batch", target, {"vouchers": len(messages), "skipped": len(skipped)})
        return len(messages), skipped
