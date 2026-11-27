from pathlib import Path

import pytest

from advtax import tb_import as tb

SAMPLES = Path(__file__).resolve().parent.parent / "demo_clients"
TALLY = "D01 Marudhar Hardware Stores/trial_balance_tally.xlsx"

EXPECTED = {
    "recurring_income": 9840000 + 2260000 + 39000,
    "one_off_income": 120000,
    "recurring_expense": 7610000 + 1720000 + 148000 + 462000 + 245000 + 58000 + 71000 + 96000 + 83000,
    "one_off_expense": 0,
    "opening_stock": 1450000,
}


def load(name):
    data = (SAMPLES / name).read_bytes()
    raw = tb.read_raw(data, name)
    table = tb.build_table(raw, tb.detect_header_row(raw))
    return tb.classify(tb.normalise(table, tb.guess_columns(table)))


@pytest.mark.parametrize("name,factor", [("D04 S Verma HUF/trial_balance_busy.csv", 0.5),
                                         ("D05 Demo Traders Firm/trial_balance_zoho.xlsx", 2)])
def test_files_with_group_column_classify_fully(name, factor):
    # these two clients carry the same books at half and at double the size
    out = load(name)
    totals = tb.summarise(out)
    for key, value in EXPECTED.items():
        assert totals[key] == pytest.approx(value * factor), key
    assert totals["needs_review"] == 0
    assert totals["difference"] == pytest.approx(0)


def test_tally_export_without_groups_is_read_and_flagged():
    data = (SAMPLES / TALLY).read_bytes()
    raw = tb.read_raw(data, TALLY)
    hdr = tb.detect_header_row(raw)
    table = tb.build_table(raw, hdr)
    mapping = tb.guess_columns(table)
    out = tb.classify(tb.normalise(table, mapping))
    assert "Grand Total" not in out["ledger"].tolist()
    assert len(out) == 24
    assert out["net"].sum() == pytest.approx(0)
    totals = tb.summarise(out)
    # no group column: classified from names, so items are flagged for the user to check
    assert totals["needs_review"] > 0
    for key, value in EXPECTED.items():
        assert totals[key] == pytest.approx(value), key


def test_template_reads():
    out = load("templates/trial_balance_template.xlsx")
    assert set(out["type"]) <= set(tb.TYPES) and len(out) == 6


@pytest.mark.parametrize("raw,expected", [("1,23,456.00 Dr", 123456.0), ("1,23,456.00 Cr", -123456.0),
                                          ("(500)", -500.0), ("", 0.0), ("-", 0.0), (None, 0.0),
                                          ("2500", 2500.0), ("₹ 1,000.50", 1000.5)])
def test_parse_amount(raw, expected):
    assert tb.parse_amount(raw) == expected


@pytest.mark.parametrize("ledger,net,expected", [
    ("Bank Charges", 5000, "Expense"), ("Vehicle Running Expenses", 9000, "Expense"),
    ("Insurance Claim Received", -120000, "Income"), ("Income Tax Paid", 50000, "Ignore"),
    ("TDS Receivable", 20000, "Ignore"), ("HDFC Bank", 100000, "Ignore"), ("Interest Received", -4000, "Income"),
    ("Capital Account", -900000, "Ignore"), ("Opening Stock", 300000, "Opening Stock")])
def test_name_based_classification(ledger, net, expected):
    assert tb.classify_one(ledger, "", net)[0] == expected
