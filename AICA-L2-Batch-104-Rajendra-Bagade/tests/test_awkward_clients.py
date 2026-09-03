"""
Clients that are not the happy path.

Every case here crashed the application with an HTTP 500 before it was
fixed. The browser reported only "Unexpected token 'I', "Internal S"... is
not valid JSON", because FastAPI's default 500 body is plain text and the
front end tried to parse it as JSON — so the real fault was invisible.

A real engagement is far more likely to look like one of these than like
the polished sample client.
"""

from __future__ import annotations

from datetime import date

import pytest

from auditlens.caro import build_checklist, check_applicability
from auditlens.pipeline import EngagementInputs, run_engagement


def write(tmp_path, name: str, body: str):
    path = tmp_path / name
    path.write_text(body)
    return path


def inputs(**kw) -> EngagementInputs:
    base = dict(
        client_name="Probe Private Limited",
        financial_year="2024-25",
        year_end=date(2025, 3, 31),
    )
    base.update(kw)
    return EngagementInputs(**base)


# --------------------------------------------------------------------------
# The crash itself
# --------------------------------------------------------------------------

def test_no_current_liabilities_does_not_crash_caro():
    """The current ratio is not computable without current liabilities.
    Clause (xix) must still be answerable."""
    checklist = build_checklist(
        check_applicability(company_class="private"), facts={"current_ratio": None}
    )
    clause = next(c for c in checklist.clauses if c.number == "(xix)")
    assert not clause.data_available
    assert "could not be computed" in clause.evidence
    assert "without relying on the current ratio" in clause.suggested_status


def test_company_with_no_current_liabilities(tmp_path):
    tb = write(tmp_path, "tb.csv",
        "account_code,account_name,debit,credit\n"
        "1001,Equity share capital,0,1000000\n"
        "2281,Cash in hand,700000,0\n"
        "3001,Sale of manufactured goods,0,200000\n"
        "4401,Power and fuel,500000,0\n")
    result = run_engagement(inputs=inputs(), trial_balance_path=tb)
    assert result.caro is not None
    current_ratio = next(r for r in result.ratios.results if r.key == "current_ratio")
    assert current_ratio.value is None


def test_loss_making_company(tmp_path):
    """A loss must not be used as a materiality benchmark."""
    tb = write(tmp_path, "tb.csv",
        "account_code,account_name,debit,credit\n"
        "1001,Equity share capital,0,2000000\n"
        "1331,Trade payables,0,500000\n"
        "2281,Cash in hand,900000,0\n"
        "3001,Sale of manufactured goods,0,1000000\n"
        "4401,Power and fuel,2600000,0\n")
    result = run_engagement(inputs=inputs(), trial_balance_path=tb)
    assert result.figures.profit_before_tax < 0
    assert result.materiality.benchmark == "revenue"
    assert "loss" in result.materiality_rationale
    assert result.materiality.overall > 0


def test_dormant_company_reports_rather_than_crashes(tmp_path):
    """No revenue and no profit: materiality computes to zero. The engine
    must say so instead of raising."""
    tb = write(tmp_path, "tb.csv",
        "account_code,account_name,debit,credit\n"
        "1001,Equity share capital,0,1000000\n"
        "2281,Cash in hand,1000000,0\n")
    gl = write(tmp_path, "gl.csv",
        "entry_id,posting_date,account_code,account_name,debit,credit,narration,posted_by\n"
        "JV1,01-04-2024,2281,Cash in hand,1000000,0,Share capital received,priya\n"
        "JV1,01-04-2024,1001,Equity share capital,0,1000000,Share capital received,priya\n")
    result = run_engagement(
        inputs=inputs(), trial_balance_path=tb, general_ledger_path=gl
    )
    assert result.materiality.overall == 0
    assert result.sample is None
    assert "benchmark" in result.sampling_note
    assert result.headlines()["sampling_note"] == result.sampling_note


def test_trial_balance_alone_is_enough(tmp_path):
    """No comparative and no general ledger. Everything that needs them is
    omitted; nothing raises."""
    tb = write(tmp_path, "tb.csv",
        "account_code,account_name,debit,credit\n"
        "1001,Equity share capital,0,1000000\n"
        "1331,Trade payables,0,300000\n"
        "2251,Trade receivables,800000,0\n"
        "2281,Cash in hand,700000,0\n"
        "3001,Sale of manufactured goods,0,900000\n"
        "4401,Power and fuel,700000,0\n")
    result = run_engagement(inputs=inputs(), trial_balance_path=tb)
    assert result.je_analysis is None
    assert result.sample is None
    assert result.prior_figures is None
    assert len(result.ratios.results) == 11
    assert all(r.variance is None for r in result.ratios.results)
    assert len(result.caro.clauses) == 21


def test_every_ratio_survives_a_sparse_trial_balance(tmp_path):
    """Most ratios are not computable here. None of them may raise."""
    tb = write(tmp_path, "tb.csv",
        "account_code,account_name,debit,credit\n"
        "1001,Equity share capital,0,500000\n"
        "2281,Cash in hand,500000,0\n")
    result = run_engagement(inputs=inputs(), trial_balance_path=tb)
    for r in result.ratios.results:
        assert r.formatted()          # never raises
        assert not r.requires_explanation


# --------------------------------------------------------------------------
# The API must never answer with plain text
# --------------------------------------------------------------------------

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from auditlens.api import app

    return TestClient(app, raise_server_exceptions=False)


def post_tb(client, tmp_path, body: str):
    path = write(tmp_path, "tb.csv", body)
    with path.open("rb") as fh:
        return client.post(
            "/api/engagements",
            data={
                "client_name": "Probe Private Limited",
                "financial_year": "2024-25",
                "year_end": "2025-03-31",
                "use_samples": "false",
            },
            files={"trial_balance": ("tb.csv", fh, "text/csv")},
        )


def test_the_crashing_trial_balance_now_succeeds(client, tmp_path):
    response = post_tb(client, tmp_path,
        "account_code,account_name,debit,credit\n"
        "1001,Equity share capital,0,1000000\n"
        "2281,Cash in hand,700000,0\n"
        "3001,Sale of manufactured goods,0,200000\n"
        "4401,Power and fuel,500000,0\n")
    assert response.status_code == 200
    assert response.json()["headlines"]["client"] == "Probe Private Limited"


def test_a_bad_file_gives_a_readable_message_not_a_500(client, tmp_path):
    response = post_tb(client, tmp_path, "wrong,columns\n1,2\n")
    assert response.status_code == 422
    body = response.json()
    assert "missing required column" in body["detail"]
    assert "account_name" in body["detail"]


def test_a_bad_date_is_rejected_clearly(client, tmp_path):
    path = write(tmp_path, "tb.csv",
        "account_code,account_name,debit,credit\n1001,Share capital,0,100\n2281,Cash,100,0\n")
    with path.open("rb") as fh:
        response = client.post(
            "/api/engagements",
            data={
                "client_name": "X", "financial_year": "2024-25",
                "year_end": "31-03-2025", "use_samples": "false",
            },
            files={"trial_balance": ("tb.csv", fh, "text/csv")},
        )
    assert response.status_code == 400
    assert "YYYY-MM-DD" in response.json()["detail"]


def test_a_missing_trial_balance_is_rejected_clearly(client):
    response = client.post(
        "/api/engagements",
        data={
            "client_name": "X", "financial_year": "2024-25",
            "year_end": "2025-03-31", "use_samples": "false",
        },
    )
    assert response.status_code == 400
    assert "trial balance is required" in response.json()["detail"]


def test_an_unknown_engagement_returns_json(client):
    response = client.get("/api/engagements/doesnotexist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Engagement not found."


def test_every_error_response_is_json(client, tmp_path):
    """The regression test for 'Unexpected token I'. Whatever goes wrong,
    the body must parse as JSON and carry a usable message."""
    responses = [
        post_tb(client, tmp_path, "wrong,columns\n1,2\n"),
        client.get("/api/engagements/nope"),
        client.post("/api/engagements/nope/drafts"),
    ]
    for response in responses:
        assert response.headers["content-type"].startswith("application/json"), (
            f"{response.request.url} answered with "
            f"{response.headers['content-type']} — the browser cannot parse that"
        )
        body = response.json()
        assert isinstance(body.get("detail"), str) and body["detail"]
