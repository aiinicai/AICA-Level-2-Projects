"""Supplier layout learning: positions learned from approved scanned bills fill gaps on the next bill."""
import datetime as dt
import json
from decimal import Decimal
from types import SimpleNamespace

from ipt.db.base import Database
from ipt.db.models import Company, SupplierLayout
from ipt.services.extraction import layouts
from ipt.services.extraction.parser import ParsedInvoice

SUP = "08AAUCA3699Q1ZE"


def _page(no, date, taxable, cgst, total, shift=0.0):
    """One supplier's bill layout; `shift` moves the whole scan down a little (as real scans do)."""
    s = shift
    return [["Invoice No", 286, 161 + s, 335, 173 + s], ["Dated", 402, 159 + s, 431, 170 + s],
            [no, 285, 173 + s, 342, 188 + s], ["741683866690", 348, 172 + s, 402, 186 + s],
            [date, 401, 172 + s, 454, 185 + s],
            ["Taxable", 250, 420 + s, 290, 430 + s], [taxable, 400, 420 + s, 450, 430 + s],
            ["CGST", 250, 440 + s, 280, 450 + s], [cgst, 410, 440 + s, 450, 450 + s],
            ["SGST", 250, 460 + s, 280, 470 + s], [cgst, 410, 460 + s, 450, 470 + s],
            ["Total", 255, 607 + s, 281, 619 + s], ["29.520 MT", 331, 607 + s, 378, 619 + s],
            [total, 451, 607 + s, 522, 619 + s]]


def _db(tmp_path):
    db = Database.for_file(tmp_path / "t.db")
    db.create_schema()
    return db


def _learn_three(s, cid, tmp_path):
    doc = tmp_path / "doc.pdf"
    bills = [("2359/26-27", "25-Oct-26", dt.date(2026, 10, 25)), ("2360/26-27", "26-Oct-26", dt.date(2026, 10, 26)),
             ("2361/26-27", "27-Oct-26", dt.date(2026, 10, 27))]
    doc.with_name("doc.pdf.ocr.json").write_text(json.dumps(
        [_page(no, txt, "1,000.00", "25.00", "1,050.00", shift=i * 2) for i, (no, txt, _) in enumerate(bills)]))
    for i, (no, _, d) in enumerate(bills):
        inv = SimpleNamespace(supplier_gstin=SUP, page_from=i + 1, company_id=cid, invoice_no=no, invoice_date=d,
                              taxable_total=Decimal("1000"), cgst=Decimal("25"), sgst=Decimal("25"), igst=None,
                              invoice_total=Decimal("1050"))
        assert layouts.learn(s, inv, doc) >= 3
    return doc


def test_learn_then_fill_missing_fields(tmp_path):
    db = _db(tmp_path)
    with db.session() as s:
        c = Company(name="B", gstin="08AJMPB2785Q1ZI", state_code="08", folder_name="b")
        s.add(c)
        s.flush()
        _learn_three(s, c.id, tmp_path)
        rows = {r.field: r for r in s.query(SupplierLayout)}
        assert rows["invoice_no"].samples == 3 and rows["invoice_no"].anchor == "Invoice"
        assert rows["invoice_total"].anchor == "Total"
        # a new bill of the same supplier, scanned 6 pt lower, OCR missed the number, date and total
        p = ParsedInvoice()
        p.put("supplier_gstin", SUP, 0.95)
        p.put("taxable_total", Decimal("2000"), 0.95)
        p.put("cgst", Decimal("50"), 0.95)
        p.put("sgst", Decimal("50"), 0.95)
        filled = layouts.apply(s, c.id, p, _page("2399/26-27", "30-Oct-26", "2,000.00", "50.00", "2,100.00",
                                                 shift=6))
        assert set(filled) == {"invoice_no", "invoice_date", "invoice_total"}
        assert p.fields["invoice_no"] == "2399/26-27"
        assert p.fields["invoice_date"] == dt.date(2026, 10, 30)
        assert p.fields["invoice_total"] == Decimal("2100.00")
        assert p.confidence["invoice_total"] == layouts.GUESS          # three bills agree, amounts add up
        assert p.confidence["invoice_no_source"].startswith("learned")


def test_confident_values_never_replaced_and_bad_sums_flagged(tmp_path):
    db = _db(tmp_path)
    with db.session() as s:
        c = Company(name="B", gstin="08AJMPB2785Q1ZI", state_code="08", folder_name="b")
        s.add(c)
        s.flush()
        _learn_three(s, c.id, tmp_path)
        p = ParsedInvoice()
        p.put("supplier_gstin", SUP, 0.95)
        p.put("invoice_no", "X-1", 0.95)
        p.put("taxable_total", Decimal("2000"), 0.95)
        filled = layouts.apply(s, c.id, p, _page("2399/26-27", "30-Oct-26", "2,000.00", "50.00", "9,999.00"))
        assert p.fields["invoice_no"] == "X-1"                        # a confident reading stays
        assert "invoice_total" in filled
        assert p.confidence["invoice_total"] == layouts.LOW            # 2000 + 0 tax != 9999: user checks


def test_unknown_supplier_or_unsure_gstin_does_nothing(tmp_path):
    db = _db(tmp_path)
    with db.session() as s:
        c = Company(name="B", gstin="08AJMPB2785Q1ZI", state_code="08", folder_name="b")
        s.add(c)
        s.flush()
        _learn_three(s, c.id, tmp_path)
        p = ParsedInvoice()
        p.put("supplier_gstin", SUP, 0.55)                             # GSTIN itself unsure
        assert layouts.apply(s, c.id, p, _page("2399/26-27", "30-Oct-26", "1.00", "1.00", "3.00")) == []
        q = ParsedInvoice()
        q.put("supplier_gstin", "27AAACR5055K1Z7", 0.95)               # nothing learned for this supplier
        assert layouts.apply(s, c.id, q, _page("2399/26-27", "30-Oct-26", "1.00", "1.00", "3.00")) == []


def test_few_samples_or_date_outside_year_stay_low(tmp_path):
    db = _db(tmp_path)
    with db.session() as s:
        c = Company(name="B", gstin="08AJMPB2785Q1ZI", state_code="08", folder_name="b")
        s.add(c)
        s.flush()
        doc = tmp_path / "doc.pdf"
        doc.with_name("doc.pdf.ocr.json").write_text(json.dumps([_page("1/26-27", "25-Oct-26", "1,000.00",
                                                                       "25.00", "1,050.00")]))
        layouts.learn(s, SimpleNamespace(supplier_gstin=SUP, page_from=1, company_id=c.id, invoice_no="1/26-27",
                                         invoice_date=dt.date(2026, 10, 25), taxable_total=Decimal("1000"),
                                         cgst=Decimal("25"), sgst=Decimal("25"), igst=None,
                                         invoice_total=Decimal("1050")), doc)
        p = ParsedInvoice()
        p.put("supplier_gstin", SUP, 0.95)
        layouts.apply(s, c.id, p, _page("2/26-27", "26-Oct-26", "1,000.00", "25.00", "1,050.00"))
        assert p.fields["invoice_no"] == "2/26-27" and p.confidence["invoice_no"] == layouts.LOW  # one sample
    assert not layouts._date_plausible(dt.date(2020, 10, 30), "2413/26-27")
    assert layouts._date_plausible(dt.date.today(), None)


def test_migration_v7_adds_layout_columns(tmp_path):
    db = _db(tmp_path)
    from sqlalchemy import inspect
    cols = {c["name"] for c in inspect(db.engine).get_columns("supplier_layouts")}
    assert {"anchor", "dx", "dy", "samples"} <= cols
