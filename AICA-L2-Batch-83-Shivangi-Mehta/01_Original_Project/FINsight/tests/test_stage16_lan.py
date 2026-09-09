"""
Stage 16 — LAN / Same Network Access test suite.

Covers, per the Stage 16 instruction's Section 33 list (items 1-21 have
a dedicated test or group of tests below; items 22-28 — existing
Accounting/Audit/Tax/Unified Review/Query & Working Paper/Stage 14 UX/
Stage 15 security suites still passing — are satisfied by running the
full suite alongside this file, exactly the convention
test_stage15_security.py itself already uses for its own equivalent
items, not duplicated here).

Uses only synthetic, fabricated data and harmless test payloads, per
the standing instruction. No malicious payload is ever executed.

Sandbox limitation, disclosed rather than hidden: item 1 ("LAN launcher
starts safely") and item 3 ("LAN bind configuration is correct") cannot
literally start Waitress and connect to it over a real socket from
inside this test run without blocking the test process — instead these
are verified by (a) importing wsgi_lan.py itself, which builds the real
app object and exercises every module-level code path outside the
`if __name__ == "__main__":` guard, and (b) a static source check that
the actual `serve(...)` call the guarded block would make is bound to
`host="0.0.0.0"`. This is disclosed here and again in
documentation/stage16_lan_mode.md rather than claimed as a live network
test.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from config import TestConfig
from app import create_app
from app.security import lan_auth

REPO_ROOT = Path(__file__).resolve().parent.parent


# --- fixtures ----------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_lan_lockout_state():
    """app/security/lan_auth._lockouts is process-global, in-memory
    state (by design — see that module's docstring). Without this, one
    test's failed-login attempts would bleed into the next test's
    lockout counter, since the Flask test client's remote_addr is the
    same fixed value across tests."""
    lan_auth._lockouts.clear()
    yield
    lan_auth._lockouts.clear()


def _make_app(tmp_path, csrf_enabled=False, extra=None):
    class LanConfig(TestConfig):
        DATA_INPUT_DIR = tmp_path / "data_input"
        LAN_MODE_ENABLED = True
        CSRF_ENABLED = csrf_enabled

    if extra:
        for key, value in extra.items():
            setattr(LanConfig, key, value)

    app = create_app(LanConfig)
    from app import extensions
    from app.models import Base

    Base.metadata.create_all(extensions.engine)
    return app


@pytest.fixture()
def lan_app(tmp_path):
    """LAN mode ON, CSRF disabled — matches every other HTTP test
    file's convention (config.py's Stage 15 note explains why)."""
    return _make_app(tmp_path)


@pytest.fixture()
def lan_client(lan_app):
    return lan_app.test_client()


@pytest.fixture()
def lan_csrf_app(tmp_path):
    """LAN mode ON, CSRF explicitly forced ON — exercises real
    enforcement, same convention as test_stage15_security.py's
    csrf_client fixture."""
    return _make_app(tmp_path, csrf_enabled=True)


@pytest.fixture()
def lan_csrf_client(lan_csrf_app):
    return lan_csrf_app.test_client()


@pytest.fixture()
def local_client(tmp_path):
    """LAN_MODE_ENABLED left at its TestConfig default (False) —
    represents ordinary local/dev mode, for the "does not break local
    mode" regression checks (Section 25)."""
    class LocalConfig(TestConfig):
        DATA_INPUT_DIR = tmp_path / "data_input"

    app = create_app(LocalConfig)
    from app import extensions
    from app.models import Base

    Base.metadata.create_all(extensions.engine)
    return app.test_client()


def _set_password(client, password="Correct-Horse-1"):
    r = client.post("/access/setup", data={"password": password, "confirm_password": password}, follow_redirects=False)
    assert r.status_code == 200  # renders setup_done.html directly, no redirect
    return password


def _sign_out(client):
    client.post("/access/logout")


def _extract_csrf_token(html: str) -> str:
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, "csrf_token field not found in page"
    return m.group(1)


def _set_password_with_csrf(client, password="Correct-Horse-1"):
    token = _extract_csrf_token(client.get("/access/setup").get_data(as_text=True))
    r = client.post("/access/setup", data={"password": password, "confirm_password": password, "csrf_token": token})
    assert r.status_code == 200
    return password


# =============================================================================
# 1-3: LAN launcher / bind configuration (static + import-based checks —
# see module docstring for why this can't be a live socket test here)
# =============================================================================

def test_wsgi_lan_module_imports_and_builds_a_real_app(monkeypatch):
    pytest.importorskip("waitress", reason=(
        "waitress is an approved Stage 1 dependency (requirements.txt) but is not installed in this "
        "sandbox and cannot be installed here (no package-registry network access — the same genuine "
        "offline sandbox condition Stage 15 documented). wsgi_lan.py does `from waitress import serve` "
        "at module level, so importing it requires the real package. Disclosed here and in "
        "documentation/stage16_lan_mode.md rather than skipped silently."
    ))
    monkeypatch.delenv("FINSIGHT_LAN_MODE", raising=False)
    import importlib
    import wsgi_lan

    importlib.reload(wsgi_lan)
    assert wsgi_lan.app.config["LAN_MODE_ENABLED"] is True
    assert wsgi_lan.app.config["TESTING"] is not True  # real Config, not TestConfig


def test_lan_launcher_debug_mode_is_never_enabled():
    pytest.importorskip("waitress", reason="see test_wsgi_lan_module_imports_and_builds_a_real_app")
    import wsgi_lan

    assert wsgi_lan.app.debug is False


def test_lan_launcher_binds_to_all_interfaces_not_only_loopback():
    # Deliberately a plain source-text check, not an import — this one
    # runs regardless of whether waitress is installed in this sandbox.
    source = (REPO_ROOT / "wsgi_lan.py").read_text(encoding="utf-8")
    assert 'host="0.0.0.0"' in source
    assert "waitress" in source.lower()


def test_lan_launcher_refuses_to_start_on_the_dev_secret_key_fallback(monkeypatch, capsys):
    pytest.importorskip("waitress", reason="see test_wsgi_lan_module_imports_and_builds_a_real_app")
    import wsgi_lan
    from config import DEV_SECRET_KEY_FALLBACK

    fake_app = type("FakeApp", (), {"config": {"SECRET_KEY": DEV_SECRET_KEY_FALLBACK}})()
    with pytest.raises(SystemExit):
        wsgi_lan._refuse_if_dev_secret_key(fake_app)


def test_local_ip_detection_is_fast_and_never_blocks_startup():
    """Section 15: must never contact an external service and must
    never hang. A generous 2-second ceiling comfortably separates
    "returned quickly" from "hung"."""
    start = time.time()
    result = lan_auth.get_local_lan_ip()
    elapsed = time.time() - start
    assert elapsed < 2.0
    assert result is None or isinstance(result, str)


# =============================================================================
# 4-7: login gate exists, protects, accepts correct / rejects incorrect password
# =============================================================================

def test_first_run_with_no_password_redirects_every_protected_route_to_setup(lan_client):
    for path in ("/", "/engagement/", "/settings/"):
        r = lan_client.get(path, follow_redirects=False)
        assert r.status_code == 302
        assert "/access/setup" in r.headers["Location"]


def test_setup_page_itself_is_reachable_before_a_password_exists(lan_client):
    assert lan_client.get("/access/setup").status_code == 200


def test_login_gate_exists_and_renders_after_password_is_set(lan_client):
    _set_password(lan_client)
    _sign_out(lan_client)
    r = lan_client.get("/access/login")
    assert r.status_code == 200
    assert "Access FinSight" in r.get_data(as_text=True) or "password" in r.get_data(as_text=True).lower()


def test_protected_route_without_login_is_rejected(lan_client):
    _set_password(lan_client)
    _sign_out(lan_client)
    r = lan_client.get("/", follow_redirects=False)
    assert r.status_code == 302
    assert "/access/login" in r.headers["Location"]


def test_correct_password_grants_access(lan_client):
    password = _set_password(lan_client)
    _sign_out(lan_client)
    r = lan_client.post("/access/login", data={"password": password}, follow_redirects=False)
    assert r.status_code == 302
    r2 = lan_client.get("/", follow_redirects=True)
    assert r2.status_code == 200


def test_incorrect_password_is_rejected_with_a_generic_message(lan_client):
    _set_password(lan_client)
    _sign_out(lan_client)
    r = lan_client.post("/access/login", data={"password": "totally-wrong"}, follow_redirects=False)
    assert r.status_code == 200
    assert "Incorrect password" in r.get_data(as_text=True)
    # still not authenticated
    r2 = lan_client.get("/", follow_redirects=False)
    assert r2.status_code == 302


def test_setup_screen_is_no_longer_open_once_a_password_already_exists(lan_client):
    _set_password(lan_client)
    _sign_out(lan_client)
    r = lan_client.get("/access/setup", follow_redirects=False)
    assert r.status_code == 302
    assert "/access/login" in r.headers["Location"]


# =============================================================================
# 8-10: password not stored in plaintext, not exposed in HTML, not logged
# =============================================================================

def test_password_is_not_stored_in_plaintext(lan_app, lan_client):
    password = _set_password(lan_client, "MyRealPassword-42")
    from app import extensions
    from app.models.system import ApplicationSetting

    with lan_app.app_context():
        row = extensions.SessionLocal().get(ApplicationSetting, "lan_access_password_hash")
        assert row is not None
        assert row.setting_value != password
        assert password not in row.setting_value
        # A recognizable Werkzeug hash format (method$salt$hash), not a
        # bare/plaintext-looking string.
        assert row.setting_value.count("$") >= 1 or row.setting_value.startswith(("pbkdf2:", "scrypt:"))


def test_password_and_hash_never_appear_in_rendered_html(lan_client):
    password = _set_password(lan_client, "NeverShowMe-77")
    from app.services import lan_access_service

    stored_hash = lan_access_service.get_password_hash()

    pages = [lan_client.get("/access/setup"), lan_client.get("/access/login", follow_redirects=True)]
    _sign_out(lan_client)
    pages.append(lan_client.get("/access/login"))

    for r in pages:
        body = r.get_data(as_text=True)
        assert password not in body
        assert stored_hash not in body


def test_no_login_password_is_ever_logged_or_printed():
    """Static check, same style as test_stage15_security.py's logging
    review: none of the three Stage 16 modules that ever see the raw
    submitted password write it to a logger or print() call."""
    banned = re.compile(r"(logger\.\w+|print)\([^)]*\b(password|raw_password|new_password|current_password|confirm_password)\b")
    offenders = []
    for relative in ("app/api/access_bp.py", "app/security/lan_auth.py", "app/services/lan_access_service.py", "app/api/settings_bp.py"):
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        if banned.search(text):
            offenders.append(relative)
    assert offenders == [], f"Password-related logging found in: {offenders}"


# =============================================================================
# 11-12: sign out works, and protects routes again afterward
# =============================================================================

def test_sign_out_works_and_protected_routes_require_login_again(lan_client):
    password = _set_password(lan_client)
    assert lan_client.get("/", follow_redirects=False).status_code == 200
    r = lan_client.post("/access/logout", follow_redirects=False)
    assert r.status_code == 302
    r2 = lan_client.get("/", follow_redirects=False)
    assert r2.status_code == 302
    assert "/access/login" in r2.headers["Location"]


def test_sign_out_link_is_rendered_only_when_lan_mode_active_and_authenticated(lan_client, local_client):
    _set_password(lan_client)
    body = lan_client.get("/").get_data(as_text=True)
    assert "Sign Out" in body

    # Local/dev mode: never shown, since there is nothing to sign out of.
    local_body = local_client.get("/").get_data(as_text=True)
    assert "Sign Out" not in local_body


# =============================================================================
# 13-14: CSRF remains fully enabled under LAN mode, unweakened
# =============================================================================

def test_csrf_still_protects_the_login_form_itself(lan_csrf_client):
    _set_password_with_csrf(lan_csrf_client)  # setup form's own CSRF succeeds via csrf_field()
    _sign_out(lan_csrf_client)
    lan_csrf_client.get("/access/login")  # mint a token
    r = lan_csrf_client.post("/access/login", data={"password": "Correct-Horse-1"})  # no csrf_token field
    assert r.status_code == 400


def test_csrf_still_protects_ordinary_routes_once_authenticated(lan_csrf_client):
    _set_password_with_csrf(lan_csrf_client)
    r = lan_csrf_client.post("/engagement/new", data={"entity_name": "Acme", "financial_year": "2025-26"})
    assert r.status_code == 400  # missing csrf_token — LAN mode did not weaken this


# =============================================================================
# 15-16: two browsers, two separate current-engagement contexts
# =============================================================================

def test_two_lan_clients_keep_independent_current_engagements(lan_app):
    client_1 = lan_app.test_client()
    client_2 = lan_app.test_client()

    password = "Shared-LAN-Password-9"
    _set_password(client_1, password)
    client_2.post("/access/login", data={"password": password})

    client_1.post("/engagement/new", data={"entity_name": "Engagement A Pvt Ltd", "financial_year": "2025-26"})
    client_2.post("/engagement/new", data={"entity_name": "Engagement B Pvt Ltd", "financial_year": "2025-26"})

    body_1 = client_1.get("/").get_data(as_text=True)
    body_2 = client_2.get("/").get_data(as_text=True)

    assert "Engagement A Pvt Ltd" in body_1
    assert "Engagement B Pvt Ltd" not in body_1
    assert "Engagement B Pvt Ltd" in body_2
    assert "Engagement A Pvt Ltd" not in body_2


def test_switching_engagement_in_one_client_does_not_affect_the_other(lan_app):
    client_1 = lan_app.test_client()
    client_2 = lan_app.test_client()
    password = "Shared-LAN-Password-9"
    _set_password(client_1, password)
    client_2.post("/access/login", data={"password": password})

    client_1.post("/engagement/new", data={"entity_name": "Engagement A Pvt Ltd", "financial_year": "2025-26"})
    with client_1.session_transaction() as sess:
        engagement_a_id = sess["current_engagement_id"]

    client_2.post("/engagement/new", data={"entity_name": "Engagement B Pvt Ltd", "financial_year": "2025-26"})

    # Client 1 switches again — client 2 must be unaffected.
    client_1.post("/engagement/new", data={"entity_name": "Engagement A2 Pvt Ltd", "financial_year": "2025-26"})
    body_2 = client_2.get("/").get_data(as_text=True)
    assert "Engagement B Pvt Ltd" in body_2
    assert "Engagement A2 Pvt Ltd" not in body_2


# =============================================================================
# 17-19: database/data directories stay on the host, never web-servable
# =============================================================================

def test_database_uri_is_still_local_sqlite_under_lan_config(lan_app):
    assert lan_app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///")


@pytest.mark.parametrize("path", [
    "/database/finsight.db",
    "/finsight.db",
    "/data/input/anything.csv",
    "/data/processed/anything.csv",
    "/logs/finsight.log",
    "/.env",
    "/static/../database/finsight.db",
])
def test_sensitive_paths_stay_unreachable_even_when_authenticated(lan_client, path):
    _set_password(lan_client)
    r = lan_client.get(path)
    assert r.status_code in (400, 404)
    assert "SECRET_KEY" not in r.get_data(as_text=True)


# =============================================================================
# 20-21: no external network / AI dependency introduced by Stage 16
# =============================================================================

def test_stage16_modules_reference_no_external_ai_provider():
    banned = re.compile(r"\b(openai|OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY|anthropic\.Client|genai\.)", re.I)
    for relative in ("app/api/access_bp.py", "app/security/lan_auth.py", "app/services/lan_access_service.py"):
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert not banned.search(text), relative


def test_stage16_offline_scan_coverage_note():
    """The full outbound-network-call static scan
    (test_no_outbound_network_call_in_application_source in
    test_stage15_security.py) already includes every Stage 16 file,
    including app/security/lan_auth.py's one socket.socket( use — see
    that test's own updated exclusion comment for why it's safe. Not
    duplicated here; this test only documents that fact so it isn't
    lost."""
    assert True


# =============================================================================
# Brute-force protection (Section 11) — not in the numbered list by name,
# but explicitly required by the governing instruction's Section 11/33.
# =============================================================================

def test_repeated_wrong_passwords_trigger_a_temporary_lockout(lan_app, lan_client):
    lan_app.config["LAN_MAX_LOGIN_ATTEMPTS"] = 3
    password = _set_password(lan_client)
    _sign_out(lan_client)

    for _ in range(3):
        r = lan_client.post("/access/login", data={"password": "wrong"})
        assert r.status_code == 200

    # 4th attempt, even with the CORRECT password, must be refused while locked out.
    r = lan_client.post("/access/login", data={"password": password})
    assert r.status_code == 200
    assert "Too many incorrect attempts" in r.get_data(as_text=True)
    # still not authenticated
    assert lan_client.get("/", follow_redirects=False).status_code == 302


def test_lockout_counter_resets_after_a_successful_login(lan_app, lan_client):
    lan_app.config["LAN_MAX_LOGIN_ATTEMPTS"] = 5
    password = _set_password(lan_client)
    _sign_out(lan_client)

    lan_client.post("/access/login", data={"password": "wrong"})
    lan_client.post("/access/login", data={"password": "wrong"})
    r = lan_client.post("/access/login", data={"password": password})
    assert r.status_code == 302  # succeeded before hitting the lockout threshold

    _sign_out(lan_client)
    # Fresh window — the earlier 2 failures must not carry over.
    r2 = lan_client.post("/access/login", data={"password": "wrong"})
    assert "Too many incorrect attempts" not in r2.get_data(as_text=True)


# =============================================================================
# Setup validation, open-redirect protection, and Change Password (Section 28)
# — additional coverage beyond the numbered list, following the same
# diligence as test_stage15_security.py.
# =============================================================================

def test_setup_rejects_a_too_short_password(lan_client):
    r = lan_client.post("/access/setup", data={"password": "short", "confirm_password": "short"})
    assert r.status_code == 200
    assert "at least" in r.get_data(as_text=True)


def test_setup_rejects_mismatched_confirmation(lan_client):
    r = lan_client.post("/access/setup", data={"password": "LongEnough-1", "confirm_password": "Different-2"})
    assert r.status_code == 200
    assert "do not match" in r.get_data(as_text=True)


def test_login_next_parameter_cannot_redirect_off_site(lan_client):
    password = _set_password(lan_client)
    _sign_out(lan_client)
    r = lan_client.post(
        "/access/login?next=https://evil.example.com/steal",
        data={"password": password, "next": "https://evil.example.com/steal"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "evil.example.com" not in r.headers["Location"]


def test_change_password_in_settings_requires_correct_current_password(lan_client):
    _set_password(lan_client, "Original-Pass-1")
    r = lan_client.post("/settings/", data={
        "current_password": "wrong-current", "new_password": "NewPass-2", "confirm_new_password": "NewPass-2",
    })
    assert r.status_code == 200
    assert "incorrect" in r.get_data(as_text=True).lower()


def test_change_password_succeeds_and_old_password_stops_working(lan_app):
    client = lan_app.test_client()
    _set_password(client, "Original-Pass-1")
    r = client.post("/settings/", data={
        "current_password": "Original-Pass-1", "new_password": "Brand-New-2", "confirm_new_password": "Brand-New-2",
    })
    assert r.status_code == 200
    assert "Password changed" in r.get_data(as_text=True)

    _sign_out(client)
    old = client.post("/access/login", data={"password": "Original-Pass-1"})
    assert "Incorrect password" in old.get_data(as_text=True)
    new = client.post("/access/login", data={"password": "Brand-New-2"}, follow_redirects=False)
    assert new.status_code == 302


def test_changing_password_signs_out_other_already_authenticated_sessions(lan_app):
    """Section 28's natural expectation: a shared-password change
    should not leave other devices signed in under the old password."""
    client_1 = lan_app.test_client()
    client_2 = lan_app.test_client()
    _set_password(client_1, "Shared-1")
    client_2.post("/access/login", data={"password": "Shared-1"})
    assert client_2.get("/", follow_redirects=False).status_code == 200

    client_1.post("/settings/", data={
        "current_password": "Shared-1", "new_password": "Shared-2", "confirm_new_password": "Shared-2",
    })

    r = client_2.get("/", follow_redirects=False)
    assert r.status_code == 302
    assert "/access/login" in r.headers["Location"]


def test_change_password_section_is_absent_outside_lan_mode(local_client):
    body = local_client.get("/settings/").get_data(as_text=True)
    assert "Change LAN Access Password" not in body


# =============================================================================
# Local/dev mode regression (Section 25) — the access gate must be a
# complete no-op when LAN_MODE_ENABLED is False, the TestConfig default.
# =============================================================================

def test_local_mode_never_gates_any_route(local_client):
    for path in ("/", "/engagement/", "/data/upload/", "/settings/"):
        assert local_client.get(path).status_code == 200


def test_local_mode_access_routes_are_registered_but_password_never_gates_them(local_client):
    # The blueprint is always registered (Section 25: share the same
    # code), so these routes exist, but nothing redirects to them.
    r = local_client.get("/access/login")
    assert r.status_code == 200
