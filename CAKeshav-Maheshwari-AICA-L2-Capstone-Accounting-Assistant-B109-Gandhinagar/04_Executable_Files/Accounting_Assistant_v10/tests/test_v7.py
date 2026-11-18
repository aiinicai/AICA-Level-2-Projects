"""v7 engines: bank duplicates and closing balance, Schedule III, TDS tracker, GST panel, ageing, search, close."""
from datetime import date
from decimal import Decimal

import pytest

from app.db.models import BankLine, Company, Invoice, MasterCache, VoucherHistory
from app.db.session import local_sessionmaker, make_local_engine
from app.engine import bank, masters as masters_mod

D = Decimal


@pytest.fixture
def db(tmp_path):
    eng = make_local_engine(f"sqlite:///{tmp_path / 'v7.db'}")
    s = local_sessionmaker(eng, "op@pc")()
    c = Company(tally_guid="g7", name="Seven Co", gstin="24AAACD1234F1Z5", state="Gujarat", settings={})
    s.add(c)
    s.commit()
    return s, c


def _t(d, nar, wd=0, dp=0, bal=None, ref=""):
    return bank.Txn(d, nar, ref, D(str(wd)), D(str(dp)), D(str(bal)) if bal is not None else None)


# ---------------------------------------------------------------- F2 duplicates
def test_overlapping_statement_only_brings_new_lines(db):
    s, c = db
    oct1_15 = bank.Statement([_t("20261005", "NEFT ABC TRADERS INV 12", wd=1000, bal=9000),
                              _t("20261012", "UPI RAMESH KUMAR", dp=500, bal=9500)])
    counts = bank.store_classified(s, c, "HDFC", bank.classify_import(s, c.id, "HDFC", oct1_15))
    assert counts["new"] == 2
    # same days exported again with a slightly different narration format, plus new days
    oct_full = bank.Statement([_t("20261005", "NEFT-ABC TRADERS-INV 12", wd=1000, bal=9000),
                               _t("20261012", "UPI/RAMESH KUMAR/x", dp=500, bal=9500),
                               _t("20261020", "CHQ 000123 SHREE STATIONERS", wd=200, bal=9300, ref="000123")])
    v = bank.classify_import(s, c.id, "HDFC", oct_full)
    assert [x.kind for x in v] == ["dup_imported", "dup_imported", "new"]
    counts = bank.store_classified(s, c, "HDFC", v)
    assert counts == {"new": 1, "dup_imported": 2, "in_tally": 0, "possible": 0}
    assert s.query(BankLine).count() == 3


def test_lines_already_entered_in_tally_are_not_posted_again(db):
    s, c = db
    s.add(VoucherHistory(company_id=c.id, guid="t1", date="20261003", voucher_type="Payment", number="P-7",
                         narration="Paid ABC Traders chq 000555", entries=[
                             {"ledger": "ABC Traders", "amount": "1000", "dr": True},
                             {"ledger": "HDFC", "amount": "1000", "dr": False}]))
    s.add(VoucherHistory(company_id=c.id, guid="t2", date="20261001", voucher_type="Payment", number="P-8",
                         narration="something else", entries=[
                             {"ledger": "Misc", "amount": "750", "dr": True},
                             {"ledger": "HDFC", "amount": "750", "dr": False}]))
    s.commit()
    st = bank.Statement([_t("20261003", "CHQ PAID 000555 ABC TRADERS", wd=1000, ref="000555"),
                         _t("20261004", "ATM CASH", wd=750),
                         _t("20261004", "ABC TRADERS", wd=1000)])          # 2nd payment of same amount: new
    v = bank.classify_import(s, c.id, "HDFC", st)
    assert v[0].kind == "in_tally" and "P-7" in v[0].reason
    assert v[1].kind == "possible"                     # same amount 3 days apart, nothing else matches
    assert v[2].kind == "new"                          # each Tally voucher explains only one line
    bank.store_classified(s, c, "HDFC", v)
    statuses = sorted(l.status for l in s.query(BankLine).all())
    assert statuses == ["in_tally", "new", "new"]


def test_duplicate_within_same_file_is_kept(db):
    s, c = db
    st = bank.Statement([_t("20261005", "SMS CHARGES", wd=15, bal=100), _t("20261005", "SMS CHARGES", wd=15, bal=85)])
    v = bank.classify_import(s, c.id, "HDFC", st)
    assert [x.kind for x in v] == ["new", "new"]       # two genuine charges on one day (different balances)


# ---------------------------------------------------------------- F3 closing balance
def test_balance_check_explains_difference(db):
    s, c = db
    st = bank.Statement([_t("20261101", "Opening deposit", dp=10000, bal=10000),
                         _t("20261105", "NEFT ABC", wd=2000, bal=8000),
                         _t("20261110", "Interest", dp=50, bal=8050)])
    bank.store_classified(s, c, "HDFC", bank.classify_import(s, c.id, "HDFC", st))
    lines = s.query(BankLine).order_by(BankLine.date).all()
    lines[0].status = lines[1].status = "posted"        # first two are in Tally, interest not yet
    s.add(VoucherHistory(company_id=c.id, guid="x1", date="20261101", voucher_type="Receipt", number="1",
                         entries=[{"ledger": "HDFC", "amount": "10000", "dr": True}]))
    s.add(VoucherHistory(company_id=c.id, guid="x2", date="20261105", voucher_type="Payment", number="2",
                         entries=[{"ledger": "HDFC", "amount": "2000", "dr": False}]))
    s.add(VoucherHistory(company_id=c.id, guid="x3", date="20261108", voucher_type="Payment", number="3",
                         narration="cheque issued, not yet cleared",
                         entries=[{"ledger": "HDFC", "amount": "300", "dr": False}]))
    s.commit()
    # Tally: 10000 - 2000 - 300 = 7700 Dr  -> Tally sign -7700
    chk = bank.balance_check(s, c.id, "HDFC", D("-7700"), "20261110")
    assert chk.statement == D("8050.00") and chk.tally == D("7700")
    assert chk.difference == D("350.00")
    assert len(chk.pending_lines) == 1 and len(chk.tally_only) == 1
    assert chk.explained == chk.difference               # interest 50 + uncleared cheque 300


# ---------------------------------------------------------------- F5 Schedule III
def test_sch3_suggestions():
    from app.engine import sch3
    assert sch3.suggest("Share Capital", "Capital Account") == "SH_CAP"
    assert sch3.suggest("Partner Current A/c", "Capital Account") == "SH_CAP"
    assert sch3.suggest("Salary", "Indirect Expenses") == "PL_EMP"
    assert sch3.suggest("Interest on Term Loan", "Indirect Expenses") == "PL_FIN"
    assert sch3.suggest("Interest Received", "Indirect Incomes") == "PL_OI"
    assert sch3.suggest("Depreciation", "Indirect Expenses") == "PL_DEP"
    assert sch3.suggest("HDFC CC A/c", "Bank OD A/c") == "CL_BOR"
    assert sch3.suggest("Computer Software", "Fixed Assets") == "NCA_INT"
    assert sch3.suggest("Input CGST", "Duties & Taxes") == "CA_OTH"        # GST input credit: other current asset
    assert sch3.suggest("Output IGST", "Duties & Taxes", closing=D("900")) == "CL_OTH"
    assert sch3.suggest("TDS Payable", "Duties & Taxes", closing=D("-50")) == "CA_OTH"   # debit balance
    assert sch3.suggest("ABC Traders", "Sundry Creditors", closing=D("-500")) == "CA_SLA"   # debit balance
    assert sch3.suggest("Customer X", "Sundry Debtors", closing=D("200")) == "CL_OTH"       # advance received
    assert sch3.suggest("Fixed Deposit with SBI", "Current Assets") == "CA_CASH"


def test_sch3_build_balances_with_notes_and_previous_year(tmp_path):
    from app.engine import sch3
    led = {"Share Capital": {"_primary": "Capital Account"}, "HDFC Bank": {"_primary": "Bank Accounts"},
           "Sales": {"_primary": "Sales Accounts"}, "Purchases": {"_primary": "Purchase Accounts"},
           "Salary": {"_primary": "Indirect Expenses"}, "Rent": {"_primary": "Indirect Expenses"},
           "ABC Traders": {"_primary": "Sundry Creditors"}, "Profit & Loss A/c": {"_primary": "Primary"}}
    cur_bs = {"Share Capital": D("100000"), "HDFC Bank": D("-180000"), "ABC Traders": D("20000"),
              "Profit & Loss A/c": D("10000")}
    prev_bs = {"Share Capital": D("100000"), "HDFC Bank": D("-110000")}
    cur_pl = {"Sales": D("200000"), "Purchases": D("-120000"), "Salary": D("-20000"), "Rent": D("-10000")}
    prev_pl = {"Sales": D("50000"), "Purchases": D("-30000"), "Salary": D("-10000")}
    st = sch3.build(led, cur_bs, prev_bs, cur_pl, prev_pl, {"Rent": "PL_OTH"},
                    {"cur_open": D("0"), "cur_close": D("0")})
    t = st.totals
    assert t["pat_c"] == D("50000") and t["pat_p"] == D("10000")
    assert t["eq_c"] == t["as_c"] == D("180000")             # capital 1L + reserves (10k opening + 50k) + TP 20k
    assert t["eq_p"] == t["as_p"] == D("110000")
    items = {it.code: it for _s, its in st.bs + st.pl for it in its}
    assert items["PL_EMP"].current == D("20000") and items["CL_TP"].current == D("20000")
    assert all(it.note for it in items.values())
    assert {n for n, _c in st.unmapped} >= {"Salary", "Sales"} and "Rent" not in {n for n, _ in st.unmapped}
    sch3.to_excel(st, tmp_path / "s3.xlsx", "Demo Co", "31-03-2027", "31-03-2026")
    from openpyxl import load_workbook
    wb = load_workbook(tmp_path / "s3.xlsx")
    assert wb.sheetnames[:3] == ["Balance Sheet", "Profit and Loss", "Notes"]
    vals = [c.value for c in wb["Profit and Loss"]["A"]]
    assert "IX. Profit / (Loss) for the period" in vals


def test_sch3_live_from_fake_tally():
    from tests import fake_tally
    from app.tally.client import TallyClient
    from app.engine import sch3
    srv, port = fake_tally.start()
    try:
        st = sch3.fetch(TallyClient("127.0.0.1", port, 10), "Demo", "20260401", "20270331", {}, {})
        assert st.totals["eq_c"] == st.totals["as_c"]
        assert st.totals["pat_c"] == D("20000")
    finally:
        srv.shutdown()


# ---------------------------------------------------------------- E1-E5
def _masters(s, c):
    def m(kind, name, parent="", **data):
        s.add(MasterCache(company_id=c.id, kind=kind, name=name, parent=parent, data=data))
    for g in ("Sundry Creditors", "Sundry Debtors", "Duties & Taxes", "Indirect Expenses", "Bank Accounts"):
        m("group", g, "Primary")
    m("ledger", "TDS Payable 194J", "Duties & Taxes")
    m("ledger", "CA Firm", "Sundry Creditors", INCOMETAXNUMBER="ABCDE1234F")
    m("ledger", "Contractor X", "Sundry Creditors")
    m("ledger", "Customer A", "Sundry Debtors")
    m("ledger", "Professional Fees", "Indirect Expenses")
    m("ledger", "Labour", "Indirect Expenses")
    m("ledger", "HDFC", "Bank Accounts")
    m("ledger", "Output CGST RCM", "Duties & Taxes")
    s.commit()
    return masters_mod.load(s, c.id)


def test_tds_tracker_due_unpaid_26q_and_threshold(db, tmp_path):
    from app.engine import compliance, periods
    s, c = db
    m = _masters(s, c)
    def vh(g, d, typ, ents):
        s.add(VoucherHistory(company_id=c.id, guid=g, date=d, voucher_type=typ, number=g, entries=ents))
    vh("j1", "20260910", "Journal", [{"ledger": "Professional Fees", "amount": "50000", "dr": True},
                                     {"ledger": "TDS Payable 194J", "amount": "5000", "dr": False},
                                     {"ledger": "CA Firm", "amount": "45000", "dr": False}])
    vh("j2", "20261015", "Journal", [{"ledger": "Professional Fees", "amount": "30000", "dr": True},
                                     {"ledger": "TDS Payable 194J", "amount": "3000", "dr": False},
                                     {"ledger": "CA Firm", "amount": "27000", "dr": False}])
    vh("p1", "20261005", "Payment", [{"ledger": "TDS Payable 194J", "amount": "5000", "dr": True},
                                     {"ledger": "HDFC", "amount": "5000", "dr": False}])
    vh("j3", "20261020", "Journal", [{"ledger": "Labour", "amount": "95000", "dr": True},
                                     {"ledger": "Contractor X", "amount": "95000", "dr": False}])
    s.commit()
    rep = compliance.tds_tracker(s, c, m, periods.quick("This FY", date(2026, 11, 13)), date(2026, 11, 13))
    sep, octo = rep.months
    assert (sep.month, sep.deducted, sep.paid, sep.unpaid, sep.due) == ("202609", D("5000"), D("5000"), D(0),
                                                                         "20261007")
    assert octo.unpaid == D("3000") and octo.due == "20261107"
    assert rep.totals["overdue"] == D("3000")                  # due 07-11, today 13-11
    assert rep.deductions[0]["pan"] == "ABCDE1234F" and rep.deductions[0]["rate"] == D("10.00")
    assert rep.near_threshold[0][0] == "Contractor X"         # 95k of the 1L 194C limit, no TDS yet
    assert compliance.due_date("202703") == "20270430"
    compliance.export_26q(rep, tmp_path / "26q.xlsx", "Seven Co", "FY 2026-27")


def test_gst_panel_rule37_rcm_and_2b(db):
    from app.engine import compliance, periods
    s, c = db
    m = _masters(s, c)
    s.add(Invoice(company_id=c.id, file_hash="a", file_path="x", status="posted", status_2b="not_in_2b",
                  extraction={"invoice_no": "INV-9", "invoice_date": "20260410", "supplier_name": "CA Firm",
                              "grand_total": "11800", "cgst_total": "900", "sgst_total": "900"}))
    s.add(VoucherHistory(company_id=c.id, guid="r1", date="20261001", voucher_type="Journal", number="1",
                         entries=[{"ledger": "Output CGST RCM", "amount": "450", "dr": False}]))
    s.commit()
    bills = [{"name": "INV-9", "party": "CA Firm", "date": "20260410", "amount": D("11800")},
             {"name": "INV-10", "party": "CA Firm", "date": "20261001", "amount": D("500")},
             {"name": "S-1", "party": "Customer A", "date": "20260101", "amount": D("-900")}]
    fy = periods.quick("This FY", date(2026, 11, 13))
    p = compliance.gst_panel(s, c, m, fy, bills, date(2026, 11, 13), {"CA Firm": {"closing": D("12300")}})
    assert len(p.reversal_180) == 1 and p.reversal_180[0][5] == D("1800")     # GST known from the invoice
    # payment of 11,800 entered On Account: Tally still shows INV-9 pending, but the ledger owes only 500
    p2 = compliance.gst_panel(s, c, m, fy, bills, date(2026, 11, 13), {"CA Firm": {"closing": D("500")}})
    assert p2.reversal_180 == []
    p3 = compliance.gst_panel(s, c, m, fy, bills, date(2026, 11, 13), {"CA Firm": {"closing": D("-100")}})
    assert p3.reversal_180 == []                                               # debit balance: nothing owed
    assert p.totals["rcm"] == D("450")
    assert p.b2b.get("not_in_2b") == 1 and p.b2b_rows[0][2] == "INV-9"


def test_ageing_and_reminder():
    from app.engine import compliance
    m = masters_mod.Masters(ledgers={"Customer A": {"_primary": "Sundry Debtors"},
                                     "CA Firm": {"_primary": "Sundry Creditors"}})
    bills = [{"name": "S-1", "party": "Customer A", "date": "20261101", "amount": D("-1000")},
             {"name": "S-0", "party": "Customer A", "date": "20260601", "amount": D("-500")},
             {"name": "P-1", "party": "CA Firm", "date": "20261001", "amount": D("700")}]
    rec = compliance.ageing(bills, m, True, date(2026, 11, 13))
    assert rec[0].total == D("1500") and rec[0].buckets[0] == D("1000") and rec[0].buckets[3] == D("500")
    pay = compliance.ageing(bills, m, False, date(2026, 11, 13))
    assert pay[0].party == "CA Firm" and pay[0].buckets[1] == D("700")
    subj, body = compliance.reminder_text("Seven Co", rec[0])
    assert "1,500.00" in subj and "S-0" in body and "Seven Co" in body


def test_global_search(db):
    from app.engine import compliance
    s, c = db
    s.add(VoucherHistory(company_id=c.id, guid="v", date="20261001", voucher_type="Payment", number="P-1",
                         narration="Paid to Shree Stationers", entries=[{"ledger": "HDFC", "amount": "1180",
                                                                         "dr": False}]))
    s.add(Invoice(company_id=c.id, file_hash="b", file_path="inv.pdf", extraction={
        "supplier_name": "Shree Stationers", "invoice_no": "SS/45", "grand_total": "1180"}))
    s.commit()
    kinds = {h.kind for h in compliance.search(s, "shree")}
    assert kinds == {"Voucher", "Invoice"}
    assert {h.kind for h in compliance.search(s, "1,180")} == {"Voucher", "Invoice"}
    assert compliance.search(s, "SS/45")[0].company == "Seven Co"


def test_close_checklist(db):
    from app.engine import compliance
    s, c = db
    m = _masters(s, c)
    s.add(BankLine(company_id=c.id, bank_ledger="HDFC", line_hash="z", date="20261012", withdrawal=10, status="new"))
    s.commit()
    items = {i.key: i for i in compliance.close_status(s, c, m, "202610", date(2026, 11, 13))}
    assert items["bank"].auto == "pending" and items["lock"].auto == "pending"
    compliance.set_close(s, c, "202610", "gst_returns", True, "op@pc", "3B filed 20-11")
    items = {i.key: i for i in compliance.close_status(s, c, m, "202610", date(2026, 11, 13))}
    assert items["gst_returns"].done and items["gst_returns"].by == "op@pc"
