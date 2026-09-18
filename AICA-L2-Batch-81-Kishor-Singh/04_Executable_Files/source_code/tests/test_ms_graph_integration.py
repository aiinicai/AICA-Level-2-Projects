"""Tests for core.ms_graph_integration -- mocked HTTP, no live Microsoft account."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.ms_graph_integration import (
    build_oauth_config,
    create_reply_draft,
    download_attachment_bytes,
    list_message_attachments,
    list_onedrive_folder,
    list_recent_messages,
    send_draft,
    upload_to_onedrive,
)
from utils.validation import ValidationError


def _mock_response(json_data, status_code=200, ok=True):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = ok
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


def test_build_oauth_config_uses_tenant_in_urls():
    config = build_oauth_config("client-id", "http://localhost/cb", tenant="contoso.onmicrosoft.com")
    assert "contoso.onmicrosoft.com" in config.endpoints.authorize_url
    assert "contoso.onmicrosoft.com" in config.endpoints.token_url
    assert config.client_secret == ""  # public client + PKCE


def test_list_recent_messages_maps_fields():
    with patch("core.ms_graph_integration.requests.get") as mock_get:
        mock_get.return_value = _mock_response({
            "value": [{
                "id": "msg1", "subject": "GST Notice", "from": {"emailAddress": {"address": "gst@dept.gov.in"}},
                "receivedDateTime": "2026-01-10T10:00:00Z", "hasAttachments": True,
            }]
        })
        messages = list_recent_messages("token123", top=5)

    assert len(messages) == 1
    assert messages[0].subject == "GST Notice"
    assert messages[0].sender == "gst@dept.gov.in"
    assert messages[0].has_attachments is True
    assert mock_get.call_args.kwargs["headers"]["Authorization"] == "Bearer token123"
    assert mock_get.call_args.kwargs["params"]["$top"] == 5


def test_list_recent_messages_unread_filter():
    with patch("core.ms_graph_integration.requests.get") as mock_get:
        mock_get.return_value = _mock_response({"value": []})
        list_recent_messages("token", unread_only=True)
    assert "isRead eq false" in mock_get.call_args.kwargs["params"]["$filter"]


def test_list_message_attachments():
    with patch("core.ms_graph_integration.requests.get") as mock_get:
        mock_get.return_value = _mock_response({"value": [{"id": "att1", "name": "invoice.pdf", "contentType": "application/pdf", "size": 1024}]})
        attachments = list_message_attachments("token", "msg1")
    assert attachments[0].name == "invoice.pdf"
    assert attachments[0].size == 1024


def test_download_attachment_decodes_base64():
    import base64

    content = b"fake pdf bytes"
    with patch("core.ms_graph_integration.requests.get") as mock_get:
        mock_get.return_value = _mock_response({"contentBytes": base64.b64encode(content).decode()})
        result = download_attachment_bytes("token", "msg1", "att1")
    assert result == content


def test_download_attachment_with_no_content_raises():
    with patch("core.ms_graph_integration.requests.get") as mock_get:
        mock_get.return_value = _mock_response({"id": "att1"})  # no contentBytes
        with pytest.raises(ValidationError, match="no downloadable content"):
            download_attachment_bytes("token", "msg1", "att1")


def test_create_reply_draft_never_sends():
    with patch("core.ms_graph_integration.requests.post") as mock_post:
        mock_post.return_value = _mock_response({"id": "draft1"})
        draft_id = create_reply_draft("token", "msg1", "Please find attached.")
    assert draft_id == "draft1"
    assert "createReply" in mock_post.call_args[0][0]
    assert "/send" not in mock_post.call_args[0][0]


def test_send_draft_calls_send_endpoint():
    with patch("core.ms_graph_integration.requests.post") as mock_post:
        mock_post.return_value = _mock_response({}, status_code=202)
        send_draft("token", "draft1")
    assert mock_post.call_args[0][0].endswith("/draft1/send")


def test_send_draft_failure_raises():
    with patch("core.ms_graph_integration.requests.post") as mock_post:
        mock_post.return_value = _mock_response({"error": {"message": "Insufficient permissions"}}, status_code=403, ok=False)
        with pytest.raises(ValidationError, match="Insufficient permissions"):
            send_draft("token", "draft1")


def test_list_onedrive_folder_root():
    with patch("core.ms_graph_integration.requests.get") as mock_get:
        mock_get.return_value = _mock_response({"value": [{"id": "f1", "name": "Signed Documents", "folder": {}, "size": 0, "webUrl": "https://x"}]})
        items = list_onedrive_folder("token")
    assert items[0].is_folder is True
    assert "root/children" in mock_get.call_args[0][0]


def test_list_onedrive_folder_subpath():
    with patch("core.ms_graph_integration.requests.get") as mock_get:
        mock_get.return_value = _mock_response({"value": []})
        list_onedrive_folder("token", folder_path="/Clients/ABC")
    assert "root:/Clients/ABC:/children" in mock_get.call_args[0][0]


def test_upload_to_onedrive_success():
    with patch("core.ms_graph_integration.requests.put") as mock_put:
        mock_put.return_value = _mock_response({"id": "item1", "name": "signed.pdf", "size": 100, "webUrl": "https://x"})
        result = upload_to_onedrive("token", "/Clients/ABC", "signed.pdf", b"x" * 100)
    assert result.name == "signed.pdf"
    assert "Clients/ABC/signed.pdf" in mock_put.call_args[0][0]


def test_upload_to_onedrive_rejects_oversized_file():
    with pytest.raises(ValidationError, match="4 MB"):
        upload_to_onedrive("token", "/", "big.pdf", b"x" * (5 * 1024 * 1024))
