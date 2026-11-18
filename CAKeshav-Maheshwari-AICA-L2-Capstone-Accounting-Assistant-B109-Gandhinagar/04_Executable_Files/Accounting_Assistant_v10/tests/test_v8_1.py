"""v8.1 feedback: bank closing from the balance chain, red flags count business once, posted vouchers reach the
local history, history refresh after re-sync, home lists every bank, Tally-style ledger overtype."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace as NS

from app.db.models import BankLine, VoucherHistory
from app.engine import bank, dashboard, history, periods, redflags
from app.engine.posting import record_history
from app.engine.voucher import Voucher, VLine
from tests.test_v8 import db, vh  # noqa: F401  (fixture)

D = Decimal


def _l(d, wd, dp, bal):
    return NS(date=d, withdrawal=wd, deposit=dp, balance=bal)


def test_statement_closing_ignores_row_order():
    # opening 2,66,251.99; same day: -29,360 then +... ; true closing 2,07,531.99 whatever order the rows come in
    rows = [_l("20261111", 29360, 0, 236891.99), _l("20261111", 29360, 0, 207531.99), _l("20261110", 0, 0, 266251.99)]
    assert bank.statement_closing(rows) == ("20261111", D("207531.99"))
    assert bank.statement_closing(list(reversed(rows))) == ("20261111", D("207531.99"))


def test_red_flags_count_bill_and_payment_once(db):
    s, c, m = db
    vh(s, c, "b1", "20261005", "Purchase", [("Purchases", 100000, True), ("Supplier S", 100000, False)])
    vh(s, c, "b2", "20261006", "Payment", [("Supplier S", 100000, True), ("HDFC", 100000, False)])
    vh(s, c, "r1", "20261007", "Payment", [("Mr A Director", 100000, True), ("HDFC", 100000, False)])
    vh(s, c, "r2", "20261008", "Receipt", [("HDFC", 100000, True), ("Mr A Director", 100000, False)])
    s.commit()
    p = periods.Period(date(2026, 4, 1), date(2027, 3, 31))
    flags = redflags.run(s, c, m, p, today=date(2026, 11, 13))
    d17 = [f for f in flags if f.rule == "D17"]
    assert d17 and all(f.amount == D(100000) for f in d17)
    j54 = [f for f in flags if f.rule == "J54" and f.party == "Supplier S"]
    assert all(f.amount == D(100000) for f in j54)


def test_posting_reaches_history_and_resync_refreshes(db):
    s, c, m = db
    n0 = len(history.vouchers(s, c.id))
    v = Voucher("Payment", "20261112", [VLine("Office Exp", D(500), True), VLine("HDFC", D(500), False)],
                narration="tea", base_type="Payment")
    record_history(s, c.id, v, "991")
    s.commit()
    assert len(history.vouchers(s, c.id)) == n0 + 1
    # re-sync with the same number of rows (ids reused) must still show the new data
    s.query(VoucherHistory).delete()
    s.commit()
    vh(s, c, "x1", "20261112", "Payment", [("Office Exp", 700, True), ("HDFC", 700, False)])
    s.commit()
    history.vouchers(s, c.id)
    s.query(VoucherHistory).delete()
    s.commit()
    vh(s, c, "x2", "20261112", "Payment", [("Office Exp", 900, True), ("HDFC", 900, False)])
    s.commit()
    history.invalidate(c.id)
    assert history.vouchers(s, c.id)[0].guid == "x2"


def test_home_lists_every_bank(db):
    s, c, m = db
    m.ledgers["IndusInd Bank"] = {"_primary": "Bank Accounts"}

    class T:
        def ledger_closings(self, *_):
            return {"HDFC": {"closing": D(-5000), "parent": "Bank Accounts"},
                    "INDUSIND  bank": {"closing": D(-1200), "parent": "Bank Accounts"},
                    "Kotak New": {"closing": D(-10), "parent": "Bank Accounts"}}

        def bills(self, *_):
            return []
    d = dashboard.fetch(T(), s, c, m, periods.Period(date(2026, 4, 1), date(2027, 3, 31)), today=date(2026, 11, 13))
    names = dict(d.cash_bank)
    assert names["HDFC"] == D(-5000) and names["IndusInd Bank"] == D(-1200) and "Kotak New" in names
    assert "Cash" in names


def test_forex_amounts_read_in_rupees():
    from app.tally.parsers import amount
    assert amount("-$ 50000.00 @ ? 90.5291/$  = -? 4526455.00") == D("-4526455.00")
    assert amount("$ 50000.00 @ ₹ 90.6423/$  = ₹ 4532115.04") == D("4532115.04")
    assert amount("-$ 100 @ ₹ 83/$") == D("-8300.00")
    assert amount("-₹ 15205952.54") == D("-15205952.54")
    assert amount("1,180.00 Dr") == D("-1180.00") and amount("") == 0 and amount("-1,52,05,952.54") == D("-15205952.54")


def test_tb_shows_pl_account_brought_forward_only():
    from app.engine import reports
    g = {"Capital Account": {"PARENT": "Primary"}, "Current Assets": {"PARENT": "Primary", "ISDEEMEDPOSITIVE": "Yes"},
         "Sales Accounts": {"PARENT": "Primary", "ISREVENUE": "Yes", "AFFECTSGROSSPROFIT": "Yes"},
         "Indirect Expenses": {"PARENT": "Primary", "ISREVENUE": "Yes", "ISDEEMEDPOSITIVE": "Yes"}}
    cl = {"Capital": {"parent": "Capital Account", "opening": D(100), "closing": D(100)},
          "Bank": {"parent": "Current Assets", "opening": D(-500), "closing": D(-560)},
          "Sales": {"parent": "Sales Accounts", "opening": D(0), "closing": D(90)},
          "Rent": {"parent": "Indirect Expenses", "opening": D(0), "closing": D(-30)},
          # Tally: closing = 400 brought forward + 60 profit of this year
          "Profit & Loss A/c": {"parent": "Primary", "opening": D(400), "closing": D(460)}}
    r = reports.build(g, cl, None)
    pl = next(n for n in r.trial_balance if n.name == "Profit & Loss A/c")
    assert pl.amount == D(400) and r.tb_dr == r.tb_cr == D(590)
    assert r.net_profit == D(60) and not r.notes


def test_receipt_retried_with_voucher_number_after_silent_exception(db):
    from app.db.models import MasterCache
    from app.db.session import local_sessionmaker
    from app.engine import numbering, posting
    s, c, m = db
    s.add(MasterCache(company_id=c.id, kind="voucher_type", name="Receipt", parent="Receipt",
                      data={"NUMBERINGMETHOD": "Automatic"}))
    vh(s, c, "rc8", "20261002", "Receipt", [("HDFC", 12000, True), ("Sales", 12000, False)])
    s.commit()
    assert numbering.next_number(s, c.id, "Receipt", "20261101") == "rc9"   # vh() uses the guid as number
    assert numbering.bump("RCPT/0099/26") == "RCPT/0100/26"

    sent = []

    class Fake:
        def import_vouchers(self, company, frags):
            sent.append(frags[0])
            ok = "<VOUCHERNUMBER>" in frags[0]
            return {"created": int(ok), "altered": 0, "errors": 0, "exceptions": int(not ok),
                    "last_vch_id": "77" if ok else "0", "last_mid": "", "line_errors": []}
    v = Voucher("Receipt", "20261101", [VLine("HDFC", D(12000), True), VLine("Sales", D(12000), False)],
                narration="incentive", base_type="Receipt")
    lock_s = local_sessionmaker(s.get_bind(), "op@pc")()
    r = posting.post(s, lock_s, Fake(), c, v, "op@pc", known_ledgers=set(m.ledgers) | {"Sales", "HDFC"})
    assert r.ok and "No. rc9" in r.message and len(sent) == 2
    assert c.settings["post_variants"]["Receipt"] == "number"
    # next time the number is sent straight away
    sent.clear()
    r2 = posting.post(s, lock_s, Fake(), c, v, "op@pc", known_ledgers=set(m.ledgers) | {"Sales", "HDFC"})
    assert r2.ok and len(sent) == 1 and "<VOUCHERNUMBER>rc10</VOUCHERNUMBER>" in sent[0]


def test_next_number_uses_live_tally_numbers(db):
    from app.engine import numbering
    s, c, m = db
    vh(s, c, "134", "20260930", "Journal", [("Office Exp", 10, True), ("Cash", 10, False)])
    s.commit()
    # 135 was entered in Tally after the last Sync
    assert numbering.next_number(s, c.id, "Journal", "20261022", [("135", "20261031"), ("GST-25/26-27", "")]) == "136"
    assert numbering.next_number(s, c.id, "Journal", "20261022") == "135"
