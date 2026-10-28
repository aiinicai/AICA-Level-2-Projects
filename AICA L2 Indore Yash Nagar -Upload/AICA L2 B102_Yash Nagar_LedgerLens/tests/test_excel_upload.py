import io
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fsbuilder import pipeline as P  # noqa: E402
from fsbuilder.mapping import map_ledgers  # noqa: E402
from fsbuilder.model import build_model  # noqa: E402
from fsbuilder.tb import normalise  # noqa: E402

SAMPLE = pd.read_csv(P.SAMPLE_TB)


def book(sheets: dict) -> io.BytesIO:
    """Build an in-memory workbook: {sheet name: list of rows}."""
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def rows_of(df, header=None):
    return [header or list(df.columns)] + [[None if pd.isna(v) else v for v in r] for r in df.itertuples(index=False)]


def read(buf, name="tb.xlsx", **kw):
    return P.read_trial_balance(buf, name, company="X", start=date(2024, 4, 1), end=date(2025, 3, 31), **kw)


def closings(tb):
    return normalise(tb).ledgers["closing"].values


REFERENCE = closings(P.load_sample())


def test_the_downloadable_template_loads_back_to_the_same_trial_balance():
    tb = read(io.BytesIO(P.sample_xlsx_bytes()))
    assert (closings(tb) == REFERENCE).all() and len(tb.ledgers) == 68
    m = build_model(normalise(tb), map_ledgers(normalise(tb)))
    assert m.profit == 2_489_416 and m.figures["cur"]["ppe"] == 2_446_741
    assert any(n.movement for n in m.notes)                    # period debit/credit survived, so the PPE table is built


def test_title_rows_above_the_header_and_a_totals_row_are_fine():
    rows = [["Acme Ltd"], ["Trial balance as on 31/03/2025"], [], *rows_of(SAMPLE.iloc[:, :9] if False else SAMPLE)]
    rows.append(["Total", None, None, 0, None, 0, 0, 0, None])
    rows.append(["Grand Total", None, None, 0, None, 0, 0, 0, None])
    assert (closings(read(book({"TB": rows}))) == REFERENCE).all()


def test_first_sheet_with_a_trial_balance_is_used_and_others_are_ignored():
    sheets = {"Summary": [["Notes about this file"], ["nothing useful here"]],
              "Cover": [["Client", "Acme"]],
              "Trial balance": rows_of(SAMPLE), "Old": rows_of(SAMPLE.head(3))}
    assert len(read(book(sheets)).ledgers) == 68


def test_everyday_header_names_are_understood():
    header = ["Ledger Name", "Under", "primary_group", "Opening Balance", "Opening Dr/Cr", "period_debit", "period_credit",
              "Closing Balance", "Closing Dr/Cr"]
    assert (closings(read(book({"T": rows_of(SAMPLE, header)}))) == REFERENCE).all()


def test_amounts_typed_as_text_and_spaced_dr_cr_are_accepted():
    df = SAMPLE.copy()
    df["closing_amount"] = [f"{v:,.2f}" for v in df["closing_amount"]]
    df["opening_amount"] = [f"Rs {v:,.0f}" for v in df["opening_amount"]]
    df["closing_dr_cr"] = df["closing_dr_cr"].map(lambda v: f" {v} " if isinstance(v, str) else v)
    assert abs(closings(read(book({"T": rows_of(df)}))) - REFERENCE).max() < 0.01


def test_plain_debit_credit_columns_are_not_mistaken_for_period_movement():
    header = list(SAMPLE.columns)
    header[header.index("period_debit")], header[header.index("period_credit")] = "Debit", "Credit"
    tb = read(book({"T": rows_of(SAMPLE, header)}))
    assert tb.ledgers["period_dr"].isna().all()                # left alone, since they probably mean closing balances


def test_groups_can_be_an_excel_file_too():
    df = SAMPLE.copy()
    df["group"] = df["group"].replace("Sundry Debtors", "Export Debtors")
    g = book({"Groups": [["name", "parent", "nature"], ["Export Debtors", "Sundry Debtors", "Assets"]]})
    tb = normalise(read(book({"T": rows_of(df)}), groups_file=g, groups_filename="g.xlsx"))
    assert map_ledgers(tb).set_index("ledger").loc["Apex Motors Pvt Ltd", "line"] == "CA.TR"


@pytest.mark.parametrize("sheets,fragment", [
    ({"A": [["x", "y"], [1, 2]], "B": [["foo"]]}, "Sheets looked at: A, B"),
    ({"T": [["name", "group"], ["Cash", "Cash-in-Hand"]]}, "missing column"),
    ({"T": rows_of(SAMPLE.assign(closing_dr_cr="Dx"))}, "must contain Dr, Cr"),
    ({"T": rows_of(SAMPLE.assign(closing_amount="abc"))}, "non-numeric"),
    ({"T": rows_of(SAMPLE.assign(group="Odd Group"))}, "not Tally's standard groups")])
def test_bad_workbooks_explain_what_is_wrong(sheets, fragment):
    with pytest.raises(ValueError) as e:
        read(book(sheets))
    assert fragment in str(e.value)


def test_missing_column_error_names_the_sheet():
    with pytest.raises(ValueError) as e:
        read(book({"My TB": [["name", "group"], ["Cash", "Cash-in-Hand"]]}))
    assert "sheet 'My TB'" in str(e.value)


def test_corrupt_and_unsupported_files_fail_politely():
    with pytest.raises(ValueError, match="Could not open"):
        read(io.BytesIO(b"this is not a workbook"))
    with pytest.raises(ValueError, match="must be a .csv or .xlsx"):
        P.read_trial_balance(io.BytesIO(b"x"), "tb.pdf")


def test_csv_still_works_through_the_new_entry_point():
    tb = P.read_trial_balance(io.StringIO(P.SAMPLE_TB.read_text(encoding="utf-8")), "tb.csv", company="X")
    assert (closings(tb) == REFERENCE).all()
