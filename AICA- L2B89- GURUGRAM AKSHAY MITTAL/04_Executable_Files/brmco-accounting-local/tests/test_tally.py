"""Tally XML generation, response parsing and connection handling."""
import socket
import xml.etree.ElementTree as ET
from decimal import Decimal

import pytest

from app.accounting.models import VoucherKind
from app.accounting.services import VoucherAssembler
from app.excel.reader import read_workbook
from app.excel.samples import SAMPLE_ROWS
from app.excel.template_spec import spec_for
from app.excel.validator import parse_rows
from app.tally.client import DemoTallyClient, TallyClient, TallyConnectionError, parse_collection
from app.tally.response_parser import parse_import_response
from app.tally.xml_generator import TallyXmlGenerator
from tests.conftest import workbook


def sample_vouchers(kind, config, masters):
    spec = spec_for(kind)
    parsed, _ = parse_rows(spec, read_workbook(workbook(kind), spec, "x.xlsx").rows)
    vouchers, _ = VoucherAssembler(spec, config, masters).assemble(parsed)
    return vouchers


def entries(vch):
    out = {}
    for tag in ("ALLLEDGERENTRIES.LIST", "LEDGERENTRIES.LIST"):
        for e in vch.findall(tag):
            out[e.findtext("LEDGERNAME")] = (e.findtext("ISDEEMEDPOSITIVE"), Decimal(e.findtext("AMOUNT")))
    return out


def test_sales_xml(config, masters):
    config = config.model_copy(update={"tally_company_name": "Test Co"})
    xml = TallyXmlGenerator(config).import_envelope(sample_vouchers(VoucherKind.SALES, config, masters))
    root = ET.fromstring(xml)
    assert root.findtext(".//SVCURRENTCOMPANY") == "Test Co"
    vchs = root.findall(".//VOUCHER")
    assert len(vchs) == 2
    first = vchs[0]
    assert first.get("VCHTYPE") == "Sales"
    assert first.findtext("DATE") == "20260925"
    assert first.findtext("VOUCHERNUMBER") == "INV-1025"
    e = entries(first)
    assert e["ABC Traders"] == ("Yes", Decimal("-118000.00"))      # debit: negative
    assert e["Sales - Services"] == ("No", Decimal("100000.00"))   # credit: positive
    assert e["Output CGST"] == ("No", Decimal("9000.00"))
    assert first.find(".//BILLALLOCATIONS.LIST/BILLTYPE").text == "New Ref"
    # every voucher balances in Tally's signed convention
    for vch in vchs:
        total = sum(Decimal(a.text) for tag in ("ALLLEDGERENTRIES.LIST", "LEDGERENTRIES.LIST", "ACCOUNTINGALLOCATIONS.LIST")
                    for a in vch.iter(tag) for a in [a.find("AMOUNT")])
        assert total == 0
    inv = vchs[1]
    assert inv.findtext("PERSISTEDVIEW") == "Invoice Voucher View"
    item = inv.find("ALLINVENTORYENTRIES.LIST")
    assert item.findtext("STOCKITEMNAME") == "Steel Rod 12mm"
    assert item.findtext("ACTUALQTY").strip() == "100 Kg"


@pytest.mark.parametrize("kind", [VoucherKind.PURCHASE, VoucherKind.JOURNAL, VoucherKind.RECEIPT, VoucherKind.PAYMENT])
def test_other_voucher_xml_balances(kind, config, masters):
    vouchers = sample_vouchers(kind, config, masters)
    root = ET.fromstring(TallyXmlGenerator(config).import_envelope(vouchers))
    for vch in root.iter("VOUCHER"):
        assert vch.get("VCHTYPE") == config.voucher_type_for(kind)
        total = sum(Decimal(e.findtext("AMOUNT")) for e in vch.findall("ALLLEDGERENTRIES.LIST"))
        assert total == 0


def test_receipt_bank_allocation(config, masters):
    [v, _] = sample_vouchers(VoucherKind.RECEIPT, config, masters)
    vch = TallyXmlGenerator(config).voucher_element(v)
    bank = vch.find(".//BANKALLOCATIONS.LIST")
    assert bank.findtext("INSTRUMENTNUMBER") == "HDFCN52026092712345"
    assert entries(vch)["HDFC Bank"] == ("Yes", Decimal("-118000.00"))


def test_journal_cost_centre(config, masters):
    v = sample_vouchers(VoucherKind.JOURNAL, config, masters)[0]
    vch = TallyXmlGenerator(config).voucher_element(v)
    assert vch.findtext(".//COSTCENTREALLOCATIONS.LIST/NAME") == "Head Office"


def test_xml_escapes_special_characters(config, masters):
    v = sample_vouchers(VoucherKind.PAYMENT, config, masters)[0]
    v.narration = 'A & B <test> "quoted"'
    ET.fromstring(TallyXmlGenerator(config).import_envelope([v]))  # must stay well-formed


# ---------------------------------------------------------------- response parsing
def test_parse_success():
    r = parse_import_response("<RESPONSE><CREATED>1</CREATED><ALTERED>0</ALTERED><LASTVCHID>55</LASTVCHID>"
                              "<ERRORS>0</ERRORS><EXCEPTIONS>0</EXCEPTIONS></RESPONSE>", expected=1)
    assert r.status == "SUCCESS" and r.created == 1 and r.last_voucher_id == "55"
    assert r.message == "1 voucher created successfully."


def test_parse_failure_with_line_error():
    r = parse_import_response("<RESPONSE><LINEERROR>Ledger 'XYZ' does not exist!</LINEERROR><CREATED>0</CREATED>"
                              "<ERRORS>1</ERRORS></RESPONSE>", expected=1)
    assert r.status == "FAILED"
    assert "XYZ" in r.message


def test_parse_envelope_wrapped_and_control_chars():
    text = ("<ENVELOPE><HEADER><VERSION>1</VERSION><STATUS>1</STATUS></HEADER><BODY><DATA><IMPORTRESULT>"
            "<CREATED>2</CREATED><ALTERED>0</ALTERED><ERRORS>0</ERRORS><EXCEPTIONS>0</EXCEPTIONS>&#4;"
            "</IMPORTRESULT></DATA></BODY></ENVELOPE>")
    assert parse_import_response(text, expected=2).status == "SUCCESS"


def test_http_ok_but_nothing_created_is_not_success():
    assert parse_import_response("<RESPONSE><CREATED>0</CREATED><ERRORS>0</ERRORS></RESPONSE>", 1).status == "FAILED"
    assert parse_import_response("", 1).status == "FAILED"
    assert parse_import_response("<RESPONSE>Unknown Request, cannot be processed</RESPONSE>", 1).status == "FAILED"
    assert parse_import_response("<RESPONSE><CREATED>0</CREATED><IGNORED>1</IGNORED></RESPONSE>", 1).status == "FAILED"


def test_parse_master_collection():
    text = ('<ENVELOPE><BODY><DATA><COLLECTION><LEDGER NAME="Cash" RESERVEDNAME=""><PARENT>Cash-in-Hand</PARENT>'
            '</LEDGER><LEDGER><NAME.LIST><NAME>ABC &amp; Co</NAME></NAME.LIST><PARENT>Sundry Debtors</PARENT></LEDGER>'
            "</COLLECTION></DATA></BODY></ENVELOPE>")
    items = parse_collection(text, "Ledger")
    assert [i["name"] for i in items] == ["Cash", "ABC & Co"]
    assert items[1]["parent"] == "Sundry Debtors"


# ---------------------------------------------------------------- connection
def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_connection_failure_is_reported_not_raised():
    client = TallyClient(f"http://127.0.0.1:{_free_port()}", timeout=2)
    status = client.status()
    assert status.connected is False
    assert "Cannot connect to Tally" in status.message
    with pytest.raises(TallyConnectionError):
        client.post(b"<ENVELOPE/>")


def test_demo_client_rejects_unknown_ledger(config, masters):
    v = sample_vouchers(VoucherKind.PAYMENT, config, masters)[0]
    v.postings[0].ledger = "Ghost Ledger"
    raw = DemoTallyClient().post(TallyXmlGenerator(config).import_envelope([v]))
    r = parse_import_response(raw, 1)
    assert r.status == "FAILED" and "Ghost Ledger" in r.message
