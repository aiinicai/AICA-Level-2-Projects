"""Phase 5: reports, dashboard figures and exports agree with each other and with the purchase register."""
from datetime import date
from decimal import Decimal as D

from tests.test_recon_services import PR_ROWS, _2b, _pr_excel


def _load(services, tmp_path):
    from ipt.services.recon.purchase_register import guess_mapping, read_rows
    _2b(services, tmp_path)
    p = _pr_excel(tmp_path, PR_ROWS[:2])
    _, rows = read_rows(p)
    services.purchases.import_excel(p, None, 3, guess_mapping(rows[2]))
    services.recon.run("tally_2b")


def test_dashboard_reports_and_workbook_totals_agree(services, tmp_path):
    _load(services, tmp_path)
    pr_taxable = sum(r.taxable_value for r in services.purchases.records())
    k = services.reports.kpis("books")
    assert k["taxable"] == pr_taxable == D("30000.00") and k["tax"] == D("1700.00") and k["documents"] == 2
    assert k["recon"] == {"NOT_IN_BOOKS": 1, "AMOUNT_MISMATCH": 1, "MATCHED": 1}
    sup = services.reports.report("supplier", "books")
    assert sup.totals[3] == pr_taxable and sup.rows[0][0] == "Shree Traders"
    monthly = services.reports.report("monthly", "books")
    assert monthly.rows[0][0] == "Oct 2025" and monthly.totals[2] == pr_taxable
    rate = services.reports.report("rate", "books")
    assert {r[0] for r in rate.rows} == {"5%", "Mixed / other"}  # 1,200 on 20,000 is not a GST slab and rate.totals[1] == pr_taxable
    # October only vs a month without data
    assert services.reports.kpis("books", date(2025, 11, 1), date(2025, 11, 30))["documents"] == 0
    for key in ("ledger", "hsn", "recon_summary", "recon_details", "exceptions", "itc", "import_log"):
        services.reports.report(key, "books")
    # 12-sheet workbook: Purchase Register total = dashboard total
    from openpyxl import load_workbook
    from ipt.services.export_service import WORKBOOK_SHEETS
    path = services.exports.workbook(tmp_path / "all.xlsx")
    wb = load_workbook(path)
    assert wb.sheetnames == WORKBOOK_SHEETS
    ws = wb["Purchase Register"]
    total_row = next(r for r in ws.iter_rows(values_only=True) if r[0] == "Total")
    assert D(str(total_row[6])) == pr_taxable


def test_single_report_exports(services, tmp_path):
    _load(services, tmp_path)
    rep = services.reports.report("supplier", "books")
    services.exports.report_xlsx(rep, tmp_path / "s.xlsx")
    services.exports.report_csv(rep, tmp_path / "s.csv")
    services.exports.report_pdf(rep, tmp_path / "s.pdf", "ABC Enterprises", "FY 2025-26")
    import pymupdf
    with pymupdf.open(tmp_path / "s.pdf") as d:
        text = d[0].get_text()
    assert "Shree Traders" in text and "30,000.00" in text
    assert (tmp_path / "s.csv").read_text(encoding="utf-8-sig").splitlines()[0].startswith("Supplier,GSTIN")


def test_tally_xml_batch_skips_unready(services, tmp_path):
    import pytest
    from tests.pdfgen import gst, make_invoice
    from ipt.services.extraction.pipeline import ExtractionPipeline
    pdf = make_invoice(tmp_path / "i.pdf", supplier_gstin=gst("08BBBCS2222B1Z"), buyer_gstin=services.company_gstin,
                       items=[("Sand", "2505", "1", "100.00", "100.00", "5%", "105.00")],
                       totals=[("Taxable Value", "100.00"), ("Grand Total", "105.00")])
    doc = services.documents.add_files([pdf]).added[0]
    iid = ExtractionPipeline(services).run(doc.id).invoice_id
    with pytest.raises(ValueError, match="ready for Tally"):
        services.exports.tally_xml_batch([iid], tmp_path / "b.xml")
