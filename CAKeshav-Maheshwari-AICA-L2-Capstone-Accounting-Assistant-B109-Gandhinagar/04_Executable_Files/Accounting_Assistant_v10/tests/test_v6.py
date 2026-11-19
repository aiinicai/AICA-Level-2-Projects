"""v6: all voucher types, cash/bank restriction, bill-wise, period lock, recurring, any-bank mapping, bank
matching, supplier layout memory, Gemini banking block, live reports, documents, period picker logic."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.db.models import (BankLine, Company, Invoice, MasterCache, Posting, RecurringEntry, VoucherHistory)
from app.db.session import local_sessionmaker, make_local_engine
from app.engine import (bank, docs, entry, layouts, masters as masters_mod, periods, recurring, reports)
from app.engine.voucher import VLine, Voucher, to_xml
from app.extract import gemini, layout as layout_mod
from app.extract.schema import Invoice as Inv

D = Decimal


@pytest.fixture
def db(tmp_path):
    eng = make_local_engine(f"sqlite:///{tmp_path / 'v6.db'}")
    s = local_sessionmaker(eng, "op@pc")()
    c = Company(tally_guid="g6", name="Demo Co", gstin="24AAACD1234F1Z5", state="Gujarat", settings={})
    s.add(c)
    s.commit()

    def m(kind, name, parent="", **data):
        s.add(MasterCache(company_id=c.id, kind=kind, name=name, parent=parent, data=data))
    for g, p in [("Sundry Creditors", "Primary"), ("Sundry Debtors", "Primary"), ("Duties & Taxes", "Primary"),
                 ("Indirect Expenses", "Primary"), ("Bank Accounts", "Primary"), ("Cash-in-Hand", "Primary"),
                 ("Bank OD A/c", "Primary"), ("Sales Accounts", "Primary"), ("Purchase Accounts", "Primary"),
                 ("Current Liabilities", "Primary"), ("HDFC Group", "Bank Accounts")]:
        m("group", g, p)
    m("ledger", "HDFC Bank", "HDFC Group")
    m("ledger", "IndusInd Bank", "Bank Accounts")
    m("ledger", "Cash", "Cash-in-Hand")
    m("ledger", "Axis CC", "Bank OD A/c")
    m("ledger", "Amex Card", "Current Liabilities")
    m("ledger", "Shree Stationers", "Sundry Creditors", _gstin="24ABCPS1234K1ZS", ISBILLWISEON="Yes")
    m("ledger", "Mumbai Buyer", "Sundry Debtors", _gstin="27AAACM1234F1Z1", ISBILLWISEON="Yes")
    m("ledger", "Local Buyer", "Sundry Debtors", _gstin="24AAACL1111F1Z1")
    m("ledger", "Sales GST", "Sales Accounts")
    m("ledger", "Purchase GST", "Purchase Accounts")
    m("ledger", "Office Rent", "Indirect Expenses")
    m("ledger", "Round Off", "Indirect Expenses")
    for n, h in [("Output CGST 9%", "Central Tax"), ("Output SGST 9%", "State Tax"),
                 ("Output IGST 18%", "Integrated Tax"), ("Input CGST 9%", "Central Tax"),
                 ("Input SGST 9%", "State Tax"), ("Input IGST 18%", "Integrated Tax")]:
        m("ledger", n, "Duties & Taxes", GSTDUTYHEAD=h)
    s.commit()
    return s, c, masters_mod.load(s, c.id)


# ---------------------------------------------------------------- periods
def test_periods_quick_picks():
    t = date(2026, 11, 13)
    assert periods.quick("This FY", t).frm == "20260401" and periods.quick("This FY", t).to == "20270331"
    assert periods.quick("Last FY", t).frm == "20250401"
    assert periods.quick("This month", t).to == "20261130"
    assert periods.quick("Last month", t).frm == "20261001" and periods.quick("Last month", t).to == "20261031"
    assert periods.quick("This quarter", t).frm == "20261001" and periods.quick("This quarter", t).to == "20261231"
    assert periods.quick("This FY", date(2027, 2, 1)).frm == "20260401"
    assert periods.default(t).contains("20270101") and not periods.default(t).contains("20260331")


# ---------------------------------------------------------------- cash / bank restriction
def test_cash_bank_ledgers_and_card_tick(db):
    s, c, m = db
    cb = entry.cash_bank_ledgers(m, c)
    assert {"HDFC Bank", "IndusInd Bank", "Cash", "Axis CC"} <= set(cb)          # sub-group of Bank Accounts too
    assert "Amex Card" not in cb and "Office Rent" not in cb
    c.settings = {"card_ledgers": ["Amex Card"]}
    assert "Amex Card" in entry.cash_bank_ledgers(m, c)


def test_payment_receipt_contra_restrictions(db):
    s, c, m = db
    f = entry.EntryForm("Payment", "Payment", "20261110", party="Shree Stationers", cash_bank="HDFC Bank",
                        amount=D("5000"))
    v = entry.build(f, m, c)
    assert v.balanced and not entry.check_restrictions(v, m, c)
    assert v.lines[1].ledger == "HDFC Bank" and not v.lines[1].dr
    assert v.lines[0].bill_type == "On Account"                      # bill-wise party, nothing ticked
    bad = entry.build(entry.EntryForm("Payment", "Payment", "20261110", party="Shree Stationers",
                                      cash_bank="Office Rent", amount=D("10")), m, c)
    assert entry.check_restrictions(bad, m, c)
    r = entry.build(entry.EntryForm("Receipt", "Receipt", "20261110", party="Mumbai Buyer", cash_bank="Axis CC",
                                    amount=D("100")), m, c)
    assert r.lines[0].dr and r.lines[0].ledger == "Axis CC" and not entry.check_restrictions(r, m, c)
    ct = entry.build(entry.EntryForm("Contra", "Contra", "20261110", cash_bank="Cash", contra_to="HDFC Bank",
                                     amount=D("2000")), m, c)
    assert not entry.check_restrictions(ct, m, c)
    ct.lines[0].ledger = "Office Rent"
    assert entry.check_restrictions(ct, m, c)


def test_sales_gst_split_and_notes(db):
    s, c, m = db
    inter = entry.build(entry.EntryForm("Sales", "Sales", "20261110", party="Mumbai Buyer", reference="S-1",
                                        items=[entry.ItemLine("Sales GST", D("1000"), D("18"))]), m, c)
    names = [l.ledger for l in inter.lines]
    assert "Output IGST 18%" in names and inter.balanced
    party = inter.lines[0]
    assert party.dr and party.amount == D("1180.00") and party.bill_ref == "S-1"
    intra = entry.build(entry.EntryForm("Sales", "Sales", "20261110", party="Local Buyer",
                                        items=[entry.ItemLine("Sales GST", D("1000"), D("18"))]), m, c)
    assert {"Output CGST 9%", "Output SGST 9%"} <= {l.ledger for l in intra.lines}
    cn = entry.build(entry.EntryForm("Credit Note", "Credit Note", "20261110", party="Local Buyer",
                                     items=[entry.ItemLine("Sales GST", D("100"), D("18"))]), m, c)
    assert not cn.lines[0].dr and cn.balanced                          # sales return: party credited
    dn = entry.build(entry.EntryForm("Debit Note", "Debit Note", "20261110", party="Shree Stationers",
                                     items=[entry.ItemLine("Purchase GST", D("100"), D("18"))]), m, c)
    assert dn.lines[0].dr and any(l.ledger == "Input CGST 9%" and not l.dr for l in dn.lines) and dn.balanced
    pu = entry.build(entry.EntryForm("Purchase", "Purchase", "20261110", party="Shree Stationers",
                                     round_off_ledger="Round Off",
                                     items=[entry.ItemLine("Purchase GST", D("1000.40"), D("18"))]), m, c)
    assert pu.balanced and any(l.kind == "round" for l in pu.lines)


def test_item_level_sales_xml(db):
    s, c, m = db
    v = entry.build(entry.EntryForm("Sales", "Sales", "20261110", party="Local Buyer",
                                    items=[entry.ItemLine("Sales GST", D("500"), D("18"), stock_item="Widget",
                                                          qty=D("5"), rate=D("100"))]), m, c)
    assert v.balanced and v.inventory and not v.inventory[0].dr
    x = to_xml(v)
    assert "<STOCKITEMNAME>Widget</STOCKITEMNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>" in x
    assert "<AMOUNT>500.00</AMOUNT>" in x


# ---------------------------------------------------------------- bill-wise
def test_billwise_allocation_xml_and_history(db):
    s, c, m = db
    s.add(VoucherHistory(company_id=c.id, guid="p1", date="20261001", voucher_type="Purchase", number="1",
                         entries=[{"ledger": "Shree Stationers", "amount": "1180", "dr": False,
                                   "bills": [{"name": "INV-1", "type": "New Ref", "amount": "1180"}]}]))
    s.add(VoucherHistory(company_id=c.id, guid="p2", date="20261005", voucher_type="Purchase", number="2",
                         entries=[{"ledger": "Shree Stationers", "amount": "590", "dr": False,
                                   "bills": [{"name": "INV-2", "type": "New Ref", "amount": "590"}]}]))
    s.add(VoucherHistory(company_id=c.id, guid="p3", date="20261008", voucher_type="Payment", number="3",
                         entries=[{"ledger": "Shree Stationers", "amount": "590", "dr": True,
                                   "bills": [{"name": "INV-2", "type": "Agst Ref", "amount": "-590"}]}]))
    s.commit()
    bills = entry.open_bills_from_history(s, c.id, "Shree Stationers")
    assert [(b.name, b.amount, b.dr) for b in bills] == [("INV-1", D("1180"), False)]
    alloc = entry.allocate(bills, {"INV-1": D("1000")}, D("1500"))
    assert alloc == [("INV-1", "Agst Ref", D("1000.00")), ("", "On Account", D("500.00"))]
    v = entry.build(entry.EntryForm("Payment", "Payment", "20261110", party="Shree Stationers",
                                    cash_bank="HDFC Bank", amount=D("1500"), bills=alloc), m, c)
    x = to_xml(v)
    assert "<NAME>INV-1</NAME><BILLTYPE>Agst Ref</BILLTYPE><AMOUNT>-1000.00</AMOUNT>" in x
    assert "<NAME/><BILLTYPE>On Account</BILLTYPE><AMOUNT>-500.00</AMOUNT>" in x
    v.lines[0].bills = [("INV-1", "Agst Ref", D("100"))]
    assert any("don't add up" in p for p in v.problems())


# ---------------------------------------------------------------- period lock
def test_period_lock(db):
    s, c, m = db
    c.settings = {"lock_until": "20260930"}
    s.commit()
    v = Voucher("Journal", "20260915", [VLine("Office Rent", D(1), True), VLine("Cash", D(1), False)])
    with pytest.raises(entry.PeriodLocked):
        entry.check_lock(s, c, v)
    entry.check_lock(s, c, v, "GST return revised", "op@pc")           # override is audited
    from app.db.models import AuditLog
    assert s.query(AuditLog).filter_by(action="lock_override").count() == 1
    v.date = "20261001"
    entry.check_lock(s, c, v)


def test_posting_refuses_locked_period(db, tmp_path):
    s, c, m = db
    from app.engine.posting import post
    c.settings = {"lock_until": "20261231"}
    s.commit()
    v = Voucher("Journal", "20261115", [VLine("Office Rent", D(1), True), VLine("Cash", D(1), False)],
                base_type="Journal")
    res = post(s, s, None, c, v, "op", None, set(m.ledgers), set())
    assert not res.ok and res.locked


# ---------------------------------------------------------------- recurring
def test_recurring_due_and_advance(db):
    s, c, m = db
    v = Voucher("Journal", "20261101", [VLine("Office Rent", D("60000"), True), VLine("Cash", D("60000"), False)],
                narration="Rent for {month} {year}", base_type="Journal")
    rec = recurring.from_voucher(c.id, "Rent", v, "monthly", 1, today=date(2026, 11, 13))
    assert rec.next_due == "20261201"
    s.add(rec)
    s.commit()
    assert recurring.due(s, c.id, date(2026, 11, 13)) == []
    assert recurring.due(s, c.id, date(2026, 12, 1))[0].name == "Rent"
    mv = recurring.make_voucher(rec)
    assert mv.narration == "Rent for December 2026" and mv.balanced
    recurring.mark_posted(s, rec, "20261201", {"Office Rent": D("61000"), "Cash": D("61000")})
    assert rec.next_due == "20270101" and rec.lines[0]["amount"] == "61000"
    rec.day, rec.frequency, rec.next_due = 31, "quarterly", "20261130"
    assert recurring.advance(rec) == "20270228"


# ---------------------------------------------------------------- bank mapping
def _sheet(path, header, rows, pre=2):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    for _ in range(pre):
        ws.append(["Some Bank Ltd statement"])
    ws.append(header)
    for r in rows:
        ws.append(r)
    wb.save(path)


def test_any_bank_mapping_saved_and_reused(tmp_path):
    p = tmp_path / "odd.xlsx"
    header = ["Dt", "Info", "Outgo", "Income", "Bal"]
    _sheet(p, header, [["05/11/2026", "UPI/DR/412345678901/RAMESH KUMAR/HDFC/x", 500, None, 9500],
                       ["06/11/2026", "Interest", None, 20, 9520]])
    with pytest.raises(ValueError):
        bank.parse(p)                                          # unknown layout -> mapping screen
    rows, hi = bank.preview(p)
    assert rows[hi][0] == "Dt"
    mapping = {"date": 0, "narration": 1, "withdrawal": 2, "deposit": 3, "balance": 4}
    st = bank.parse(p, mapping, header_index=hi)
    assert len(st.txns) == 2 and st.txns[0].withdrawal == D("500.00") and st.signature
    saved = {bank.header_signature(header): mapping}
    st2 = bank.parse(p, saved=saved)                           # next time: no questions asked
    assert len(st2.txns) == 2 and st2.txns[1].deposit == D("20.00")
    with pytest.raises(ValueError):
        bank.parse(p, {"date": 0}, header_index=hi)


def test_common_header_synonyms_detected(tmp_path):
    p = tmp_path / "x.xlsx"
    _sheet(p, ["Txn Dt", "Remarks", "Money Out", "Money In", "Bal"], [["05/11/2026", "Fee", 10, None, 90]])
    st = bank.parse(p)
    assert st.txns[0].withdrawal == D("10.00") and st.txns[0].balance == D("90.00")


def test_counterparty_and_suggestion(db):
    s, c, m = db
    assert bank.counterparty("UPI/DR/412345678901/RAMESH KUMAR/HDFC/UPI") == "RAMESH KUMAR"
    assert bank.counterparty("NEFT-HDFC0000123-SHREE STATIONERS-INV 45") == "SHREE STATIONERS"
    assert bank.counterparty("ATM WDL 1234") == ""
    t = bank.Txn("20261105", "NEFT-HDFC0000123-SHREE STATIONERS LLP-INV 45", "", D("500"), D(0))
    sg = bank.suggest(s, c, m, "HDFC Bank", t)
    assert sg.ledger == "Shree Stationers" and sg.vtype == "Payment"


def test_match_single_and_combo(db):
    s, c, m = db
    for g, d, amt in (("a", "20261104", "300"), ("b", "20261106", "200"), ("c", "20261110", "999")):
        s.add(VoucherHistory(company_id=c.id, guid=f"guid-{g}", date=d, voucher_type="Receipt", number=g,
                             entries=[{"ledger": "HDFC Bank", "amount": amt, "dr": True},
                                      {"ledger": "Local Buyer", "amount": amt, "dr": False}]))
    s.commit()
    one = bank.match_candidates(s, c.id, "HDFC Bank", bank.Txn("20261110", "x", "", D(0), D("999")))
    assert len(one[0].vouchers) == 1 and one[0].vouchers[0].number == "c"
    combo = bank.match_candidates(s, c.id, "HDFC Bank", bank.Txn("20261105", "x", "", D(0), D("500")))
    assert combo and {v.number for v in combo[0].vouchers} == {"a", "b"}
    ln = BankLine(company_id=c.id, bank_ledger="HDFC Bank", line_hash="h", date="20261105", deposit=500.0)
    s.add(ln)
    s.commit()
    bank.mark_matched(s, ln, combo[0])
    assert ln.status == "in_tally"
    again = bank.match_candidates(s, c.id, "HDFC Bank", bank.Txn("20261105", "x", "", D(0), D("500")))
    assert not again                                          # matched vouchers aren't offered twice


# ---------------------------------------------------------------- layout memory (offline learning)
TEXT_A = """ACME SUPPLIES
GSTIN 24ABCPS1234K1ZS
Bill No : AC/77/26     Bill Dt : 03/11/2026
Description            Amount
Paper                  1,000.00
Taxable Amt            1,000.00
CGST @9%                  90.00
SGST @9%                  90.00
Net Payable            1,180.00
"""
TEXT_B = TEXT_A.replace("AC/77/26", "AC/91/26").replace("03/11/2026", "10/11/2026").replace(
    "1,000.00", "2,000.00").replace("90.00", "180.00").replace("1,180.00", "2,360.00")


def test_layout_learn_then_read_offline(db):
    s, c, m = db
    inv = Inv(supplier_gstin="24ABCPS1234K1ZS", invoice_no="AC/77/26", invoice_date="20261103",
              taxable_total=D("1000"), cgst_total=D("90"), sgst_total=D("90"), grand_total=D("1180"))
    layouts.learn(s, c.id, "24ABCPS1234K1ZS", inv, TEXT_A)
    fields = layouts.load_all(s, c.id)["24ABCPS1234K1ZS"]
    assert fields["grand_total"]["labels"][0] == "Net Payable"
    got = layout_mod.read(fields, TEXT_B)
    assert got["invoice_no"] == "AC/91/26" and got["invoice_date"] == "20261110"
    assert got["grand_total"] == D("2360.00") and got["taxable_total"] == D("2000.00")


def test_pipeline_skips_gemini_for_learned_supplier(db, tmp_path, monkeypatch):
    s, c, m = db
    from app.extract import pipeline
    inv = Inv(supplier_gstin="24ABCPS1234K1ZS", invoice_no="AC/77/26", invoice_date="20261103",
              taxable_total=D("1000"), cgst_total=D("90"), sgst_total=D("90"), grand_total=D("1180"))
    layouts.learn(s, c.id, "24ABCPS1234K1ZS", inv, TEXT_A)
    p = tmp_path / "b.txt"
    p.write_text(TEXT_B)
    from app.extract import readers

    class Doc:
        kind, pages, has_text_layer, page_images, text = "pdf", 1, True, [b""], TEXT_B
    monkeypatch.setattr(readers, "read", lambda path: Doc())
    monkeypatch.setattr(pipeline.ocr_mod, "ocr", lambda img: type("R", (), {"text": "", "error": "", "words": []})())

    def boom(*a, **k):
        raise AssertionError("Gemini must not be called")
    monkeypatch.setattr(gemini, "extract", boom)
    opt = pipeline.ExtractOptions(company_gstin="24AAACD1234F1Z5", company_state="24", gemini_key="k",
                                  layouts=layouts.load_all(s, c.id))
    res = pipeline.process(p, opt, today=date(2026, 11, 13))
    assert res.invoice.source == "layout" and res.invoice.grand_total == D("2360.00")
    assert res.invoice.invoice_no == "AC/91/26"


# ---------------------------------------------------------------- Gemini hard block for banking
def test_gemini_never_called_from_banking_code():
    root = Path(__file__).resolve().parent.parent / "app"
    for f in [root / "engine" / "bank.py", root / "ui" / "bank_page.py", root / "engine" / "entry.py"]:
        src = f.read_text(encoding="utf-8")
        assert "gemini" not in src.lower().replace("never sent to gemini", ""), f.name


def test_gemini_runtime_block_from_bank_module():
    import types
    fake = types.ModuleType("app.engine.bank_fake")
    code = "def go(g):\n    return g.extract('key', 'm', text='x')\n"
    exec(code, fake.__dict__)
    with pytest.raises(gemini.GeminiError, match="banking"):
        fake.go(gemini)


# ---------------------------------------------------------------- reports
def _groups():
    return {g: {"PARENT": "Primary"} for g in ("Capital Account", "Sundry Creditors", "Bank Accounts",
                                                  "Sales Accounts", "Purchase Accounts", "Indirect Expenses",
                                                  "Duties & Taxes")} | \
        {"Rent & Rates": {"PARENT": "Indirect Expenses"}}


def test_reports_build_tb_pl_bs():
    closings = {
        "Capital": {"parent": "Capital Account", "closing": D("100000")},
        "HDFC Bank": {"parent": "Bank Accounts", "closing": D("-150000")},
        "Sales GST": {"parent": "Sales Accounts", "closing": D("200000")},
        "Purchase GST": {"parent": "Purchase Accounts", "closing": D("-120000")},
        "Office Rent": {"parent": "Rent & Rates", "closing": D("-30000")},
        "Shree Stationers": {"parent": "Sundry Creditors", "closing": D("0")},
    }
    rep = reports.build(_groups(), closings, None)
    assert rep.tb_dr == rep.tb_cr == D("300000")
    assert rep.gross_profit == D("80000") and rep.net_profit == D("50000")
    assert not rep.notes                                       # balance sheet balances
    names = [n.name for n in rep.bs_liabilities]
    assert "Profit & Loss A/c" in names
    ind = next(n for n in rep.pl_left if n.name == "Indirect Expenses")
    assert ind.children[0].name == "Rent & Rates" and ind.children[0].children[0].name == "Office Rent"
    # period P&L: subtract the balance before the period
    before = {"Sales GST": {"parent": "Sales Accounts", "closing": D("150000")}}
    rep2 = reports.build(_groups(), closings, before)
    assert rep2.gross_profit == D("-70000")


def test_reports_live_via_fake_tally(tmp_path):
    from tests import fake_tally
    from app.tally.client import TallyClient
    srv, port = fake_tally.start()
    try:
        cl = TallyClient("127.0.0.1", port, 10)
        rep = reports.fetch(cl, "Demo", "20261001", "20261031")
        assert rep.tb_dr == rep.tb_cr and rep.tb_dr > 0
        reports.to_excel(rep, tmp_path / "r.xlsx", "Demo", "Oct 2026")
        from openpyxl import load_workbook
        wb = load_workbook(tmp_path / "r.xlsx")
        assert wb.sheetnames == ["Trial Balance", "Profit & Loss", "Balance Sheet"]
        bills = cl.bills("Demo", "Shree Stationers")
        assert bills and bills[0]["name"] == "INV-1"
        req = fake_tally._H.requests_seen[-1]
        assert b"<TYPE>Bills</TYPE>" in req
    finally:
        srv.shutdown()


# ---------------------------------------------------------------- documents
def test_find_document_for_posted_voucher(db, tmp_path):
    s, c, m = db
    f = tmp_path / "inv.pdf"
    f.write_bytes(b"%PDF")
    inv = Invoice(company_id=c.id, file_hash="x", file_path=str(f), status="posted",
                  extraction={"invoice_no": "AC/77", "invoice_date": "20261103"})
    s.add(inv)
    s.commit()
    s.add(Posting(company_id=c.id, invoice_id=inv.id, voucher_xml="", tally_master_id="457", ok=True))
    s.commit()
    assert docs.find_document(s, c.id, masterid="457") == str(f)
    assert docs.find_document(s, c.id, reference="ac/77", date="20261105") == str(f)
    assert docs.find_document(s, c.id, masterid="999", reference="nope") == ""
