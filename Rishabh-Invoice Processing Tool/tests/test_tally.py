"""Tally: client parsing (fake HTTP server), master sync, mapping and voucher XML."""
import threading
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from ipt.db.models import Invoice, TallyMaster
from ipt.services.extraction.pipeline import ExtractionPipeline
from ipt.services.tally.client import TallyClient, parse_import_response
from ipt.services.tally.voucher import amounts_sum_zero
from tests.pdfgen import gst, make_invoice

SUP = gst("08BBBCS2222B1Z")

COMPANIES = b"""<ENVELOPE><BODY><DATA><COLLECTION><COMPANY NAME="ABC Tally Co"><NAME>ABC Tally Co</NAME>
<BOOKSFROM>20210401</BOOKSFROM></COMPANY></COLLECTION></DATA></BODY></ENVELOPE>"""
LEDGERS = ("""<ENVELOPE><BODY><DATA><COLLECTION>
<LEDGER NAME="Shree Ganesh Traders"><PARENT>Sundry Creditors</PARENT><PARTYGSTIN>%s</PARTYGSTIN></LEDGER>
<LEDGER NAME="Purchase Within State"><PARENT>Purchase Accounts</PARENT></LEDGER>
<LEDGER NAME="Purchase Interstate"><PARENT>Purchase Accounts</PARENT></LEDGER>
<LEDGER NAME="INPUT CGST"><PARENT>GST</PARENT></LEDGER>
<LEDGER NAME="INPUT SGST"><PARENT>GST</PARENT></LEDGER>
<LEDGER NAME="Output CGST"><PARENT>GST</PARENT></LEDGER>
<LEDGER NAME="Rounding Off"><PARENT>Indirect Expenses</PARENT></LEDGER>
<LEDGER NAME="Bad &#4; char"><PARENT>Indirect Expenses</PARENT></LEDGER>
</COLLECTION></DATA></BODY></ENVELOPE>""" % SUP).encode()
GROUPS = b"""<ENVELOPE><BODY><DATA><COLLECTION><GROUP NAME="GST"><PARENT>Duties &amp; Taxes</PARENT></GROUP>
</COLLECTION></DATA></BODY></ENVELOPE>"""
ITEMS = b"""<ENVELOPE><BODY><DATA><COLLECTION><STOCKITEM NAME="Cement"><BASEUNITS>BAG</BASEUNITS>
<HSNDETAILS.LIST><HSNCODE>2523</HSNCODE></HSNDETAILS.LIST><GSTDETAILS.LIST><RATEDETAILS.LIST>
<GSTRATEDUTYHEAD>IGST</GSTRATEDUTYHEAD><GSTRATE>18</GSTRATE></RATEDETAILS.LIST></GSTDETAILS.LIST></STOCKITEM>
</COLLECTION></DATA></BODY></ENVELOPE>"""
OTHER = {"GODOWN": b'<ENVELOPE><GODOWN NAME="Main Location"/></ENVELOPE>',
         "VOUCHERTYPE": b'<ENVELOPE><VOUCHERTYPE NAME="Purchase"><PARENT>Purchase</PARENT></VOUCHERTYPE>'
                        b'<VOUCHERTYPE NAME="Debit Note"><PARENT>Debit Note</PARENT></VOUCHERTYPE></ENVELOPE>',
         "UNIT": b'<ENVELOPE><UNIT NAME="BAG"/></ENVELOPE>', "COSTCENTRE": b"<ENVELOPE/>"}
received = []
imported_vouchers = []          # vouchers the fake Tally "contains"
created_masters = []            # LEDGER / STOCKITEM elements created through Import Data
FAIL_NEXT = {"line_error": None}
ALTERED = {"ledger_state": {}, "unit_uqc": {}}   # GST details written through ACTION="Alter"


class FakeTally(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self._send(b"<RESPONSE>TallyPrime Server is Running</RESPONSE>")

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"])).decode()
        received.append(body)
        if "Import Data" in body:
            if FAIL_NEXT["line_error"]:
                err, FAIL_NEXT["line_error"] = FAIL_NEXT["line_error"], None
                return self._send(f"<RESPONSE><CREATED>0</CREATED><ERRORS>1</ERRORS><LINEERROR>{err}</LINEERROR>"
                                  "</RESPONSE>".encode())
            import re
            alt = re.findall(r'<(LEDGER|UNIT) NAME="([^"]+)" ACTION="Alter">(.*?)</(?:LEDGER|UNIT)>', body, re.S)
            if alt:
                for kind, name, inner in alt:
                    if kind == "LEDGER":
                        st = re.search(r"<LEDMAILINGDETAILS.LIST>.*?<STATE>(.*?)</STATE>", inner, re.S)
                        ALTERED["ledger_state"][name] = st.group(1) if st else ""
                    else:
                        u = re.search(r"<GSTREPUOM>(.*?)</GSTREPUOM>", inner)
                        ALTERED["unit_uqc"][name] = u.group(1) if u else ""
                return self._send(b"<RESPONSE><CREATED>0</CREATED><ALTERED>1</ALTERED><ERRORS>0</ERRORS></RESPONSE>")
            created_masters.extend(re.findall(r"<(?:LEDGER|STOCKITEM) NAME=.*?</(?:LEDGER|STOCKITEM)>", body, re.S))
            for v in re.findall(r"<VOUCHER[ >].*?</VOUCHER>", body, re.S):
                imported_vouchers.append(v.replace("<VOUCHER ", "<VOUCHER ") + "")
            return self._send(b"<RESPONSE><CREATED>1</CREATED><ALTERED>0</ALTERED><ERRORS>0</ERRORS>"
                              b"<LASTVCHID>777</LASTVCHID></RESPONSE>")
        if "Day Book" in body:
            vs = "".join(v.replace("</VOUCHER>", "<MASTERID>777</MASTERID></VOUCHER>") for v in imported_vouchers)
            return self._send(f"<ENVELOPE><BODY><DATA><TALLYMESSAGE>{vs}</TALLYMESSAGE></DATA></BODY></ENVELOPE>"
                              .encode())
        if "IPTGstLedgers" in body:
            sup_state = ALTERED["ledger_state"].get("Shree Ganesh Traders", "")
            mail = f"<LEDMAILINGDETAILS.LIST><STATE>{sup_state}</STATE></LEDMAILINGDETAILS.LIST>" if sup_state else ""
            reg = f"<LEDGSTREGDETAILS.LIST><GSTIN>{SUP}</GSTIN><STATE>{sup_state}</STATE></LEDGSTREGDETAILS.LIST>"
            return self._send(f'<ENVELOPE><LEDGER NAME="Shree Ganesh Traders"><PARTYGSTIN>{SUP}</PARTYGSTIN>{reg}'
                              f'{mail}</LEDGER><LEDGER NAME="INPUT CGST"></LEDGER></ENVELOPE>'.encode())
        if "IPTGstUnits" in body:
            units = "".join(f'<UNIT NAME="{u}"><GSTREPUOM>{ALTERED["unit_uqc"].get(u, "")}</GSTREPUOM></UNIT>'
                            for u in ("BAG", "MT", "XYZ"))
            return self._send(f"<ENVELOPE>{units}</ENVELOPE>".encode())
        for tag, data in (("<TYPE>Company</TYPE>", COMPANIES), ("<TYPE>Ledger</TYPE>", LEDGERS),
                          ("<TYPE>Group</TYPE>", GROUPS), ("<TYPE>StockItem</TYPE>", ITEMS),
                          ("<TYPE>Godown</TYPE>", OTHER["GODOWN"]), ("<TYPE>VoucherType</TYPE>", OTHER["VOUCHERTYPE"]),
                          ("<TYPE>Unit</TYPE>", OTHER["UNIT"]), ("<TYPE>CostCentre</TYPE>", OTHER["COSTCENTRE"])):
            if tag in body:
                extra = "".join(m for m in created_masters
                                if (tag == "<TYPE>Ledger</TYPE>" and m.startswith("<LEDGER"))
                                or (tag == "<TYPE>StockItem</TYPE>" and m.startswith("<STOCKITEM")))
                if extra:
                    data = data.replace(b"</COLLECTION>", extra.encode() + b"</COLLECTION>")
                return self._send(data)
        self._send(b"<ENVELOPE/>")

    def _send(self, data):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def fake_tally():
    imported_vouchers.clear()
    created_masters.clear()
    ALTERED["ledger_state"].clear()
    ALTERED["unit_uqc"].clear()
    srv = HTTPServer(("127.0.0.1", 0), FakeTally)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()


@pytest.fixture
def tally_services(services, fake_tally, admin):
    from ipt.services.company_service import CompanyInput
    c = services.companies.get_company(services.ctx.company_id)
    services.companies.update_company(c.id, CompanyInput(name=c.name, state_code="08", gstin=c.gstin,
                                                         tally_company_name="ABC Tally Co", tally_port=fake_tally),
                                      admin)
    return services


def test_import_response_parsing():
    ok = parse_import_response("<RESPONSE><CREATED>1</CREATED><ERRORS>0</ERRORS><LASTVCHID>9</LASTVCHID></RESPONSE>")
    assert ok.ok and ok.last_vch_id == "9"
    bad = parse_import_response("<RESPONSE><CREATED>0</CREATED><ERRORS>1</ERRORS>"
                                "<LINEERROR>Ledger 'X' does not exist!</LINEERROR></RESPONSE>")
    assert not bad.ok and bad.line_errors == ["Ledger 'X' does not exist!"]


def test_status_and_sync(tally_services):
    st = tally_services.tally.status()
    assert st.reachable and st.company_open and "TallyPrime" in st.product
    counts = tally_services.tally.sync_masters()
    assert counts["ledger"] == 8 and counts["stock_item"] == 1
    led = {m.name: m for m in tally_services.tally.masters("ledger")}
    assert led["INPUT CGST"].primary_group == "Duties & Taxes"       # GST -> Duties & Taxes
    assert led["Shree Ganesh Traders"].gstin == SUP
    item = tally_services.tally.masters("stock_item")[0]
    assert item.hsn == "2523" and item.gst_rate == Decimal("18") and item.base_unit == "BAG"
    assert all("Import Data" not in r for r in received)            # sync never writes to Tally


def test_unreachable_tally_gives_clear_message(services):
    from ipt.services.tally.client import TallyNotReachable
    with pytest.raises(TallyNotReachable):
        TallyClient("127.0.0.1", 1, timeout=2).ping()


def _approved_invoice(s, tmp_path, total="4,130.00", inv_no="SGT/25-26/0147"):
    pdf = make_invoice(tmp_path / f"v{inv_no[-3:]}.pdf", supplier_gstin=SUP, buyer_gstin=s.company_gstin, inv_no=inv_no,
                       items=[("Cement bags", "2523", "10", "350.00", "3,500.00", "18%", "4,130.00")],
                       totals=[("Taxable Value", "3,500.00"), ("CGST", "315.00"), ("SGST", "315.00"),
                               ("Grand Total", total)])
    doc = s.documents.add_files([pdf]).added[0]
    iid = ExtractionPipeline(s).run(doc.id).invoice_id
    if total != "4,130.00":
        s.invoices.update(iid, {"round_off": ""})
    s.invoices.approve(iid, "test" if total != "4,130.00" else "")
    return iid


def _approve_all(s, iid):
    for ln in s.mapping.lines_for(iid):
        if ln.entity == "debit_ledger":
            continue                      # optional: only for suppliers booked without items
        assert ln.best, f"no suggestion for {ln.entity}"
        s.mapping.approve(ln.entity, ln.source_key, ln.best.name)


def test_mapping_suggestions_and_voucher_xml(tally_services, tmp_path):
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path)
    lines = {(ln.entity, ln.source_key): ln for ln in s.mapping.lines_for(iid)}
    assert lines[("party", SUP)].best.name == "Shree Ganesh Traders"
    assert lines[("party", SUP)].best.reason == "Same GSTIN in Tally"
    assert lines[("purchase_ledger", "intra")].best.name == "Purchase Within State"
    assert lines[("tax_ledger", "CGST")].best.name == "INPUT CGST"   # not 'Output CGST'
    assert lines[("stock_item", "cement bags")].best.name == "Cement"
    built = s.vouchers.build(iid)
    assert not built.ok and any("Not mapped" in b for b in built.blockers)
    _approve_all(s, iid)
    built = s.vouchers.build(iid)
    assert built.ok, built.blockers
    assert built.debit == built.credit == Decimal("4130.00")
    assert amounts_sum_zero(built.xml)
    x = built.xml
    assert "<STOCKITEMNAME>Cement</STOCKITEMNAME>" in x and "<RATE>350.00/BAG</RATE>" in x
    assert "<COUNTRYOFRESIDENCE>India</COUNTRYOFRESIDENCE>" in x and "<CMPGSTSTATE>Rajasthan</CMPGSTSTATE>" in x
    assert "<CMPGSTREGISTRATIONTYPE>Regular</CMPGSTREGISTRATIONTYPE>" in x
    assert "<ACTUALQTY> 10 BAG</ACTUALQTY>" in x and "<GODOWNNAME>Main Location</GODOWNNAME>" in x
    assert "<LEDGERNAME>Shree Ganesh Traders</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>" in x
    assert "<AMOUNT>4130.00</AMOUNT>" in x and "<AMOUNT>-315.00</AMOUNT>" in x
    assert "<VOUCHERNUMBER>SGT/25-26/0147</VOUCHERNUMBER>" in x and "<DATE>20251015</DATE>" in x
    # Tally's invoice view needs the party as the FIRST ledger entry, then the GST ledgers
    import xml.etree.ElementTree as ET
    names = [le.findtext("LEDGERNAME") for le in ET.fromstring(x).iter("LEDGERENTRIES.LIST")]
    assert names[0] == "Shree Ganesh Traders" and names[1:3] == ["INPUT CGST", "INPUT SGST"], names
    # remembered: a second invoice from the same supplier is pre-approved
    assert all(ln.approved for ln in s.mapping.lines_for(iid) if ln.entity != "debit_ledger")


def test_round_off_and_blockers(tally_services, tmp_path):
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path, total="4,130.40")
    _approve_all(s, iid)
    built = s.vouchers.build(iid)
    assert built.ok, built.blockers
    ro = [ln for ln in built.lines if ln.note == "round off"]
    assert ro and ro[0].amount == Decimal("0.40") and amounts_sum_zero(built.xml)
    s.invoices.reject(iid, "test")
    assert any("not approved" in b for b in s.vouchers.build(iid).blockers)


def test_mapping_rejects_unknown_master(tally_services, tmp_path):
    s = tally_services
    s.tally.sync_masters()
    with pytest.raises(ValueError):
        s.mapping.approve("party", SUP, "Ledger That Does Not Exist")


def test_tally_pages_render(tally_services, tmp_path):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ipt.ui.main_window import MainWindow
    from ipt.ui.pages.mapping import MappingPage
    from ipt.ui.pages.vouchers import VouchersPage
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path)
    w = MainWindow(s)
    for row in range(w.nav.count()):
        w.nav.setCurrentRow(row)
    mp = next(p for p in w._pages if isinstance(p, MappingPage))
    mp.refresh()
    mp.invoices.selectRow(0)
    assert mp.grid.rowCount() >= 6
    mp._save()
    assert "Mapping saved" in mp.msg.text()
    vp = next(p for p in w._pages if isinstance(p, VouchersPage))
    vp.refresh()
    vp.list.selectRow(0)
    assert "Ready" in vp.blockers.text() and "<VOUCHER" in vp.xml.toPlainText()
    w.close()
    app.processEvents()


def test_import_verified_then_duplicate_blocked(tally_services, tmp_path):
    from ipt.services.tally.client import TallyError
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path)
    _approve_all(s, iid)
    rec = s.imports.import_invoice(iid)
    assert rec.status == "success" and rec.verified and rec.created == 1
    assert s.invoices.get(iid).status == "imported"
    assert (s.data_root / rec.request_xml_path).is_file()
    with pytest.raises(TallyError):            # same invoice again
        s.imports.import_invoice(iid)
    assert "tally.import" in [r.action for r in s.audit.recent()]


def test_duplicate_already_in_tally_needs_remark(tally_services, tmp_path):
    from ipt.services.tally.client import TallyError
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path)
    _approve_all(s, iid)
    built = s.vouchers.build(iid)
    import re
    imported_vouchers.append(re.search(r"<VOUCHER[ >].*?</VOUCHER>", built.xml, re.S).group(0))  # entered manually
    assert s.imports.check_duplicate(iid)
    with pytest.raises(TallyError, match="may already be in Tally"):
        s.imports.import_invoice(iid)


def test_tally_error_is_recorded_as_failed(tally_services, tmp_path):
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path)
    _approve_all(s, iid)
    FAIL_NEXT["line_error"] = "Ledger 'INPUT CGST' does not exist!"
    rec = s.imports.import_invoice(iid)
    assert rec.status == "failed" and "does not exist" in rec.line_errors
    assert s.invoices.get(iid).status == "approved"        # can be retried after fixing


def test_reviewer_cannot_import(tally_services, tmp_path, db, admin):
    from ipt.core.permissions import PermissionDenied
    from ipt.services.auth_service import AuthService
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path)
    s.ctx.user = AuthService(db).create_user("rev", "password123", "reviewer", actor=admin)
    with pytest.raises(PermissionDenied):
        s.imports.import_invoice(iid)


def test_multi_invoice_pdf_is_split(services, tmp_path):
    import pymupdf
    a = make_invoice(tmp_path / "a.pdf", supplier_gstin=SUP, buyer_gstin=services.company_gstin, inv_no="A-1",
                     items=[("Cement", "2523", "1", "100.00", "100.00", "18%", "118.00")],
                     totals=[("Taxable Value", "100.00"), ("Grand Total", "118.00")])
    b = make_invoice(tmp_path / "b.pdf", supplier_gstin=SUP, buyer_gstin=services.company_gstin, inv_no="B-2",
                     items=[("Sand", "2505", "2", "50.00", "100.00", "5%", "105.00")],
                     totals=[("Taxable Value", "100.00"), ("Grand Total", "105.00")])
    merged = pymupdf.open()
    for f in (a, b):
        with pymupdf.open(f) as d:
            merged.insert_pdf(d)
    merged.save(tmp_path / "both.pdf")
    doc = services.documents.add_files([tmp_path / "both.pdf"]).added[0]
    out = ExtractionPipeline(services).run(doc.id)
    assert out.ok and "2 invoices" in out.message
    invs = sorted(services.invoices.list_invoices(), key=lambda i: i.page_from)
    assert [(i.invoice_no, i.page_from) for i in invs] == [("A-1", 1), ("B-2", 2)]
    # delete the second invoice only: the file is queued again and only page 2 is re-extracted
    services.invoices.delete(invs[1].id)
    assert services.documents.get(doc.id).status == "queued"
    again = ExtractionPipeline(services).run(doc.id)
    assert again.ok
    invs2 = sorted(services.invoices.list_invoices(), key=lambda i: i.page_from)
    assert [(i.invoice_no, i.page_from) for i in invs2] == [("A-1", 1), ("B-2", 2)]
    assert invs2[0].id == invs[0].id                 # the kept invoice is untouched
    assert not ExtractionPipeline(services).run(doc.id).ok   # nothing left to extract


def test_day_book_request_carries_typed_dates(tally_services, tmp_path):
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path)
    _approve_all(s, iid)
    received.clear()
    s.imports.check_duplicate(iid)
    day_book = [r for r in received if "Day Book" in r][0]
    assert '<SVCURRENTDATE TYPE="Date">20251015</SVCURRENTDATE>' in day_book
    assert '<SVFROMDATE TYPE="Date">20251015</SVFROMDATE>' in day_book


def test_recheck_marks_unverified_import_success(tally_services, tmp_path):
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path)
    _approve_all(s, iid)
    rec = s.imports.import_invoice(iid)
    with s.db.session() as ss:                       # simulate the earlier 'not found again' result
        from ipt.db.models import Invoice, TallyImport
        r = ss.get(TallyImport, rec.id)
        r.status, r.verified = "unverified", False
        ss.get(Invoice, iid).status = "approved"
    again = s.imports.recheck(rec.id)
    assert again.status == "success" and s.invoices.get(iid).status == "imported"


def test_recheck_after_voucher_deleted_in_tally_frees_invoice(tally_services, tmp_path):
    from tests import test_tally as me
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path)
    _approve_all(s, iid)
    rec = s.imports.import_invoice(iid)
    assert rec.status == "success" and s.invoices.get(iid).status == "imported"
    me.imported_vouchers.clear()                     # the user deleted the voucher in Tally
    again = s.imports.recheck(rec.id)
    assert again.status == "removed" and s.invoices.get(iid).status == "approved"
    rec2 = s.imports.import_invoice(iid)             # corrected voucher can now be imported again
    assert rec2.status == "success"


def test_reimport_after_delete_in_tally_without_manual_recheck(tally_services, tmp_path):
    from tests import test_tally as me
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path)
    _approve_all(s, iid)
    assert s.imports.import_invoice(iid).status == "success"
    assert s.imports.release_if_deleted(iid) is False          # voucher still in Tally: stays imported
    assert s.invoices.get(iid).status == "imported"
    import pytest
    from ipt.services.tally.service import TallyError
    with pytest.raises(TallyError, match="still in Tally"):
        s.imports.import_invoice(iid)
    me.imported_vouchers.clear()                               # the user deleted it in Tally
    assert s.imports.release_if_deleted(iid) is True
    assert s.invoices.get(iid).status == "approved"
    assert s.imports.import_invoice(iid).status == "success"


def test_supplier_booked_to_a_ledger_needs_no_items(tally_services, tmp_path):
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path)
    _approve_all(s, iid)
    line = next(ln for ln in s.mapping.lines_for(iid) if ln.entity == "debit_ledger")
    assert line.candidates, "expense / purchase ledgers are offered"
    s.mapping.approve("debit_ledger", line.source_key, line.candidates[0].name)
    assert s.mapping.effective_mode(iid, "inventory") == "accounting"
    built = s.vouchers.build(iid, "auto")
    assert built.ok, built.blockers
    assert "ALLINVENTORYENTRIES" not in built.xml and "Accounting Invoice" in built.xml
    assert built.lines[0].ledger == line.candidates[0].name
    assert amounts_sum_zero(built.xml)


def test_import_many_imports_each_and_skips_bills_already_in_the_register(tally_services, tmp_path):
    from ipt.db.models import Invoice, PurchaseRegisterRecord, PurchaseRegisterUpload
    s = tally_services
    s.tally.sync_masters()
    a = _approved_invoice(s, tmp_path)
    _approve_all(s, a)
    res = s.imports.import_many([a], "auto")
    assert res[0]["status"] == "success" and s.invoices.get(a).status == "imported"
    # a second bill that the fetched purchase register already holds (entered by hand in Tally) is skipped
    b = _approved_invoice(s, tmp_path, inv_no="SGT/25-26/0148")
    with s.db.session() as ses:
        inv = ses.get(Invoice, b)
        up = PurchaseRegisterUpload(company_id=inv.company_id, fy_id=inv.fy_id, source="tally", is_current=True,
                                    period_from=inv.invoice_date, period_to=inv.invoice_date, rows_ok=1)
        ses.add(up)
        ses.flush()
        ses.add(PurchaseRegisterRecord(upload_id=up.id, company_id=inv.company_id, fy_id=inv.fy_id, row_no=1,
                                       voucher_no="J-77", voucher_type="Journal", voucher_date=inv.invoice_date,
                                       doc_type="INV", supplier_gstin=inv.supplier_gstin,
                                       supplier_invoice_no=inv.invoice_no, invoice_no_normalized="X",
                                       supplier_invoice_date=inv.invoice_date, invoice_total=inv.invoice_total))
    dups = s.imports.register_duplicates(b)
    assert dups and dups[0]["voucher_number"] == "J-77"            # same GSTIN, date and total
    res = s.imports.import_many([b], "auto")
    assert res[0]["status"] == "skipped" and "J-77" in res[0]["message"]
    assert s.invoices.get(b).status == "approved"


def test_create_supplier_ledger_and_stock_item_in_tally(tally_services):
    from ipt.services.tally.client import TallyError
    s = tally_services
    s.tally.sync_masters()
    new = gst("08AAUCA3699Q1Z")
    assert s.tally.create_master("ledger", "Aglow Chemicals", gstin=new) == "Aglow Chemicals"
    led = {m.name: m for m in s.tally.masters("ledger")}
    assert led["Aglow Chemicals"].gstin == new and led["Aglow Chemicals"].primary_group == "Sundry Creditors"
    body = next(r for r in received if "Aglow Chemicals" in r and "Import Data" in r)
    assert "<STATE>Rajasthan</STATE>" in body and "<PARENT>Sundry Creditors</PARENT>" in body
    with pytest.raises(TallyError, match="already has"):
        s.tally.create_master("ledger", "aglow chemicals", gstin=new)
    with pytest.raises(TallyError, match="Unit 'MT' is not in Tally"):
        s.tally.create_master("stock_item", "Lime Stone Chips", unit="MT", hsn="25210090", gst_rate=Decimal("5"))
    assert s.tally.create_master("stock_item", "Lime Stone Chips", unit="bag", hsn="25210090",
                                 gst_rate=Decimal("5")) == "Lime Stone Chips"
    body = [r for r in received if "Lime Stone Chips" in r and "Import Data" in r][-1]
    assert "<BASEUNITS>BAG</BASEUNITS>" in body and "<GSTRATE>2.5</GSTRATE>" in body and "<HSNCODE>25210090" in body


def test_reopen_approved_invoice_but_not_imported_one(tally_services, tmp_path):
    from ipt.services.invoice_service import InvoiceError
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path)
    with pytest.raises(InvoiceError):
        s.invoices.reopen(iid, "")
    s.invoices.reopen(iid, "quantity missing")
    assert s.invoices.get(iid).status == "needs_review"
    s.invoices.update(iid, {"po_no": "PO-1"})                   # editable again
    s.invoices.approve(iid)
    _approve_all(s, iid)
    s.imports.import_invoice(iid)
    with pytest.raises(InvoiceError, match="in Tally"):
        s.invoices.reopen(iid, "too late")


def test_supplier_credit_note_becomes_debit_note_voucher_against_the_imported_bill(tally_services, tmp_path):
    import xml.etree.ElementTree as ET
    s = tally_services
    s.tally.sync_masters()
    bill = _approved_invoice(s, tmp_path)
    _approve_all(s, bill)
    assert s.imports.import_invoice(bill, "auto").status == "success"
    # a credit note (full return: 3,500 + 315 + 315) against that bill, entered in IPT
    cn = _approved_invoice(s, tmp_path, inv_no="CN-7")
    s.invoices.reopen(cn, "make it a credit note")
    s.invoices.update(cn, {"doc_type": "credit_note", "original_invoice_ref": "SGT/25-26/0147"})
    s.invoices.approve(cn)
    _approve_all(s, cn)
    v = s.vouchers.build(cn, "auto")
    assert v.ok, v.blockers
    root = ET.fromstring(v.xml)
    vch = root.find(".//VOUCHER")
    assert vch.findtext("VOUCHERTYPENAME") == "Debit Note" and vch.findtext("VCHENTRYMODE") == "Accounting Invoice"
    les = vch.findall("LEDGERENTRIES.LIST")
    amounts = {le.findtext("LEDGERNAME"): Decimal(le.findtext("AMOUNT")) for le in les}
    assert amounts["Shree Ganesh Traders"] == Decimal("-4130.00")          # party debited
    assert amounts["INPUT CGST"] == Decimal("315.00") and amounts["INPUT SGST"] == Decimal("315.00")  # credited
    assert sum(amounts.values()) == 0 and amounts_sum_zero(v.xml)
    bill_alloc = les[0].find("BILLALLOCATIONS.LIST")
    assert (bill_alloc.findtext("NAME"), bill_alloc.findtext("BILLTYPE")) == ("SGT/25-26/0147", "Agst Ref")
    assert "credit note CN-7" in vch.findtext("NARRATION")
    assert s.imports.import_invoice(cn, "auto").status == "success"


def test_supplier_debit_note_without_known_original_is_a_new_ref_purchase(tally_services, tmp_path):
    import xml.etree.ElementTree as ET
    s = tally_services
    s.tally.sync_masters()
    dn = _approved_invoice(s, tmp_path, inv_no="DN-3")
    s.invoices.reopen(dn, "debit note")
    s.invoices.update(dn, {"doc_type": "debit_note", "original_invoice_ref": "NOT-IN-TALLY"})
    s.invoices.approve(dn)
    _approve_all(s, dn)
    v = s.vouchers.build(dn, "inventory")                      # notes always go without items
    assert v.ok, v.blockers
    vch = ET.fromstring(v.xml).find(".//VOUCHER")
    assert vch.findtext("VOUCHERTYPENAME") == "Purchase" and vch.find(".//ALLINVENTORYENTRIES.LIST") is None
    party = vch.findall("LEDGERENTRIES.LIST")[0]
    assert Decimal(party.findtext("AMOUNT")) > 0                                  # party credited
    assert party.find("BILLALLOCATIONS.LIST").findtext("BILLTYPE") == "New Ref"


def test_check_tally_for_many_ticked_imported_invoices(tally_services, tmp_path):
    from tests import test_tally as me
    s = tally_services
    s.tally.sync_masters()
    ids = [_approved_invoice(s, tmp_path, inv_no=f"SGT/25-26/0{n}") for n in (147, 148, 149)]
    for iid in ids:
        _approve_all(s, iid)
        assert s.imports.import_invoice(iid).status == "success"
    keep = [v for v in me.imported_vouchers if "0149" in str(v)]
    me.imported_vouchers[:] = keep                       # the user deleted two of the three in Tally
    res = s.imports.release_many(ids)
    assert [r["status"] for r in res].count("freed") == 2
    assert [s.invoices.get(i).status for i in ids] == ["approved", "approved", "imported"]


def test_other_document_type_is_booked_as_a_tax_invoice(tally_services, tmp_path):
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path)
    _approve_all(s, iid)
    with s.db.session() as ss:
        ss.get(Invoice, iid).doc_type = "other"
    v = s.vouchers.build(iid, "accounting")
    assert not any("document type" in b for b in v.blockers)


def test_fix_gst_details_in_tally(tally_services):
    s = tally_services
    plan = s.tally.gst_fix_preview()
    assert [x["name"] for x in plan["ledgers"]] == ["Shree Ganesh Traders"]          # no state in Tally
    assert {u["name"]: u["suggested"] for u in plan["units"]} == {"BAG": "BAG-BAGS", "MT": "MTS-METRIC TON"}
    assert plan["units_unknown"] == ["XYZ"]
    assert not any('ACTION="Alter"' in r for r in received)                         # preview never writes
    res = s.tally.gst_fix_apply()
    assert res["ledgers_fixed"] == ["Shree Ganesh Traders"] and sorted(res["units_fixed"]) == ["BAG", "MT"]
    assert ALTERED["ledger_state"]["Shree Ganesh Traders"] == "Rajasthan"
    assert res["not_fixed"] == [] and res["errors"] == []
    assert s.tally.gst_fix_preview()["ledgers"] == []                              # read back: complete


def test_new_ledger_and_voucher_carry_gst_state():
    from ipt.services.tally.create_masters import ledger_xml
    x = ledger_xml("Co", "Krishna Lime", "08AGTPK9837A2ZY")
    assert "<LEDMAILINGDETAILS.LIST>" in x and "<STATE>Rajasthan</STATE><COUNTRY>India</COUNTRY>" in x
    assert "<GSTIN>08AGTPK9837A2ZY</GSTIN>" in x


def test_item_without_stock_item_is_not_ready(tally_services, tmp_path):
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path)
    _approve_all(s, iid)
    from ipt.db.models import InvoiceItem
    with s.db.session() as ss:                          # the item lost its description: no mapping applies
        for it in ss.query(InvoiceItem).filter_by(invoice_id=iid):
            it.description = None
    v = s.vouchers.build(iid, "inventory")
    assert not v.ok and any("no Tally stock item" in b for b in v.blockers)


def test_fix_keeps_the_ledgers_own_address_and_settings():
    from ipt.services.tally.create_masters import ledger_gst_alter_xml
    m = ['<LEDMAILINGDETAILS.LIST><ADDRESS.LIST TYPE="String"><ADDRESS>Plot 5, RIICO</ADDRESS></ADDRESS.LIST>'
         '<APPLICABLEFROM>20170701</APPLICABLEFROM><PINCODE>342001</PINCODE><STATE></STATE></LEDMAILINGDETAILS.LIST>']
    g = ['<LEDGSTREGDETAILS.LIST><APPLICABLEFROM>20170701</APPLICABLEFROM><GSTIN>08AGTPK9837A2ZY</GSTIN>'
         '<ISTRANSPORTER>Yes</ISTRANSPORTER><STATE>Gujarat</STATE></LEDGSTREGDETAILS.LIST>']
    x = ledger_gst_alter_xml("Co", "X", "08AGTPK9837A2ZY", m, g)
    assert "<ADDRESS>Plot 5, RIICO</ADDRESS>" in x and "<PINCODE>342001</PINCODE>" in x
    assert "<ISTRANSPORTER>Yes</ISTRANSPORTER>" in x
    assert "<STATE>Rajasthan</STATE>" in x and "<COUNTRY>India</COUNTRY>" in x      # empty state filled
    assert "<STATE>Gujarat</STATE>" in x                                             # a value entered is kept


def test_invoice_list_shows_what_tally_import_still_needs(tally_services, tmp_path):
    s = tally_services
    s.tally.sync_masters()
    iid = _approved_invoice(s, tmp_path)
    assert s.vouchers.readiness(iid, "approved").startswith("Map:")
    _approve_all(s, iid)
    assert s.vouchers.readiness(iid, "approved") == "Ready"
    assert s.vouchers.readiness(iid, "imported") == "In Tally"
