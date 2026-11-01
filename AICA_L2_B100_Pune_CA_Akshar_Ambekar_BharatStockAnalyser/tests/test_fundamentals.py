import pytest

from bsa import fundamentals as fd


@pytest.fixture
def fund(synthetic_raw):
    return fd.build(synthetic_raw, financial=False)


def test_annual_ratios_hand_checked(fund):
    a = fund["annual"]
    assert [r["label"] for r in a] == ["FY23", "FY24", "FY25", "FY26"]
    fy26 = a[-1]
    assert fy26["roe"] == pytest.approx(133.1 / 750 * 100)          # average equity (800 + 700) / 2
    assert fy26["roce"] == pytest.approx(226.2 / 1100 * 100)        # EBIT / (TA - CL)
    assert fy26["net_debt_equity"] == pytest.approx(0.125)          # (200 - 100) / 800
    assert fy26["interest_cover"] == pytest.approx(11.31)
    assert fy26["cfo_to_pat"] == pytest.approx(150 / 133.1)
    assert fy26["fcf"] == pytest.approx(100e7)                      # CFO + capex (negative)
    assert fy26["payout"] == pytest.approx(30 / 133.1 * 100)
    assert fy26["eps_adj"] == pytest.approx(13.31)
    assert fy26["bvps_adj"] == pytest.approx(80.0)
    assert fy26["ebitda_margin"] == pytest.approx(20.0)


def test_growth_and_quarters(fund):
    g = fund["growth"]
    assert g["years"] == 3 and g["from"] == "FY23" and g["to"] == "FY26"
    assert g["revenue"] == pytest.approx(10.0)
    assert g["pat"] == pytest.approx(10.0)
    qc = fund["quarter_changes"]
    assert qc["latest"] == "Q1FY27" and qc["year_ago"] == "Q1FY26"
    assert qc["qoq"]["revenue"] == pytest.approx(360 / 340 * 100 - 100)
    assert qc["yoy"]["revenue"] == pytest.approx(12.5)
    assert qc["yoy"]["pat"] == pytest.approx(12.5)
    assert fund["ttm_pat"] == pytest.approx((36 + 34 + 33.5 + 33) * 1e7)


def test_historical_pe_uses_fy_end_price(fund, synthetic_raw):
    fy26 = fund["annual"][-1]
    price = synthetic_raw.ohlc["Close"].asof(fy26["date"])
    assert fy26["pe"] == pytest.approx(price / 13.31)
    assert fund["pe_history_median"] is not None


def test_financial_detection(synthetic_raw):
    assert fd.is_financial({"sector": "Financial Services"}, synthetic_raw.income)
    assert not fd.is_financial({"sector": "Industrials"}, synthetic_raw.income)
