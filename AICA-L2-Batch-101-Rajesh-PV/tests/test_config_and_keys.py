import json

from judgment_analyzer import key_store
from judgment_analyzer.config import AppSettings, load_settings, save_settings, settings_path
from judgment_analyzer.logging_setup import redact


def test_default_settings_valid():
    assert AppSettings().validate() == []


def test_invalid_settings_detected():
    s = AppSettings(model="bad model!", temperature=5, chunk_max_chars=10, ocr_language="eng;rm -rf")
    problems = s.validate()
    assert len(problems) >= 4


def test_settings_roundtrip_and_no_key_persisted():
    s = AppSettings(model="gemini-3.6-flash", analysis_depth="Detailed")
    save_settings(s)
    data = json.loads(settings_path().read_text())
    assert "api_key" not in json.dumps(data).lower()
    loaded = load_settings()
    assert loaded.model == "gemini-3.6-flash" and loaded.analysis_depth == "Detailed"


def test_corrupt_settings_fall_back_to_defaults():
    settings_path().write_text("{not json")
    assert load_settings() == AppSettings()


def test_env_model_override(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    assert load_settings().model == "gemini-3.5-flash-lite"


def test_key_format_validation_and_mask():
    assert key_store.validate_api_key_format("") is not None
    assert key_store.validate_api_key_format("short") is not None
    assert "U+00E9" in key_store.validate_api_key_format("AIzaSy" + "é" * 20)
    assert key_store.validate_api_key_format("A" * 39) is None
    # newer key formats containing '.' must be accepted
    assert key_store.validate_api_key_format("AQ.Ab8RN6" + "x" * 40) is None
    masked = key_store.mask_key("AIzaSyExampleExampleExample1234")
    assert masked.startswith("AIza") and masked.endswith("1234") and "Example" not in masked


def test_load_key_from_environment(monkeypatch):
    monkeypatch.setattr(key_store, "_keyring", lambda: (_ for _ in ()).throw(key_store.KeyStoreError("none")))
    monkeypatch.setenv("GEMINI_API_KEY", "B" * 39)
    assert key_store.load_api_key() == ("B" * 39, "environment")
    monkeypatch.setenv("GEMINI_API_KEY", "your-gemini-api-key-here")
    assert key_store.load_api_key() == ("", "")


def test_save_key_uses_keyring(monkeypatch):
    stored = {}

    class FakeKeyring:
        @staticmethod
        def set_password(service, account, value):
            stored[(service, account)] = value

    monkeypatch.setattr(key_store, "_keyring", lambda: FakeKeyring)
    key_store.save_api_key("C" * 39)
    assert stored[(key_store.SERVICE_NAME, key_store.ACCOUNT_NAME)] == "C" * 39


def test_log_redaction():
    line = redact("calling with key AIzaSyA1234567890abcdefghijklmnop and api_key=secret123")
    assert "AIzaSy" not in line and "secret123" not in line


def test_normalize_api_key_cleans_paste_artefacts():
    key = "AIzaSy" + "Q" * 33
    for raw in (f"  {key}\n", f'"{key}"', f"'{key}'", f"GEMINI_API_KEY={key}", f"export GEMINI_API_KEY='{key}'",
                f"\ufeff{key}\u200b", f"{key[:20]}\n{key[20:]}", f"\u00a0{key}\u00a0"):
        assert key_store.normalize_api_key(raw) == key, repr(raw)
        assert key_store.validate_api_key_format(raw) is None


def test_defaults_detailed_and_font_settings():
    s = AppSettings()
    assert s.analysis_depth == "Detailed"
    assert s.ocr_language == "eng"
    assert s.view_font_size == 12
    assert AppSettings(view_font_size=40).validate()
    save_settings(AppSettings(view_font_family="Georgia", view_font_size=15))
    loaded = load_settings()
    assert (loaded.view_font_family, loaded.view_font_size) == ("Georgia", 15)


def test_windows_data_dir_outside_appdata_and_migration(tmp_path, monkeypatch):
    from judgment_analyzer import config

    monkeypatch.delenv("JIA_CONFIG_DIR", raising=False)
    monkeypatch.setattr(config.sys, "platform", "win32")
    profile, appdata = tmp_path / "user1", tmp_path / "user1" / "AppData" / "Roaming"
    monkeypatch.setenv("USERPROFILE", str(profile))
    monkeypatch.setenv("APPDATA", str(appdata))
    new_dir = config.user_config_dir()
    assert new_dir == profile / ".JudgmentInsightAnalyzer" / "data"
    assert "AppData" not in str(new_dir)

    legacy = appdata / "JudgmentInsightAnalyzer"
    legacy.mkdir(parents=True)
    (legacy / "email_audit_log.csv").write_text("old audit")
    (legacy / "sender_profile.json").write_text("{}")
    (new_dir / "sender_profile.json").write_text('{"name": "kept"}')  # existing file must not be overwritten
    assert config.migrate_legacy_data() == ["email_audit_log.csv"]
    assert (new_dir / "email_audit_log.csv").read_text() == "old audit"
    assert "kept" in (new_dir / "sender_profile.json").read_text()
    assert config.migrate_legacy_data() == []  # idempotent


def test_migration_noop_off_windows(monkeypatch):
    from judgment_analyzer import config

    monkeypatch.setattr(config.sys, "platform", "linux")
    assert config.migrate_legacy_data() == []
