import io
import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from daybook_auditor.fs_format import check_file  # noqa: E402
from fsbuilder import pipeline as P  # noqa: E402
from fsbuilder.mapping import Rulebook, map_ledgers  # noqa: E402
from fsbuilder.model import build_model  # noqa: E402
from fsbuilder.reviewer import run_review  # noqa: E402
from fsbuilder.tb import normalise  # noqa: E402

RB = Rulebook.load()
CSV = P.SAMPLE_TB.read_text(encoding="utf-8")


def read(text, groups=None):
    return P.read_trial_balance_csv(io.StringIO(text), groups, "X", date(2024, 4, 1), date(2025, 3, 31))


# ------------------------------------------------------------------ reading an uploaded CSV
def test_uploaded_csv_gives_the_same_trial_balance_as_the_sample_loader():
    a, b = normalise(read(CSV)), normalise(P.load_sample())
    assert (a.ledgers["closing"].values == b.ledgers["closing"].values).all() and len(a.ledgers) == 68
    assert a.adjustments and not a.warnings


def test_dr_cr_words_and_spacing_are_tolerated():
    text = CSV.replace(",Dr,", ", debit ,").replace(",Cr,", ",CREDIT,")
    assert (normalise(read(text)).ledgers["closing"].values == normalise(P.load_sample()).ledgers["closing"].values).all()


@pytest.mark.parametrize("text,fragment", [
    (CSV.replace("closing_amount", "zzz"), "missing column"),
    (CSV.replace(",Dr,", ",Dx,", 3), "must contain Dr, Cr"),
    (CSV.replace("1071233.1", "abc"), "non-numeric"),
    (CSV.replace("Sundry Debtors", "Weird Group"), "not Tally's standard groups"),
    ("name,group,opening_amount,opening_dr_cr,closing_amount,closing_dr_cr\n", "no rows"),
    ("only one column\nvalue", "missing column")])
def test_bad_uploads_give_actionable_errors(text, fragment):
    with pytest.raises(ValueError) as e:
        read(text)
    assert fragment in str(e.value)


def test_custom_groups_are_accepted_with_a_groups_file():
    text = CSV.replace("Sundry Debtors", "Export Debtors")
    groups = io.StringIO("name,parent,nature\nExport Debtors,Sundry Debtors,Assets\n")
    tb = normalise(read(text, groups))
    assert map_ledgers(tb).set_index("ledger").loc["Apex Motors Pvt Ltd", "line"] == "CA.TR"


def test_last_financial_year():
    assert P.last_financial_year(date(2026, 10, 20)) == (date(2025, 4, 1), date(2026, 3, 31))
    assert P.last_financial_year(date(2026, 2, 1)) == (date(2024, 4, 1), date(2025, 3, 31))


# ------------------------------------------------------------------ turning edits into overrides
@pytest.fixture(scope="module")
def tb():
    return normalise(P.load_sample())


def test_unchanged_table_yields_no_overrides(tb):
    rm = map_ledgers(tb)
    assert P.overrides_from_edits(rm, P.editor_frame(rm, RB)) == {}


def test_changing_line_or_subhead_becomes_an_override_and_reverting_removes_it(tb):
    rm = map_ledgers(tb)
    frame = P.editor_frame(rm, RB)
    i = frame.index[frame["Ledger"] == "Fixed Deposit - HDFC Bank"][0]
    frame.loc[i, "Schedule III line"] = P.option_for(RB, "NCA.ONCA")
    frame.loc[i, "Override reason"] = "FD matures in 18 months"
    o = P.overrides_from_edits(rm, frame)
    assert o == {"Fixed Deposit - HDFC Bank": {"line": "NCA.ONCA", "sub": "Other bank balances (bank deposits)",
                                               "reason": "FD matures in 18 months"}}
    j = frame.index[frame["Ledger"] == "Cash"][0]
    frame.loc[j, "Sub-head"] = "Cash in hand"
    assert set(P.overrides_from_edits(rm, frame)) == {"Fixed Deposit - HDFC Bank", "Cash"}
    frame.loc[i, "Schedule III line"] = P.option_for(RB, "CA.CBB")
    assert set(P.overrides_from_edits(rm, frame)) == {"Cash"}


def test_an_override_changes_the_statements_and_the_signature(tb):
    base = build_model(tb, map_ledgers(tb))
    o = {"Fixed Deposit - HDFC Bank": {"line": "NCA.ONCA", "sub": "Bank deposits maturing after 12 months", "reason": "x"}}
    changed = build_model(tb, map_ledgers(tb, overrides=o))
    assert P.signature(base) == P.signature(build_model(tb, map_ledgers(tb)))
    assert P.signature(base) != P.signature(changed)
    assert any(r.label.endswith("Other non-current assets") and r.cur == 500_000 for r in changed.bs)
    assert changed.figures["cur"]["cce"] == base.figures["cur"]["cce"]
    assert not any("does not agree" in b for b in changed.basis)    # still balances


def test_unmapped_selection_is_ignored_not_saved(tb):
    rm = map_ledgers(tb)
    frame = P.editor_frame(rm, RB)
    frame.loc[0, "Schedule III line"] = P.UNMAPPED_OPTION
    assert P.overrides_from_edits(rm, frame) == {}


def test_override_file_round_trip_and_validation():
    data = P.overrides_bytes({"Cash": {"line": "CA.CBB", "sub": "Cash on hand", "reason": "r"}})
    assert P.parse_overrides_json(data, RB)["Cash"]["line"] == "CA.CBB"
    for bad in (b"not json", b"[1,2]", json.dumps({"Cash": {"line": "NOPE"}}).encode()):
        with pytest.raises(ValueError):
            P.parse_overrides_json(bad, RB)


# ------------------------------------------------------------------ display frames and files
def test_statement_frames_use_indian_format_and_show_markers(tb):
    m = build_model(tb, map_ledgers(tb))
    bs = P.statement_frame(m.bs)
    assert list(bs.columns) == ["Particulars", "Note", "Current year", "Previous year"]
    row = bs[bs["Particulars"].str.contains("TOTAL ASSETS")].iloc[0]
    assert row["Current year"] == "1,50,86,416" and row["Previous year"] == "60,80,000"
    assert bs["Particulars"].str.contains(r"\[R\d").any()
    cf = P.statement_frame(m.cashflow, prev_col=False, note_col=False)
    assert list(cf.columns) == ["Particulars", "Current year", "Previous year"] and cf["Previous year"].isin(["", "-"]).all()


def test_build_files_returns_four_valid_deliverables(tb):
    m = build_model(tb, map_ledgers(tb))
    files = P.build_files(m, run_review(m, m.mapping))
    assert list(files) == ["Statements (Word)", "Statements (Excel)", "Review (Word)", "Review (Excel)"]
    for label, (name, data, mime) in files.items():
        assert len(data) > 5000 and name.endswith((".docx", ".xlsx")) and "openxmlformats" in mime
        findings, _ = check_file(name, data)
        assert findings.empty, (label, findings.to_string())
