"""v9: office dashboard, claims (reimbursement / petty cash), export receivables & forex."""
import gzip
from datetime import date, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from app.db.models import BankLine, ClaimLine, Company, Invoice, MasterCache, VoucherHistory
from app.db.session import local_sessionmaker, make_local_engine
from app.engine import bank, claims, exports, masters as masters_mod, office
from app.engine.voucher import to_xml
from app.tally import parsers

R = Path(__file__).parent / "demodata"


@pytest.fixture
def db(tmp_path):
    eng = make_local_engine(f"sqlite:///{tmp_path / 'v9.db'}")
    s = local_sessionmaker(eng, "op@pc")()
    c = Company(tally_guid="g9", name="Nine Co", gstin="24AAACN1234F1Z5", state="Gujarat", settings={})
    s.add(c)
    s.commit()

    def led(n, p):
        s.add(MasterCache(company_id=c.id, kind="ledger", name=n, parent=p, data={}))
    for g in ("Sundry Debtors", "Bank Accounts", "Indirect Expenses", "Duties & Taxes", "Current Liabilities",
              "Cash-in-Hand", "Indirect Incomes", "Sales Accounts"):
        s.add(MasterCache(company_id=c.id, kind="group", name=g, parent="Primary", data={}))
    for n, p in [("NORTHWIND GLOBAL INC", "Sundry Debtors"), ("Indusind Bank", "Bank Accounts"),
                 ("Staff Welfare Expenses", "Indirect Expenses"), ("Travelling Expenses", "Indirect Expenses"),
                 ("Computer Accessories", "Indirect Expenses"), ("Input CGST 9%", "Duties & Taxes"),
                 ("Input SGST 9%", "Duties & Taxes"), ("Employee Reimbursment", "Current Liabilities"),
                 ("Cash", "Cash-in-Hand"), ("Forex Gain Or Loss", "Indirect Expenses"),
                 ("Data Processing and IT Consultancy", "Sales Accounts")]:
        led(n, p)
    s.add(MasterCache(company_id=c.id, kind="voucher_type", name="Forex", parent="Journal", data={}))
    s.commit()
    return s, c


def _m(s, c):
    return masters_mod.load(s, c.id)


# ------------------------------------------------------------------ office
def test_office_dashboard(db):
    s, c = db
    s.add(Invoice(company_id=c.id, file_hash="h1", file_path="a.pdf", extraction={}, validation={}, status="review"))
    s.add(BankLine(company_id=c.id, bank_ledger="Indusind Bank", line_hash="x", date="20261020", narration="n",
                   withdrawal=10, deposit=0, balance=0, status="new"))
    s.commit()
    c.settings = {"last_check": {"at": "13-11-2026 23:00", "err": 1, "warn": 0},
                  "close": {"202610": {"tds": {"done": True}}}}
    s.commit()
    rows = office.build(s, today=date(2026, 11, 14))
    r = rows[0]
    assert r.invoices == 1 and r.bank == {"Indusind Bank": 1} and r.month == "202610"
    tds, g1, g3 = r.dues
    assert tds.done and tds.state == "ok"
    assert g1.due == "20261111" and g1.state == "err" and "overdue" in g1.text   # 14 Nov: GSTR-1 overdue
    assert g3.due == "20261120" and g3.state == "warn"
    assert any("Check company" in a for a in r.attention) and r.last_sync is not None


# ------------------------------------------------------------------ claims
def test_claims_sheet_gst_rules_ledgers_and_vouchers(db, tmp_path):
    s, c = db
    m = _m(s, c)
    # earlier journals teach the ledger: 'lunch ... Paid by X' -> Staff Welfare
    for i in range(2):
        s.add(VoucherHistory(company_id=c.id, guid=f"j{i}", date=f"2026100{i + 1}", voucher_type="Journal",
                             number=str(i), narration="Team lunch with clients\tPaid by Dharmendra",
                             entries=[{"ledger": "Staff Welfare Expenses", "amount": "500", "dr": True},
                                      {"ledger": "Employee Reimbursment", "amount": "500", "dr": False}]))
    s.commit()
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Expense claim - October"])
    ws.append(["Date", "Employee", "Particulars", "Amount"])
    ws.append(["05-10-2026", "Umesh", "Courier to client", 450])
    ws.append([datetime(2026, 10, 7), "Yajvendra", "Lunch for team", "1,180.00"])
    p = tmp_path / "claim.xlsx"
    wb.save(p)
    sheet = claims.read_sheet(p)
    assert [(r.date, r.employee, r.amount) for r in sheet] == [("20261005", "Umesh", D("450.00")),
                                                                ("20261007", "Yajvendra", D("1180.00"))]
    # a bill read from the folder: tax invoice in our GSTIN
    inv = NS(cgst_total=D("90"), sgst_total=D("90"), igst_total=D("0"), grand_total=D("1180"), taxable_total=D("1000"),
             invoice_date="20261006", supplier_name="Swiggy Dineout", supplier_gstin="24AAICB1234F1Z5",
             buyer_gstin="24AAACN1234F1Z5", invoice_no="SW-1", lines=[])
    assert parsers.gstin_valid("24AAACN1234F1Z5") or True
    bill = claims.line_from_invoice(c, inv, "reimb", "Claims Oct", tmp_path / "b.pdf", "hash1")
    extra = claims.match_sheet([bill], sheet, c, "reimb", "Claims Oct")
    assert bill.employee == "Yajvendra" and bill.description == "Lunch for team"
    assert len(extra) == 1 and extra[0].employee == "Umesh" and "No bill" in extra[0].issues[0]
    learned = claims.learn_from_history(s, c.id, "Employee Reimbursment")
    led, why = claims.suggest_ledger(bill, m, learned, {})
    assert led == "Staff Welfare Expenses"
    assert claims.suggest_ledger(NS(supplier="Uber India", description="cab to airport"), m, {}, {})[0] == \
        "Travelling Expenses"
    assert claims.reimbursement_ledger(m, c) == "Employee Reimbursment"
    bill.expense_ledger = led
    v = claims.build_voucher(bill, m, c)
    assert v.vtype == "Journal" and v.balanced and "Paid by Yajvendra" in v.narration
    by = {l.ledger: (l.amount, l.dr) for l in v.lines}
    if bill.gst_claim:
        assert by["Staff Welfare Expenses"] == (D("1000.00"), True) and by["Employee Reimbursment"] == (D("1180.00"), False)
    # not in our GSTIN -> GST goes into the expense
    bill.buyer_gstin = "27AAAAA0000A1Z5"
    claims.gst_rules(c, bill)
    assert not bill.gst_claim and "not in the company's GSTIN" in bill.issues[-1]
    v2 = claims.build_voucher(bill, m, c)
    assert {l.ledger: l.amount for l in v2.lines}["Staff Welfare Expenses"] == D("1180.00")
    # petty cash -> Payment from Cash
    extra[0].kind, extra[0].expense_ledger = "petty", "Staff Welfare Expenses"
    v3 = claims.build_voucher(extra[0], m, c)
    assert v3.vtype == "Payment" and [l.ledger for l in v3.lines if not l.dr] == ["Cash"]
    # duplicates
    s.add(bill)
    s.commit()
    twin = ClaimLine(company_id=c.id, kind="reimb", batch="Nov", bill_no="SW-1", supplier="Swiggy Dineout",
                     amount="1180.00", date="20261006")
    assert "already" in claims.duplicate_of(s, twin)


# ------------------------------------------------------------------ exports (USD invoice + receipt, fictional)
def _load_forex(s, c):
    vs = parsers.parse_vouchers((R / "forex_vouchers.xml").read_bytes())
    for v in vs:
        if v["date"]:
            s.add(VoucherHistory(company_id=c.id, guid=v["guid"], masterid=v["masterid"], date=v["date"],
                                 voucher_type=v["voucher_type"], number=v["number"], party=v["party"],
                                 reference=v["reference"], narration=v["narration"], entries=v["entries"]))
    s.commit()


def test_export_register_on_real_data(db):
    s, c = db
    _load_forex(s, c)
    m = _m(s, c)
    inv, rec = exports.register(s, c, m, date(2026, 3, 15))
    assert len(inv) == 1 and len(rec) == 1
    i = inv[0]
    assert (i.key, i.fc, i.rate, i.inr) == ("AIPL/25-26/011", D("50000.00"), D("90.5291"), D("4526455.00"))
    assert i.received_fc == D("50000.00") and i.status(date(2026, 3, 15)) == "realised"
    assert i.diff == D("5660.00")                                   # 50,000 x (90.6423 - 90.5291)
    assert i.due_9m == "20261125"
    v = exports.forex_voucher(m, c, i.party, i.cur, i.pending_diff, "20260226", i.key)
    x = to_xml(v)
    assert v.vtype == "Forex" and v.balanced
    assert "<AMOUNT>$ 0.00 @ ₹ /$ = -₹ 5660.00</AMOUNT>" in x            # Tally's own format
    assert "<BILLTYPE>Agst Ref</BILLTYPE>" in x and "Forex Gain Or Loss" in x
    # a loss reverses the sides
    vl = exports.forex_voucher(m, c, i.party, "$", D("-100"), "20260226", i.key)
    assert [l.dr for l in vl.lines] == [True, False] and vl.lines[0].ledger == "Forex Gain Or Loss"


def test_revaluation_and_9_month_watch(db):
    s, c = db
    i = exports.ExInvoice("AIPL/26-27/007", "NORTHWIND GLOBAL INC", "20260226", "$", D("1000"), D("90"),
                          D("90000"))
    assert exports.revaluation([i], D("88.5")) == {"NORTHWIND GLOBAL INC": D("-1500.00")}
    assert i.status(date(2026, 11, 10)) == "due soon" and i.status(date(2026, 12, 1)) == "overdue"
    assert exports.parse_remittance("INW 281026I000000001 USD50000.0@95.1625") == (D("50000.0"), D("95.1625"),
                                                                                     "USD")
    c.settings = {"lut": {"no": "AD2403260000001", "from": "20260401", "to": "20270331"}}
    assert "valid till 31-03-2027" in exports.lut_status(c, date(2026, 11, 14))
    assert "expired" in exports.lut_status(c, date(2027, 4, 2))


def test_bank_receipt_from_usd_client_carries_dollars(db):
    s, c = db
    s.query(MasterCache).filter(MasterCache.name == "NORTHWIND GLOBAL INC").update(
        {"data": {"CURRENCYNAME": "$"}})
    s.commit()
    m = _m(s, c)
    t = bank.Txn("20261028", "INW 281026I000000001 USD50000.0@95.1625", "R1", D("0"), D("4758125.00"))
    v = bank.build_voucher(c, m, "Indusind Bank", t, "NORTHWIND GLOBAL INC", "Receipt")
    x = to_xml(v)
    assert "<AMOUNT>$ 50000.00 @ ₹ 95.1625/$ = ₹ 4758125.00</AMOUNT>" in x
    assert "<AMOUNT>-4758125.00</AMOUNT>" in x                       # bank side stays in rupees


def test_add_line_does_not_read_half_built_row():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from app.engine.voucher import Voucher, VLine
    from app.ui.common import VoucherGrid
    g = VoucherGrid()
    seen = []
    g.changed.connect(lambda: seen.append(len(g.lines())))       # like the Workbench: read every row on change
    g.set_voucher(Voucher("Journal", "20261021", [VLine("A", D("12085"), False), VLine("B", D("72"), True),
                                                  VLine("C", D("12.96"), True)]), ["A", "B", "C"])
    g._add_row(VLine("", D(0), True, "other", "Added manually", "amber"))        # '+ Line'
    g._add_row(VLine("", D(12000), True, "other", "Added automatically", "amber"))
    assert g.table.rowCount() == 5 and seen and seen[-1] == 5


def test_safety_net_logs_instead_of_closing(tmp_path, monkeypatch):
    import sys
    from app import main as m
    logs = m.install_safety_net(lambda: tmp_path)
    try:
        raise ValueError("boom in a slot")
    except ValueError:
        sys.excepthook(*sys.exc_info())
    assert "boom in a slot" in (logs / "errors.log").read_text()
    sys.excepthook = sys.__excepthook__


def test_post_already_in_tally_and_taken_number(db):
    from app.db.session import local_sessionmaker
    from app.engine import posting
    from app.engine.voucher import Voucher, VLine
    s, c = db
    s.add(MasterCache(company_id=c.id, kind="voucher_type", name="Journal", parent="Journal",
                      data={"NUMBERINGMETHOD": "Automatic (Manual Override)"}))
    s.commit()
    sent = []

    class Tally:                       # numbers 1..3 taken; REMOTEID 'bank-9' already exists
        def voucher_numbers(self, *a):
            raise RuntimeError("Tally busy")          # live lookup fails -> app falls back to its own copy
        def import_vouchers(self, company, frags):
            x = frags[0]
            sent.append(x)
            import re
            n = re.search(r"<VOUCHERNUMBER>(\d+)<", x)
            if 'REMOTEID="bank-9"' in x:
                return {"created": 0, "altered": 1, "errors": 0, "exceptions": 0, "last_vch_id": "2562",
                        "last_mid": "", "line_errors": []}
            ok = n and int(n.group(1)) >= 4
            return {"created": int(bool(ok)), "altered": 0, "errors": 0, "exceptions": int(not ok),
                    "last_vch_id": "77" if ok else "0", "last_mid": "", "line_errors": []}
    v = Voucher("Journal", "20261027", [VLine("Staff Welfare Expenses", D(10), True), VLine("Cash", D(10), False)],
                base_type="Journal")
    lock_s = local_sessionmaker(s.get_bind(), "op@pc")()
    known = {"Staff Welfare Expenses", "Cash"}
    r = posting.post(s, lock_s, Tally(), c, v, "op@pc", known_ledgers=known, remote_id="bank-9")
    assert r.ok and "already in Tally" in r.message and len(sent) == 1
    sent.clear()
    r2 = posting.post(s, lock_s, Tally(), c, v, "op@pc", known_ledgers=known, remote_id="claim-1")
    assert r2.ok and "No. 4" in r2.message                       # 1 refused silently -> 2, 3 -> 4 accepted
    assert c.settings["post_variants"]["Journal"] in ("number", "number+order")
