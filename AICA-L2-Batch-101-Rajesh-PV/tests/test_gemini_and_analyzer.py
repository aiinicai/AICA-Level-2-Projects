import threading

import httpx
import pytest
from conftest import SAMPLE_REPORT
from google.genai import errors as genai_errors

from judgment_analyzer import gemini_client as gc
from judgment_analyzer.analyzer import Analyzer
from judgment_analyzer.config import AppSettings
from judgment_analyzer.pdf_processor import CancelledError, validate_pdf


def api_error(code, status, message):
    return genai_errors.APIError(code, {"error": {"code": code, "status": status, "message": message}})


@pytest.mark.parametrize("err,expected", [
    (api_error(400, "INVALID_ARGUMENT", "API key not valid. Please pass a valid API key."), gc.InvalidApiKeyError),
    (api_error(403, "PERMISSION_DENIED", "Permission denied"), gc.PermissionDeniedError),
    (api_error(404, "NOT_FOUND", "models/x is not found"), gc.ModelNotFoundError),
    (api_error(429, "RESOURCE_EXHAUSTED", "Quota exceeded"), gc.RateLimitError),
    (api_error(400, "INVALID_ARGUMENT", "The input token count exceeds the maximum"), gc.TokenLimitError),
    (api_error(503, "UNAVAILABLE", "overloaded"), gc.ServiceUnavailableError),
    (api_error(400, "INVALID_ARGUMENT", "something else"), gc.BadRequestError),
    (httpx.ConnectError("boom"), gc.NetworkError),
    (httpx.ReadTimeout("slow"), gc.NetworkError),
    (RuntimeError("weird"), gc.GeminiError),
])
def test_translate_exception(err, expected):
    translated = gc.translate_exception(err, "gemini-x")
    assert type(translated) is expected
    assert str(translated)


def make_client(fake_sdk, responses=None, errors=None, retries=2):
    return gc.GeminiClient("A" * 39, "gemini-3.8-flash", max_retries=retries,
                           client=fake_sdk(responses, errors))


def test_client_requires_key():
    with pytest.raises(gc.InvalidApiKeyError):
        gc.GeminiClient("", "m")


def test_generate_success_and_config(fake_sdk):
    client = make_client(fake_sdk, ["hello"])
    result = client.generate("prompt", "system")
    assert result.text == "hello" and not result.truncated
    call = client._client.models.calls[0]
    assert call["model"] == "gemini-3.8-flash"
    assert call["config"].system_instruction == "system"


def test_generate_retries_transient(fake_sdk, monkeypatch):
    monkeypatch.setattr(gc, "_sleep_with_cancel", lambda s, e: None)
    statuses = []
    client = make_client(fake_sdk, ["ok"], [api_error(429, "RESOURCE_EXHAUSTED", "quota"), None])
    assert client.generate("p", "s", on_status=statuses.append).text == "ok"
    assert len(statuses) == 1


def test_generate_gives_up_after_retries(fake_sdk, monkeypatch):
    monkeypatch.setattr(gc, "_sleep_with_cancel", lambda s, e: None)
    errs = [api_error(503, "UNAVAILABLE", "x")] * 5
    with pytest.raises(gc.ServiceUnavailableError):
        make_client(fake_sdk, errors=errs, retries=2).generate("p", "s")


def test_generate_does_not_retry_invalid_key(fake_sdk):
    client = make_client(fake_sdk, errors=[api_error(400, "INVALID_ARGUMENT", "API key not valid")])
    with pytest.raises(gc.InvalidApiKeyError):
        client.generate("p", "s")
    assert len(client._client.models.calls) == 1


def test_empty_and_blocked_responses():
    from types import SimpleNamespace as NS
    with pytest.raises(gc.ContentBlockedError):
        gc.GeminiClient._read_response(NS(prompt_feedback=NS(block_reason="SAFETY"), candidates=[], text=None))
    with pytest.raises(gc.EmptyResponseError):
        gc.GeminiClient._read_response(NS(prompt_feedback=None, candidates=[NS(finish_reason="STOP")], text=""))
    r = gc.GeminiClient._read_response(NS(prompt_feedback=None, candidates=[NS(finish_reason="MAX_TOKENS")],
                                          text="partial", usage_metadata=None))
    assert r.truncated


def test_cancel_during_generate(fake_sdk):
    event = threading.Event()
    event.set()
    with pytest.raises(CancelledError):
        make_client(fake_sdk).generate("p", "s", cancel_event=event)


def test_test_connection_and_list_models(fake_sdk):
    client = make_client(fake_sdk)
    assert "valid" in client.test_connection()
    assert client.list_text_models() == ["gemini-3.8-flash"]


# ------------------------------------------------------------- analyzer ---
def test_single_pass_analysis(text_pdf, fake_sdk):
    client = make_client(fake_sdk, [SAMPLE_REPORT])
    progress = []
    result = Analyzer(AppSettings(ocr_mode="Off"), client, progress=lambda f, m: progress.append(f)).run(
        validate_pdf(text_pdf))
    assert result.mode == "Single pass"
    assert result.report.missing_sections == []
    assert progress[-1] == 1.0
    prompt = client._client.models.calls[0]["contents"]
    assert "[Page 1]" in prompt and "## 14. Points for Consideration" in prompt


def test_sectioned_analysis_includes_excerpts(long_text_pdf, fake_sdk):
    settings = AppSettings(ocr_mode="Off", force_sectioned=True, chunk_max_chars=10_000, chunk_overlap_chars=500,
                           consistency_check=False)
    client = make_client(fake_sdk)
    models = client._client.models
    original = models.generate_content

    def routed(model, contents, config=None):
        # Section prompts get notes back; the consolidation prompt gets the full report.
        final = "final consolidated analysis" in contents
        models.responses = [SAMPLE_REPORT if final else "### Facts\n- A note (p. 1)"]
        return original(model, contents, config)

    models.generate_content = routed
    result = Analyzer(settings, client).run(validate_pdf(long_text_pdf))
    assert result.sections_processed > 1
    assert result.mode.startswith("Section-by-section")
    final_prompt = [c["contents"] for c in models.calls if "final consolidated analysis" in c["contents"]][-1]
    assert "OPENING EXCERPT" in final_prompt and "[Page 1]" in final_prompt
    assert final_prompt.count("=== SECTION") == result.sections_processed
    assert result.report.missing_sections == []


def test_token_limit_falls_back_to_sections(text_pdf, fake_sdk):
    client = make_client(fake_sdk, responses=["notes", SAMPLE_REPORT],
                         errors=[api_error(400, "INVALID_ARGUMENT", "input token count exceeds limit")])
    result = Analyzer(AppSettings(ocr_mode="Off"), client).run(validate_pdf(text_pdf))
    assert result.mode.startswith("Section-by-section")
    assert any("section by section" in w for w in result.warnings)


def test_analyzer_cancel(text_pdf, fake_sdk):
    event = threading.Event()
    event.set()
    with pytest.raises(CancelledError):
        Analyzer(AppSettings(ocr_mode="Off"), make_client(fake_sdk), cancel_event=event).run(validate_pdf(text_pdf))


def quota_error(quota_id, value="250000", delay="31s"):
    return genai_errors.APIError(429, {"error": {
        "code": 429, "status": "RESOURCE_EXHAUSTED", "message": "You exceeded your current quota.",
        "details": [
            {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [{
                "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                "quotaId": quota_id, "quotaValue": value}]},
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": delay},
        ]}})


@pytest.mark.parametrize("quota_id,value,kind,retryable", [
    ("GenerateContentInputTokensPerModelPerMinute-FreeTier", "250000", "minute", True),
    ("GenerateRequestsPerMinutePerProjectPerModel-FreeTier", "10", "minute", True),
    ("GenerateRequestsPerDayPerProjectPerModel-FreeTier", "250", "daily", False),
    ("GenerateRequestsPerMinutePerProjectPerModel-FreeTier", "0", "no_free_quota", False),
])
def test_rate_limit_classification(quota_id, value, kind, retryable):
    err = gc.translate_exception(quota_error(quota_id, value), "gemini-3.8-flash")
    assert isinstance(err, gc.RateLimitError)
    assert err.kind == kind and err.retryable is retryable
    if kind == "minute":
        assert err.retry_after == 31.0
    if kind == "no_free_quota":
        assert "another model" in str(err)


def test_daily_quota_not_retried(fake_sdk):
    client = make_client(fake_sdk, errors=[quota_error("GenerateRequestsPerDayPerProjectPerModel-FreeTier", "250")])
    with pytest.raises(gc.RateLimitError, match="daily"):
        client.generate("p", "s")
    assert len(client._client.models.calls) == 1


def test_minute_quota_uses_retry_delay(fake_sdk, monkeypatch):
    waits = []
    monkeypatch.setattr(gc, "_sleep_with_cancel", lambda s, e: waits.append(s))
    client = make_client(fake_sdk, ["ok"], [quota_error("GenerateRequestsPerMinutePerProjectPerModel-FreeTier"), None])
    assert client.generate("p", "s").text == "ok"
    assert 32 <= waits[0] <= 33
