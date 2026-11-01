"""Controls added after the Dixon Technologies review (1 November 2026).

Each test pins one rule: date-matched quarters, trailing EPS from consecutive quarters only,
one-off removal, results freshness, the provisional gate, the re-rating and consensus caps,
scenarios, the non-circular scorecard, and commentary-driven provisional ratings.
"""

from dataclasses import replace
from datetime import date

import pytest

from bsa import data, peers, pipeline, scoring, valuation
from bsa import fundamentals as fd
from bsa import indicators as ind

CR = 1e7


def _q(label, d, revenue, pat, other_income=None, pbt=None, tax=None, unusual=None):
    return {"label": label, "date": d, "revenue": revenue * CR, "pat": pat * CR, "ebitda_reported": None,
            "other_income": None if other_income is None else other_income * CR,
            "pbt": None if pbt is None else pbt * CR, "tax": None if tax is None else tax * CR,
            "unusual": None if unusual is None else unusual * CR, "nii": None}


# Dixon-like shape: Yahoo returned Q4FY25, Q1FY26, Q3FY26, Q4FY26, Q1FY27 (no Q2FY26).
GAPPED = [
    _q("Q4FY25", "2025-03-31", 10293, 401, 11, 576, 111, 250),
    _q("Q1FY26", "2025-06-30", 12836, 225, 2, 366, 86),
    _q("Q3FY26", "2025-12-31", 10672, 287, 131, 412, 91),
    _q("Q4FY26", "2026-03-31", 10511, 256, 84, 370, 72),
    _q("Q1FY27", "2026-06-30", 15548, 663, 528, 869, 151),
]


@pytest.fixture
def gapped():
    qs = [dict(q) for q in GAPPED]
    fd.normalise(qs)
    return qs


def test_yoy_is_matched_by_date_not_position(gapped):
    qc = fd.quarter_changes(gapped)
    assert qc["year_ago"] == "Q1FY26"                     # not Q4FY25, which is five rows back
    assert qc["prev"] == "Q4FY26"
    assert qc["yoy"]["revenue"] == pytest.approx((15548 / 12836 - 1) * 100)   # +21.1%, the reported figure
    assert qc["missing"] == ["Q2FY26"]


def test_missing_comparison_quarter_gives_none():
    qs = [dict(q) for q in GAPPED if q["label"] != "Q1FY26"]
    fd.normalise(qs)
    qc = fd.quarter_changes(qs)
    assert qc["year_ago"] is None and qc["yoy"] == {}


def test_trailing_eps_needs_four_consecutive_quarters(gapped):
    annual = [{"label": "FY26", "eps_norm": 236.6}]
    te = fd.trailing_eps(annual, gapped, shares=6.08 * CR)
    assert te["eps"] == pytest.approx(236.6) and "FY26 full year" in te["basis"] and "gap" in te["basis"]
    consecutive = [dict(GAPPED[1]), _q("Q2FY26", "2025-09-30", 14855, 670, 20, 900, 200)] + \
        [dict(q) for q in GAPPED[2:]]
    fd.normalise(consecutive)
    te2 = fd.trailing_eps(annual, consecutive, shares=10 * CR)
    assert "four quarters to Q1FY27" in te2["basis"]
    assert te2["ttm_pat_norm"] == pytest.approx(sum(q["pat_norm"] for q in consecutive[-4:]))


def test_other_income_spike_is_removed_after_tax(gapped):
    q = gapped[-1]
    # Median other income of the other quarters = median(11, 2, 131, 84) = 47.5 crore.
    excess = (528 - 47.5) * CR
    rate = 151 / 869
    assert q["one_off"] == pytest.approx(excess)
    assert q["one_off_source"] == "other income spike"
    assert q["pat_norm"] == pytest.approx(663 * CR - excess * (1 - rate))
    assert gapped[2]["one_off"] == 0.0                     # 131 crore is not a spike (below 3x median)


def test_unusual_items_are_removed_and_not_double_counted():
    qs = [dict(q) for q in GAPPED]
    fd.normalise(qs)
    q4fy25 = qs[0]
    assert q4fy25["one_off"] == pytest.approx(250 * CR)    # unusual items only; other income 11 cr is normal
    assert q4fy25["pat_norm"] == pytest.approx(401 * CR - 250 * CR * (1 - 111 / 576))
    both = [dict(q) for q in GAPPED]
    both[-1]["unusual"] = 300 * CR                        # same period flagged twice: the larger is used
    fd.normalise(both)
    assert both[-1]["one_off"] == pytest.approx((528 - 47.5) * CR)


def test_ebitda_excludes_other_income_and_unusual_items():
    rows = [{"ebitda_reported": 1000 * CR, "other_income": 528 * CR, "unusual": 0.0, "pbt": 869 * CR,
             "tax": 151 * CR, "pat": 663 * CR}]
    fd.normalise(rows)
    assert rows[0]["ebitda"] == pytest.approx(472 * CR)


@pytest.mark.parametrize("today,quarters,overdue", [
    (date(2026, 11, 1), ["Q2FY27"], False),     # 32 days after quarter end: check, not yet overdue
    (date(2026, 11, 20), ["Q2FY27"], True),     # past the 45-day deadline
    (date(2027, 1, 5), ["Q2FY27", "Q3FY27"], True),
    (date(2026, 7, 20), [], False),
])
def test_freshness(gapped, today, quarters, overdue):
    f = fd.freshness(gapped, today)
    assert [x["quarter"] for x in f["missing"]] == quarters
    assert f["overdue"] is overdue and f["check_required"] is bool(quarters)


def test_annual_accounts_count_as_coverage():
    # Quarterly data stops at Q1FY26 but FY26 annual accounts exist: only quarters after March 2026 are missing.
    qs = [{"label": "Q1FY26", "date": "2025-06-30"}]
    f = fd.freshness(qs, date(2026, 11, 1), [{"label": "FY26", "date": "2026-03-31"}])
    assert f["latest_quarter"] == "FY26 (annual)"
    assert [x["quarter"] for x in f["missing"]] == ["Q1FY27", "Q2FY27"]
    assert f["missing"][0]["overdue"] and not f["missing"][1]["overdue"]


def test_march_quarter_has_60_day_deadline():
    qs = [{"label": "Q3FY26", "date": "2025-12-31"}]
    f = fd.freshness(qs, date(2026, 5, 20))
    assert f["missing"][0]["due_by"] == "30-May-2026" and not f["overdue"]


def test_provisional_gate_blocks_buy():
    r = scoring.rating(30.0, 70.0, 3, 20.0, ["Company profile download failed."])
    assert r["rating"] == "HOLD" and r["base_rating"] == "BUY" and r["provisional"] and r["conviction"] == "Low"
    single = scoring.rating(89.0, 74.0, 1, None)          # the Dixon case: one method, 89% upside
    assert single["rating"] == "HOLD" and single["provisional"]
    assert "Only one valuation method" in single["provisional_reasons"][0]
    sell = scoring.rating(-20.0, 30.0, 3, 20.0, ["x"])
    assert sell["rating"] == "SELL" and sell["provisional"]
    clean = scoring.rating(30.0, 70.0, 3, 20.0)
    assert clean["rating"] == "BUY" and not clean["provisional"]


def test_excluded_method_conflict_lowers_conviction():
    r = scoring.rating(30.0, 70.0, 2, 20.0, conflicts=["Discounted cash flow gives Rs 976."])
    assert r["rating"] == "BUY" and r["conviction"] == "Low"


def test_rerating_cap():
    m, note = valuation.target_multiple([70.6], 46.7, 5.0, 80.0)
    assert m == pytest.approx(1.25 * 46.7) and "capped" in note
    m2, note2 = valuation.target_multiple([40.0, 50.0], 46.7, 5.0, 80.0)
    assert m2 == pytest.approx(45.0) and note2 is None


def _setup(raw):
    fund = fd.build(raw, financial=False)
    tech = ind.technical_summary(raw.ohlc, raw.bench)
    return fund, tech, raw.info["currentPrice"]


def test_consensus_cap(synthetic_raw):
    fund, tech, cmp = _setup(synthetic_raw)
    info = dict(synthetic_raw.info, targetMeanPrice=cmp * 0.45, targetLowPrice=cmp * 0.42, targetHighPrice=cmp * 0.5)
    v = valuation.value(cmp, info, fund, tech, {"pe": None, "pb": None})
    assert v["target_before_caps"] > 1.15 * cmp * 0.5
    assert v["target"] == pytest.approx(1.15 * cmp * 0.5)
    assert any("highest of 12 analyst targets" in x for x in v["adjustments"])


def test_scenarios_bracket_the_relative_value(synthetic_raw):
    fund, tech, cmp = _setup(synthetic_raw)
    v = valuation.value(cmp, synthetic_raw.info, fund, tech, {"pe": None, "pb": None})
    s = {x["case"]: x["value"] for x in v["scenarios"]}
    assert s["Bear"] < s["Base"] < s["Bull"]
    assert s["Base"] == pytest.approx(v["methods"][0]["value"])


def test_scorecard_does_not_score_its_own_upside(synthetic_raw):
    fund, tech, cmp = _setup(synthetic_raw)
    v = valuation.value(cmp, synthetic_raw.info, fund, tech, {"pe": None, "pb": None})
    names = [m["metric"] for p in scoring.scorecard(fund, v, tech)["pillars"] for m in p["metrics"]]
    assert not any("Upside" in n for n in names)
    assert "Free cash flow yield" in names
    # PEG uses forward growth (consensus 14.6 vs trailing four-quarter EPS 13.65), not the historical CAGR.
    assert v["trailing_eps"] == pytest.approx(13.65)
    assert v["multiples"]["peg"] == pytest.approx(v["multiples"]["pe"] / ((14.6 / 13.65 - 1) * 100))


@pytest.fixture
def offline(monkeypatch, synthetic_raw):
    monkeypatch.setattr(data, "resolve", lambda q: {"symbol": "DEMO.NS", "exchange": "NSE", "matched_by": "test"})
    monkeypatch.setattr(data, "fetch", lambda s, e: synthetic_raw)
    monkeypatch.setattr(data, "fetch_peers", lambda bases: [])
    monkeypatch.setattr(data, "fetch_sector_index", lambda t: None)


def test_failed_profile_download_makes_rating_provisional(monkeypatch, synthetic_raw, tmp_path):
    failed = replace(synthetic_raw, failed=["Company profile"])
    monkeypatch.setattr(data, "resolve", lambda q: {"symbol": "DEMO.NS", "exchange": "NSE", "matched_by": "test"})
    monkeypatch.setattr(data, "fetch", lambda s, e: failed)
    monkeypatch.setattr(data, "fetch_peers", lambda bases: [])
    monkeypatch.setattr(data, "fetch_sector_index", lambda t: None)
    a = pipeline.run("demo", str(tmp_path), make_pdf=False, today=date(2026, 8, 1))
    assert a["rating"]["provisional"] and a["rating"]["rating"] != "BUY"
    assert "Provisional rating." in open(a["files"]["html"], encoding="utf-8").read()


def test_overdue_results_make_rating_provisional(offline, tmp_path):
    a = pipeline.run("demo", str(tmp_path), make_pdf=False, today=date(2026, 11, 20))
    assert any("Q2FY27 results were due by 14-Nov-2026" in x for x in a["rating"]["provisional_reasons"])
    d = pipeline.digest(a)
    assert "Results freshness: CHECK REQUIRED" in d and "OVERDUE" in d


def test_newer_results_in_commentary_make_rating_provisional(offline, tmp_path):
    a = pipeline.run("demo", str(tmp_path), make_pdf=False, today=date(2026, 8, 1))
    c = {"summary": "Test.", "newer_results": {"quarter": "Q2FY27", "date": "30-Oct-2026",
                                               "source": "https://example.com/filing"}}
    b = pipeline.rerender(a["files"]["json"], c, make_pdf=False)
    assert b["rating"]["provisional"] and b["rating"]["rating"] != "BUY"
    assert any("Q2FY27" in x for x in b["rating"]["provisional_reasons"])
    assert b["valuation"]["target"] == a["valuation"]["target"]          # numbers never change
    assert "(provisional)" in b["narrative"]["headline"]


def test_commentary_validation_of_new_fields():
    with pytest.raises(ValueError):
        pipeline.validate_commentary({"newer_results": {"date": "30-Oct-2026"}})
    with pytest.raises(ValueError):
        pipeline.validate_commentary({"data_conflicts": [1, 2]})
    ok = pipeline.validate_commentary({"data_conflicts": ["Reported PAT differs from source."]})
    assert ok["data_conflicts"]


def test_dixon_is_in_the_ems_peer_group():
    g = peers.group_for("DIXON", "Consumer Electronics")
    assert g == "Electronics Manufacturing Services"
    assert "KAYNES" in peers.peers_for("DIXON", g) and peers.sector_index_for(g) is None
