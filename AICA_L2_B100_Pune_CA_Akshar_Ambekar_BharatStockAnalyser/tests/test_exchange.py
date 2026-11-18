"""Exchange layer (v1.2): XBRL parsing, results meetings, merge with Yahoo, freshness and fail-safe.

The XBRL snippets are minimal synthetic instances in the SEBI layout, with the Dixon
Technologies Q2FY27 consolidated figures filed with NSE on 30 October 2026.
"""

from datetime import date

import pandas as pd
import pytest

from bsa import data, exchange, fundamentals, pipeline

CR = 1e7
TODAY = date(2026, 11, 1)


def _ctx(cid, start=None, end=None, instant=None, member=None):
    period = (f"<xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{end}</xbrli:endDate>" if start
              else f"<xbrli:instant>{instant}</xbrli:instant>")
    seg = (f"<xbrli:segment><xbrldi:explicitMember dimension='in-capmkt:X'>{member}</xbrldi:explicitMember>"
           "</xbrli:segment>" if member else "")
    return (f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier scheme="s">540699</xbrli:identifier>{seg}'
            f"</xbrli:entity><xbrli:period>{period}</xbrli:period></xbrli:context>")


def _fact(name, ctx, value, prefix="in-capmkt"):
    return f'<{prefix}:{name} contextRef="{ctx}" unitRef="INR" decimals="-5">{value}</{prefix}:{name}>'


def results_xml(facts: dict, quarter=("2026-07-01", "2026-09-30")) -> str:
    body = [_ctx("OneD", *quarter), _ctx("FourD", "2026-04-01", quarter[1]), _ctx("OneI", instant=quarter[1]),
            _ctx("SegD", *quarter, member="in-capmkt:Segment1Member"),
            _fact("DateOfEndOfReportingPeriod", "OneD", quarter[1]),
            _fact("NatureOfReportStandaloneConsolidated", "OneD", "Consolidated"),
            _fact("RevenueFromOperations", "SegD", "999")]  # segment value must be ignored
    for name, (q, half) in facts.items():
        body.append(_fact(name, "OneD", q))
        body.append(_fact(name, "FourD", half))
    return "<?xml version='1.0'?><xbrli:xbrl>" + "".join(body) + "</xbrli:xbrl>"


DIXON_Q2 = {
    "RevenueFromOperations": (217936400000, 373413000000),
    "OtherIncome": (687300000, 5970200000),
    "FinanceCosts": (259500000, 500700000),
    "DepreciationDepletionAndAmortisationExpense": (1100600000, 2170100000),
    "ProfitBeforeExceptionalItemsAndTax": (5295400000, 13898800000),
    "ProfitBeforeTax": (5295400000, 13898800000),
    "TaxExpense": (1214800000, 2726300000),
    "ProfitLossForPeriod": (4108700000, 11287000000),
    "ProfitOrLossAttributableToOwnersOfParent": (3436600000, 10070800000),
    "ProfitOrLossAttributableToNonControllingInterests": (672100000, 1216200000),
    "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations": (67.44, 185.27),
}


def test_parse_results_takes_the_quarter_not_the_half_year_or_a_segment():
    r = exchange.parse_results_xbrl(results_xml(DIXON_Q2))
    assert r["label"] == "Q2FY27" and r["nature"] == "Consolidated" and not r["is_bank"]
    assert r["revenue"] / CR == pytest.approx(21793.64)
    assert r["pat"] / CR == pytest.approx(343.66) and r["pat_total"] / CR == pytest.approx(410.87)
    assert r["minority"] / CR == pytest.approx(67.21) and r["eps_basic"] == 67.44
    assert r["exceptional"] == 0


def test_exceptional_items_come_from_the_pbt_difference():
    facts = dict(DIXON_Q2, ProfitBeforeTax=(5295400000 - 345480000, 1))  # a Rs 34.55 cr charge
    r = exchange.parse_results_xbrl(results_xml(facts))
    assert r["exceptional"] / CR == pytest.approx(-34.548)


def test_bank_filing_maps_to_total_income_and_nii():
    facts = {"InterestEarned": (951316300000, 1), "InterestExpended": (506674300000, 1),
             "Income": (1293586900000, 1), "OtherIncome": (342270600000, 1),
             "ProfitLossFromOrdinaryActivitiesBeforeTax": (278254800000, 1), "TaxExpense": (71254500000, 1),
             "ProfitLossForThePeriod": (207000300000, 1),
             "ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates": (207000300000, 1)}
    r = exchange.parse_results_xbrl(results_xml(facts))
    assert r["is_bank"] and r["pat"] / CR == pytest.approx(20700.03)
    rows = exchange.to_yahoo_rows(r)
    assert rows["Net Interest Income"] / CR == pytest.approx(44464.20)
    assert rows["Total Revenue"] / CR == pytest.approx(129358.69)
    assert "Other Non Operating Income Expenses" not in rows  # fee income is not a one-off for a bank


def test_unreadable_xbrl_returns_none():
    assert exchange.parse_results_xbrl("<xbrli:xbrl></xbrli:xbrl>") is None


def shp_xml(pledge=None):
    body = [_ctx("P", instant="2026-09-30", member="in-bse-shp:ShareholdingOfPromoterAndPromoterGroupMember"),
            _ctx("PUB", instant="2026-09-30", member="in-bse-shp:PublicShareholdingMember"),
            _ctx("FII", instant="2026-09-30", member="in-bse-shp:InstitutionsForeignMember"),
            _ctx("DII", instant="2026-09-30", member="in-bse-shp:InstitutionsDomesticMember"),
            _ctx("MF", instant="2026-09-30", member="in-bse-shp:MutualFundsOrUTIMember"),
            _ctx("ALL", instant="2026-09-30")]
    for c, v in (("P", "0.285"), ("PUB", "0.715"), ("FII", "0.1896"), ("DII", "0.2871"), ("MF", "0.1926")):
        body.append(_fact("ShareholdingAsAPercentageOfTotalNumberOfShares", c, v, "in-bse-shp"))
    body.append(_fact("WhetherAnySharesHeldByPromotersAreEncumberedUnderPledged", "ALL",
                      "true" if pledge else "false", "in-bse-shp"))
    if pledge:
        body.append(_fact("EncumberedShareUnderPledgedAsPercentageOfTotalNumberOfShares", "P", pledge, "in-bse-shp"))
    return "<xbrli:xbrl>" + "".join(body) + "</xbrli:xbrl>"


def test_shareholding_split_and_pledge():
    s = exchange.parse_shareholding_xbrl(shp_xml())
    assert s["promoter"] == pytest.approx(28.5) and s["fii"] == pytest.approx(18.96)
    assert s["dii"] == pytest.approx(28.71) and s["mutual_funds"] == pytest.approx(19.26)
    assert s["public_other"] == pytest.approx(71.5 - 18.96 - 28.71)
    assert s["pledged_pct_of_promoter"] == 0.0 and s["pledge_reported"] is False
    p = exchange.parse_shareholding_xbrl(shp_xml(pledge="0.7299"))
    assert p["pledged_pct_of_promoter"] == pytest.approx(72.99) and p["pledge_reported"] is True


def test_results_meetings_and_rescheduling():
    rows = [{"bm_date": "30-Oct-2026", "bm_purpose": "Financial Results", "bm_desc": ""},
            {"bm_date": "31-Jul-2026", "bm_purpose": "Financial Results", "bm_desc": ""},
            {"bm_date": "15-Oct-2026", "bm_purpose": "Fund Raising", "bm_desc": "Issue of debentures"}]
    m = exchange.results_meetings(rows, TODAY)
    assert m["last"]["date"] == "30-Oct-2026" and m["last"]["quarter"] == "Q2FY27"
    assert not m["last"]["rescheduled"] and m["next"] is None
    # Tata Steel, October 2026: 27-Oct meeting re-scheduled to 07-Nov.
    rows = [{"bm_date": "27-Oct-2026", "bm_purpose": "Financial Results/Other business matters", "bm_desc": ""},
            {"bm_date": "07-Nov-2026", "bm_purpose": "Board Meeting Intimation",
             "bm_desc": "to consider and approve the Quarterly Audited Financial results"}]
    m = exchange.results_meetings(rows, TODAY)
    assert m["last"]["rescheduled"] and m["next"] == {"date": "07-Nov-2026", "quarter": "Q2FY27"}


def test_quarter_end_before():
    assert exchange.quarter_end_before(date(2026, 10, 1)) == date(2026, 9, 30)
    assert exchange.quarter_end_before(date(2026, 9, 30)) == date(2026, 6, 30)
    assert exchange.quarter_end_before(date(2026, 5, 12)) == date(2026, 3, 31)


def test_pick_filings_prefers_consolidated_and_latest_revision():
    rows = [
        {"qe_Date": "30-SEP-2026", "consolidated": "Standalone", "broadcast_Date": "30-Oct-2026 20:21:13",
         "type": "Integrated Filing- Financials", "xbrl": "s.xml"},
        {"qe_Date": "30-SEP-2026", "consolidated": "Consolidated", "broadcast_Date": "30-Oct-2026 20:22:02",
         "type": "Integrated Filing- Financials", "xbrl": "c1.xml", "type_Sub": "Original"},
        {"qe_Date": "30-SEP-2026", "consolidated": "Consolidated", "broadcast_Date": "02-Nov-2026 10:00:00",
         "type": "Integrated Filing- Financials", "xbrl": "c2.xml", "type_Sub": "Revised"},
        {"qe_Date": "30-JUN-2026", "consolidated": "Consolidated", "broadcast_Date": "31-Jul-2026 18:00:00",
         "type": "Integrated Filing- Financials", "xbrl": "j.xml"},
    ]
    f = exchange.pick_filings(rows)
    assert [x["label"] for x in f] == ["Q2FY27", "Q1FY27"]
    assert f[0]["xbrl"] == "c2.xml" and f[0]["revised"] and f[0]["nature"] == "Consolidated"


def _rec(label, end, revenue, pat, other_income=10.0):
    return {"label": label, "period_end": end, "nature": "Consolidated", "is_bank": False,
            "revenue": revenue * CR, "other_income": other_income * CR, "finance_costs": 2 * CR,
            "depreciation": 5 * CR, "exceptional": 0.0, "pbt": (pat * 1.33) * CR, "tax": (pat * 0.33) * CR,
            "pat_total": pat * CR, "pat": pat * CR, "minority": 0.0}


def test_merge_adds_newer_quarters_replaces_overlaps_and_feeds_fundamentals(synthetic_raw):
    recs = [_rec("Q1FY27", "2026-06-30", 361, 36), _rec("Q2FY27", "2026-09-30", 380, 40)]
    assert exchange.cross_check(synthetic_raw.q_income, recs) == []  # 361 vs 360 is within 2%
    recs_off = [_rec("Q1FY27", "2026-06-30", 400, 36)]
    assert "Q1FY27 revenue" in exchange.cross_check(synthetic_raw.q_income, recs_off)[0]
    assert exchange.cross_check(synthetic_raw.q_income, recs_off, fx=88.0) == []  # other currency: skipped

    df, sources = exchange.merge_quarters(synthetic_raw.q_income, recs)
    assert sources == {"2026-06-30": "NSE filing (consolidated)", "2026-09-30": "NSE filing (consolidated)"}
    synthetic_raw.q_income, synthetic_raw.q_sources = df, sources
    qs = fundamentals.quarterly_table(synthetic_raw, 10 * CR)
    assert [q["label"] for q in qs] == ["Q2FY26", "Q3FY26", "Q4FY26", "Q1FY27", "Q2FY27"]
    last = qs[-1]
    assert last["source"].startswith("NSE") and qs[0]["source"] == "Yahoo Finance"
    # EBITDA excludes other income: PBT + finance costs + depreciation - other income.
    assert last["ebitda"] / CR == pytest.approx(40 * 1.33 + 2 + 5 - 10)
    assert fundamentals.quarter_changes(qs)["year_ago"] == "Q2FY26"


def _exch(**kw):
    e = exchange.ExchangeData(source="NSE")
    for k, v in kw.items():
        setattr(e, k, v)
    return e


def _fund(last_q="2026-06-30"):
    return {"quarters": [{"label": "Q1FY27", "date": last_q}], "annual": [{"label": "FY26", "date": "2026-03-31"}],
            "quarter_changes": {}}


class _Raw:
    failed: list = []


def test_filing_newer_than_data_makes_rating_provisional():
    e = _exch(filings=[{"period_end": "2026-09-30", "label": "Q2FY27", "filed": "30-Oct-2026",
                        "nature": "Consolidated"}],
              meetings={"last": {"date": "30-Oct-2026", "quarter_end": "2026-09-30", "quarter": "Q2FY27",
                                 "rescheduled": False}, "next": None})
    reasons, warns, fresh = pipeline.data_checks(_Raw(), _fund(), TODAY, e)
    assert any("Q2FY27 results were filed with NSE on 30-Oct-2026" in r for r in reasons)
    assert len([r for r in reasons if "Q2FY27" in r]) == 1  # the meeting does not add a second reason


def test_meeting_held_without_a_filing_makes_rating_provisional():
    e = _exch(filings=[{"period_end": "2026-06-30", "label": "Q1FY27", "filed": "31-Jul-2026",
                        "nature": "Consolidated"}],
              meetings={"last": {"date": "31-Oct-2026", "quarter_end": "2026-09-30", "quarter": "Q2FY27",
                                 "rescheduled": False}, "next": None})
    reasons, _, _ = pipeline.data_checks(_Raw(), _fund(), TODAY, e)
    assert any("board meeting on 31-Oct-2026 covered Q2FY27" in r for r in reasons)


def test_rescheduled_meeting_confirms_freshness_without_web_search():
    e = _exch(filings=[{"period_end": "2026-06-30", "label": "Q1FY27", "filed": "30-Jul-2026",
                        "nature": "Consolidated"}],
              meetings={"last": {"date": "27-Oct-2026", "quarter_end": "2026-09-30", "quarter": "Q2FY27",
                                 "rescheduled": True}, "next": {"date": "07-Nov-2026", "quarter": "Q2FY27"}})
    reasons, warns, fresh = pipeline.data_checks(_Raw(), _fund(), TODAY, e)
    assert reasons == []
    assert fresh["check_required"] is False and fresh["confirmed_by_exchange"]
    assert any("Q2FY27 results are not yet published" in w and "07-Nov-2026" in w for w in warns)


def test_without_exchange_the_freshness_check_still_asks_for_a_search():
    _, warns, fresh = pipeline.data_checks(_Raw(), _fund(), TODAY, exchange.ExchangeData())
    assert fresh["check_required"] and not fresh.get("confirmed_by_exchange")
    assert any("may already be published" in w for w in warns)


class _FailingClient:
    calls = 0

    def get(self, *a, **k):
        _FailingClient.calls += 1
        raise RuntimeError("HTTP 403")


def test_fetch_never_raises_when_the_exchanges_block_us():
    e = exchange.fetch("DIXON.NS", TODAY, client=_FailingClient())
    assert not e.checked and e.quarters == [] and e.shareholding is None
    assert "NSE board meetings" in e.failed and any("not available" in w for w in e.warnings)


def test_switched_off_by_environment(monkeypatch):
    monkeypatch.setenv("BSA_NO_EXCHANGE", "1")
    _FailingClient.calls = 0
    e = exchange.fetch("DIXON.NS", TODAY, client=_FailingClient())
    assert _FailingClient.calls == 0 and not e.checked


def test_pipeline_uses_filed_quarter_and_exchange_shareholding(monkeypatch, synthetic_raw, tmp_path):
    e = _exch(filings=[{"period_end": "2026-09-30", "label": "Q2FY27", "filed": "30-Oct-2026",
                        "nature": "Consolidated", "revised": False, "xbrl": "https://example.com/q2.xml"}],
              quarters=[_rec("Q2FY27", "2026-09-30", 380, 40)],
              meetings={"last": {"date": "30-Oct-2026", "quarter_end": "2026-09-30", "quarter": "Q2FY27",
                                 "rescheduled": False}, "next": None},
              shareholding=exchange.parse_shareholding_xbrl(shp_xml(pledge="0.15")) | {
                  "as_of": "30-Sep-2026", "source": "NSE shareholding pattern",
                  "promoter_trend": [{"date": "30-Sep-2025", "promoter": 31.0},
                                     {"date": "30-Sep-2026", "promoter": 28.5}]},
              links=[{"title": "NSE results filing, Q2FY27 (consolidated)", "url": "https://example.com/q2.xml",
                      "date": "30-Oct-2026"}])
    monkeypatch.setattr(data, "resolve", lambda q: {"symbol": "DEMO.NS", "exchange": "NSE", "matched_by": "test"})
    monkeypatch.setattr(data, "fetch", lambda s, x: synthetic_raw)
    monkeypatch.setattr(data, "fetch_peers", lambda bases: [])
    monkeypatch.setattr(data, "fetch_sector_index", lambda t: None)
    monkeypatch.setattr(exchange, "fetch", lambda symbol, today: e)
    a = pipeline.run("demo", str(tmp_path), make_pdf=False, today=TODAY)
    assert a["fundamentals"]["quarter_changes"]["latest"] == "Q2FY27"
    assert not a["rating"].get("provisional")  # the filed quarter is in the data
    assert a["data_quality"]["freshness"]["missing"] == []
    assert a["holdings"]["promoter"] == pytest.approx(28.5)
    concerns = " ".join(a["narrative"]["concerns"])
    assert "pledged" in concerns and "Promoters are selling" in concerns
    html = open(a["files"]["html"], encoding="utf-8").read()
    assert "Promoter and group" in html and "NSE results filings (consolidated XBRL)" in html
    assert "Exchange filings used by the model" in html
    d = pipeline.digest(a)
    assert "## Exchange filings (NSE)" in d and "| NSE filing (consolidated) |" in d
