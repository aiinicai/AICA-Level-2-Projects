"""Secret-handling regression tests.

The Gemini key was once passed as a ?key= query parameter. httpx logs full
request URLs at INFO and embeds them in error messages, so the plaintext key
reached stdout logs, HTTP error responses and the AICallLog.error column.
These tests pin the fixes so the credential cannot drift back into a URL.
"""
from __future__ import annotations

import logging
import os
import stat

import httpx
import pytest

from app.services.ai.gemini import GeminiProvider
from app.utils import crypto

CANARY = "CANARY-not-a-real-key-0000"


def _sent_request(monkeypatch) -> dict:
    """Capture the request GeminiProvider would send, without doing any I/O."""
    captured: dict = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs.get("headers") or {}
        captured["params"] = kwargs.get("params")
        request = httpx.Request("POST", url, headers=captured["headers"],
                                params=captured["params"], json=kwargs.get("json"))
        captured["full_url"] = str(request.url)
        return httpx.Response(200, json={
            "candidates": [{"content": {"parts": [{"text": "{}"}]}}]
        }, request=request)

    monkeypatch.setattr(httpx, "post", fake_post)
    GeminiProvider(api_key=CANARY)._generate([{"text": "hi"}], "system")
    return captured


def test_api_key_is_sent_as_header_not_query_param(monkeypatch):
    sent = _sent_request(monkeypatch)
    assert sent["headers"].get("x-goog-api-key") == CANARY
    assert not sent["params"], "credential must not be passed as a query parameter"


def test_api_key_never_appears_in_the_request_url(monkeypatch):
    sent = _sent_request(monkeypatch)
    # httpx logs this URL at INFO and puts it in error messages
    assert CANARY not in sent["full_url"]
    assert "key=" not in sent["full_url"]


def test_transport_loggers_are_not_verbose():
    import app.main  # noqa: F401 — importing configures logging
    for name in ("httpx", "httpcore"):
        assert logging.getLogger(name).level >= logging.WARNING, (
            f"{name} at INFO would log full request URLs"
        )


def test_connection_errors_do_not_carry_the_key(monkeypatch):
    def boom(url, **kwargs):
        # httpx errors embed the request URL; with header auth it holds no secret
        raise httpx.ConnectError(f"failed connecting to {url}")

    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(Exception) as exc:
        GeminiProvider(api_key=CANARY)._generate([{"text": "hi"}], "system")
    # this string is persisted to AICallLog.error and surfaced to the client
    assert CANARY not in str(exc.value)


def test_dev_master_key_file_is_owner_only(tmp_path, monkeypatch):
    key_file = tmp_path / ".master_key"
    monkeypatch.setattr(crypto, "_DEV_KEY_FILE", key_file)
    monkeypatch.setattr(crypto.get_settings(), "companyval_master_key", "", raising=False)

    key = crypto._master_key()
    assert key, "a dev master key should be generated"
    mode = stat.S_IMODE(os.stat(key_file).st_mode)
    assert mode == 0o600, f"master key readable beyond owner (mode {mode:o})"
