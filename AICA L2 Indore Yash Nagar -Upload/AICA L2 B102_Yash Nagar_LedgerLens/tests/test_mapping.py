import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fsbuilder import tb as tbmod  # noqa: E402
from fsbuilder.mapping import map_ledgers  # noqa: E402
from fsbuilder.statements import balance_check, line_totals  # noqa: E402
from fsbuilder.tb import load_snapshot, normalise  # noqa: E402

TB_CSV, GROUPS_CSV = ROOT / "samples" / "rpi_trial_balance.csv", ROOT / "samples" / "rpi_groups.csv"


@pytest.fixture(scope="module")
def tb():
    return normalise(load_snapshot(TB_CSV, GROUPS_CSV))


def _closing(t, line):
    return round(t.loc[t["line"] == line, "closing"].sum(), 2)


def test_profit_double_count_is_removed_and_tb_agrees(tb):
    assert len(tb.adjustments) == 1 and "24,89,415.93" in tb.adjustments[0]
    assert tb.warnings == []
    assert abs(tb.ledgers["closing"].sum()) < 0.01 and abs(tb.ledgers["opening"].sum()) < 0.01


def test_every_ledger_maps_and_matches_tallys_own_balance_sheet(tb):
    m = map_ledgers(tb)
    assert (m["source"] == "unmapped").sum() == 0
    t = line_totals(m)
    # figures taken from Tally's Balance Sheet / P&L for the same period
    expected = {"EQ.SC": 2_930_000.00, "EQ.RS": 3_334_415.93, "NCL.LTB": 1_550_000.00, "CL.TP": 6_501_803.32,
                "CL.OCL": 770_196.83, "NCA.PPE": 2_446_741.04, "CA.INV": 1_075_000.00, "CA.TR": 8_612_375.89,
                "CA.CBB": 2_952_299.15, "REV.OPS": 11_913_203.03, "REV.OI": 85_702.95}
    for line, amount in expected.items():
        assert _closing(t, line) == amount, line
    chk = balance_check(t)
    assert abs(chk["closing"]["difference"]) < 0.01 and abs(chk["opening"]["difference"]) < 0.01
    assert round(chk["closing"]["assets"], 2) == 15_086_416.08
    assert round(t.attrs["profit"], 2) == 2_489_415.93


def test_judgement_calls_are_flagged_for_review(tb):
    m = map_ledgers(tb).set_index("ledger")
    assert m.loc["Fixed Deposit - HDFC Bank", "line"] == "CA.CBB" and "not an 'investment'" in m.loc["Fixed Deposit - HDFC Bank", "review"]
    assert m.loc["Outstanding Salary", "line"] == "CL.OCL" and "AS 29" in m.loc["Outstanding Salary", "review"]
    assert "Related-party" in m.loc["Unsecured Loan - Director", "review"]
    assert "current maturities" in m.loc["Term Loan - HDFC Bank", "review"]
    assert "Key managerial" in m.loc["Directors Remuneration", "review"]


def test_gst_input_and_output_net_per_head(tb):
    m = map_ledgers(tb)
    gst = m[m["ledger"].str.contains("GST")]
    assert set(gst["line"]) == {"CL.OCL"}
    # all heads are net payable here; flip CGST to a net input credit and it becomes an asset
    L = tb.ledgers.copy()
    L.loc[L["name"] == "CGST Output", "closing"] = -100_000.0
    m2 = map_ledgers(replace(tb, ledgers=L)).set_index("ledger")
    assert m2.loc["CGST Input", "line"] == "CA.OCA" and m2.loc["CGST Output", "line"] == "CA.OCA"
    assert m2.loc["SGST Input", "line"] == "CL.OCL"  # other heads unaffected


def test_wrong_sign_balances_are_not_netted_away(tb):
    L = tb.ledgers.copy()
    L.loc[L["name"] == "Apex Motors Pvt Ltd", "closing"] = -50_000.0       # customer paid in advance
    L.loc[L["name"] == "Bright Bearings Co.", "closing"] = 30_000.0        # advance paid to supplier
    L.loc[L["name"] == "ICICI Bank - Current A/c", "closing"] = -10_000.0  # overdrawn
    m = map_ledgers(replace(tb, ledgers=L)).set_index("ledger")
    assert m.loc["Apex Motors Pvt Ltd", "line"] == "CL.OCL"
    assert m.loc["Bright Bearings Co.", "line"] == "CA.STLA"
    assert m.loc["ICICI Bank - Current A/c", "line"] == "CL.STB"


def test_unknown_group_is_unmapped_and_override_fixes_it(tb):
    L = tb.ledgers.copy()
    L.loc[L["name"] == "General Expenses", "group"] = "Custom Weird Group"
    groups = dict(tb.groups) | {"Custom Weird Group": ("", "Expenses")}
    t2 = replace(tb, ledgers=L, groups=groups)
    m = map_ledgers(t2).set_index("ledger")
    assert m.loc["General Expenses", "source"] == "unmapped" and m.loc["General Expenses", "line"] == "UNMAPPED"
    m = map_ledgers(t2, overrides={"General Expenses": {"line": "EXP.OTH", "sub": "Miscellaneous expenses", "reason": "client policy"}}).set_index("ledger")
    assert m.loc["General Expenses", "source"] == "override" and "client policy" in m.loc["General Expenses", "review"]


def test_custom_subgroup_inherits_parent_rule(tb):
    L = tb.ledgers.copy()
    L.loc[L["name"] == "Sharma Steel Traders", "group"] = "Steel Suppliers"
    groups = dict(tb.groups) | {"Steel Suppliers": ("Sundry Creditors", "Liabilities")}
    m = map_ledgers(replace(tb, ledgers=L, groups=groups)).set_index("ledger")
    assert m.loc["Sharma Steel Traders", "line"] == "CL.TP"


def test_stock_movement_flows_to_cost_of_materials(tb):
    L = tb.ledgers.copy()
    L.loc[L["name"] == "Raw Material Stock", "closing"] = 800_000.0   # stock rose by 150,000
    L.loc[L["name"] == "Purchase - Raw Material", "closing"] -= 0      # purchases unchanged
    t = line_totals(map_ledgers(replace(tb, ledgers=L)))
    assert _closing(t, "EXP.COM") == round(7_709_375.48 - 150_000, 2)


def test_parse_amount_variants():
    assert tbmod.parse_amount("-1,000.50") == (-1000.5, None)
    assert tbmod.parse_amount("1,000.00 Dr") == (1000.0, "Dr")
    assert tbmod.parse_amount("") == (0.0, None)
    assert tbmod.parse_amount("₹ 2,500.00 Cr") == (2500.0, "Cr")


def _fake_tally(tb, dr_negative=True):
    """Build the XML shape we expect from Tally for this trial balance."""
    def amt(x):
        return f"{(-x if dr_negative else x):.2f}"
    led = "".join(f'<LEDGER NAME="{r.name}"><PARENT>{"&#4; Primary" if r.group == "Primary" else r.group}</PARENT>'
                  f"<OPENINGBALANCE>{amt(r.opening)}</OPENINGBALANCE><CLOSINGBALANCE>{amt(r.closing)}</CLOSINGBALANCE></LEDGER>"
                  for r in tb.ledgers.itertuples()).replace("&", "&amp;").replace("&amp;#4;", "&#4;")
    grp = "".join(f'<GROUP NAME="{g}"><PARENT>{p or "Primary"}</PARENT></GROUP>' for g, (p, _) in tb.groups.items()).replace("&", "&amp;")
    wrap = lambda body: f"<ENVELOPE><BODY><DATA><COLLECTION>{body}</COLLECTION></DATA></BODY></ENVELOPE>".encode("utf-8")  # noqa: E731

    def post(host, port, body, timeout):
        return wrap(led if b"FSBLedger" in body else grp)
    return post


@pytest.mark.parametrize("dr_negative", [True, False])
def test_live_client_parses_and_detects_sign(tb, monkeypatch, dr_negative):
    from datetime import date
    raw = load_snapshot(TB_CSV, GROUPS_CSV)
    monkeypatch.setattr(tbmod, "_post", _fake_tally(raw, dr_negative))
    got = tbmod.fetch_from_tally("Rajasthan Precision Industries Private Limited", date(2024, 4, 1), date(2025, 3, 31))
    assert len(got.ledgers) == 68
    a = got.ledgers.set_index("name")["closing"]
    b = raw.ledgers.set_index("name")["closing"]
    assert (a - b).abs().max() < 0.01
    assert abs(line_totals(map_ledgers(normalise(got))).attrs["profit"] - 2_489_415.93) < 0.01


def test_tally_down_gives_actionable_error(monkeypatch):
    import urllib.error
    from datetime import date

    def boom(*a, **k):
        raise urllib.error.URLError("refused")
    monkeypatch.setattr(tbmod.urllib.request, "urlopen", boom)
    with pytest.raises(tbmod.TallyError, match="Connectivity"):
        tbmod.fetch_from_tally("X", date(2024, 4, 1), date(2025, 3, 31))
