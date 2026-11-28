"""GSTR-2B upload, purchase register (Excel + Tally Day Book) and the stored reconciliation."""
from datetime import date
from decimal import Decimal as D

import pytest

from ipt.services.recon.gstr2b_service import Gstr2bError, NeedsReplace
from ipt.services.recon.purchase_register import TallyMasters, guess_mapping, parse_day_book
from ipt.services.recon.recon_service import ReconError
from tests.gstr2b_samples import make_2b_excel
from tests.pdfgen import gst

S1 = gst("08AAACS1111A1Z")
S2 = gst("08AAACT2222B1Z")
B2B = [(S1, "Shree Traders", "ST/25-26/101", "05-10-2025", 10500, "08-Rajasthan", "No", 10000, 0, 250, 250, 0, "Yes"),
       (S1, "Shree Traders", "ST/25-26/102", "06-10-2025", 21000, "08-Rajasthan", "No", 20000, 0, 500, 500, 0, "Yes"),
       (S2, "Tara Minerals", "TM-55", "12-10-2025", 5250, "08-Rajasthan", "No", 5000, 0, 125, 125, 0, "Yes")]


def _2b(services, tmp_path, rows=B2B, name="2b.xlsx"):
    p = make_2b_excel(tmp_path / name, rows, period_month="October", fy="2025-26", gstin=services.company_gstin)
    return services.gstr2b.upload(p)


def _pr_excel(tmp_path, rows):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Purchase Register", None, None, None, None, None, None, None, None])
    ws.append(["1-Oct-25 to 31-Oct-25"])
    ws.append(["Date", "Particulars", "Voucher Type", "Voucher No.", "Supplier Invoice No.", "Supplier Invoice Date",
               "GSTIN/UIN", "Purchase Within State", "Input CGST", "Input SGST", "Gross Total"])
    for r in rows:
        ws.append(list(r))
    ws.append(["Grand Total", None, None, None, None, None, None, 35000, 875, 875, 36750])
    p = tmp_path / "pr.xlsx"
    wb.save(p)
    return p


PR_ROWS = [(date(2025, 10, 5), "Shree Traders", "Purchase", "1", "ST/25-26/101", date(2025, 10, 5), S1, 10000, 250,
            250, 10500),
           (date(2025, 10, 6), "Shree Traders", "Purchase", "2", "ST/25-26/102", date(2025, 10, 6), S1, 20000, 600,
            600, 21200),
           (date(2025, 10, 9), "Gupta Stores", "Purchase", "3", "G-1", date(2025, 10, 9), "08BADGSTIN0000X", 5000,
            125, 125, 5250),
           (date(2025, 10, 9), "Shree Traders", "Purchase", "4", "", None, S1, 5000, 125, 125, 5250)]


def test_gstr2b_upload_replace_and_history(services, tmp_path):
    up = _2b(services, tmp_path)
    assert up.period == "2025-10" and len(services.gstr2b.records()) == 3
    with pytest.raises(NeedsReplace):
        _2b(services, tmp_path, rows=B2B[:1], name="again.xlsx")
    up2 = services.gstr2b.upload(tmp_path / "again.xlsx", replace=True)
    assert len(services.gstr2b.records()) == 1 and up2.is_current
    assert [u.is_current for u in services.gstr2b.uploads(include_history=True)].count(False) == 1


def test_gstr2b_wrong_company_or_year(services, tmp_path):
    p = make_2b_excel(tmp_path / "x.xlsx", B2B, period_month="October", fy="2026-27")
    with pytest.raises(Gstr2bError, match="outside the financial year"):
        services.gstr2b.upload(p)
    p = make_2b_excel(tmp_path / "y.xlsx", B2B, period_month="October", fy="2025-26", gstin=gst("27AAACZ9999Z1Z"))
    with pytest.raises(Gstr2bError, match="GSTIN"):
        services.gstr2b.upload(p)


def test_purchase_register_excel_with_mapping_and_rejects(services, tmp_path):
    p = _pr_excel(tmp_path, PR_ROWS)
    from ipt.services.recon.purchase_register import guess_header_row, read_rows
    _, rows = read_rows(p)
    h = guess_header_row(rows)
    assert h == 3
    mapping = guess_mapping(rows[h - 1])
    assert mapping["supplier_invoice_no"] == [4] and mapping["cgst"] == [8] and mapping["taxable_value"] == [7]
    up = services.purchases.import_excel(p, None, h, mapping, template_name="Tally default")
    assert (up.rows_ok, up.rows_rejected) == (3, 1)          # bad GSTIN rejected, Grand Total skipped
    rej = services.purchases.rejects(up.id)
    assert "GSTIN" in rej[0].reason
    rec = services.purchases.records()
    assert rec[0].invoice_no_normalized == "ST101" and rec[0].cgst == D("250.00")
    assert rec[-1].supplier_invoice_no == "4"                 # no supplier invoice no: voucher no is used
    assert [t.name for t in services.purchases.templates()] == ["Tally default"]
    services.purchases.export_rejects(up.id, tmp_path / "rej.xlsx")


DAY_BOOK = """<ENVELOPE><BODY><DATA><TALLYMESSAGE>
<VOUCHER VCHTYPE="Purchase"><DATE>20251005</DATE><VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
<VOUCHERNUMBER>1</VOUCHERNUMBER><REFERENCE>ST/25-26/101</REFERENCE><REFERENCEDATE>20251004</REFERENCEDATE>
<PARTYLEDGERNAME>Shree Traders</PARTYLEDGERNAME><MASTERID>11</MASTERID>
<ALLINVENTORYENTRIES.LIST><STOCKITEMNAME>Lime</STOCKITEMNAME><AMOUNT>-10000.00</AMOUNT>
<ACCOUNTINGALLOCATIONS.LIST><LEDGERNAME>Purchase Within State</LEDGERNAME><AMOUNT>-10000.00</AMOUNT></ACCOUNTINGALLOCATIONS.LIST>
</ALLINVENTORYENTRIES.LIST>
<LEDGERENTRIES.LIST><LEDGERNAME>Shree Traders</LEDGERNAME><AMOUNT>10500.00</AMOUNT></LEDGERENTRIES.LIST>
<LEDGERENTRIES.LIST><LEDGERNAME>Input CGST</LEDGERNAME><AMOUNT>-250.00</AMOUNT></LEDGERENTRIES.LIST>
<LEDGERENTRIES.LIST><LEDGERNAME>Input SGST</LEDGERNAME><AMOUNT>-250.00</AMOUNT></LEDGERENTRIES.LIST>
</VOUCHER>
<VOUCHER VCHTYPE="Sales"><DATE>20251005</DATE><VOUCHERTYPENAME>Sales</VOUCHERTYPENAME><VOUCHERNUMBER>9</VOUCHERNUMBER>
<PARTYLEDGERNAME>Customer</PARTYLEDGERNAME></VOUCHER>
<VOUCHER VCHTYPE="Purchase"><DATE>20251007</DATE><VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME><ISCANCELLED>Yes</ISCANCELLED>
<VOUCHERNUMBER>2</VOUCHERNUMBER><PARTYLEDGERNAME>Shree Traders</PARTYLEDGERNAME></VOUCHER>
<VOUCHER VCHTYPE="Debit Note"><DATE>20251008</DATE><VOUCHERTYPENAME>Purchase Return</VOUCHERTYPENAME>
<VOUCHERNUMBER>DN1</VOUCHERNUMBER><REFERENCE>CN-7</REFERENCE><PARTYLEDGERNAME>Shree Traders</PARTYLEDGERNAME>
<LEDGERENTRIES.LIST><LEDGERNAME>Shree Traders</LEDGERNAME><AMOUNT>-525.00</AMOUNT></LEDGERENTRIES.LIST>
<LEDGERENTRIES.LIST><LEDGERNAME>Purchase Within State</LEDGERNAME><AMOUNT>500.00</AMOUNT></LEDGERENTRIES.LIST>
<LEDGERENTRIES.LIST><LEDGERNAME>Input CGST</LEDGERNAME><AMOUNT>12.50</AMOUNT></LEDGERENTRIES.LIST>
<LEDGERENTRIES.LIST><LEDGERNAME>Input SGST</LEDGERNAME><AMOUNT>12.50</AMOUNT></LEDGERENTRIES.LIST>
</VOUCHER>
</TALLYMESSAGE></DATA></BODY></ENVELOPE>"""


def test_tally_day_book_to_purchase_register():
    m = TallyMasters(primary={"Shree Traders": "Sundry Creditors", "Purchase Within State": "Purchase Accounts",
                              "Input CGST": "Duties & Taxes", "Input SGST": "Duties & Taxes"},
                     gstin={"Shree Traders": S1},
                     vch_base={"Purchase": "Purchase", "Purchase Return": "Debit Note", "Debit Note": "Debit Note",
                               "Sales": "Sales"})
    rows = parse_day_book(DAY_BOOK, m, date(2025, 10, 1), date(2025, 10, 31))
    assert len(rows) == 2                          # sales and cancelled vouchers are left out
    inv, dn = rows
    assert (inv["supplier_invoice_no"], inv["supplier_invoice_date"], inv["supplier_gstin"]) == \
        ("ST/25-26/101", date(2025, 10, 4), S1)
    assert (inv["taxable_value"], inv["cgst"], inv["sgst"], inv["igst"], inv["invoice_total"]) == \
        (D("10000.00"), D("250.00"), D("250.00"), None, D("10500.00"))
    assert dn["doc_type"] == "CRN" and dn["taxable_value"] == D("500.00") and dn["invoice_total"] == D("525.00")


def test_reconcile_store_manual_link_itc_and_export(services, tmp_path):
    _2b(services, tmp_path)
    p = _pr_excel(tmp_path, PR_ROWS[:2])
    from ipt.services.recon.purchase_register import read_rows
    _, rows = read_rows(p)
    services.purchases.import_excel(p, None, 3, guess_mapping(rows[2]))
    with pytest.raises(ReconError):
        services.recon.run("three_way")             # no IPT invoices loaded
    run = services.recon.run("tally_2b")
    got = {r.doc_no: r.status for r in services.recon.rows()}
    assert got == {"ST/25-26/101": "MATCHED", "ST/25-26/102": "AMOUNT_MISMATCH", "TM-55": "NOT_IN_BOOKS"}
    assert run.is_latest
    mism = next(r for r in services.recon.rows() if r.status == "AMOUNT_MISMATCH")
    services.recon.update_action(mism.id, "Under Review", "asked supplier")
    # action status and remarks survive a re-run
    services.recon.run("tally_2b")
    again = next(r for r in services.recon.rows() if r.status == "AMOUNT_MISMATCH")
    assert (again.action_status, again.remarks) == ("Under Review", "asked supplier")
    # unmatch with remark, then link manually again
    parts = services.recon.unlink(again.id, "check")
    with pytest.raises(ReconError):
        services.recon.manual_link([p.id for p in parts], "")
    linked = services.recon.manual_link([p.id for p in parts], "same invoice")
    assert linked.is_manual and linked.status == "AMOUNT_MISMATCH"
    # manual link is kept on the next run
    services.recon.run("tally_2b")
    assert any(r.is_manual for r in services.recon.rows())
    # ITC: computed, never decided automatically
    itc = services.recon.itc_rows()
    row = next(x for x in itc if x["doc_no"] == "ST/25-26/102")
    assert row["itc_books"] == D("1200.00") and row["itc_2b"] == D("1000.00") and row["eligibility"] == "Pending review"
    services.recon.save_itc_review(row["row_id"], "Eligible", "Restricted to 2B amount", "", "Claim 1,000")
    assert next(x for x in services.recon.itc_rows() if x["doc_no"] == "ST/25-26/102")["eligibility"] == "Eligible"
    assert len(services.recon.exceptions()) == 2
    services.recon.export_xlsx(tmp_path / "recon.xlsx")
    from openpyxl import load_workbook
    wb = load_workbook(tmp_path / "recon.xlsx")
    assert wb.sheetnames == ["Recon Summary", "Recon Details"]
    # supplier follow-up list: the amount mismatch of Shree Traders, with what to ask
    services.recon.export_followup(tmp_path / "follow.xlsx")
    fw = load_workbook(tmp_path / "follow.xlsx")
    assert fw.sheetnames == ["Supplier summary", "Bills to follow up"]
    bills = list(fw["Bills to follow up"].iter_rows(min_row=2, values_only=True))
    assert len(bills) == 1 and bills[0][2] == "ST/25-26/102" and "amend" in bills[0][9]
    summ = list(fw["Supplier summary"].iter_rows(min_row=2, values_only=True))
    assert summ == [("Shree Traders", S1, 1, 200.0)]


def test_fetch_from_tally_reads_every_day(services, monkeypatch):
    """TallyPrime's Day Book export returns only the SVCURRENTDATE day - a month must be read day by day."""
    import re as _re
    pr = services.purchases
    m = TallyMasters(primary={"Shree Traders": "Sundry Creditors", "Purchase Within State": "Purchase Accounts",
                              "Input CGST": "Duties & Taxes", "Input SGST": "Duties & Taxes"},
                     gstin={"Shree Traders": S1}, vch_base={"Purchase": "Purchase"})
    monkeypatch.setattr(pr, "masters", lambda s, cid: m)

    def day_xml(d):
        return (f'<VOUCHER VCHTYPE="Purchase"><DATE>{d:%Y%m%d}</DATE><VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>'
                f'<VOUCHERNUMBER>V{d:%d}</VOUCHERNUMBER><REFERENCE>ST/{d:%d}</REFERENCE>'
                f'<PARTYLEDGERNAME>Shree Traders</PARTYLEDGERNAME>'
                '<LEDGERENTRIES.LIST><LEDGERNAME>Shree Traders</LEDGERNAME><AMOUNT>1050.00</AMOUNT></LEDGERENTRIES.LIST>'
                '<LEDGERENTRIES.LIST><LEDGERNAME>Purchase Within State</LEDGERNAME><AMOUNT>-1000.00</AMOUNT>'
                '</LEDGERENTRIES.LIST><LEDGERENTRIES.LIST><LEDGERNAME>Input CGST</LEDGERNAME><AMOUNT>-25.00</AMOUNT>'
                '</LEDGERENTRIES.LIST><LEDGERENTRIES.LIST><LEDGERNAME>Input SGST</LEDGERNAME><AMOUNT>-25.00</AMOUNT>'
                '</LEDGERENTRIES.LIST></VOUCHER>')

    from ipt.db.models import Company
    with services.db.session() as ses:
        ses.get(Company, services.ctx.company_id).tally_company_name = "ABC Enterprises"

    class FakeClient:
        def companies(self):
            return [{"name": "ABC Enterprises"}]

        def post(self, xml):
            cur = _re.search(r'<SVCURRENTDATE TYPE="Date">(\d{8})<', xml).group(1)   # like real Tally
            d = date(int(cur[:4]), int(cur[4:6]), int(cur[6:]))
            return f"<ENVELOPE><BODY><DATA><TALLYMESSAGE>{day_xml(d)}</TALLYMESSAGE></DATA></BODY></ENVELOPE>"

    class FakeTally:
        def client(self, company):
            return FakeClient()

    monkeypatch.setattr(pr, "tally", FakeTally())
    up = pr.fetch_from_tally(date(2025, 10, 1), date(2025, 10, 31))
    assert up.rows_ok == 31                       # one voucher on each day of October, all read


def test_day_book_expense_ledgers_count_as_taxable():
    """Freight / repairs / machinery booked on a purchase voucher are the taxable value too; round off is not."""
    m = TallyMasters(primary={"Baba Transport": "Sundry Creditors", "Freight Inward": "Direct Expenses",
                              "Input CGST": "Duties & Taxes", "Input SGST": "Duties & Taxes",
                              "Rounding Off": "Indirect Expenses"},
                     vch_base={"Purchase": "Purchase"})
    raw = ('<VOUCHER VCHTYPE="Purchase"><DATE>20260405</DATE><VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>'
           '<VOUCHERNUMBER>12</VOUCHERNUMBER><PARTYLEDGERNAME>Baba Transport</PARTYLEDGERNAME>'
           '<LEDGERENTRIES.LIST><LEDGERNAME>Baba Transport</LEDGERNAME><AMOUNT>10500.00</AMOUNT></LEDGERENTRIES.LIST>'
           '<LEDGERENTRIES.LIST><LEDGERNAME>Freight Inward</LEDGERNAME><AMOUNT>-10000.40</AMOUNT></LEDGERENTRIES.LIST>'
           '<LEDGERENTRIES.LIST><LEDGERNAME>Input CGST</LEDGERNAME><AMOUNT>-250.01</AMOUNT></LEDGERENTRIES.LIST>'
           '<LEDGERENTRIES.LIST><LEDGERNAME>Input SGST</LEDGERNAME><AMOUNT>-250.01</AMOUNT></LEDGERENTRIES.LIST>'
           '<LEDGERENTRIES.LIST><LEDGERNAME>Rounding Off</LEDGERNAME><AMOUNT>0.42</AMOUNT></LEDGERENTRIES.LIST>'
           '</VOUCHER>')
    (r,) = parse_day_book(raw, m, date(2026, 4, 1), date(2026, 4, 30))
    assert r["taxable_value"] == D("10000.40") and r["purchase_ledger"] == "Freight Inward"
    assert r["invoice_total"] == D("10500.00")


def test_rcm_entries_are_not_reconciled(services, tmp_path):
    rows = B2B + [(S2, "Anant Road Lines", "GR-35", "12-10-2025", 107529, "08-Rajasthan", "Yes", 107529, 0, 2688.23,
                   2688.23, 0, "Yes")]
    _2b(services, tmp_path, rows=rows)
    assert len(services.gstr2b.records()) == 4                  # stored and visible in the 2B screen...
    assert services.recon.availability()["2b"] == 3            # ...but left out of the reconciliation


def test_journal_with_input_gst_is_in_register_and_untaxed_purchase_is_not():
    m = TallyMasters(primary={"Anant Road Lines": "Sundry Creditors", "Freight Inward": "Direct Expenses",
                              "Input CGST": "Duties & Taxes", "Input SGST": "Duties & Taxes",
                              "CGST RCM Payable": "Duties & Taxes", "SGST RCM Payable": "Duties & Taxes",
                              "Shree Traders": "Sundry Creditors", "Purchase Exempt": "Purchase Accounts",
                              "Repairs": "Indirect Expenses"},
                     gstin={"Shree Traders": S1}, vch_base={"Purchase": "Purchase", "Journal": "Journal"})

    def vch(vtype, no, party, lines):
        le = "".join(f"<LEDGERENTRIES.LIST><LEDGERNAME>{n}</LEDGERNAME><AMOUNT>{a}</AMOUNT></LEDGERENTRIES.LIST>"
                     for n, a in lines)
        return (f'<VOUCHER VCHTYPE="{vtype}"><DATE>20251010</DATE><VOUCHERTYPENAME>{vtype}</VOUCHERTYPENAME>'
                f'<VOUCHERNUMBER>{no}</VOUCHERNUMBER><PARTYLEDGERNAME>{party}</PARTYLEDGERNAME>{le}</VOUCHER>')

    raw = (vch("Journal", "J1", "Shree Traders", [("Shree Traders", "1180.00"), ("Repairs", "-1000.00"),
                                                  ("Input CGST", "-90.00"), ("Input SGST", "-90.00")])
           + vch("Purchase", "P9", "Shree Traders", [("Shree Traders", "5000.00"), ("Purchase Exempt", "-5000.00")])
           + vch("Journal", "J2", "Anant Road Lines", [("Anant Road Lines", "107529.00"), ("Freight Inward", "-107529.00"),
                                                       ("Input CGST", "-2688.23"), ("Input SGST", "-2688.23"),
                                                       ("CGST RCM Payable", "2688.23"), ("SGST RCM Payable", "2688.23")]))
    rows = parse_day_book(raw, m, date(2025, 10, 1), date(2025, 10, 31))
    assert [r["voucher_no"] for r in rows] == ["J1", "J2"]        # untaxed purchase P9 left out
    j1, j2 = rows
    assert (j1["taxable_value"], j1["cgst"], j1["invoice_total"], j1["supplier_gstin"]) == \
        (D("1000.00"), D("90.00"), D("1180.00"), S1)
    assert j2["cgst"] == D("2688.23") and j2["narration"].startswith("[RCM]")


def test_2b_with_bad_or_other_gstin_needs_confirmation(services, tmp_path):
    from ipt.services.recon.gstr2b_parser import Parsed2B
    from ipt.services.recon.gstr2b_service import NeedsGstinConfirm, gstin_problem
    own = services.company_gstin
    assert gstin_problem(Parsed2B(gstin_raw=own[:2] + own[3:]), "2b.xlsx", own)          # a character missing
    assert gstin_problem(Parsed2B(gstin=own), f"042026_{S1}_GSTR2B.xlsx", own)          # other GSTIN in name
    assert gstin_problem(Parsed2B(gstin=own, gstin_raw=own), f"042026_{own}_GSTR2B.xlsx", own) == ""
    p = make_2b_excel(tmp_path / f"102025_{S1}_GSTR2B.xlsx", B2B, period_month="October", fy="2025-26",
                      gstin=own)
    with pytest.raises(NeedsGstinConfirm):
        services.gstr2b.upload(p)
    assert services.gstr2b.upload(p, gstin_confirmed=True).period == "2025-10"


def test_itc_timing_from_2b(services, tmp_path):
    late = B2B + [(S2, "Tara Minerals", "TM-9", "11-12-2023", 1050, "08-Rajasthan", "No", 1000, 0, 25, 25, 0, "No")]
    _2b(services, tmp_path, rows=late)
    from ipt.db.models import Gstr2bRecord
    with services.db.session() as ses:
        g = ses.query(Gstr2bRecord).filter_by(doc_no="TM-9").one()
        g.itc_reason = "Record is not eligible for ITC as per section 16(4) of CGST Act, 2017"
    p = _pr_excel(tmp_path, PR_ROWS[:1])
    from ipt.services.recon.purchase_register import read_rows
    _, rows = read_rows(p)
    services.purchases.import_excel(p, None, 3, guess_mapping(rows[2]))
    services.recon.run("tally_2b")
    t = {x["doc_no"]: x["timing"] for x in services.recon.itc_rows()}
    assert t["TM-9"].startswith("Time-barred") and t["ST/25-26/101"] == ""


def test_gstr3b_itc_working(services, tmp_path):
    rows = B2B + [(S2, "Anant Road Lines", "GR-35", "12-10-2025", 107529, "08-Rajasthan", "Yes", 107529, 0, 2688.23,
                   2688.23, 0, "Yes"),
                  (S2, "Tara Minerals", "TM-9", "11-10-2025", 1050, "08-Rajasthan", "No", 1000, 0, 25, 25, 0, "No")]
    cdnr = [(S1, "Shree Traders", "CN-7", "Credit Note", "20-10-2025", 525, 500, 0, 12.5, 12.5, "Yes")]
    p = make_2b_excel(tmp_path / "2b.xlsx", rows, cdnr=cdnr, period_month="October", fy="2025-26",
                      gstin=services.company_gstin)
    services.gstr2b.upload(p)
    pr = _pr_excel(tmp_path, [PR_ROWS[0], (date(2025, 10, 9), "Tara Minerals", "Purchase", "3", "TM-77",
                                           date(2025, 10, 9), S2, 5000, 125, 125, 5250)])
    from ipt.services.recon.purchase_register import read_rows
    _, prow = read_rows(pr)
    services.purchases.import_excel(pr, None, 3, guess_mapping(prow[2]))
    assert services.recon.gstr3b_periods() == ["2025-10"]
    w = services.recon.gstr3b_working("2025-10")
    ln = {x.code: x.amounts for x in w.lines}
    assert ln["4(A)(5)"]["cgst"] == D("862.50")           # 250 + 500 + 125 - 12.50 credit note; RCM and 'No' out
    assert ln["4(D)(2)"]["cgst"] == D("25")
    assert ln["4(B)(2)"]["cgst"] == D("612.50")           # 102, TM-55 and the note are not in the books
    assert ln["4(C)"]["cgst"] == D("250.00")
    groups = {}
    for b in w.bills:
        groups.setdefault(b.group, set()).add(b.doc_no)
    assert groups["not_in_books"] == {"ST/25-26/102", "TM-55", "CN-7"}
    assert groups["not_in_2b"] == {"TM-77"}
    assert groups["not_available"] == {"TM-9"}
    assert w.books_itc["cgst"] == D("375")
    with pytest.raises(ReconError):
        services.recon.gstr3b_working("2025-13")
    services.recon.export_gstr3b("2025-10", tmp_path / "3b.xlsx")
    from openpyxl import load_workbook
    wb = load_workbook(tmp_path / "3b.xlsx")
    assert wb.sheetnames == ["3B Table 4 working", "Bills to check"]
    assert any("Working only" in str(c.value) for c in wb["3B Table 4 working"]["A"])
    # a reverse-charge entry in the books goes to 4(A)(3), not to the 'not in 2B' list
    from ipt.db.models import PurchaseRegisterRecord
    with services.db.session() as ses:
        ses.query(PurchaseRegisterRecord).filter_by(supplier_invoice_no="TM-77").one().narration = "[RCM] freight"
    w = services.recon.gstr3b_working("2025-10")
    ln = {x.code: x.amounts for x in w.lines}
    assert ln["4(A)(3)"]["cgst"] == D("125") and not any(b.group == "not_in_2b" for b in w.bills)


def test_itc_rows_skip_rows_whose_records_were_deleted(services, tmp_path):
    p = make_2b_excel(tmp_path / "2b.xlsx", B2B, period_month="October", fy="2025-26", gstin=services.company_gstin)
    services.gstr2b.upload(p)
    pr = _pr_excel(tmp_path, [PR_ROWS[0]])
    from ipt.services.recon.purchase_register import read_rows
    _, prow = read_rows(pr)
    services.purchases.import_excel(pr, None, 3, guess_mapping(prow[2]))
    run = services.recon.run("tally_2b")
    from ipt.db.models import ReconRow
    with services.db.session() as ses:                   # a bill deleted after the run: nothing left to show
        ses.add(ReconRow(run_id=run.id, company_id=services.ctx.company_id, fy_id=services.ctx.fy_id,
                         status="NOT_IN_IPT"))
    rows = services.recon.itc_rows()
    assert rows and all(r["doc_no"] is not None or r["gstin"] for r in rows)
