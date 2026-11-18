"""v9.2: fixes found while preparing the demo data pack (Aarohan Infotech)."""
from datetime import date
from decimal import Decimal as D

from app.db.models import MasterCache, VoucherHistory
from app.engine import bank, compliance, masters as masters_mod, periods, redflags, rules
from app.engine.voucher import to_xml
from app.extract.parser import is_date_only, parse
from app.extract.validator import validate
from app.tally import parsers
from tests import samples as S
from tests.test_engine import db  # noqa: F401  (fixture)

CO = "24AAHCA4821K1ZR"
HEAD = """{sup}                                                    {kind}
Shop 21-24, Lamington Road                                          {label}: {no}
Mumbai, Maharashtra - 400007                                        Date: 14-11-2026
GSTIN: {gstin}    PAN: {pan}                                        {extra}

 Bill To:
 Aarohan Infotech Private Limited
 GSTIN: {co}    Place of supply: {pos}
"""


def _doc(body, sup="Vertex Computers Private Limited", kind="TAX INVOICE", label="Invoice No.", no="VC/2627/0389",
         gstin="27AACCV3381N1ZU", extra="", pos="24-Gujarat", co=CO):
    return HEAD.format(sup=sup, kind=kind, label=label, no=no, gstin=gstin, pan=gstin[2:12], extra=extra, pos=pos,
                       co=co) + body


# ---------------------------------------------------------------- bank: "Debit/Credit" marker column
def test_debit_credit_marker_column(tmp_path):
    f = tmp_path / "card.csv"
    f.write_text("Txn Date,Description,Amount,Debit/Credit,Balance\n01/11/2026,POS ZENITH,1899.00,Debit,\n"
                 "02/11/2026,REFUND,500.00,Credit,\n03/11/2026,FEE,59.00,Debit / Credit,\n")
    st = bank.parse(f)
    assert st.mapping["drcr"] == 3 and "withdrawal" not in st.mapping and "deposit" not in st.mapping
    assert [(t.withdrawal, t.deposit) for t in st.txns[:2]] == [(D("1899.00"), 0), (0, D("500.00"))]
    # spaced variant of the header is the same column
    assert bank.detect_mapping(["Date", "Narration", "Amount", "Debit / Credit"])["drcr"] == 3
    # separate Debit and Credit columns still map as before
    m = bank.detect_mapping(["Date", "Narration", "Debit", "Credit", "Balance"])
    assert m["withdrawal"] == 2 and m["deposit"] == 3 and "drcr" not in m


# ---------------------------------------------------------------- invoice number that looks like a date
def test_invoice_number_with_date_like_parts():
    assert not is_date_only("CN/INV/26-11/0457") and is_date_only("05-11-2026") and is_date_only("05/Nov/26")
    inv = parse(_doc("""
1      Cloud hosting                   998315     1   Month   28,000.00   18   28,000.00
                                                         Taxable value         28,000.00
                                                           IGST @ 18%           5,040.00
                                                               Total           33,040.00
""", sup="CloudNest Technologies Private Limited", no="CN/INV/26-11/0457", gstin="29AAHCC9120B1ZW"), CO)
    assert inv.invoice_no == "CN/INV/26-11/0457" and inv.invoice_date == "20261114"


# ---------------------------------------------------------------- supplier credit note -> Debit Note
CN_BODY = """
1      Keyboard Mouse Combo - return    84716060    2   Nos   1,050.00   18    2,100.00
                                                         Taxable value          2,100.00
                                                           IGST @ 18%             378.00
Amount in words: Rupees Two Thousand Four Hundred Seventy Eight Only           Total    2,478.00
"""


def test_credit_note_read_offline():
    inv = parse(_doc(CN_BODY, kind="CREDIT NOTE", label="Note No.", no="CN/VC/2627/021",
                     extra="Against Invoice: VC/2627/0389"), CO)
    assert inv.invoice_no == "CN/VC/2627/021" and inv.document_type == "credit_note"
    assert inv.original_invoice_no == "VC/2627/0389" and inv.grand_total == D("2478.00")
    v = validate(inv, CO, "Gujarat", today=date(2026, 11, 17))
    assert any(i.level == "info" and "Debit Note" in i.message for i in v.issues)
    # an ordinary invoice is not taken as a note, and "Against Invoice" is never the document number
    inv2 = parse(_doc(CN_BODY), CO)
    assert inv2.document_type == "tax_invoice" and inv2.invoice_no == "VC/2627/0389" and not inv2.original_invoice_no


def test_credit_note_posts_as_debit_note(db):  # noqa: F811
    s, c = db
    s.add(MasterCache(company_id=c.id, kind="ledger", name="Cloudnine Returns", parent="Indirect Expenses", data={}))
    s.commit()
    m = masters_mod.load(s, c.id)
    inv = parse(S.INTER, S.COMPANY_GSTIN)
    inv.document_type, inv.original_invoice_no = "credit_note", "CL/9/2026"
    v = rules.suggest(s, c, m, inv).voucher
    assert v.base_type == "Debit Note" and v.vtype == "Debit Note"
    party = next(l for l in v.lines if l.kind == "party")
    assert party.dr and party.bills == [("CL/9/2026", "Agst Ref", party.amount)]
    assert all(not l.dr for l in v.lines if l.kind in ("expense", "gst_in"))
    assert v.balanced and not any(l.kind == "tds" for l in v.lines)
    x = to_xml(v)
    assert "<VOUCHERTYPENAME>Debit Note</VOUCHERTYPENAME>" in x and "<BILLTYPE>Agst Ref</BILLTYPE>" in x
    assert "purchase return / credit note" in v.narration


# ---------------------------------------------------------------- mixed GST rates from the GST% column
def test_mixed_rate_invoice_slabs():
    inv = parse(_doc("""
#      Description          HSN/SAC     Qty   Unit    Rate    GST%     Amount
1      A4 copier paper      48025690     20   Ream   285.00    12    5,700.00
2      Ball pens            96081019      5    Box   160.00    18      800.00
3      Spiral notebooks     48202000     24    Nos    55.00    12    1,320.00
4      Stapler              84729010      4    Nos   145.00    18      580.00
5      Printer labels       48211020      2   Pack   390.00    18      780.00
6      Highlighters         96082000      6    Set   120.00    18      720.00
7      Clear bags           39269099     10   Pack    65.00    18      650.00
                                                  Taxable value          10,550.00
                                                            CGST            738.90
                                                            SGST            738.90
                                                       Round off               0.20
Amount in words: Rupees Twelve Thousand Twenty Eight Only               Total       12,028.00
""", sup="Om Stationers", no="OS/26-27/1466", gstin="24AJWPS6123K1ZL"), CO)
    assert [(t.rate, t.taxable, t.cgst) for t in inv.taxes] == [(D(12), D("7020.00"), D("421.20")),
                                                                (D(18), D("3530.00"), D("317.70"))]
    v = validate(inv, CO, "Gujarat", today=date(2026, 11, 17))
    assert not [i for i in v.issues if i.level == "error"], v.issues


# ---------------------------------------------------------------- printed total that doesn't add up
def test_wrong_printed_total_is_flagged():
    inv = parse(_doc("""
1      Digital campaign       998365      1   Month   65,000.00   18   65,000.00
                                                  Taxable value         65,000.00
                                                    IGST @ 18%          11,700.00
Amount in words: Rupees Seventy Six Thousand Eight Hundred Only              Total       76,800.00
""", sup="Pixel Craft Media", no="PCM/26-27/077", gstin="08AAWFP1176J1ZL"), CO)
    assert inv.grand_total == D("76800.00")
    v = validate(inv, CO, "Gujarat", today=date(2026, 11, 17))
    assert any(i.field == "grand_total" and i.level == "error" and "diff 100.00" in i.message for i in v.issues)


# ---------------------------------------------------------------- place of supply in another state
def test_out_of_state_place_of_supply_warns():
    inv = parse(_doc("""
1      Room charges           996311      2   Night   4,200.00   12    8,400.00
2      Food and beverages     996331      1   Bill    1,850.00    5    1,850.00
                                                  Taxable value         10,250.00
                                                            CGST            550.25
                                                            SGST            550.25
                                                       Round off               0.50
                                                             Total         11,351.00
""", sup="Hotel Grand Residency", no="HGR/2627/4471", gstin="27AAGFH2231P1Z7", pos="27-Maharashtra"), CO)
    v = validate(inv, CO, "Gujarat", today=date(2026, 11, 17))
    assert any(i.field == "place_of_supply" and "not available" in i.message for i in v.issues)
    assert not any("not a GST rate" in i.message for i in v.issues)


# ---------------------------------------------------------------- item invoices: stock-line ledgers are read
ITEM_VCH = b"""<ENVELOPE><BODY><DATA><COLLECTION><VOUCHER><DATE>20261106</DATE>
<VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME><VOUCHERNUMBER>1</VOUCHERNUMBER><PARTYLEDGERNAME>Vertex</PARTYLEDGERNAME>
<ALLINVENTORYENTRIES.LIST><STOCKITEMNAME>Monitor</STOCKITEMNAME><AMOUNT>-60000.00</AMOUNT>
<ACCOUNTINGALLOCATIONS.LIST><LEDGERNAME>Purchase - Hardware</LEDGERNAME><ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
<AMOUNT>-60000.00</AMOUNT></ACCOUNTINGALLOCATIONS.LIST></ALLINVENTORYENTRIES.LIST>
<ALLINVENTORYENTRIES.LIST><STOCKITEMNAME>Keyboard</STOCKITEMNAME><AMOUNT>-24900.00</AMOUNT>
<ACCOUNTINGALLOCATIONS.LIST><LEDGERNAME>Purchase - Hardware</LEDGERNAME><ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
<AMOUNT>-24900.00</AMOUNT></ACCOUNTINGALLOCATIONS.LIST></ALLINVENTORYENTRIES.LIST>
<LEDGERENTRIES.LIST><LEDGERNAME>Vertex</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>100182.00</AMOUNT>
</LEDGERENTRIES.LIST>
<LEDGERENTRIES.LIST><LEDGERNAME>Input IGST</LEDGERNAME><ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-15282.00</AMOUNT>
</LEDGERENTRIES.LIST></VOUCHER></COLLECTION></DATA></BODY></ENVELOPE>"""


def test_item_invoice_entries_balance():
    v = parsers.parse_vouchers(ITEM_VCH)[0]
    e = {x["ledger"]: (D(x["amount"]), x["dr"]) for x in v["entries"]}
    assert e["Purchase - Hardware"] == (D("84900.00"), True)
    dr = sum(D(x["amount"]) for x in v["entries"] if x["dr"])
    cr = sum(D(x["amount"]) for x in v["entries"] if not x["dr"])
    assert dr == cr == D("100182.00")


# ---------------------------------------------------------------- red flags that were false alarms
def _book(s, c, ledgers, vouchers):
    for g in ("Sundry Creditors", "Duties & Taxes", "Indirect Expenses", "Purchase Accounts", "Current Liabilities",
              "Bank Accounts", "Fixed Assets"):
        s.add(MasterCache(company_id=c.id, kind="group", name=g, parent="Primary", data={}))
    for n, p in ledgers:
        s.add(MasterCache(company_id=c.id, kind="ledger", name=n, parent=p, data={}))
    for i, (d, t, ents, nar) in enumerate(vouchers):
        s.add(VoucherHistory(company_id=c.id, guid=f"r{i}", masterid=str(i + 1), date=d, voucher_type=t,
                             number=str(i + 1), party="", reference="", narration=nar,
                             entries=[{"ledger": l, "amount": str(a), "dr": dr} for l, a, dr in ents]))
    s.commit()
    return masters_mod.load(s, c.id)


def test_salary_tds_goods_and_depreciation_not_flagged(db):  # noqa: F811
    s, c = db
    m = _book(s, c, [("Salary", "Indirect Expenses"), ("Salary Payable", "Current Liabilities"),
                     ("PF Payable", "Duties & Taxes"), ("TDS Payable u/s 192", "Duties & Taxes"),
                     ("Vertex", "Sundry Creditors"), ("Purchase - Hardware", "Purchase Accounts"),
                     ("Depreciation", "Indirect Expenses"), ("Computers", "Fixed Assets")],
              [("20261031", "Journal", [("Salary", 340000, True), ("Salary Payable", 300000, False),
                                        ("PF Payable", 17500, False), ("TDS Payable u/s 192", 22500, False)], "Oct"),
               ("20261106", "Purchase", [("Purchase - Hardware", 405920, True), ("Vertex", 405920, False)], ""),
               ("20261031", "Journal", [("Depreciation", 127250, True), ("Computers", 127250, False)],
                "Depreciation on computers, furniture and server for H1")])
    rep = compliance.tds_tracker(s, c, m, periods.Period(date(2026, 4, 1), date(2027, 3, 31)), date(2026, 11, 17))
    assert rep.deductions[0]["party"].startswith("Employees")
    fl = redflags.run(s, c, m, periods.Period(date(2026, 4, 1), date(2027, 3, 31)), today=date(2026, 11, 17))
    rules_hit = {f.rule for f in fl}
    assert "C14" not in rules_hit and "I49" not in rules_hit
    assert not any(f.rule == "C11" and f.party == "Vertex" for f in fl)


def test_item_invoice_xml_sets_entry_mode():
    from app.engine.voucher import InvLine, VLine, Voucher
    v = Voucher(vtype="Purchase", base_type="Purchase", date="20260410", party="Vertex",
                lines=[VLine("Vertex", D("1180"), False, "party"), VLine("Input IGST", D("180"), True, "gst_in")],
                inventory=[InvLine("Monitor", D("1"), "Nos", D("1000"), D("1000"), "Purchase - Hardware")])
    x = to_xml(v)
    assert "<VCHENTRYMODE>Item Invoice</VCHENTRYMODE>" in x and 'OBJVIEW="Invoice Voucher View"' in x
    v.inventory = []
    v.lines.append(VLine("Office Expenses", D("1000"), True, "expense"))
    assert "VCHENTRYMODE" not in to_xml(v)


def test_trading_ledgers_affect_stock():
    from app.tally.masters_write import ledger_xml
    assert "<AFFECTSSTOCK>Yes</AFFECTSSTOCK>" in ledger_xml("Purchase - Hardware", "Purchase Accounts")
    assert "<AFFECTSSTOCK>Yes</AFFECTSSTOCK>" in ledger_xml("Sales - Hardware", "Sales Accounts")
    assert "<AFFECTSSTOCK>No</AFFECTSSTOCK>" in ledger_xml("Office Expenses", "Indirect Expenses")
    assert "<AFFECTSSTOCK>No</AFFECTSSTOCK>" in ledger_xml("Sales - Services", "Sales Accounts", affects_stock=False)


# ---------------------------------------------------------------- lines entered in Tally after the import
def test_recheck_marks_lines_posted_from_another_statement(db):  # noqa: F811
    from app.db.models import BankLine
    from app.engine.posting import record_history
    from app.engine.voucher import VLine, Voucher
    s, c = db

    def line(bank, date, nar, dep=0.0, wd=0.0, status="new"):
        ln = BankLine(company_id=c.id, bank_ledger=bank, line_hash=f"{bank}{date}{nar}{dep}{wd}", date=date,
                      narration=nar, deposit=dep, withdrawal=wd, status=status)
        s.add(ln)
        return ln

    icici = line("ICICI CA", "20261109", "INF/INFT/IB FUNDS TRANSFER/HDFC BANK CA", dep=100000)
    card = line("HDFC Card", "20261116", "PAYMENT RECEIVED - THANK YOU (NACH)", dep=14854)
    far = line("HDFC Card", "20261125", "PAYMENT RECEIVED - THANK YOU (NACH)", dep=14854)  # 9 days later
    # two equal ATM withdrawals on one statement: the first posted from this statement, the second still new
    atm1 = line("ICICI CA", "20261103", "ATM WDL 1", wd=10000, status="posted")
    atm2 = line("ICICI CA", "20261103", "ATM WDL 2", wd=10000)
    s.commit()
    assert bank.recheck_new_lines(s, c.id, "ICICI CA") == []         # nothing in Tally yet
    for v in (Voucher(vtype="Contra", base_type="Contra", date="20261109", narration="IB FUNDS TRANSFER",
                      lines=[VLine("ICICI CA", D("100000"), True), VLine("HDFC CA", D("100000"), False)]),
              Voucher(vtype="Contra", base_type="Contra", date="20261116", narration="NACH DR CARD AUTOPAY",
                      lines=[VLine("HDFC Card", D("14854"), True), VLine("HDFC CA", D("14854"), False)]),
              Voucher(vtype="Contra", base_type="Contra", date="20261103", narration="ATM",
                      lines=[VLine("Cash", D("10000"), True), VLine("ICICI CA", D("10000"), False)])):
        record_history(s, c.id, v)                                    # posted from the HDFC / ICICI page
    s.commit()
    got = bank.recheck_new_lines(s, c.id, "ICICI CA")
    assert [ln for ln, _d in got] == [icici] and icici.status == "in_tally" and "Contra" in got[0][1]
    assert atm2.status == "new" and atm1.status == "posted"          # the ATM voucher belongs to the posted line
    got = bank.recheck_new_lines(s, c.id, "HDFC Card")
    assert [ln for ln, _d in got] == [card] and far.status == "new"   # beyond 3 days: left for the user
    assert bank.recheck_new_lines(s, c.id, "HDFC Card") == []         # nothing marked twice


def test_settings_page_removes_gemini_key(monkeypatch):
    from unittest.mock import MagicMock
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from app import config
    from app.ui import main_window as mw
    QApplication.instance() or QApplication([])
    store = {"gemini_api_key": "AIza-test"}
    monkeypatch.setattr(mw, "get_secret", lambda n: store.get(n))
    monkeypatch.setattr(mw, "delete_secret", lambda n: store.pop(n, None))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    st = MagicMock()
    st.settings = config.Settings()
    st.settings.use_gemini = True
    st.settings.save = lambda: None
    page = mw.SettingsPage(st)
    assert page.btn_del_key.isEnabled()
    page.remove_key()
    assert "gemini_api_key" not in store and not st.settings.use_gemini and not page.btn_del_key.isEnabled()
