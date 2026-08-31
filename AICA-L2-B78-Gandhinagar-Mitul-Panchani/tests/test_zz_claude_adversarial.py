"""Adversarial checks written by Claude to verify Codex's guarantees independently."""
import os, socket, pytest

def test_claude_outbound_tcp_is_blocked():
    """Try to actually reach Google. The socket guard must stop this."""
    with pytest.raises(BaseException) as exc:
        socket.create_connection(("generativelanguage.googleapis.com", 443), timeout=5)
    assert "network" in str(exc.value).lower() or "Test attempted" in str(exc.value)

def test_claude_raw_socket_connect_is_blocked():
    """The lower-level socket.connect path must be blocked too, not just create_connection."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with pytest.raises(BaseException) as exc:
        s.connect(("142.250.190.46", 443))   # a Google IP, bypasses DNS
    assert "network" in str(exc.value).lower() or "Test attempted" in str(exc.value)

def test_claude_loopback_still_allowed():
    """Loopback must still work or FastAPI TestClient breaks in Phase 7."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0)); srv.listen(1)
    port = srv.getsockname()[1]
    c = socket.create_connection(("127.0.0.1", port), timeout=5)
    c.close(); srv.close()

def test_claude_offline_defaults_true_when_env_absent(monkeypatch):
    """AMG_OFFLINE must default ON, so a bare checkout cannot spend quota."""
    import amg.config as cfg
    monkeypatch.delenv("AMG_OFFLINE", raising=False)
    cfg.get_settings.cache_clear()
    assert cfg.get_settings().offline is True

def test_claude_live_provider_blocked_even_with_real_keys(monkeypatch):
    """With real keys present but offline on, resolution must still be stub/local."""
    import amg.config as cfg
    monkeypatch.setenv("GEMINI_API_KEY", "fake-but-nonempty")
    monkeypatch.setenv("VOYAGE_API_KEY", "fake-but-nonempty")
    monkeypatch.setenv("AMG_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("AMG_EMBED_PROVIDER", "voyage")
    monkeypatch.setenv("AMG_OFFLINE", "1")
    cfg.get_settings.cache_clear()
    s = cfg.get_settings()
    assert s.resolved_llm_provider() == "stub"
    assert s.resolved_embed_provider() == "local"
