import json
from decimal import Decimal

import pytest
from openpyxl import load_workbook

from ipt.core.permissions import PermissionDenied
from ipt.services.auth_service import AuthService
from ipt.services.extraction.pipeline import ExtractionPipeline
from ipt.services.extraction.sources import find_tesseract
from ipt.services.invoice_service import InvoiceError
from tests.pdfgen import gst, make_invoice

SUP = gst("08BBBCS2222B1Z")
GOOD_TOTALS = [("Taxable Value", "3,500.00"), ("CGST", "315.00"), ("SGST", "315.00"), ("Grand Total", "4,130.00")]
ITEMS = [("Cement bags", "2523", "10", "350.00", "3,500.00", "18%", "4,130.00")]


def _extract(services, tmp_path, name="a.pdf", **kw):
    args = dict(supplier_gstin=SUP, buyer_gstin=services.company_gstin, items=ITEMS, totals=GOOD_TOTALS)
    args.update(kw)
    pdf = make_invoice(tmp_path / name, **args)
    doc = services.documents.add_files([pdf]).added[0]
    out = ExtractionPipeline(services).run(doc.id)
    assert out.ok, out.message
    return out.invoice_id


def test_clean_invoice_approves_and_locks(services, tmp_path):
    iid = _extract(services, tmp_path)
    assert services.invoices.get(iid).status == "validated"
    services.invoices.approve(iid)
    assert services.invoices.get(iid).status == "approved"
    services.invoices.delete(iid)                      # approved but not in Tally: can be deleted
    assert services.invoices.get(iid) is None


def test_approved_invoice_can_be_edited(services, tmp_path):
    from ipt.db.models import AuditLog
    iid = _extract(services, tmp_path)
    services.invoices.approve(iid)
    # a clean correction keeps the approval
    assert services.invoices.update(iid, {"invoice_no": "INV-CORRECTED"}) == "approved"
    inv = services.invoices.get(iid)
    assert inv.status == "approved" and inv.invoice_no == "INV-CORRECTED"
    # an edit that breaks the bill sends it back to review
    assert services.invoices.update(iid, {"invoice_total": "99999"}) == "needs_review"
    assert services.invoices.get(iid).status == "needs_review"
    with services.db.session() as s:
        acts = [a.remark for a in s.query(AuditLog).filter_by(action="invoice.edit_approved")]
    assert acts[0] == "Approved invoice edited – still approved" and acts[1].startswith("Approval removed")


def test_imported_invoice_cannot_be_edited(services, tmp_path):
    from ipt.db.models import Invoice
    iid = _extract(services, tmp_path)
    with services.db.session() as s:
        s.get(Invoice, iid).status = "imported"
    with pytest.raises(InvoiceError, match="already in Tally"):
        services.invoices.update(iid, {"invoice_no": "X"})


def test_only_approvers_edit_approved_invoices(services, tmp_path, admin, db):
    iid = _extract(services, tmp_path)
    services.invoices.approve(iid)
    services.ctx.user = AuthService(db).create_user("acc2", "password123", "accountant", actor=admin)
    from ipt.core.permissions import has_permission
    if has_permission("accountant", "invoice.approve"):
        assert services.invoices.update(iid, {"invoice_no": "A2"}) == "approved"
    else:
        with pytest.raises(PermissionDenied):
            services.invoices.update(iid, {"invoice_no": "A2"})


def test_approval_blocked_until_fixed_then_edit_marks_verified(services, tmp_path):
    iid = _extract(services, tmp_path, totals=[("Taxable Value", "3,500.00"), ("CGST", "315.00"),
                                                ("SGST", "315.00"), ("Grand Total", "4,500.00")])
    with pytest.raises(InvoiceError):
        services.invoices.approve(iid)
    services.invoices.update(iid, {"invoice_total": "4,130.00"})
    inv = services.invoices.get(iid)
    assert inv.invoice_total == Decimal("4130.00") and inv.status == "validated"
    assert json.loads(inv.field_confidence_json)["invoice_total"] == 1.0
    actions = [r.action for r in services.audit.recent()]
    assert "invoice.edit" in actions


def test_admin_override_needs_remark_accountant_cannot(services, tmp_path, admin, db):
    iid = _extract(services, tmp_path, totals=[("Taxable Value", "3,500.00"), ("Grand Total", "9.00")])
    acc = AuthService(db).create_user("acc", "password123", "accountant", actor=admin)
    services.ctx.user = acc
    with pytest.raises(PermissionDenied):
        services.invoices.approve(iid, "please")
    services.ctx.user = admin
    with pytest.raises(InvoiceError):
        services.invoices.approve(iid, "")
    services.invoices.approve(iid, "Supplier confirmed by phone")
    assert services.invoices.get(iid).status == "approved"
    assert "invoice.approve_override" in [r.action for r in services.audit.recent()]


def test_reviewer_cannot_edit_or_delete(services, tmp_path, admin, db):
    iid = _extract(services, tmp_path)
    services.ctx.user = AuthService(db).create_user("rev", "password123", "reviewer", actor=admin)
    with pytest.raises(PermissionDenied):
        services.invoices.update(iid, {"invoice_no": "X"})
    with pytest.raises(PermissionDenied):
        services.invoices.delete(iid)


def test_duplicate_invoice_detected_across_files(services, tmp_path):
    a = _extract(services, tmp_path, "a.pdf", inv_no="SGT-001")
    b = _extract(services, tmp_path, "b.pdf", inv_no="SGT/001", extra_lines=["copy"])
    codes = {f.check_code for f in services.invoices.findings(b)}
    assert "DUPLICATE_INVOICE" in codes
    services.invoices.reject(a, "booked twice")
    services.invoices.revalidate(b)
    assert "DUPLICATE_INVOICE" not in {f.check_code for f in services.invoices.findings(b)}


def test_delete_returns_document_to_queue(services, tmp_path):
    iid = _extract(services, tmp_path)
    doc_id = services.invoices.get(iid).document_id
    services.invoices.delete(iid)
    assert services.documents.get(doc_id).status == "queued"
    assert ExtractionPipeline(services).run(doc_id).ok


def test_supplier_created_once(services, tmp_path):
    _extract(services, tmp_path, "a.pdf", inv_no="A1")
    _extract(services, tmp_path, "b.pdf", inv_no="A2", extra_lines=["second"])
    sups = services.invoices.list_suppliers()
    assert len(sups) == 1 and sups[0][1] == 2 and sups[0][2] == Decimal("8260.00")


def test_export_xlsx(services, tmp_path):
    iid = _extract(services, tmp_path)
    out = services.invoices.export_xlsx([iid], tmp_path / "out.xlsx")
    wb = load_workbook(out)
    assert wb.sheetnames == ["Invoice Summary", "Invoice Item Details"]
    assert wb["Invoice Summary"]["T2"].value == 4130.0
    assert wb["Invoice Item Details"]["D2"].value == "Cement bags"


@pytest.mark.skipif(find_tesseract() is None, reason="Tesseract not installed")
def test_ocr_on_scanned_image(services, tmp_path):
    import pymupdf
    pdf = make_invoice(tmp_path / "s.pdf", supplier_gstin=SUP, buyer_gstin=services.company_gstin, items=ITEMS,
                       totals=GOOD_TOTALS)
    png = tmp_path / "scan.png"
    with pymupdf.open(pdf) as d:
        d[0].get_pixmap(dpi=200).save(png)
    doc = services.documents.add_files([png]).added[0]
    out = ExtractionPipeline(services).run(doc.id)
    assert out.ok and out.method == "ocr"
    inv = services.invoices.get(out.invoice_id)
    assert inv.supplier_gstin == SUP
    assert inv.invoice_total == Decimal("4130.00")


def test_quantity_keeps_three_decimals(services, tmp_path):
    iid = _extract(services, tmp_path)
    services.invoices.update(iid, {}, [{"description": "Quick Lime Loose", "hsn_sac": "2522", "qty": "14.645",
                                        "unit": "MT", "rate": "5975", "taxable_value": "87503.88", "gst_rate": "5",
                                        "cgst": "2187.60", "sgst": "2187.59", "total": "91879.07"}])
    it = services.invoices.get(iid).items[0]
    assert it.qty == Decimal("14.645") and it.rate == Decimal("5975")
    codes = {f.check_code for f in services.invoices.findings(iid)}
    assert "ITEM_AMOUNT_MISMATCH" not in codes


def test_parser_keeps_quantity_decimals(services, tmp_path):
    iid = _extract(services, tmp_path, items=[("Quick Lime", "2522", "14.645", "5975.00", "87,503.88", "5%",
                                                "91,879.07")],
                   totals=[("Taxable Value", "87,503.88"), ("CGST", "2,187.60"), ("SGST", "2,187.59"),
                           ("Round Off", "-0.07"), ("Grand Total", "91,879.00")])
    assert services.invoices.get(iid).items[0].qty == Decimal("14.645")


def test_imported_invoice_cannot_be_deleted(services, tmp_path):
    import pytest
    from ipt.db.models import Invoice
    from ipt.services.invoice_service import InvoiceError
    from tests.pdfgen import gst, make_invoice
    pdf = make_invoice(tmp_path / "x.pdf", supplier_gstin=gst("08BBBCS2222B1Z"), buyer_gstin=services.company_gstin,
                       items=[("Sand", "2505", "1", "100.00", "100.00", "5%", "105.00")],
                       totals=[("Taxable Value", "100.00"), ("Grand Total", "105.00")])
    doc = services.documents.add_files([pdf]).added[0]
    iid = services.invoices.create_from_extraction(doc.id, {"invoice_no": "X-1"}, {"invoice_no": 0.95}, [], 0.0)
    with services.db.session() as s:
        s.get(Invoice, iid).status = "imported"
    with pytest.raises(InvoiceError):
        services.invoices.delete(iid)


def test_supplier_name_taken_from_tally_ledger_with_same_gstin(services, tmp_path):
    from ipt.db.models import TallyMaster
    from tests.pdfgen import gst, make_invoice
    g = gst("08BBBCS2222B1Z")
    with services.db.session() as s:
        s.add(TallyMaster(company_id=services.ctx.company_id, master_type="ledger", name="Shree Cement Traders",
                          primary_group="Sundry Creditors", gstin=g))
    pdf = make_invoice(tmp_path / "n.pdf", supplier_gstin=g, buyer_gstin=services.company_gstin,
                       items=[("Sand", "2505", "1", "100.00", "100.00", "5%", "105.00")],
                       totals=[("Taxable Value", "100.00"), ("Grand Total", "105.00")])
    doc = services.documents.add_files([pdf]).added[0]
    iid = services.invoices.create_from_extraction(doc.id, {"supplier_name": "No. Dated", "supplier_gstin": g},
                                                   {"supplier_name": 0.65, "supplier_gstin": 0.68}, [], 0.0)
    inv = services.invoices.get(iid)
    conf = services.invoices.confidence(inv)
    assert inv.supplier_name == "Shree Cement Traders" and conf["supplier_name"] == 0.95
    assert conf["supplier_gstin"] >= 0.9 and conf["supplier_name_source"] == "Tally ledger"


def test_stray_item_row_and_missing_item_name_are_flagged_at_review(services, tmp_path):
    iid = _extract(services, tmp_path)
    inv = services.invoices.get(iid)
    items = [{"line_no": it.line_no, "description": it.description, "hsn_sac": it.hsn_sac, "qty": it.qty,
              "unit": it.unit, "rate": it.rate, "taxable_value": it.taxable_value, "gst_rate": it.gst_rate}
             for it in inv.items]
    items.append({"line_no": len(items) + 1, "description": "No.", "qty": "10", "unit": "MT", "rate": "0",
                  "taxable_value": None})
    services.invoices.update(iid, {}, items)
    codes = {f.check_code for f in services.invoices.findings(iid)}
    assert {"ITEM_NO_AMOUNT", "ITEM_DESC_MISSING"} <= codes
    assert services.invoices.get(iid).status == "needs_review"
