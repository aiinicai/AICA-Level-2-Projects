"""Offline test of tally_extract parsing, using SYNTHETIC XML written in Tally's export shape.
NOTE: the XML below follows Tally Prime's documented format but was not captured from a live Tally;
run `python tally_extract.py --dump-xml ...` against your own Tally to confirm on your version."""
import json, tempfile
from pathlib import Path
import tally_extract as T

LEDGERS = """<ENVELOPE><BODY><DATA><COLLECTION>
<LEDGER NAME="Bank A - Current A/c"><PARENT>Bank Accounts</PARENT><OPENINGBALANCE>-100000.00</OPENINGBALANCE></LEDGER>
<LEDGER NAME="Bank B - Savings A/c"><PARENT>Bank Accounts</PARENT><OPENINGBALANCE>-50000.00</OPENINGBALANCE></LEDGER>
</COLLECTION></DATA></BODY></ENVELOPE>"""


def v(date, vtype, no, entries, narr="", cancelled="No"):
    e = "".join(f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{n}</LEDGERNAME><AMOUNT>{a}</AMOUNT>{x}</ALLLEDGERENTRIES.LIST>" for n, a, x in entries)
    return (f"<VOUCHER><DATE>{date}</DATE><VOUCHERTYPENAME>{vtype}</VOUCHERTYPENAME><VOUCHERNUMBER>{no}</VOUCHERNUMBER>"
            f"<NARRATION>{narr}</NARRATION><ISCANCELLED>{cancelled}</ISCANCELLED>{e}</VOUCHER>")


chq = "<BANKALLOCATIONS.LIST><INSTRUMENTNUMBER>000123</INSTRUMENTNUMBER></BANKALLOCATIONS.LIST>"
DAYBOOK = "<ENVELOPE><BODY><DATA><TALLYMESSAGE>" + "".join([
    v("20260815", "Receipt", "1", [("Bank A - Current A/c", "-20000.00", ""), ("Sharma Retail", "20000.00", "")]),   # before period
    v("20261005", "Receipt", "2", [("Bank A - Current A/c", "-5000.00", ""), ("Iyer Traders", "5000.00", "")], "INV 55"),
    v("20261010", "Payment", "3", [("Bank A - Current A/c", "1200.50", chq), ("Fortune Chemicals", "-1200.50", "")]),
    v("20261012", "Contra", "4", [("Bank B - Savings A/c", "-3000.00", ""), ("Bank A - Current A/c", "3000.00", "")]),
    v("20261015", "Payment", "5", [("Bank B - Savings A/c", "999.00", ""), ("Cash", "-999.00", "")], cancelled="Yes"),
    v("20261101", "Payment", "6", [("Bank A - Current A/c", "7.00", ""), ("Cash", "-7.00", "")]),                 # after period
]) + "</TALLYMESSAGE></DATA></BODY></ENVELOPE>"


def test_parse_and_roll_forward():
    opening = T.parse_bank_ledgers(LEDGERS)
    assert opening == {"Bank A - Current A/c": 100000.0, "Bank B - Savings A/c": 50000.0}
    rows = T.parse_vouchers(DAYBOOK, set(opening))
    banks = {b["name"]: b for b in T.build_banks(opening, rows, T.dmy("01-10-2026"), T.dmy("31-10-2026"))}
    a, b = banks["Bank A - Current A/c"], banks["Bank B - Savings A/c"]
    assert a["opening_balance"] == 120000.0                       # 100000 + 20000 (Aug receipt)
    assert [r["Receipt"] or r["Payment"] for r in a["rows"]] == ["5000.00", "1200.50", "3000.00"]
    assert a["rows"][1]["Voucher_Ref"] == "000123"
    assert a["closing_balance"] == 120000 + 5000 - 1200.50 - 3000
    assert b["opening_balance"] == 50000.0 and len(b["rows"]) == 1   # contra receipt only; cancelled voucher skipped
    assert b["closing_balance"] == 53000.0


def test_write_outputs():
    opening = T.parse_bank_ledgers(LEDGERS)
    banks = T.build_banks(opening, T.parse_vouchers(DAYBOOK, set(opening)), T.dmy("01-10-2026"), T.dmy("31-10-2026"))
    out = Path(tempfile.mkdtemp())
    T.write_outputs(out, "Test Co", T.dmy("01-10-2026"), T.dmy("31-10-2026"), banks)
    j = json.loads((out / "tally_bank_books.json").read_text())
    assert [x["name"] for x in j["banks"]] == ["Bank A - Current A/c", "Bank B - Savings A/c"]
    assert (out / "bank_books_bank_a_current_a_c.csv").exists() and (out / "banks" / "bank_b_savings_a_c").is_dir()


if __name__ == "__main__":
    test_parse_and_roll_forward(); test_write_outputs(); print("tally_extract tests pass")
