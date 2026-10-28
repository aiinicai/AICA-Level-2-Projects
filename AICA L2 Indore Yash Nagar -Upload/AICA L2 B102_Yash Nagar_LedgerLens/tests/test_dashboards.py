import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from daybook_auditor import narration  # noqa: E402
from daybook_auditor.analytics import daybook_dashboard, family  # noqa: E402
from daybook_auditor.parser import load_daybook  # noqa: E402
from daybook_auditor.rules import Config, run_rules  # noqa: E402
from fsbuilder.analytics import fs_dashboard  # noqa: E402
from fsbuilder.mapping import map_ledgers  # noqa: E402
from fsbuilder.model import build_model  # noqa: E402
from fsbuilder.reviewer import run_review  # noqa: E402
from fsbuilder.tb import load_snapshot, normalise  # noqa: E402


@pytest.fixture(scope="module")
def fs():
    tb = normalise(load_snapshot(ROOT / "samples" / "rpi_trial_balance.csv", ROOT / "samples" / "rpi_groups.csv",
                                 "RPI", date(2024, 4, 1), date(2025, 3, 31)))
    return build_model(tb, map_ledgers(tb))


def test_family_names_the_kind_of_test():
    assert family("anything", "AI") == "AI review"
    assert family(narration.R_NEAR, "Rule") == "Amount pattern"
    assert family(narration.R_NARR_PREFIX + "gift", "Rule") == "Narration"
    assert family("Cash payment over limit", "Rule") == "Accounting rule"


def test_statement_dashboard_agrees_with_the_statements(fs):
    d = fs_dashboard(fs, run_review(fs))
    k = d["kpis"]
    assert k["profit"] == fs.profit
    assert k["revenue"] == fs.figures["pl"]["revenue"]
    pl = d["pl_bridge"].set_index("item")["amount"]
    income = pl["Revenue from operations"] + pl.get("Other income", 0)
    costs = d["pl_bridge"].query("kind == 'Cost'")["amount"].sum()
    assert income - costs == pytest.approx(pl["Profit for the year"])      # the bridge adds up
    cb = d["cash_bridge"].set_index("step")["amount"]
    assert cb["Opening cash"] + cb["Operating activities"] + cb["Investing activities"] + cb["Financing activities"] == cb["Closing cash"]
    assert d["health"]["failed"] == 0


def test_statement_dashboard_scales_to_the_unit(fs):
    tb = normalise(load_snapshot(ROOT / "samples" / "rpi_trial_balance.csv", ROOT / "samples" / "rpi_groups.csv",
                                 "RPI", date(2024, 4, 1), date(2025, 3, 31)))
    mp = map_ledgers(tb)
    lakhs = build_model(tb, mp, unit="lakhs")
    d = fs_dashboard(lakhs)
    full = fs_dashboard(fs)
    assert d["health"] is None
    assert d["pl_bridge"]["amount"].iloc[0] == pytest.approx(full["pl_bridge"]["amount"].iloc[0] / 100000, abs=0.01)


def test_daybook_dashboard_counts_are_consistent():
    df, meta = load_daybook("tally_daybook_export.xlsx", (ROOT / "samples" / "tally_daybook_export.xlsx").read_bytes())
    f = run_rules(df, Config(date(2025, 4, 1), date(2026, 3, 31)))
    d = daybook_dashboard(df, f)
    k = d["kpis"]
    assert k["vouchers"] == d["by_type"]["vouchers"].sum()
    assert k["findings"] == len(f) == d["severity_by_family"]["findings"].sum()
    assert k["flagged_vouchers"] == d["by_type"]["flagged"].sum() <= k["vouchers"]
    assert 0 <= k["flagged_share"] <= 1
    assert k["flagged_value"] <= d["by_type"]["value"].sum()
    if d["monthly"] is not None:
        assert d["monthly"]["vouchers"].sum() == k["vouchers"] - k["undated"]


def test_daybook_dashboard_copes_with_no_findings():
    df, _ = load_daybook("tally_daybook_export.xlsx", (ROOT / "samples" / "tally_daybook_export.xlsx").read_bytes())
    empty = run_rules(df, Config(date(2025, 4, 1), date(2026, 3, 31))).iloc[0:0]
    d = daybook_dashboard(df, empty)
    assert d["kpis"]["flagged_vouchers"] == 0 and d["kpis"]["findings"] == 0
    assert d["severity_by_family"].empty and d["top_rules"].empty
