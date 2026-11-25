from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.money import fmt_money, from_minor, round_money, to_decimal, to_minor


def test_defaults_and_paths(isolated_instance):
    s = get_settings()
    assert s.instance_dir == isolated_instance
    assert s.database_path.parent == isolated_instance
    assert s.uploads_dir.exists() and s.backups_dir.exists() and s.exports_dir.exists()
    assert s.upload_allowed_extensions == (".xlsx", ".csv")


def test_secrets_generated_once_outside_code(isolated_instance):
    s1 = get_settings()
    key_file = isolated_instance / "secret.key"
    assert key_file.exists() and len(s1.secret_key) >= 40
    get_settings.cache_clear()
    assert get_settings().secret_key == s1.secret_key  # stable across restarts


def test_lan_without_https_is_refused(monkeypatch):
    monkeypatch.setenv("CFF_HOST", "0.0.0.0")
    with pytest.raises(RuntimeError, match="HTTPS"):
        Settings().check_network_safety()


def test_loopback_without_https_is_allowed():
    Settings(host="127.0.0.1").check_network_safety()


def test_ssl_needs_both_files():
    with pytest.raises(ValueError):
        Settings(ssl_certfile="cert.pem")


def test_money_rounding_and_minor_units():
    assert round_money("1.0005") == Decimal("1.001")  # half-up
    assert to_minor("1,234.567") == 1234567
    assert from_minor(1234567) == Decimal("1234.567")
    assert to_decimal("(12.500)") == Decimal("-12.500")
    assert to_decimal(None) == Decimal(0)
    assert fmt_money(1234.5) == "1,234.500"
    with pytest.raises(ValueError):
        to_decimal("abc")


def test_healthz():
    from app.main import create_app

    client = TestClient(create_app())
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["business_defaults"]["base_currency"] == "OMR"
    assert body["business_defaults"]["currency_decimals"] == 3
    assert body["business_defaults"]["lot_scheme"] == "month_thirds"
    assert body["business_defaults"]["approver_enabled"] is False
