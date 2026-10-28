"""TB / GL exports in three different system layouts (Tally-style, Oracle-style, ad-hoc Excel). Synthetic data from sample_data/make_format_samples.py."""
import sys
from pathlib import Path

import pytest

from helpers import ROOT, make_project  # noqa: F401  (sets sys.path)

sys.path.insert(0, str(ROOT / "sample_data"))
import make_format_samples  # noqa: E402

from ct_tool.extract import parse_gl, parse_tb, to_num  # noqa: E402
from ct_tool.fx import default_settings  # noqa: E402
from ct_tool.pipeline import run_analysis  # noqa: E402
from ct_tool.project import Project  # noqa: E402

PBT_AED = 4_210_500.00     # profit before tax of the synthetic company at scale 1.0


@pytest.fixture(scope="module")
def files(tmp_path_factory):
    out = tmp_path_factory.mktemp("formats")
    make_format_samples.main(["x", str(out)])
    return out


def _project(files, tag, ccy, rates=None):
    p = Project(name=tag)
    p.tb = parse_tb(str(files / f"{tag}_TB_{ccy}.xlsx"), currency=ccy)
    p.gl = parse_gl(str(files / f"{tag}_GL_{ccy}.xlsx"))
    p.fx = default_settings(ccy, "2025-01-01", "2025-12-31")
    if rates:
        p.fx.rates[ccy] = rates
        p.fx.method, p.fx.rate_source, p.fx.method_reason = "manual", "test only", "test"
        p.fx.translation_diff_approved = True
    p.fx_confirmed = True
    return p


def _check(an, cid):
    return next(c for c in an.checks if c.id == cid)


def test_to_num_handles_currency_prefix_and_dr_cr():
    assert to_num("EUR 1,200.50") == 1200.50
    assert to_num("1,200.50 Cr") == -1200.50
    assert to_num("(1,200.50)") == -1200.50
    assert to_num("AED 5") == 5.0


def test_tally_group_subtotals_are_excluded_and_parties_are_mapped(files):
    p = _project(files, "1_Tally", "AED")
    assert len(p.tb.accounts) == 49 and abs(sum(a.net for a in p.tb.accounts)) < 0.01
    assert any("group sub-total" in w for w in p.tb.warnings)
    assert not any(a.name in ("Capital Account", "Current Assets", "Sundry Debtors") for a in p.tb.accounts)
    an = run_analysis(p)
    line = {m.account.name: m.line for m in an.mapped}
    assert line["Hamdan Trading Co"] == "A_TRADE_REC" and line["Gulf Wholesale FZE"] == "L_TRADE_PAY"
    assert line["Profit & Loss A/c (opening)"] == "E_RE"
    assert line["Suspense Account"] == "UNMAPPED"               # never guessed - needs the user's decision
    assert abs(an.comp.A - PBT_AED) < 0.01
    assert _check(an, "GL-06").status == "PASS" and "49 account" in _check(an, "GL-06").detail
    assert an.entity.startswith("Sample Gulf Trading LLC")


def test_tally_gl_blocks_have_ledger_names_and_opening_lines_are_flagged(files):
    gl = parse_gl(str(files / "1_Tally_GL_AED.xlsx"))
    assert all(l.account_name for l in gl.lines)
    assert sum(l.reference == "OPENING" for l in gl.lines) == 24
    assert not any("Closing" in l.description for l in gl.lines)


def test_oracle_segments_become_code_and_description_becomes_name(files):
    p = _project(files, "2_Oracle", "USD")
    a = p.tb.accounts[0]
    assert a.code == "101.000.1000.0000.000" and a.name.startswith("Cash at bank")
    assert len(p.tb.accounts) == 43 and abs(sum(x.net for x in p.tb.accounts)) < 0.01
    assert not any("total" in x.name.lower() for x in p.tb.accounts)
    an = run_analysis(p)
    assert _check(an, "GL-06").status == "PASS"
    assert _check(an, "TB-06").status == "PASS"                 # beginning + period activity = ending
    assert an.entity.startswith("Sample Gulf Trading LLC")
    assert abs(an.comp.A - PBT_AED * 3.6725) < 0.5


def test_random_layout_uses_side_column_text_amounts_and_account_names(files):
    p = _project(files, "3_Random", "EUR", {"pl": 4.0, "closing": 4.2, "equity": 3.9})
    assert len(p.tb.accounts) == 43 and abs(sum(a.net for a in p.tb.accounts)) < 0.01
    by = {a.name: a.net for a in p.tb.accounts}
    assert by["Cash at bank - current account"] == 4_700_000.00 and by["Trade payables"] == -1_350_000.00      # sign from the Dr/Cr marker
    gl = p.gl
    assert all(l.date for l in gl.lines) and gl.lines[0].account_code        # dd.mm.yyyy text dates, 'code name' in one cell
    an = run_analysis(p)
    assert _check(an, "GL-06").status == "PASS"
    assert an.entity == "Sample Gulf Trading LLC"
    assert abs(an.comp.A - PBT_AED * 4.0) < 0.5


def test_normal_tb_without_group_rows_is_not_altered(files):
    p = make_project("USD", gl=False)
    assert not any("group sub-total" in w for w in p.tb.warnings)
