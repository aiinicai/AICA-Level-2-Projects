"""Extraction on the user's real sample invoice and on synthetic layouts."""
from datetime import date
from decimal import Decimal
from pathlib import Path

from ipt.services.extraction.pipeline import ExtractionPipeline
from tests.pdfgen import gst, make_invoice

SAMPLE = Path(__file__).parent / "fixtures" / "invoices" / "Invoice_INV-2026-0001.pdf"
SUP = gst("08BBBCS2222B1Z")


def _run(services, pdf):
    doc = services.documents.add_files([pdf]).added[0]
    out = ExtractionPipeline(services).run(doc.id)
    assert out.ok, out.message
    return services.invoices.get(out.invoice_id), out


def _codes(services, inv):
    return {f.check_code for f in services.invoices.findings(inv.id)}


def test_user_sample_invoice(services, admin):
    # sample is dated 17-11-2026 -> needs FY 2026-27
    fy = services.companies.create_fy(services.ctx.company_id, 2026, admin)
    services.ctx.fy_id = fy.id
    inv, out = _run(services, SAMPLE)
    assert out.method == "pdf_text"
    assert inv.invoice_no == "INV-2026-0001"
    assert inv.invoice_date == date(2026, 11, 17)
    assert inv.supplier_name == "Smart Business Solutions"
    assert inv.supplier_gstin == "27AABCS1429B1ZB"
    assert inv.place_of_supply == "27" and inv.reverse_charge is False
    assert inv.invoice_total == Decimal("0.00") and inv.cgst == Decimal("0.00")
    assert len(inv.items) == 1 and inv.items[0].description == "Consultancy Recived"
    assert inv.items[0].gst_rate == Decimal("18.00")
    codes = _codes(services, inv)
    assert "SUPPLIER_GSTIN_INVALID" in codes          # check digit of this GSTIN is wrong
    assert "BUYER_GSTIN_MISSING" in codes and "ZERO_VALUE" in codes
    assert inv.status == "needs_review"


def test_intra_state_multi_rate(services, tmp_path):
    pdf = make_invoice(tmp_path / "multi.pdf", supplier_gstin=SUP, buyer_gstin=services.company_gstin,
                       items=[("Cement bags", "2523", "10", "350.00", "3,500.00", "18%", "4,130.00"),
                              ("Sugar", "1701", "50", "40.00", "2,000.00", "5%", "2,100.00")],
                       totals=[("Taxable Value", "5,500.00"), ("CGST", "365.00"), ("SGST", "365.00"),
                               ("Round Off", "0.00"), ("Grand Total", "6,230.00")])
    inv, _ = _run(services, pdf)
    assert inv.invoice_no == "SGT/25-26/0147" and inv.invoice_date == date(2025, 10, 15)
    assert inv.supplier_gstin == SUP and inv.buyer_gstin == services.company_gstin
    assert inv.taxable_total == Decimal("5500.00") and inv.cgst == Decimal("365.00")
    assert inv.sgst == Decimal("365.00") and inv.invoice_total == Decimal("6230.00")
    assert [i.hsn_sac for i in inv.items] == ["2523", "1701"]
    assert [i.gst_rate for i in inv.items] == [Decimal("18.00"), Decimal("5.00")]
    assert _codes(services, inv) == set() and inv.status == "validated"


def test_inter_state_igst_and_wrong_tax_type(services, tmp_path):
    mh = gst("27CCCDE3333C1Z")
    pdf = make_invoice(tmp_path / "igst.pdf", supplier_gstin=mh, buyer_gstin=services.company_gstin,
                       inv_no="MH/889", items=[("Steel rods", "7214", "2", "1000.00", "2,000.00", "18%", "2,360.00")],
                       totals=[("Taxable Value", "2,000.00"), ("IGST", "360.00"), ("Grand Total", "2,360.00")])
    inv, _ = _run(services, pdf)
    assert inv.igst == Decimal("360.00") and inv.cgst is None
    assert "CGST_ON_INTER" not in _codes(services, inv)
    bad = make_invoice(tmp_path / "bad.pdf", supplier_gstin=mh, buyer_gstin=services.company_gstin,
                       inv_no="MH/890", items=[("Steel", "7214", "1", "100.00", "100.00", "18%", "118.00")],
                       totals=[("Taxable Value", "100.00"), ("CGST", "9.00"), ("SGST", "9.00"),
                               ("Grand Total", "118.00")])
    inv2, _ = _run(services, bad)
    assert "CGST_ON_INTER" in _codes(services, inv2) and inv2.status == "needs_review"


def test_credit_note_and_total_mismatch(services, tmp_path):
    pdf = make_invoice(tmp_path / "cn.pdf", title="CREDIT NOTE", supplier_gstin=SUP,
                       buyer_gstin=services.company_gstin, inv_no="CN-12",
                       items=[("Return of cement", "2523", "1", "350.00", "350.00", "18%", "413.00")],
                       totals=[("Taxable Value", "350.00"), ("CGST", "31.50"), ("SGST", "31.50"),
                               ("Grand Total", "500.00")])
    inv, _ = _run(services, pdf)
    assert inv.doc_type == "credit_note"
    codes = _codes(services, inv)
    assert "TOTAL_MISMATCH" in codes and "NOTE_REF_MISSING" in codes


def test_text_only_mode_rejects_images(services, tmp_path):
    from PIL import Image
    img = tmp_path / "scan.png"
    Image.new("RGB", (100, 100), "white").save(img)
    doc = services.documents.add_files([img]).added[0]
    out = ExtractionPipeline(services).run(doc.id, mode="text")
    assert not out.ok and "OCR" in out.message
    assert services.documents.get(doc.id).status == "failed"
