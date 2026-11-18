import os
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models import Company, JournalTemplate, MappingRule, MasterCache, Vendor, VoucherHistory
from app.db.session import local_sessionmaker, make_local_engine
from app.engine import gstr2b, journals, masters as masters_mod, rules
from app.engine.voucher import to_xml
from app.extract import gemini, readers
from app.extract.parser import parse
from app.extract.pipeline import ExtractOptions, process
from app.extract.redact import mask_text
from app.extract.validator import validate
from tests import samples as S


@pytest.fixture
def db(tmp_path):
    eng = make_local_engine(f"sqlite:///{tmp_path / 'l.db'}")
    s = local_sessionmaker(eng, "op@pc")()
    c = Company(tally_guid="g", name="Aarohan Infotech Private Limited", gstin=S.COMPANY_GSTIN, state="Gujarat",
                voucher_style="purchase_accounting", settings={})
    s.add(c)
    s.commit()

    def m(kind, name, parent="", **data):
        s.add(MasterCache(company_id=c.id, kind=kind, name=name, parent=parent, data=data))
    for g, p in [("Sundry Creditors", "Primary"), ("Duties & Taxes", "Primary"), ("Indirect Expenses", "Primary"),
                 ("Creditors - Expenses", "Sundry Creditors")]:
        m("group", g, p)
    m("ledger", "Shree Stationers", "Creditors - Expenses", PARTYGSTIN=S.SUPPLIER_GJ, _gstin=S.SUPPLIER_GJ,
      ISBILLWISEON="Yes", BILLCREDITPERIOD="30 Days")
    m("ledger", "Cloudnine Software Solutions Pvt Ltd", "Sundry Creditors", _gstin=S.SUPPLIER_MH, ISBILLWISEON="No")
    m("ledger", "Printing & Stationery", "Indirect Expenses")
    m("ledger", "Software Expenses", "Indirect Expenses")
    m("ledger", "Office Rent", "Indirect Expenses")
    m("ledger", "Input CGST 9%", "Duties & Taxes", GSTDUTYHEAD="Central Tax")
    m("ledger", "Input SGST 9%", "Duties & Taxes", GSTDUTYHEAD="State Tax")
    m("ledger", "Input IGST 18%", "Duties & Taxes", GSTDUTYHEAD="Integrated Tax")
    m("ledger", "Input CGST RCM", "Duties & Taxes", GSTDUTYHEAD="Central Tax")
    m("ledger", "Output CGST RCM Payable", "Duties & Taxes", GSTDUTYHEAD="Central Tax")
    m("ledger", "TDS on Professional 194J", "Duties & Taxes")
    m("ledger", "Round Off", "Indirect Expenses")
    s.commit()
    return s, c


def _inv(text):
    inv = parse(text, S.COMPANY_GSTIN)
    from app.extract.parser import hsn_codes
    inv.hsn_codes = hsn_codes(text)
    return inv


# ---------------------------------------------------------------- suggestion + learning
def test_first_suggestion_then_learning(db):
    s, c = db
    m = masters_mod.load(s, c.id)
    inv = _inv(S.INTRA)
    sug = rules.suggest(s, c, m, inv)
    v = sug.voucher
    party = v.lines[0]
    assert party.ledger == "Shree Stationers" and party.confidence == "green" and not party.dr
    assert party.amount == Decimal("11800.00") and party.bill_ref == "SS/2026/0457" and party.credit_days == 30
    names = {l.ledger for l in v.lines}
    assert {"Input CGST 9%", "Input SGST 9%"} <= names
    exp = next(l for l in v.lines if l.kind == "expense")
    assert exp.ledger == "" and exp.confidence == "red"           # no rule yet
    exp.ledger = "Printing & Stationery"                          # reviewer picks it
    assert v.balanced
    rules.learn(s, c, inv, v, "op@pc")
    rules.learn(s, c, inv, v, "op@pc")
    sug2 = rules.suggest(s, c, m, inv)
    exp2 = next(l for l in sug2.voucher.lines if l.kind == "expense")
    assert exp2.ledger == "Printing & Stationery" and exp2.confidence == "green"


def test_override_counts_and_new_rule(db):
    s, c = db
    m = masters_mod.load(s, c.id)
    inv = _inv(S.INTRA)
    v = rules.suggest(s, c, m, inv).voucher
    next(l for l in v.lines if l.kind == "expense").ledger = "Printing & Stationery"
    rules.learn(s, c, inv, v, "op")
    next(l for l in v.lines if l.kind == "expense").ledger = "Office Rent"
    rules.learn(s, c, inv, v, "op")
    rs = s.scalars(select(MappingRule)).all()
    assert any(r.overrides == 1 for r in rs) and any(r.target_name == "Office Rent" for r in rs)


def test_interstate_igst_and_tds(db):
    s, c = db
    s.add(Vendor(company_id=c.id, vendor_key=S.SUPPLIER_MH, gstin=S.SUPPLIER_MH, tds_section="194J-T"))
    s.add(MappingRule(company_id=c.id, vendor_key=S.SUPPLIER_MH, target_name="Software Expenses", hits=3))
    # earlier bill this FY takes the aggregate past the Rs 50,000 threshold
    s.add(VoucherHistory(company_id=c.id, guid="p1", date="20260715", voucher_type="Purchase", entries=[
        {"ledger": "Software Expenses", "amount": "30000", "dr": True},
        {"ledger": "Cloudnine Software Solutions Pvt Ltd", "amount": "30000", "dr": False}]))
    s.commit()
    m = masters_mod.load(s, c.id)
    v = rules.suggest(s, c, m, _inv(S.INTER)).voucher
    led = {l.ledger: l for l in v.lines}
    assert led["Input IGST 18%"].amount == Decimal("5310.00")
    tds = next(l for l in v.lines if l.kind == "tds")
    assert tds.amount == Decimal("590") and not tds.dr                 # 2% of 29,500
    assert led["Cloudnine Software Solutions Pvt Ltd"].amount == Decimal("34220.00")
    assert v.balanced


def test_blocked_17_5_puts_gst_in_cost(db):
    s, c = db
    s.add(MappingRule(company_id=c.id, vendor_key=S.SUPPLIER_GJ, target_name="Printing & Stationery", hits=2,
                      blocked_17_5=True))
    s.commit()
    v = rules.suggest(s, c, masters_mod.load(s, c.id), _inv(S.INTRA)).voucher
    assert not any(l.kind == "gst_in" for l in v.lines)
    assert next(l for l in v.lines if l.kind == "expense").amount == Decimal("11800.00")
    assert v.balanced


def test_rcm_unregistered(db):
    s, c = db
    m = masters_mod.load(s, c.id)
    inv = parse("Ramesh Transport\nBill No: 77  Date: 02/11/2026\nFreight charges   5,000.00\nTotal  5,000.00",
                S.COMPANY_GSTIN)
    inv.reverse_charge = True
    sug = rules.suggest(s, c, m, inv)
    kinds = [l.kind for l in sug.voucher.lines]
    assert "gst_rcm_in" in kinds and "gst_rcm_out" in kinds and sug.voucher.balanced
    assert any("self-invoice" in f for f in sug.flags)


def test_duplicate_flag(db):
    s, c = db
    s.add(VoucherHistory(company_id=c.id, guid="x", date="20261106", voucher_type="Purchase", number="12",
                         party="Shree Stationers", reference="SS/2026/457", entries=[]))
    s.commit()
    sug = rules.suggest(s, c, masters_mod.load(s, c.id), _inv(S.INTRA))
    assert any(f.startswith("DUPLICATE?") for f in sug.flags)


def test_warm_start(db):
    s, c = db
    for mth in ("08", "09", "10"):
        s.add(VoucherHistory(company_id=c.id, guid=mth, date=f"2026{mth}05", voucher_type="Purchase", entries=[
            {"ledger": "Printing & Stationery", "amount": "1000", "dr": True},
            {"ledger": "Shree Stationers", "amount": "1000", "dr": False}]))
    s.commit()
    assert rules.warm_start(s, c, masters_mod.load(s, c.id)) == 1
    r = s.scalar(select(MappingRule))
    assert r.target_name == "Printing & Stationery" and r.source == "warm_start" and rules.tier(r) == "amber"


# ---------------------------------------------------------------- voucher XML
def test_voucher_xml(db):
    s, c = db
    v = rules.suggest(s, c, masters_mod.load(s, c.id), _inv(S.INTRA)).voucher
    next(l for l in v.lines if l.kind == "expense").ledger = "Printing & Stationery"
    x = to_xml(v)
    assert '<VOUCHER VCHTYPE="Purchase" ACTION="Create"' in x
    assert "<REFERENCE>SS/2026/0457</REFERENCE>" in x and "<DATE>20261105</DATE>" in x
    assert "<LEDGERNAME>Shree Stationers</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>" in x
    assert "<AMOUNT>-10000.00</AMOUNT>" in x and "<BILLTYPE>New Ref</BILLTYPE>" in x
    assert "<BILLCREDITPERIOD>30 Days</BILLCREDITPERIOD>" in x
    import xml.etree.ElementTree as ET
    ET.fromstring(x)                                               # well-formed


def test_post_to_fake_tally(db, tmp_path):
    from tests import fake_tally
    from app.engine.posting import post
    from app.tally.client import TallyClient
    from app.db.models import Invoice as Row
    s, c = db
    srv, port = fake_tally.start()
    try:
        m = masters_mod.load(s, c.id)
        v = rules.suggest(s, c, m, _inv(S.INTRA)).voucher
        next(l for l in v.lines if l.kind == "expense").ledger = "Printing & Stationery"
        row = Row(company_id=c.id, file_hash="h", file_path="x.pdf")
        s.add(row)
        s.commit()
        r = post(s, s, TallyClient("127.0.0.1", port, 5), c, v, "op@pc", row, set(m.ledgers), set())
        assert r.ok and row.status == "posted" and r.tally_id == "457"
        v.lines[0].ledger = "Ghost Ledger"
        r2 = post(s, s, TallyClient("127.0.0.1", port, 5), c, v, "op@pc", None, set(m.ledgers), set())
        assert not r2.ok and "does not exist" in r2.message
    finally:
        srv.shutdown()


# ---------------------------------------------------------------- journals
def test_roll_narration():
    assert journals.roll_narration("Rent for Oct-26") == "Rent for Nov-26"
    assert journals.roll_narration("Salary for December 2026") == "Salary for January 2027"
    assert journals.roll_narration("Provision 03/2026") == "Provision 04/2026"


def test_template_rent_tds_rcm():
    lines = [{"ledger": "Office Rent", "side": "Dr", "expr": {"type": "input", "key": "rent"}},
             {"ledger": "Input CGST RCM", "side": "Dr", "expr": {"type": "pct", "of": 0, "rate": 9}},
             {"ledger": "Input SGST RCM", "side": "Dr", "expr": {"type": "pct", "of": 0, "rate": 9}},
             {"ledger": "Output CGST RCM", "side": "Cr", "expr": {"type": "pct", "of": 0, "rate": 9}},
             {"ledger": "Output SGST RCM", "side": "Cr", "expr": {"type": "pct", "of": 0, "rate": 9}},
             {"ledger": "TDS on Rent", "side": "Cr", "expr": {"type": "pct", "of": 0, "rate": 10}},
             {"ledger": "Landlord", "side": "Cr", "expr": {"type": "balance"}}]
    out = journals.evaluate(lines, {"rent": Decimal("60000")})
    amt = {l.ledger: l.amount for l in out}
    assert amt["TDS on Rent"] == Decimal("6000.00") and amt["Landlord"] == Decimal("54000.00")
    assert sum(l.amount for l in out if l.dr) == sum(l.amount for l in out if not l.dr)
    assert journals.template_inputs(lines) == ["rent"]


def test_learn_and_clone(db):
    s, c = db
    for i, mth in enumerate(("07", "08", "09", "10")):
        rent = Decimal(60000 + i * 1000)
        s.add(VoucherHistory(company_id=c.id, guid=mth, date=f"2026{mth}28", voucher_type="Journal",
                             narration=f"Rent for {['Jul', 'Aug', 'Sep', 'Oct'][i]}-26", entries=[
                                 {"ledger": "Office Rent", "amount": str(rent), "dr": True},
                                 {"ledger": "TDS on Rent", "amount": str(rent / 10), "dr": False},
                                 {"ledger": "Landlord", "amount": str(rent * 9 / 10), "dr": False}]))
    s.commit()
    rec = journals.recurring_vouchers(s, c.id)
    assert rec and rec[0]["months"] == 4
    v = journals.clone(rec[0]["latest"], "20261128")
    assert v.narration == "Rent for Nov-26" and v.balanced
    made = journals.learn_templates(s, c.id)
    assert len(made) == 1
    t = made[0]
    expr = {l["ledger"]: l["expr"] for l in t.lines}
    assert expr["Office Rent"]["type"] == "input" and expr["TDS on Rent"] == {"type": "pct", "of": 0, "rate": 10.0}
    assert expr["Landlord"]["type"] == "balance"


def test_salary_register(tmp_path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Salary Register Oct-26"])
    ws.append(["Emp", "Name", "Basic", "HRA", "Shift Allowance", "PF Employee", "ESIC Employee", "PT", "TDS", "Net"])
    ws.append([1, "A", 20000, 8000, 1500, 2400, 0, 200, 1000, 25900])
    ws.append([2, "B", 15000, 6000, 0, 1800, 158, 200, 0, 18842])
    ws.append(["Total", "", 35000, 14000, 1500, 4200, 158, 400, 1000, 44742])
    p = tmp_path / "reg.xlsx"
    wb.save(p)
    cols, totals, n = journals.read_register(p)
    assert n == 2 and totals["Basic"] == 35000 and "Net" in cols
    mapping = {"Basic": ("Salary - Basic", "Dr"), "HRA": ("HRA", "Dr"), "Shift Allowance": ("Shift Allowance", "Dr"),
               "PF Employee": ("PF Payable", "Cr"), "ESIC Employee": ("ESIC Payable", "Cr"),
               "PT": ("Professional Tax Payable", "Cr"), "TDS": ("TDS on Salary", "Cr")}
    v = journals.salary_journal(totals, mapping, "Salary Payable", "20261031", "Salary for Oct-26")
    assert v.balanced and next(l for l in v.lines if l.ledger == "Salary Payable").amount == Decimal("44742.00")


# ---------------------------------------------------------------- 2B
def test_2b_reconcile(tmp_path):
    import json
    data = {"data": {"docdata": {"b2b": [
        {"ctin": S.SUPPLIER_GJ, "trdnm": "SHREE STATIONERS", "inv": [
            {"inum": "SS/2026/457", "dt": "05-11-2026", "val": 11800, "rev": "N",
             "items": [{"txval": 10000, "cgst": 900, "sgst": 900, "igst": 0, "cess": 0}]}]},
        {"ctin": S.SUPPLIER_MH, "trdnm": "CLOUDNINE", "inv": [
            {"inum": "CN-1182", "dt": "28-10-2026", "val": 34000, "items": [{"txval": 29500, "igst": 5310}]},
            {"inum": "CN-1190", "dt": "30-10-2026", "val": 1180, "items": [{"txval": 1000, "igst": 180}]}]}]}}}
    p = tmp_path / "2b.json"
    p.write_text(json.dumps(data))
    recs = gstr2b.load(p)
    assert len(recs) == 3 and recs[0].inv_date == "20261105"
    books = [{"id": "1", "supplier_gstin": S.SUPPLIER_GJ, "invoice_no": "SS/2026/0457", "grand_total": "11800",
              "tax_total": "1800"},
             {"id": "2", "supplier_gstin": S.SUPPLIER_MH, "invoice_no": "CN-1182", "grand_total": "34810",
              "tax_total": "5310"},
             {"id": "3", "supplier_gstin": "24AAACL1234F1Z5", "invoice_no": "X1", "grand_total": "100",
              "tax_total": "0"}]
    st = {m.inv_no: m.status for m in gstr2b.reconcile(books, recs)}
    assert st == {"SS/2026/0457": "matched", "CN-1182": "amount_mismatch", "X1": "not_in_2b",
                  "CN-1190": "in_2b_not_booked"}


# ---------------------------------------------------------------- extraction formats + privacy
@pytest.mark.parametrize("writer,ext", [(S.write_pdf, ".pdf"), (S.write_docx, ".docx"), (S.write_xlsx, ".xlsx")])
def test_pipeline_formats(tmp_path, writer, ext, qapp):
    p = writer(S.INTRA, tmp_path / f"inv{ext}")
    r = process(p, ExtractOptions(company_gstin=S.COMPANY_GSTIN, use_gemini=False), date(2026, 11, 11))
    i = r.invoice
    assert (i.supplier_gstin, i.invoice_no, i.invoice_date) == (S.SUPPLIER_GJ, "SS/2026/0457", "20261105"), r.trail
    assert i.grand_total == Decimal("11800.00") and i.cgst_total == Decimal("900.00")
    assert r.validation.status in ("green", "amber"), r.validation.issues


def test_validator_catches_errors():
    v = validate(parse(S.BAD_TOTAL, S.COMPANY_GSTIN), S.COMPANY_GSTIN, "24", date(2026, 11, 11))
    assert v.status == "red" and any(i.field == "grand_total" for i in v.issues)
    v2 = validate(parse(S.WRONG_TAX_TYPE, S.COMPANY_GSTIN), S.COMPANY_GSTIN, "24", date(2026, 11, 11))
    assert any("IGST charged on an intra-state" in i.message for i in v2.issues)
    v3 = validate(parse(S.INTRA, S.COMPANY_GSTIN), S.COMPANY_GSTIN, "24", date(2028, 1, 5))
    assert any("time-barred" in i.message for i in v3.issues)


def test_masking_keeps_gstin_hides_pan_and_bank():
    masked, n = mask_text(S.INTRA)
    assert S.SUPPLIER_GJ in masked and S.COMPANY_GSTIN in masked
    assert "ABCPS1234K " not in masked + " " and "50200012345678" not in masked and "HDFC0001234" not in masked
    assert n >= 3


def test_gemini_payload_mapping():
    inv = gemini.from_payload({"supplier_gstin": S.SUPPLIER_MH, "invoice_no": "CN-1182", "invoice_date": "28-10-2026",
                               "taxable_total": 29500, "igst_total": 5310, "grand_total": 34810,
                               "lines": [{"description": "Subscription", "hsn": "997331", "taxable": 29500,
                                          "gst_rate": 18}]})
    assert inv.invoice_date == "20261028" and inv.taxes[0].igst == Decimal("5310.00")
    assert validate(inv, S.COMPANY_GSTIN, "24", date(2026, 11, 11)).status != "red"


def test_ccitt_tiff_header():
    t = readers._ccitt_to_tiff(b"\x00" * 10, 100, 50, -1, False)
    assert t[:4] == b"II*\x00" and len(t) > 100


def test_scanned_image_ocr_and_redaction(tmp_path, qapp):
    from app.extract import ocr as ocr_mod
    if not ocr_mod._tesseract_exe() and os.name != "nt":
        pytest.skip("no OCR engine on this machine")
    from PyQt6.QtGui import QColor, QFont, QImage, QPainter
    img = QImage(1700, 2200, QImage.Format.Format_RGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    f = QFont("DejaVu Sans Mono")
    f.setPointSize(13)
    p.setFont(f)
    p.setPen(QColor("black"))
    for i, ln in enumerate(S.INTRA.splitlines()):
        p.drawText(40, 80 + 42 * i, ln)
    p.end()
    path = tmp_path / "scan.png"
    img.save(str(path))
    r = process(path, ExtractOptions(company_gstin=S.COMPANY_GSTIN, use_gemini=False), date(2026, 11, 11))
    assert r.invoice.source == "ocr" and r.invoice.grand_total == Decimal("11800.00"), r.trail
    from app.extract.redact import redact_image
    words = ocr_mod.ocr(path.read_bytes()).words
    _, n = redact_image(path.read_bytes(), words, 1700)
    assert n >= 3                     # PAN, account number, IFSC


def test_tally_printed_layout_values_below_labels_and_phone_number():
    inv = parse(S.TALLY_STYLE, S.COMPANY_GSTIN)
    assert inv.supplier_name == "S K AGENCIES"
    assert (inv.invoice_no, inv.invoice_date) == ("SKP/1125/26-27", "20261106")
    assert inv.taxable_total == Decimal("236140.00") and inv.grand_total == Decimal("278645.00")
    assert inv.round_off == Decimal("-0.20")
    assert validate(inv, S.COMPANY_GSTIN, "24", date(2026, 11, 11)).status == "green"


def test_utility_bill_without_gst():
    inv = parse(S.UTILITY, S.COMPANY_GSTIN)
    assert (inv.invoice_no, inv.invoice_date) == ("TP/26/0098123", "20261104")
    assert inv.grand_total == Decimal("12282.00")          # not the after-due-date amount, not service no


def test_scan_sends_redacted_image_to_gemini(tmp_path, qapp, monkeypatch):
    from app.extract import ocr as ocr_mod, pipeline
    if not ocr_mod._tesseract_exe() and os.name != "nt":
        pytest.skip("no OCR engine")
    from PyQt6.QtGui import QColor, QFont, QImage, QPainter
    img = QImage(1700, 1200, QImage.Format.Format_RGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    f = QFont("DejaVu Sans Mono")
    f.setPointSize(13)
    p.setFont(f)
    p.setPen(QColor("black"))
    for i, ln in enumerate(["Some Vendor", "PAN: ABCPS1234K", "Bank A/c No: 50200012345678", "Total 999"]):
        p.drawText(40, 80 + 42 * i, ln)
    p.end()
    path = tmp_path / "scan.png"
    img.save(str(path))
    seen = {}

    def fake_extract(key, model, *, text="", images=None, file_name="", redactions=0, **kw):
        seen.update(text=text, image=(images or [b""])[0], redactions=redactions)
        return gemini.from_payload({"supplier_gstin": S.SUPPLIER_GJ, "invoice_no": "X1", "invoice_date": "01-11-2026",
                                    "taxable_total": 999, "grand_total": 999})
    monkeypatch.setattr(pipeline.gemini, "extract", fake_extract)
    r = pipeline.process(path, ExtractOptions(company_gstin=S.COMPANY_GSTIN, gemini_key="k"), date(2026, 11, 11))
    assert seen["image"] and seen["redactions"] >= 2
    assert "ABCPS1234K" not in seen["text"] and "50200012345678" not in seen["text"]
    assert r.invoice.invoice_no == "X1"


def test_best_flash_model_pick():
    models = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.8-flash-lite",
              "gemini-3.9-flash-preview-0915", "gemini-3.1-pro-preview", "gemini-3.8-flash-image"]
    assert gemini.best_flash(models) == "gemini-3.8-flash"


def test_gemini_self_correction(monkeypatch):
    calls = []
    first = {"document_type": "tax_invoice", "supplier_gstin": S.SUPPLIER_GJ, "invoice_no": "A1",
             "invoice_date": "05-11-2026", "taxable_total": 6111967912, "cgst_total": 21252.6, "sgst_total": 21252.6,
             "grand_total": 6112010419}
    fixed = dict(first, taxable_total=236140, grand_total=278645, round_off=-0.2)

    def fake_call(key, model, parts, timeout):
        calls.append(parts)
        return first if len(calls) == 1 else fixed
    monkeypatch.setattr(gemini, "_call", fake_call)
    monkeypatch.setattr(gemini, "resolve_model", lambda k, m: "gemini-x-flash")
    chk = lambda inv: [i.message for i in validate(inv, S.COMPANY_GSTIN, "24", date(2026, 11, 11)).issues
                       if i.level == "error"]
    inv = gemini.extract("k", "auto", text="t", check=chk)
    assert len(calls) == 2 and "fails these checks" in calls[1][-1]["text"]
    assert inv.taxable_total == Decimal("236140.00") and inv.grand_total == Decimal("278645.00")
    assert not chk(inv)


def test_gemini_first_with_cross_check(tmp_path, qapp, monkeypatch):
    from app.extract import pipeline
    p = S.write_pdf(S.INTRA, tmp_path / "i.pdf")
    payload = {"document_type": "tax_invoice", "supplier_name": "Shree Stationers", "supplier_gstin": S.SUPPLIER_GJ,
               "buyer_gstin": S.COMPANY_GSTIN, "invoice_no": "SS/2026/0457", "invoice_date": "05-11-2026",
               "taxable_total": 10000, "cgst_total": 900, "sgst_total": 900, "grand_total": 11800,
               "tax_summary": [{"gst_rate": 18, "taxable": 10000, "cgst": 900, "sgst": 900}]}
    monkeypatch.setattr(pipeline.gemini, "_call", lambda *a, **k: payload)
    monkeypatch.setattr(pipeline.gemini, "resolve_model", lambda k, m: "gemini-x-flash")
    r = pipeline.process(p, ExtractOptions(company_gstin=S.COMPANY_GSTIN, gemini_key="k", company_name="Aarohan"),
                         date(2026, 11, 11))
    assert r.invoice.source == "gemini" and r.validation.status == "green"
    assert r.invoice.field_confidence["invoice_no"] == 0.98          # Gemini and text layer agree
    payload["invoice_no"] = "SS/2026/0475"                             # disagreement must be surfaced
    r2 = pipeline.process(p, ExtractOptions(company_gstin=S.COMPANY_GSTIN, gemini_key="k"), date(2026, 11, 11))
    assert r2.validation.status == "amber" and any("Invoice no" in i.message for i in r2.validation.issues)


def test_no_key_falls_back_to_local(tmp_path, qapp):
    p = S.write_pdf(S.INTRA, tmp_path / "i.pdf")
    r = process(p, ExtractOptions(company_gstin=S.COMPANY_GSTIN), date(2026, 11, 11))
    assert r.invoice.source == "text" and any("no API key" in t for t in r.trail)


def test_debug_bundle_masks_identity(tmp_path):
    from types import SimpleNamespace
    from app.extract.debug_bundle import export
    inv = parse(S.TALLY_STYLE, S.COMPANY_GSTIN)
    row = SimpleNamespace(extraction={**inv.to_json(), "_text": S.TALLY_STYLE, "_trail": ["Local reading: green"]},
                          validation={"status": "green", "issues": []}, file_path="x.pdf", extraction_source="text")
    comp = SimpleNamespace(name="Aarohan Infotech Private Limited")
    out = export(row, comp, tmp_path).read_text(encoding="utf-8")
    for secret in ("S K AGENCIES", "Aarohan Infotech", S.SUPPLIER_GJ, S.COMPANY_GSTIN, "6112010419",
                   "920020045671234", "UTIB0001234", "382330"):
        assert secret not in out, secret
    for kept in ("2,36,140.00", "21,252.60", "2,78,645.00", "CGST @ 9%", "Invoice No.", "6-Nov-2026", "24XXXXX"):
        assert kept in out, kept


def test_heal_split_tokens_in_pdf_text():
    from app.extract.readers import heal_pdf_text as h
    assert h("CGST @ 9%   21,25 2.60") == "CGST @ 9%   21,252.60"
    assert h("Total ₹ 2,78,64 5.00") == "Total ₹ 2,78,645.00"
    assert h("SKP/1125 /26-27") == "SKP/1125/26-27"
    assert h("₹ 2 ,78,645.00") == "₹ 2,78,645.00" and h("2,78,645 .00") == "2,78,645.00"   # split before , / .
    assert h("Naroda      SKP/112 5/2 6-2 7         6-Nov-2026") == "Naroda      SKP/1125/26-27         6-Nov-2026"
    assert h("CGST @ 9%      2 1,2 52.60") == "CGST @ 9%      21,252.60"
    assert h("GSTIN/UIN: 2 4ABCPS12 34K1ZS") == "GSTIN/UIN: 24ABCPS1234K1ZS"
    assert h("Qty   2   10.00") == "Qty   2   10.00"            # separate columns stay separate
    assert h("2,36,140.00 21,252.60") == "2,36,140.00 21,252.60"


def test_tally_style_pdf_end_to_end(tmp_path, qapp):
    p = S.write_pdf(S.TALLY_STYLE, tmp_path / "rr.pdf")
    r = process(p, ExtractOptions(company_gstin=S.COMPANY_GSTIN), date(2026, 11, 11))
    i = r.invoice
    assert (i.supplier_name, i.invoice_no, i.taxable_total, i.grand_total) == \
        ("S K AGENCIES", "SKP/1125/26-27", Decimal("236140.00"), Decimal("278645.00"))
    assert r.validation.status == "green"


def test_gemini_404_switches_to_newest_flash(monkeypatch):
    calls = []

    def fake_call(key, model, parts, timeout):
        calls.append(model)
        if model == "gemini-2.5-flash":
            raise gemini.GeminiError("Gemini HTTP 404 (gemini-2.5-flash): no longer available")
        return {"document_type": "tax_invoice", "supplier_gstin": S.SUPPLIER_GJ, "invoice_no": "A", "invoice_date":
                "01-11-2026", "taxable_total": 100, "grand_total": 100}
    monkeypatch.setattr(gemini, "_call", fake_call)
    monkeypatch.setattr(gemini, "resolve_model", lambda k, m: m)
    monkeypatch.setattr(gemini, "list_models", lambda k: ["gemini-3.5-flash", "gemini-3.8-flash"])
    inv = gemini.extract("k", "gemini-2.5-flash", text="x")
    assert calls == ["gemini-2.5-flash", "gemini-3.8-flash"] and inv.model == "gemini-3.8-flash"


def test_lite_model_pick_and_escalation(monkeypatch):
    ms = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.5-flash"]
    assert gemini.best_flash(ms, lite=True) == "gemini-3.5-flash-lite"
    bad = {"document_type": "tax_invoice", "supplier_gstin": S.SUPPLIER_GJ, "invoice_no": "A",
           "invoice_date": "01-11-2026", "taxable_total": 100, "cgst_total": 9, "sgst_total": 9, "grand_total": 500}
    good = dict(bad, grand_total=118)
    calls = []

    def fake_call(key, model, parts, timeout):
        calls.append(model)
        return good if model == "gemini-3.8-flash" else bad
    monkeypatch.setattr(gemini, "_call", fake_call)
    monkeypatch.setattr(gemini, "resolve_model", lambda k, m: m)
    monkeypatch.setattr(gemini, "list_models", lambda k: ms)
    chk = lambda inv: [i.message for i in validate(inv, S.COMPANY_GSTIN, "24", date(2026, 11, 11)).issues
                       if i.level == "error"]
    inv = gemini.extract("k", "gemini-3.5-flash-lite", text="x", check=chk)
    assert calls == ["gemini-3.5-flash-lite", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
    assert inv.grand_total == Decimal("118.00") and inv.model == "gemini-3.8-flash"


# ---------------------------------------------------------------- new: ledger creation, entry type, TDS history
def test_create_ledger_xml_and_fake_tally(db):
    from app.engine.ledgers import create_ledger
    from app.tally.masters_write import ledger_xml
    from app.tally.client import TallyClient
    from tests import fake_tally
    x = ledger_xml(name="New Vendor & Co", parent="Sundry Creditors", gstin=S.SUPPLIER_MH, bill_wise=True)
    assert "<PARENT>Sundry Creditors</PARENT>" in x and "<LEDSTATENAME>Maharashtra</LEDSTATENAME>" in x
    assert f"<GSTIN>{S.SUPPLIER_MH}</GSTIN>" in x and "New Vendor &amp; Co" in x
    import xml.etree.ElementTree as ET
    ET.fromstring(x)
    s, c = db
    srv, port = fake_tally.start()
    try:
        create_ledger(s, TallyClient("127.0.0.1", port, 5), c, "New Vendor & Co", "Sundry Creditors",
                      gstin=S.SUPPLIER_MH, bill_wise=True, vendor_key=S.SUPPLIER_MH)
    finally:
        srv.shutdown()
    m = masters_mod.load(s, c.id)
    assert m.party_by_gstin(S.SUPPLIER_MH) in ("New Vendor & Co", "Cloudnine Software Solutions Pvt Ltd")
    assert s.scalar(select(Vendor).where(Vendor.vendor_key == S.SUPPLIER_MH)).party_ledger == "New Vendor & Co"


def test_company_default_journal_and_per_supplier_override(db):
    s, c = db
    c.voucher_style = "journal"
    s.commit()
    m = masters_mod.load(s, c.id)
    inv = _inv(S.INTRA)
    v = rules.suggest(s, c, m, inv).voucher
    assert v.base_type == "Journal" and v.vtype == "Journal"
    v2 = rules.suggest(s, c, m, inv, style_override="purchase_accounting").voucher
    assert v2.base_type == "Purchase"
    next(l for l in v2.lines if l.kind == "expense").ledger = "Printing & Stationery"
    rules.learn(s, c, inv, v2, "op")                       # supplier booked as purchase -> remembered
    assert rules.suggest(s, c, m, inv).voucher.base_type == "Purchase"


def test_tds_from_history(db):
    s, c = db
    s.add(MasterCache(company_id=c.id, kind="ledger", name="TDS Payable 194C", parent="Duties & Taxes", data={}))
    for i, mth in enumerate(("08", "09")):
        s.add(VoucherHistory(company_id=c.id, guid=f"t{i}", date=f"2026{mth}10", voucher_type="Journal", entries=[
            {"ledger": "Printing & Stationery", "amount": "20000", "dr": True},
            {"ledger": "Input CGST 9%", "amount": "1800", "dr": True},
            {"ledger": "Input SGST 9%", "amount": "1800", "dr": True},
            {"ledger": "Shree Stationers", "amount": "23200", "dr": False},
            {"ledger": "TDS Payable 194C", "amount": "400", "dr": False}]))
    s.commit()
    sug = rules.suggest(s, c, masters_mod.load(s, c.id), _inv(S.INTRA))
    tds = next(l for l in sug.voucher.lines if l.kind == "tds")
    assert tds.ledger == "TDS Payable 194C" and tds.amount == Decimal("200") and tds.confidence == "green"
    assert "2 past entries" in tds.note
    party = next(l for l in sug.voucher.lines if l.kind == "party")
    assert party.amount == Decimal("11600.00")


# ---------------------------------------------------------------- bank statements
def _statement_xlsx(path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["IndusInd Bank - Account Statement"])
    ws.append(["Account No", "XXXXXXXX1234"])
    ws.append([])
    ws.append(["Date", "Type", "Description", "Debit", "Credit", "Balance"])
    ws.append(["01/11/2026", "NEFT", "NEFT/N3051234/SHREE STATIONERS/PURCHASE", "11,800.00", "", "88,200.00"])
    ws.append(["03/11/2026", "UPI", "UPI/630912345/RAMESH TRANSPORT/FREIGHT", "5,000.00", "", "83,200.00"])
    ws.append(["", "", "NOV DELIVERY", "", "", ""])
    ws.append(["05/11/2026", "CHG", "SMS ALERT CHARGES OCT-26", "15.00", "", "83,185.00"])
    ws.append(["07/11/2026", "NEFT", "NEFT/CITIN1234/ABC CLIENT PVT LTD", "", "50,000.00", "1,33,185.00"])
    wb.save(path)
    return path


def test_bank_parse_and_suggest(db, tmp_path):
    from app.engine import bank
    s, c = db
    for n, grp in (("IndusInd Bank 1234", "Bank Accounts"), ("Bank Charges", "Indirect Expenses"),
                   ("ABC Client Pvt Ltd", "Sundry Debtors")):
        s.add(MasterCache(company_id=c.id, kind="ledger", name=n, parent=grp, data={}))
    s.add(MasterCache(company_id=c.id, kind="group", name="Bank Accounts", parent="Primary", data={}))
    s.add(MasterCache(company_id=c.id, kind="group", name="Sundry Debtors", parent="Primary", data={}))
    s.add(VoucherHistory(company_id=c.id, guid="p", date="20261101", voucher_type="Payment", number="P-9", entries=[
        {"ledger": "Shree Stationers", "amount": "11800", "dr": True},
        {"ledger": "IndusInd Bank 1234", "amount": "11800", "dr": False}]))
    s.commit()
    st = bank.parse(_statement_xlsx(tmp_path / "st.xlsx"))
    assert len(st.txns) == 4 and not st.warnings
    assert st.txns[1].narration.endswith("NOV DELIVERY")                  # wrapped narration joined
    assert st.txns[3].deposit == Decimal("50000.00") and st.txns[2].withdrawal == Decimal("15.00")
    m = masters_mod.load(s, c.id)
    sg = [bank.suggest(s, c, m, "IndusInd Bank 1234", t) for t in st.txns]
    assert sg[0].in_tally.startswith("Payment P-9")                        # already in Tally
    assert sg[2].ledger == "Bank Charges" and sg[2].vtype == "Payment"
    assert sg[3].ledger == "ABC Client Pvt Ltd" and sg[3].vtype == "Receipt"
    v = bank.build_voucher(c, m, "IndusInd Bank 1234", st.txns[3], "ABC Client Pvt Ltd", "Receipt")
    assert v.balanced and v.lines[0].ledger == "IndusInd Bank 1234" and v.lines[0].dr
    # learning
    bank.learn(s, c, "IndusInd Bank 1234", st.txns[1], "Bank Charges")
    bank.learn(s, c, "IndusInd Bank 1234", st.txns[1], "Bank Charges")
    again = bank.suggest(s, c, m, "IndusInd Bank 1234", st.txns[1])
    assert again.ledger == "Bank Charges" and again.confidence == "green"
    new, dup = bank.store(s, c, "IndusInd Bank 1234", st)
    assert (new, dup) == (4, 0) and bank.store(s, c, "IndusInd Bank 1234", st) == (0, 4)


def test_bank_pdf_statement(tmp_path, qapp):
    from app.engine import bank
    text = """Statement of Account
Date        Particulars                                   Withdrawal     Deposit       Balance
            Opening Balance                                                          1,00,000.00
01-11-2026  NEFT SHREE STATIONERS N3051234                 11,800.00                    88,200.00
07-11-2026  NEFT ABC CLIENT PVT LTD CITIN1234                             50,000.00   1,38,200.00
"""
    p = S.write_pdf(text, tmp_path / "st.pdf")
    st = bank.parse(p)
    assert [(t.date, t.withdrawal, t.deposit) for t in st.txns] == [
        ("20261101", Decimal("11800.00"), Decimal("0")), ("20261107", Decimal("0"), Decimal("50000.00"))]


def test_indusind_layout(tmp_path):
    """Layout as IndusInd exports it (synthetic values)."""
    from openpyxl import Workbook
    from app.engine import bank
    wb = Workbook()
    ws = wb.active
    ws.title = "AccountStatement"
    ws.append(["Account Statement"])
    ws.append([])
    ws.append(["Customer Name (Account Name)"])
    ws.append(["From Date", None, None, "To Date", None, "", "", ""])
    ws.append([])
    ws.append(["Bank Reference", "Value Date", "Transaction Date & Time", "Type", "Payment Narration", "Debit",
               "Credit", "Available Balance"])
    ws.append(["  M100001", "01 Oct 2026", "'01-OCT-26 14:53:22", "Debit", "REIMB0926ABC001/ TRF TO 15760",
               "5868.00", "0.00", 12507])
    ws.append(["  M100002", "03 Oct 2026", "'03-OCT-26 10:02:11", "Credit", "NEFT CR-ABC CLIENT PVT LTD",
               "0.00", "20000.00", 32507])
    p = tmp_path / "indusind.xlsx"
    wb.save(p)
    st = bank.parse(p)
    assert [(t.date, t.withdrawal, t.deposit, t.balance) for t in st.txns] == [
        ("20261001", Decimal("5868.00"), Decimal("0.00"), Decimal("12507.00")),
        ("20261003", Decimal("0.00"), Decimal("20000.00"), Decimal("32507.00"))]
    assert st.txns[0].ref == "M100001" and not st.warnings


def test_hdfc_xls_layout(tmp_path):
    """HDFC .xls: details block, header, row of asterisks, dd/mm/yy dates, footer (synthetic values)."""
    pytest.importorskip("xlwt")
    import xlwt
    from app.engine import bank
    wb = xlwt.Workbook()
    ws = wb.add_sheet("Sheet 1")
    rows = [["HDFC BANK Ltd."], ["Statement From  :  01/08/26  To : 31/08/26"], [],
            ["Date", "Narration", "Chq./Ref.No.", "Value Dt", "Withdrawal Amt.", "Deposit Amt.", "Closing Balance"],
            ["********", "********************", "************", "********", "******", "******", "******"],
            ["06/08/26", "POS 514834XXXXXX6298 STORE", "0000000000897196", "06/08/26", 1000.0, "", 23052.0],
            ["07/08/26", "NEFT CR-ABC CLIENT", "N219260000123", "07/08/26", "", 5000.0, 28052.0],
            [], ["This is a computer generated statement"], ["State account branch GSTN:", "24AAACH2702H1Z6"]]
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            ws.write(i, j, v)
    p = tmp_path / "hdfc.xls"
    wb.save(str(p))
    st = bank.parse(p)
    assert [(t.date, t.withdrawal, t.deposit) for t in st.txns] == [
        ("20260806", Decimal("1000.00"), Decimal("0")), ("20260807", Decimal("0"), Decimal("5000.00"))]
    assert "GSTN" not in st.txns[-1].narration and not st.warnings


# ---------------------------------------------------------------- supplier panel
def test_live_balance_recent_and_copy(db):
    from app.engine import party
    from app.tally.client import TallyClient
    from tests import fake_tally
    s, c = db
    srv, port = fake_tally.start()
    try:
        bal = TallyClient("127.0.0.1", port, 5).ledger_balance(c.name, "Shree Stationers", "20260401", "20261113")
    finally:
        srv.shutdown()
    assert bal["closing"] == Decimal("23600.00") and party.fmt_balance(bal["closing"]) == "₹ 23,600.00 Cr"
    s.add(MasterCache(company_id=c.id, kind="ledger", name="TDS Payable 194C", parent="Duties & Taxes", data={}))
    s.add(VoucherHistory(company_id=c.id, guid="j1", date="20261010", voucher_type="Journal", number="J-41",
                         narration="Stationery Sep", entries=[
                             {"ledger": "Printing & Stationery", "amount": "15000", "dr": True},
                             {"ledger": "Office Rent", "amount": "5000", "dr": True},
                             {"ledger": "Input CGST 9%", "amount": "1800", "dr": True},
                             {"ledger": "Input SGST 9%", "amount": "1800", "dr": True},
                             {"ledger": "Shree Stationers", "amount": "23400", "dr": False},
                             {"ledger": "TDS Payable 194C", "amount": "200", "dr": False}]))
    s.add(VoucherHistory(company_id=c.id, guid="p1", date="20261020", voucher_type="Payment", number="P-7",
                         entries=[{"ledger": "Shree Stationers", "amount": "23400", "dr": True},
                                  {"ledger": "IndusInd Bank", "amount": "23400", "dr": False}]))
    s.commit()
    rec = party.recent_entries(s, c.id, "Shree Stationers")
    assert [r.vh.number for r in rec] == ["P-7", "J-41"] and rec[0].party_dr
    m = masters_mod.load(s, c.id)
    v = party.copy_entry(rec[1].vh, _inv(S.INTRA), m, "Shree Stationers")
    amt = {l.ledger: l.amount for l in v.lines}
    assert amt["Printing & Stationery"] == Decimal("7500.00") and amt["Office Rent"] == Decimal("2500.00")
    assert amt["Input CGST 9%"] == Decimal("900.00") and amt["TDS Payable 194C"] == Decimal("100")
    assert amt["Shree Stationers"] == Decimal("11700.00") and v.balanced and v.base_type == "Journal"
