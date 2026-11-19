"""v8: red flags, related parties, TDS section labels / guessing, Rule 37 FIFO, trading account, TB cross-check."""
from datetime import date
from decimal import Decimal

import pytest

from app.db.models import BankLine, Company, Invoice, MasterCache, VoucherHistory
from app.db.session import local_sessionmaker, make_local_engine
from app.engine import masters as masters_mod, periods, redflags, tds_map

D = Decimal
TODAY = date(2026, 11, 13)


@pytest.fixture
def db(tmp_path):
    eng = make_local_engine(f"sqlite:///{tmp_path / 'v8.db'}")
    s = local_sessionmaker(eng, "op@pc")()
    c = Company(tally_guid="g8", name="Eight Co", gstin="24AAACD1234F1Z5", state="Gujarat",
                settings={"related_parties": [{"name": "Mr A Director", "relation": "Director",
                                               "ledgers": ["Mr A Director", "A Holdings"]}]})
    s.add(c)
    s.commit()

    def m(kind, name, parent="", **data):
        s.add(MasterCache(company_id=c.id, kind=kind, name=name, parent=parent, data=data))
    for g in ("Sundry Creditors", "Sundry Debtors", "Duties & Taxes", "Indirect Expenses", "Bank Accounts",
              "Cash-in-Hand", "Unsecured Loans", "Loans & Advances (Asset)", "Sales Accounts", "Purchase Accounts",
              "Fixed Assets"):
        m("group", g, "Primary")
    for n, p in [("Cash", "Cash-in-Hand"), ("HDFC", "Bank Accounts"), ("Supplier S", "Sundry Creditors"),
                 ("Customer C", "Sundry Debtors"), ("Trader T", "Sundry Debtors"), ("Office Exp", "Indirect Expenses"),
                 ("Loan from X", "Unsecured Loans"), ("Mr A Director", "Loans & Advances (Asset)"),
                 ("A Holdings", "Sundry Debtors"), ("Sales", "Sales Accounts"), ("Purchases", "Purchase Accounts"),
                 ("Input CGST", "Duties & Taxes"), ("Motor Car Expenses", "Indirect Expenses"),
                 ("Interest Paid", "Indirect Expenses"), ("School Fees", "Indirect Expenses")]:
        m("ledger", n, p)
    s.commit()
    return s, c, masters_mod.load(s, c.id)


def vh(s, c, g, d, typ, ents, narr=""):
    s.add(VoucherHistory(company_id=c.id, guid=g, masterid=str(len(g) * 7 + int(d[-2:])), date=d, voucher_type=typ,
                         number=g, narration=narr, entries=[{"ledger": l, "amount": str(a), "dr": dr}
                                                            for l, a, dr in ents]))


def test_red_flags_cover_the_main_groups(db):
    s, c, m = db
    vh(s, c, "r1", "20261002", "Receipt", [("Cash", 250000, True), ("Customer C", 250000, False)])          # A1
    vh(s, c, "r2", "20261003", "Receipt", [("Cash", 50000, True), ("Loan from X", 50000, False)], "loan")   # A2
    vh(s, c, "p1", "20261004", "Payment", [("Office Exp", 15000, True), ("Cash", 15000, False)])            # A3
    vh(s, c, "p2", "20261010", "Payment", [("Supplier S", 9500, True), ("Cash", 9500, False)])              # A4
    vh(s, c, "p3", "20261011", "Payment", [("Supplier S", 9800, True), ("Cash", 9800, False)])
    vh(s, c, "t1", "20261012", "Payment", [("Trader T", 300000, True), ("HDFC", 300000, False)])            # E21
    vh(s, c, "t2", "20261020", "Receipt", [("HDFC", 300000, True), ("Trader T", 300000, False)])
    vh(s, c, "l1", "20261101", "Payment", [("Mr A Director", 500000, True), ("HDFC", 500000, False)])       # D18
    vh(s, c, "i1", "20261102", "Journal", [("Interest Paid", 10000, True), ("Loan from X", 10000, False)])
    vh(s, c, "g1", "20261103", "Purchase", [("Motor Car Expenses", 10000, True), ("Input CGST", 900, True),
                                            ("Supplier S", 10900, False)])                                  # G36
    vh(s, c, "x1", "20261104", "Journal", [("School Fees", 40000, True), ("Mr A Director", 40000, False)],
       "son's school fees")                                                                                  # I48
    vh(s, c, "dp1", "20261105", "Payment", [("Supplier S", 25000, True), ("HDFC", 25000, False)])           # J52
    vh(s, c, "dp2", "20261107", "Payment", [("Supplier S", 25000, True), ("HDFC", 25000, False)])
    vh(s, c, "s1", "20261003", "Sales", [("Trader T", 200000, True), ("Sales", 200000, False)])             # G34
    vh(s, c, "s2", "20261005", "Purchase", [("Purchases", 190000, True), ("Trader T", 190000, False)])
    s.add(BankLine(company_id=c.id, bank_ledger="HDFC", line_hash="b1", date="20261006", narration="CASH DEPOSIT",
                   deposit=49000.0))
    s.add(BankLine(company_id=c.id, bank_ledger="HDFC", line_hash="b2", date="20261008", narration="CASH DEP BR",
                   deposit=48500.0))                                                                         # H43
    s.add(BankLine(company_id=c.id, bank_ledger="HDFC", line_hash="b3", date="20261009",
                   narration="SWIFT INWARD REMITTANCE ACME LLC", deposit=900000.0))                         # H47
    s.commit()
    flags = redflags.run(s, c, m, periods.quick("This FY", TODAY), TODAY)
    rules = {f.rule for f in flags}
    for r in ("A1", "A2", "A3", "A4", "E21", "D17", "D18", "D19", "G36", "I48", "J52", "G34", "H43", "H47"):
        assert r in rules, r
    assert "Z0" not in rules, [f.detail for f in flags if f.rule == "Z0"]
    a1 = next(f for f in flags if f.rule == "A1")
    assert a1.party == "Customer C" and a1.severity == "high" and "186" in a1.law
    top = redflags.party_scores(flags)
    assert top and top[0][1] >= 10


def test_review_persists_and_party_suppression(db):
    s, c, m = db
    vh(s, c, "r1", "20261002", "Receipt", [("Cash", 250000, True), ("Customer C", 250000, False)])
    vh(s, c, "r2", "20261009", "Receipt", [("Cash", 260000, True), ("Customer C", 260000, False)])
    s.commit()
    per = periods.quick("This FY", TODAY)
    f = [x for x in redflags.run(s, c, m, per, TODAY) if x.rule == "A1"]
    assert len(f) == 2
    redflags.review(s, c, f[0], "false_positive", "Bank deposit wrongly entered as cash", "op@pc")
    again = [x for x in redflags.run(s, c, m, per, TODAY) if x.rule == "A1"]
    assert sorted(x.status for x in again) == ["false_positive", "open"]
    redflags.review(s, c, again[1], "explained", "Customer's cash sales are part of trade", "op@pc", whole_party=True)
    again = [x for x in redflags.run(s, c, m, per, TODAY) if x.rule == "A1"]
    assert all(x.status != "open" for x in again)


def test_related_transactions_view(db):
    s, c, m = db
    vh(s, c, "l1", "20261101", "Payment", [("Mr A Director", 500000, True), ("HDFC", 500000, False)])
    vh(s, c, "l2", "20261102", "Sales", [("A Holdings", 100000, True), ("Sales", 100000, False)])
    s.commit()
    rt = redflags.related_transactions(s, c, m, periods.quick("This FY", TODAY))
    assert set(rt) == {"Mr A Director", "A Holdings"}


def test_excel_export(db, tmp_path):
    s, c, m = db
    vh(s, c, "r1", "20261002", "Receipt", [("Cash", 250000, True), ("Customer C", 250000, False)])
    s.commit()
    flags = redflags.run(s, c, m, periods.quick("This FY", TODAY), TODAY)
    redflags.to_excel(flags, tmp_path / "rf.xlsx", "Eight Co", "FY 2026-27")
    from openpyxl import load_workbook
    assert load_workbook(tmp_path / "rf.xlsx")["Red flags"].max_row >= 3


# ---------------------------------------------------------------- TDS labels and guessing
def test_tds_labels_by_date_and_guess():
    assert tds_map.label("194C", "20260315") == "194C"
    assert tds_map.label("194C", "20261015") == "393(1) Sl. 6(i) (old 194C)"
    assert tds_map.label("194J", "20261015").endswith("(old 194J(b))")
    assert tds_map.label("NA", "20261015") == "Not applicable"
    assert tds_map.guess(["Insurance Premium"]) == "NA"
    assert tds_map.guess(["Hotel & Lodging"]) == "NA"
    assert tds_map.guess(["Professional Fees"]) == "194J-P"
    assert tds_map.guess(["Office Rent"]) == "194I-B"
    assert tds_map.guess(["Freight Inward"]) == "194C"
    assert tds_map.guess(["Purchases"], is_goods_purchase=True) == "194Q"


def test_party_section_override_is_used(db):
    from app.engine import compliance
    s, c, m = db
    for i in range(4):
        vh(s, c, f"h{i}", f"2026100{i + 1}", "Journal", [("Office Exp", 30000, True), ("Supplier S", 30000, False)])
    s.commit()
    near = compliance.tds_threshold_watch(s, c, m, TODAY)
    assert near and near[0][0] == "Supplier S"
    compliance.set_party_section(s, c, "Supplier S", "NA")
    assert compliance.tds_threshold_watch(s, c, m, TODAY) == []


# ---------------------------------------------------------------- trading account
def test_trading_account_with_stock_ledger():
    from app.engine import reports
    groups = {g: {"PARENT": "Primary"} for g in ("Capital Account", "Bank Accounts", "Sales Accounts",
                                                   "Purchase Accounts", "Indirect Expenses", "Stock-in-Hand",
                                                   "Direct Expenses")}
    closings = {
        "Capital": {"parent": "Capital Account", "closing": D("100000"), "opening": D("100000")},
        "Bank": {"parent": "Bank Accounts", "closing": D("-60000"), "opening": D("-60000")},
        "Sales": {"parent": "Sales Accounts", "closing": D("200000"), "opening": D(0)},
        "Purchases": {"parent": "Purchase Accounts", "closing": D("-150000"), "opening": D(0)},
        "Freight": {"parent": "Direct Expenses", "closing": D("-10000"), "opening": D(0)},
        "Rent": {"parent": "Indirect Expenses", "closing": D("-20000"), "opening": D(0)},
        "Closing Stock": {"parent": "Stock-in-Hand", "closing": D("-30000"), "opening": D("-40000")},
    }
    rep = reports.build(groups, closings, None)
    assert rep.stock_source == "Stock-in-Hand ledger(s)"
    # GP = 200000 + 30000 - 40000 - 150000 - 10000 = 30000 ; NP = 10000
    assert rep.gross_profit == D("30000") and rep.net_profit == D("10000")
    assert rep.trading_total == D("230000") and rep.plac_total == D("30000")
    names_left = [n.name for n in rep.trading_left]
    assert names_left[0] == "Opening Stock" and "Gross Profit c/o" in names_left
    assert [n.name for n in rep.plac_right][0] == "Gross Profit b/f"


def test_tb_cross_check():
    from app.engine import reports
    from app.tally.parsers import parse_tb_report
    raw = (b"<ENVELOPE><DSPACCNAME><DSPDISPNAME>Capital Account</DSPDISPNAME></DSPACCNAME><DSPACCINFO>"
           b"<DSPCLDRAMT><DSPCLDRAMTA></DSPCLDRAMTA></DSPCLDRAMT><DSPCLCRAMT><DSPCLCRAMTA>50000.00</DSPCLCRAMTA>"
           b"</DSPCLCRAMT></DSPACCINFO><DSPACCNAME><DSPDISPNAME>Bank Accounts</DSPDISPNAME></DSPACCNAME>"
           b"<DSPACCINFO><DSPCLDRAMT><DSPCLDRAMTA>-70000.00</DSPCLDRAMTA></DSPCLDRAMT><DSPCLCRAMT><DSPCLCRAMTA>"
           b"</DSPCLCRAMTA></DSPCLCRAMT></DSPACCINFO></ENVELOPE>")
    tb = parse_tb_report(raw)
    assert tb == [("Capital Account", D(0), D("50000.00")), ("Bank Accounts", D("70000.00"), D(0))]
    groups = {"Capital Account": {"PARENT": "Primary"}, "Bank Accounts": {"PARENT": "Primary"}}
    rep = reports.build(groups, {"Cap": {"parent": "Capital Account", "closing": D("50000")},
                                 "HDFC": {"parent": "Bank Accounts", "closing": D("-50000")}}, None)
    mism = reports.compare_tb(rep, tb)
    assert [x[0] for x in mism] == ["Bank Accounts"]
