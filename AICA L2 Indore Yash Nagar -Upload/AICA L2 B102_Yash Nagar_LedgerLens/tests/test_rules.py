import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "samples"))

import make_sample  # noqa: E402
from daybook_auditor import rules  # noqa: E402
from daybook_auditor.parser import load_daybook  # noqa: E402

CFG = rules.Config(fy_start=date(2025, 4, 1), fy_end=date(2026, 3, 31))


def _findings():
    df, meta = load_daybook("sample.xml", make_sample.build().encode())
    return df, meta, rules.run_rules(df, CFG, meta["ledger_level"])


def test_parser_reads_all_lines_and_balances():
    df, meta, _ = _findings()
    assert meta["ledger_level"] and meta["vouchers"] == len(make_sample.V) + len(make_sample.EXTRA)
    assert set(df["side"]) == {"Dr", "Cr"}


def test_every_seeded_issue_is_detected():
    _, _, f = _findings()
    got = set(f["rule"])
    expected = {rules.R_CASH_PAY, rules.R_CASH_NEAR, rules.R_CASH_RCPT, rules.R_NEG_CASH, rules.R_DUP,
                rules.R_IMBAL, rules.R_GAP, rules.R_PERIOD, rules.R_SUNDAY, rules.R_NARR, rules.R_SUSP,
                rules.R_TDS, rules.R_GST}
    assert expected <= got, expected - got


def test_cash_split_is_aggregated_per_party_per_day():
    _, _, f = _findings()
    row = f[(f["rule"] == rules.R_CASH_PAY) & (f["ledger"] == "Verma Transport")]
    assert len(row) == 1 and row.iloc[0]["amount"] == 28_500


def test_tds_flags_missed_rent_month_only():
    _, _, f = _findings()
    rent = f[(f["rule"] == rules.R_TDS) & (f["ledger"] == "Office Rent")]
    assert len(rent) == 1 and rent.iloc[0]["date"].month == 10


def test_condensed_export_skips_ledger_level_rules():
    df, _ = load_daybook("s.xml", make_sample.build().encode())
    f = rules.run_rules(df, CFG, ledger_level=False)
    assert rules.R_IMBAL not in set(f["rule"]) and rules.R_CASH_PAY not in set(f["rule"])


def test_ai_response_parsing_and_prompt_line():
    from daybook_auditor.ai_review import _parse, _voucher_line
    assert _parse('```json\n[{"voucher_id": "V1"}]\n```') == [{"voucher_id": "V1"}]
    assert _parse('{"findings": [{"voucher_id": "V2"}]}') == [{"voucher_id": "V2"}]
    df, _ = load_daybook("s.xml", make_sample.build().encode())
    line = _voucher_line(rules.summarise_vouchers(df).iloc[0].to_dict())
    assert line.startswith("V00001 | 2025-04-01 | Contra 1 | Dr: Cash 200,000")


def test_fs_formatting_clean_and_seeded():
    import make_sample_fs
    from daybook_auditor.fs_format import check_docx

    def run(errors):
        import io
        buf = io.BytesIO()
        make_sample_fs.build(errors).save(buf)
        return check_docx(buf.getvalue())[0]

    assert run(False).empty
    f = run(True)
    by = f.groupby("check").size().to_dict()
    assert by == {"Font type": 3, "Font size": 2, "Date format": 4, "Negative number": 2}, by


def test_fs_ties_to_daybook():
    import make_sample_fs
    s = make_sample_fs.statements()
    assert round(s["revenue"]) == 1_200_000 and round(s["diff"]) == 1_000


def test_fs_formatting_xlsx_clean_and_seeded():
    import io
    import make_sample_fs
    from daybook_auditor.fs_format import check_file

    def run(errors):
        buf = io.BytesIO()
        make_sample_fs.build_xlsx(errors).save(buf)
        return check_file("fs.xlsx", buf.getvalue())[0]

    assert run(False).empty
    by = run(True).groupby("check").size().to_dict()
    assert by == {"Font type": 2, "Font size": 1, "Date format": 3, "Negative number": 2,
                  "Negative number format": 2}, by


def test_negative_format_detection():
    from daybook_auditor.fs_format import _negatives_bracketed
    assert _negatives_bracketed("#,##0_);(#,##0)") and _negatives_bracketed("#,##0;(#,##0);-")
    assert not _negatives_bracketed("#,##0") and not _negatives_bracketed("General")
    assert not _negatives_bracketed("#,##0;-#,##0") and not _negatives_bracketed("#,##0;[Red]-#,##0")
