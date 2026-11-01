"""Full pipeline on the synthetic company with the network layer replaced by fixtures."""

import json
from datetime import date

import pytest

from bsa import data, exchange, pipeline

# The synthetic data ends at Q1FY27 (30 June 2026); 1 August 2026 needs no newer quarter.
TODAY = date(2026, 8, 1)


@pytest.fixture
def offline(monkeypatch, synthetic_raw):
    monkeypatch.setattr(data, "resolve", lambda q: {"symbol": "DEMO.NS", "exchange": "NSE", "matched_by": "test"})
    monkeypatch.setattr(data, "fetch", lambda s, e: synthetic_raw)
    monkeypatch.setattr(data, "fetch_peers", lambda bases: [])
    monkeypatch.setattr(data, "fetch_sector_index", lambda t: None)
    monkeypatch.setattr(exchange, "fetch", lambda symbol, today: exchange.ExchangeData())


def test_run_writes_json_html_and_digest(offline, tmp_path):
    a = pipeline.run("demo", str(tmp_path), make_pdf=False, today=TODAY)
    assert a["rating"]["rating"] in ("BUY", "HOLD", "SELL")
    assert a["valuation"]["target"] and a["scorecard"]["composite"] is not None
    for key in ("json", "html"):
        assert (tmp_path / a["files"][key].split("/")[-1]).exists()
    html = (tmp_path / a["files"]["html"].split("/")[-1]).read_text()
    assert "Demo Industries Limited" in html and "Exhibit 1:" in html and "SEBI" in html
    assert "data:image/png;base64," in html
    saved = json.loads((tmp_path / a["files"]["json"].split("/")[-1]).read_text())
    assert saved["meta"]["nse_symbol"] == "DEMO"
    d = pipeline.digest(a)
    assert "## Rating:" in d and "## Valuation methods" in d and "## Scorecard" in d


def test_rerender_with_commentary(offline, tmp_path):
    a = pipeline.run("demo", str(tmp_path), make_pdf=False, today=TODAY)
    c = {"headline": "Steady compounder at a fair price", "summary": "Test summary.",
         "highlights": ["Revenue CAGR of 10.0% over FY23 to FY26."], "risks": ["Test risk."],
         "sources": [{"title": "Annual report FY26", "url": "https://example.com/ar", "date": "01-Jun-2026"}]}
    b = pipeline.rerender(a["files"]["json"], c, make_pdf=False)
    html = open(b["files"]["html"], encoding="utf-8").read()
    assert "Steady compounder at a fair price" in html and "Analyst view" in html and "Annual report FY26" in html
    assert b["rating"] == a["rating"] and b["valuation"]["target"] == a["valuation"]["target"]


def test_commentary_validation():
    with pytest.raises(ValueError):
        pipeline.validate_commentary({"target_price": 500})
    with pytest.raises(ValueError):
        pipeline.validate_commentary({"risks": "not a list"})
    assert pipeline.validate_commentary({"summary": "ok"}) == {"summary": "ok"}


def test_consistency_checks_flag_gaps():
    info = {"bookValue": 100.0, "returnOnEquity": 0.20}
    fund = {"annual": [{"label": "FY26", "bvps_adj": 140.0, "roe": 12.0}]}
    msgs = pipeline.consistency_checks(info, fund)
    assert len(msgs) == 2
