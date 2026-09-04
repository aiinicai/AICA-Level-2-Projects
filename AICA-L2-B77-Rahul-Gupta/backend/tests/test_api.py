"""API smoke tests against an in-memory database with seeded demo data."""
import os
import tempfile

import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture(scope="module")
def client():
    seed(verbose=False)
    with TestClient(app) as c:
        yield c


def _abc_case(client) -> dict:
    cases = client.get("/api/valuations").json()
    return next(c for c in cases if c["company_name"] == "ABC Food Pvt. Ltd.")


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_dashboard(client):
    d = client.get("/api/dashboard").json()
    assert d["total_cases"] == 5
    assert d["avg_valuation"] > 0
    assert d["recent"]


def test_case_detail_and_readiness(client):
    case = _abc_case(client)
    detail = client.get(f"/api/valuations/{case['id']}").json()
    assert detail["financials_locked"] is True
    assert detail["readiness"]["score"] > 60


def test_financials_endpoint(client):
    case = _abc_case(client)
    fin = client.get(f"/api/valuations/{case['id']}/financials").json()
    assert fin["locked"] is True
    assert fin["periods"] == ["FY2022-23", "FY2023-24", "FY2024-25"]
    assert fin["counts"]["total"] > 80
    assert fin["validation"]["failed"] == 0


def test_valuation_run_reproducible(client):
    case = _abc_case(client)
    v = client.get(f"/api/valuations/{case['id']}/valuation").json()
    run = v["run"]
    assert run["enterprise_value"] > 0
    assert run["range_low"] <= run["central_estimate"] <= run["range_high"]
    assert set(run["methods"].keys()) == {"dcf", "market_multiple", "adjusted_nav"}
    # recalculate → same result from same stored inputs
    r2 = client.post(f"/api/valuations/{case['id']}/calculate").json()
    assert r2["enterprise_value"] == pytest.approx(run["enterprise_value"])


def test_simulation_no_ai_and_wacc_effect(client):
    case = _abc_case(client)
    base = client.post(f"/api/valuations/{case['id']}/simulate",
                       json={"overrides": {}}).json()
    up = client.post(f"/api/valuations/{case['id']}/simulate",
                     json={"overrides": {"wacc": 0.16}}).json()
    assert up["enterprise_value"] < base["enterprise_value"]
    assert up["vs_current_pct"] is not None
    assert "tornado" in up and "scenarios" in up


def test_interview_state_and_flow(client):
    case = _abc_case(client)
    st = client.get(f"/api/valuations/{case['id']}/interview/state").json()
    assert st["session"] is not None
    assert st["session"]["answered"] >= 8
    # growth trigger produced the rule-based question
    trig = client.get(f"/api/valuations/{case['id']}/triggers").json()
    assert any(t["rule_code"] == "REV_GROWTH_HIGH" for t in trig)
    # answer remaining questions if active
    for _ in range(20):
        st = client.get(f"/api/valuations/{case['id']}/interview/state").json()
        q = st.get("current_question")
        if not q or st["session"]["status"] != "active":
            break
        value = q["options"][0] if q["options"] else "12"
        r = client.post(f"/api/valuations/{case['id']}/interview/answer",
                        json={"question_id": q["id"], "value": value}).json()
        assert "signal" in r


def test_assumptions_weight_validation(client):
    case = _abc_case(client)
    r = client.put(f"/api/valuations/{case['id']}/assumptions",
                   json={"values": {"weight_dcf": 0.9}})
    assert r.status_code == 422  # weights must total 100%
    r = client.put(f"/api/valuations/{case['id']}/assumptions",
                   json={"values": {"weight_dcf": 0.5, "weight_market_multiple": 0.3,
                                    "weight_adjusted_nav": 0.2}})
    assert r.status_code == 200


def test_insights(client):
    case = _abc_case(client)
    rows = client.get(f"/api/valuations/{case['id']}/insights").json()
    sections = {r["section"] for r in rows}
    assert "positive_driver" in sections
    assert "risk_flag" in sections


def test_report_generation(client):
    case = _abc_case(client)
    rep = client.post(f"/api/valuations/{case['id']}/reports",
                      json={"template": "comprehensive", "options": {"ai_narrative": False}})
    assert rep.status_code == 201, rep.text
    body = rep.json()
    assert body["has_html"]
    dl = client.get(f"/api/reports/{body['id']}/download?format=pdf")
    assert dl.status_code == 200


def test_settings_key_never_returned(client):
    s = client.get("/api/settings").json()
    assert "encrypted_key" not in s["ai"]
    assert s["ai"]["model_display"] == "Gemini 3.6 Flash"
