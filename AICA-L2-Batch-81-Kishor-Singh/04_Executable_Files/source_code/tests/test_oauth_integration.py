"""Tests for core.oauth_integration: the shared OAuth2 Authorization Code flow
helper. All HTTP calls are mocked -- no live Microsoft/Google account is used."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.oauth_integration import (
    OAuthConfig,
    OAuthError,
    OAuthProviderEndpoints,
    build_authorization_url,
    exchange_code_for_token,
    generate_pkce_pair,
    refresh_access_token,
)


def _config():
    return OAuthConfig(
        client_id="test-client-id",
        client_secret="",
        redirect_uri="http://localhost:8400/callback",
        scopes=["Mail.Read", "Files.ReadWrite"],
        endpoints=OAuthProviderEndpoints(
            authorize_url="https://provider.example.com/authorize",
            token_url="https://provider.example.com/token",
        ),
    )


def _mock_response(json_data, status_code=200, ok=True):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = ok
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


def test_pkce_pair_is_well_formed():
    verifier, challenge = generate_pkce_pair()
    assert 43 <= len(verifier) <= 128
    assert len(challenge) > 0
    assert challenge != verifier


def test_pkce_pairs_are_unique():
    v1, c1 = generate_pkce_pair()
    v2, c2 = generate_pkce_pair()
    assert v1 != v2
    assert c1 != c2


def test_build_authorization_url_includes_required_params():
    url = build_authorization_url(_config(), state="xyz123", code_challenge="abc")
    assert "client_id=test-client-id" in url
    assert "response_type=code" in url
    assert "state=xyz123" in url
    assert "code_challenge=abc" in url
    assert "code_challenge_method=S256" in url
    assert url.startswith("https://provider.example.com/authorize?")


def test_build_authorization_url_scopes_space_joined():
    url = build_authorization_url(_config(), state="s")
    assert "Mail.Read" in url and "Files.ReadWrite" in url


def test_exchange_code_for_token_success():
    with patch("core.oauth_integration.requests.post") as mock_post:
        mock_post.return_value = _mock_response(
            {"access_token": "tok123", "refresh_token": "refresh123", "expires_in": 3600, "token_type": "Bearer"}
        )
        token = exchange_code_for_token(_config(), authorization_code="auth-code", code_verifier="verifier")

    assert token.access_token == "tok123"
    assert token.refresh_token == "refresh123"
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["data"]["code"] == "auth-code"
    assert call_kwargs.kwargs["data"]["code_verifier"] == "verifier"
    assert call_kwargs.kwargs["data"]["grant_type"] == "authorization_code"


def test_exchange_code_for_token_includes_client_secret_when_present():
    config = _config()
    config.client_secret = "shh-secret"
    with patch("core.oauth_integration.requests.post") as mock_post:
        mock_post.return_value = _mock_response({"access_token": "t", "expires_in": 3600})
        exchange_code_for_token(config, authorization_code="code")
    assert mock_post.call_args.kwargs["data"]["client_secret"] == "shh-secret"


def test_exchange_code_for_token_failure_raises_oauth_error():
    with patch("core.oauth_integration.requests.post") as mock_post:
        mock_post.return_value = _mock_response(
            {"error": "invalid_grant", "error_description": "The authorization code has expired."},
            status_code=400, ok=False,
        )
        with pytest.raises(OAuthError, match="expired"):
            exchange_code_for_token(_config(), authorization_code="stale-code")


def test_refresh_access_token_success():
    with patch("core.oauth_integration.requests.post") as mock_post:
        mock_post.return_value = _mock_response({"access_token": "new-token", "expires_in": 3600})
        token = refresh_access_token(_config(), refresh_token="old-refresh")
    assert token.access_token == "new-token"
    assert mock_post.call_args.kwargs["data"]["grant_type"] == "refresh_token"
    assert mock_post.call_args.kwargs["data"]["refresh_token"] == "old-refresh"


def test_refresh_access_token_failure_raises():
    with patch("core.oauth_integration.requests.post") as mock_post:
        mock_post.return_value = _mock_response({"error": "invalid_grant"}, status_code=400, ok=False)
        with pytest.raises(OAuthError):
            refresh_access_token(_config(), refresh_token="revoked-token")
