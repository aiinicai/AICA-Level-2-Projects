"""Tests for core.google_integration -- mocked HTTP, no live Google account."""
from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest

from core.google_integration import (
    build_oauth_config,
    create_draft_reply,
    download_attachment_bytes,
    list_drive_files,
    list_recent_messages,
    send_draft,
    upload_to_drive,
)
from utils.validation import ValidationError


def _mock_response(json_data, status_code=200, ok=True):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = ok
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


def test_build_oauth_config_defaults():
    config = build_oauth_config("client-id", "secret", "http://localhost/cb")
    assert "accounts.google.com" in config.endpoints.authorize_url
    assert "oauth2.googleapis.com" in config.endpoints.token_url
    assert "gmail.readonly" in " ".join(config.scopes)


def test_list_recent_messages_fetches_details_for_each_message():
    list_resp = _mock_response({"messages": [{"id": "m1"}, {"id": "m2"}]})
    detail_resp_1 = _mock_response({
        "snippet": "Please see attached invoice",
        "payload": {"headers": [{"name": "Subject", "value": "Invoice"}, {"name": "From", "value": "a@b.com"}],
                    "parts": [{"filename": "invoice.pdf"}]},
    })
    detail_resp_2 = _mock_response({
        "snippet": "No attachment here",
        "payload": {"headers": [{"name": "Subject", "value": "Update"}, {"name": "From", "value": "c@d.com"}]},
    })

    with patch("core.google_integration.requests.get", side_effect=[list_resp, detail_resp_1, detail_resp_2]):
        messages = list_recent_messages("token", max_results=2)

    assert len(messages) == 2
    assert messages[0].subject == "Invoice"
    assert messages[0].has_attachments is True
    assert messages[1].has_attachments is False


def test_list_recent_messages_passes_query():
    with patch("core.google_integration.requests.get") as mock_get:
        mock_get.return_value = _mock_response({"messages": []})
        list_recent_messages("token", query="is:unread has:attachment")
    assert mock_get.call_args.kwargs["params"]["q"] == "is:unread has:attachment"


def test_download_attachment_decodes_urlsafe_base64():
    content = b"fake pdf bytes for gmail attachment"
    encoded = base64.urlsafe_b64encode(content).decode().rstrip("=")
    with patch("core.google_integration.requests.get") as mock_get:
        mock_get.return_value = _mock_response({"data": encoded})
        result = download_attachment_bytes("token", "msg1", "att1")
    assert result == content


def test_download_attachment_no_data_raises():
    with patch("core.google_integration.requests.get") as mock_get:
        mock_get.return_value = _mock_response({})
        with pytest.raises(ValidationError, match="no downloadable content"):
            download_attachment_bytes("token", "msg1", "att1")


def test_create_draft_reply_never_sends():
    with patch("core.google_integration.requests.post") as mock_post:
        mock_post.return_value = _mock_response({"id": "draft1"})
        draft_id = create_draft_reply("token", "thread1", "client@example.com", "Re: Notice", "Please find attached.")
    assert draft_id == "draft1"
    assert "/drafts" in mock_post.call_args[0][0]
    assert "/send" not in mock_post.call_args[0][0]


def test_send_draft_calls_send_endpoint():
    with patch("core.google_integration.requests.post") as mock_post:
        mock_post.return_value = _mock_response({"id": "draft1"})
        send_draft("token", "draft1")
    assert mock_post.call_args[0][0].endswith("/drafts/send")
    assert mock_post.call_args.kwargs["json"]["id"] == "draft1"


def test_send_draft_failure_raises():
    with patch("core.google_integration.requests.post") as mock_post:
        mock_post.return_value = _mock_response({"error": {"message": "Quota exceeded"}}, status_code=429, ok=False)
        with pytest.raises(ValidationError, match="Quota exceeded"):
            send_draft("token", "draft1")


def test_list_drive_files_with_folder_filter():
    with patch("core.google_integration.requests.get") as mock_get:
        mock_get.return_value = _mock_response({"files": [{"id": "f1", "name": "signed.pdf", "mimeType": "application/pdf", "size": "1024", "webViewLink": "https://x"}]})
        files = list_drive_files("token", folder_id="folder123")
    assert files[0].name == "signed.pdf"
    assert files[0].size == 1024
    assert "'folder123' in parents" in mock_get.call_args.kwargs["params"]["q"]


def test_upload_to_drive_success():
    with patch("core.google_integration.requests.post") as mock_post:
        mock_post.return_value = _mock_response({"id": "item1", "name": "signed.pdf", "mimeType": "application/pdf", "size": "500", "webViewLink": "https://x"})
        result = upload_to_drive("token", "signed.pdf", b"x" * 500, folder_id="folder123")
    assert result.name == "signed.pdf"
    assert result.size == 500
    assert mock_post.call_args.kwargs["params"]["uploadType"] == "multipart"
