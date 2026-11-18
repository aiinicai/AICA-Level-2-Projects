"""Phase 1 tests: the Tally reader copes with the odd things real Tally sends."""
import pytest

from app.tally.values import canonical_paise, parse_credit_period, parse_tally_date, scale_decimal
from app.tally.xmlstream import TallyResponseError, stream_records, txt


def run(data: bytes, chunk=7):
    chunks = [data[i:i + chunk] for i in range(0, len(data), chunk)]  # tiny chunks: splits tags and &#refs
    return [(r.tag, (r.get("NAME") or txt(r, "NAME"))) for r in stream_records(chunks)]


XML = ('<ENVELOPE><HEADER><VERSION>1</VERSION></HEADER><BODY><DATA><COLLECTION>'
       '<LEDGER NAME="Cash"><NAME>Cash</NAME><PARENT>Cash-in-Hand</PARENT></LEDGER>'
       '<LEDGER NAME="Sales"><NARRATION>bad&#4;char</NARRATION></LEDGER>'
       '</COLLECTION></DATA></BODY></ENVELOPE>')


def test_basic_and_split_chunks():
    assert run(XML.encode()) == [("LEDGER", "Cash"), ("LEDGER", "Sales")]


def test_utf16_with_bom():
    assert run(b"\xff\xfe" + XML.encode("utf-16-le")) == [("LEDGER", "Cash"), ("LEDGER", "Sales")]


def test_illegal_characters_are_removed():
    raw = XML.replace("bad&#4;char", "bad\x04char").encode()
    assert len(run(raw)) == 2


def test_cmpinfo_counts_are_not_records():
    x = b"<ENVELOPE><CMPINFO><COMPANY>0</COMPANY><LEDGER>0</LEDGER></CMPINFO><COLLECTION><LEDGER NAME='A'/></COLLECTION></ENVELOPE>"
    assert run(x) == [("LEDGER", "A")]


def test_nested_record_tags_are_not_split_out():
    x = b"<E><VOUCHER><UNIT>Nos</UNIT><LEDGER>inner</LEDGER></VOUCHER></E>"
    assert [t for t, _ in run(x)] == ["VOUCHER"]


def test_error_reply_raises():
    with pytest.raises(TallyResponseError, match="Could not find Company"):
        run(b"<ENVELOPE><BODY><DATA><LINEERROR>Could not find Company 'X'</LINEERROR></DATA></BODY></ENVELOPE>")
    with pytest.raises(TallyResponseError):
        run(b"<RESPONSE>Unknown Request, cannot be processed</RESPONSE>")


def test_empty_and_malformed():
    with pytest.raises(TallyResponseError):
        run(b"")
    with pytest.raises(TallyResponseError):
        run(b"<ENVELOPE><LEDGER></ENVELOPE>")


def test_amounts_dates():
    assert canonical_paise("-11,800.00") == 1180000   # Tally debit (negative) -> debit-positive
    assert canonical_paise("500.50 Cr") == -50050
    assert scale_decimal("0.005", 2) == 1              # half rounds away from zero
    assert parse_tally_date("20240415") == "2024-04-15"
    assert parse_tally_date("31-Feb-2024") is None
    assert parse_credit_period("30 Days") == {"days": 30}


def test_undeclared_udf_prefix_from_real_tally():
    """Real TallyPrime sends <UDF:_UDF_123.LIST> without declaring the prefix; it must read, even split across chunks."""
    x = (b"<ENVELOPE><BODY><DATA><COLLECTION><VOUCHER NAME='V1'><DATE>20240401</DATE>"
         b"<UDF:_UDF_553650057.LIST DESC='x'><UDF:_UDF_553650057 DESC='y'>5</UDF:_UDF_553650057></UDF:_UDF_553650057.LIST>"
         b"<NARRATION>Dr: a UDF: b</NARRATION></VOUCHER></COLLECTION></DATA></BODY></ENVELOPE>")
    for chunk in (1, 2, 3, 5, 7, 11, 64, 10000):
        assert run(x, chunk) == [("VOUCHER", "V1")], chunk
    for size in (1, 3, 4, 10000):
        kept = [(r.tag, txt(r, "NARRATION")) for r in stream_records([x[i:i + size] for i in range(0, len(x), size)])]
        assert kept == [("VOUCHER", "Dr: a UDF: b")], size  # ordinary text that contains "UDF:" is never changed
