import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from daybook_auditor import ai_review as A  # noqa: E402
from fsbuilder.reviewer import llm as L  # noqa: E402

BUSY = "503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand.'}}"


class Resp:
    def __init__(self, text):
        self.text = text


class FakeClient:
    """models.generate_content that fails for the models named in `busy` and records every model asked."""
    def __init__(self, busy=(), reply="[]", error=BUSY):
        self.asked, self.busy, self.reply, self.error = [], set(busy), reply, error
        self.models = self

    def generate_content(self, model, contents, config):
        self.asked.append(model)
        if model in self.busy:
            raise RuntimeError(self.error)
        return Resp(self.reply)


@pytest.mark.parametrize("text", ["503 UNAVAILABLE", "504 DEADLINE_EXCEEDED", "429 RESOURCE_EXHAUSTED", "model is overloaded"])
def test_capacity_errors_are_recognised(text):
    assert L.is_busy(RuntimeError(text))


@pytest.mark.parametrize("text", ["400 INVALID_ARGUMENT api key not valid", "401 UNAUTHENTICATED", "404 NOT_FOUND"])
def test_other_errors_are_not_treated_as_busy(text):
    assert not L.is_busy(RuntimeError(text))


def test_a_busy_model_falls_through_to_the_next():
    first = L.FALLBACK_MODELS[0]
    c = FakeClient(busy={"gemini-flash-latest"}, reply="ok")
    text, used = L.generate_with_fallback(c, "gemini-flash-latest", "x", None, pause=lambda s: None)
    assert (text, used) == ("ok", first)
    assert c.asked == ["gemini-flash-latest", "gemini-flash-latest", first]                   # two tries, then the next model


def test_a_real_error_is_raised_at_once_without_trying_other_models():
    c = FakeClient(busy={"gemini-flash-latest"}, error="400 INVALID_ARGUMENT api key not valid")
    with pytest.raises(RuntimeError, match="api key"):
        L.generate_with_fallback(c, "gemini-flash-latest", "x", None, pause=lambda s: None)
    assert c.asked == ["gemini-flash-latest"]


def test_when_every_model_is_busy_the_last_error_is_raised():
    c = FakeClient(busy=set(L.models_to_try("gemini-flash-latest")))
    with pytest.raises(RuntimeError, match="503"):
        L.generate_with_fallback(c, "gemini-flash-latest", "x", None, pause=lambda s: None)
    assert len(c.asked) == 2 * len(L.models_to_try("gemini-flash-latest"))


def _vouchers():
    return pd.DataFrame([{"voucher_id": "V1", "date": pd.Timestamp(2025, 5, 1), "vch_type": "Payment", "vch_no": "7",
                          "dr_lines": [("Travelling & Conveyance", 148069.0)], "cr_lines": [("HDFC Bank", 148069.0)],
                          "narration": "Director's family visit to Singapore", "total": 148069.0}])


def _patch_client(monkeypatch, client, tmp_path=None):
    import google.genai as genai
    monkeypatch.setattr(A, "CACHE_PATH", (tmp_path or Path(__file__).parent / "_nocache") / "ai.json")
    monkeypatch.setattr(genai, "Client", lambda **kw: client)
    monkeypatch.setattr(L.time, "sleep", lambda s: None)


def test_day_book_review_survives_a_busy_model_and_says_so(monkeypatch, tmp_path):
    reply = json.dumps([{"voucher_id": "V1", "category": "Personal / non-business or director-related expense", "severity": "High",
                         "observation": "Director's family trip booked to travelling", "suggestion": "Reclassify"}])
    c = FakeClient(busy={"gemini-flash-latest"}, reply=reply)
    _patch_client(monkeypatch, c, tmp_path)
    found, errors = A.review_vouchers(_vouchers(), "key", "gemini-flash-latest")
    assert len(found) == 1 and found.iloc[0]["source"] == "AI" and found.iloc[0]["severity"] == "High"
    assert not any(e.startswith("Batch") for e in errors)                               # nothing failed
    assert any("was busy" in e and L.FALLBACK_MODELS[0] in e for e in errors)


def test_day_book_review_reports_a_batch_only_when_every_model_is_busy(monkeypatch, tmp_path):
    c = FakeClient(busy=set(L.models_to_try("gemini-flash-latest")))
    _patch_client(monkeypatch, c, tmp_path)
    found, errors = A.review_vouchers(_vouchers(), "key", "gemini-flash-latest")
    assert found.empty and errors and errors[0].startswith("Batch 1/1 failed") and "503" in errors[0]


QUOTA = ("429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota', 'details': "
         "[{'violations': [{'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier'}]}]}}")


def test_a_model_out_of_daily_quota_is_skipped_without_waiting():
    waits = []
    c = FakeClient(busy={"gemini-2.5-flash"}, reply="ok", error=QUOTA)
    text, used = L.generate_with_fallback(c, "gemini-2.5-flash", "x", None, pause=waits.append)
    assert used == L.FALLBACK_MODELS[0] and c.asked == ["gemini-2.5-flash", L.FALLBACK_MODELS[0]]   # one try, no retry
    assert waits == []                                                                           # and no sleeping


def test_the_default_is_a_named_model_not_the_moving_alias():
    assert L.DEFAULT_MODEL == "gemini-2.5-flash" and "latest" not in L.DEFAULT_MODEL


def test_an_identical_review_is_served_from_the_cache_and_uses_no_requests(monkeypatch, tmp_path):
    reply = json.dumps([{"voucher_id": "V1", "category": "Vague narration on a material entry", "severity": "Medium",
                         "observation": "vague", "suggestion": "ask"}])
    c = FakeClient(reply=reply)
    _patch_client(monkeypatch, c, tmp_path)
    first, _ = A.review_vouchers(_vouchers(), "key", "gemini-2.5-flash")
    again, notes = A.review_vouchers(_vouchers(), "key", "gemini-2.5-flash")
    assert len(first) == len(again) == 1
    assert len(c.asked) == 1                                                                     # the second run asked nothing
    assert any("reused from an earlier identical review" in n for n in notes)
