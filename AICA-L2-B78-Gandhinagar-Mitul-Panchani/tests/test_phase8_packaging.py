"""Phase 8 packaging boundaries; all non-artifact tests run without network."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import amg.config as config_module
from build_exe import (
    _collect_prohibited_name,
    _is_prohibited_data_name,
    _is_prohibited_module_name,
    _load_secret_values,
    _raise_archive_violations,
    _scan_bytes,
)
from amg.config import get_settings, user_data_dir
from amg.providers import reset_provider_state
from amg.settings_store import clear_provider_settings, save_provider_settings
from amg.web.app import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = PROJECT_ROOT / "AIMemoryGovernance.spec"
EXE_PATH = PROJECT_ROOT / "dist" / "AIMemoryGovernance.exe"


def _analysis_keywords() -> dict[str, ast.expr]:
    tree = ast.parse(SPEC_PATH.read_text(encoding="utf-8"), filename=str(SPEC_PATH))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Analysis"
        ):
            return {
                keyword.arg: keyword.value
                for keyword in node.keywords
                if keyword.arg is not None
            }
    raise AssertionError("The spec has no PyInstaller Analysis call.")


@pytest.mark.parametrize(
    "module_name",
    (
        "jinja2.tests",
        "voyageai.tests",
        "anyio.tests",
        "amg.db",
        "amg.web.app",
    ),
)
def test_bundle_module_names_allow_application_modules(module_name: str) -> None:
    assert _is_prohibited_module_name(module_name) is False


@pytest.mark.parametrize(
    "module_name",
    ("tests", "tests.test_phase1", "pytest", "_pytest.fixtures"),
)
def test_bundle_module_names_reject_test_modules(module_name: str) -> None:
    assert _is_prohibited_module_name(module_name) is True


@pytest.mark.parametrize(
    ("data_name", "expected"),
    (
        ("memory.db", True),
        ("x.sqlite3", True),
        (".env", True),
        (".env.keys-backup", True),
        (".amg_usage.json", True),
        (".env.example", False),
        ("tests/conftest.py", True),
        ("amg/web/static/app.js", False),
    ),
)
def test_bundle_data_names_apply_file_rules(data_name: str, expected: bool) -> None:
    assert _is_prohibited_data_name(data_name) is expected


def test_bundle_data_and_module_predicates_remain_distinct() -> None:
    assert _is_prohibited_data_name is not _is_prohibited_module_name
    assert _is_prohibited_data_name("regression.db") is True
    assert _is_prohibited_module_name("amg.db") is False


def test_bundle_violation_report_collects_all_bad_names() -> None:
    violations: list[tuple[str, str, str]] = []
    _collect_prohibited_name(violations, "CArchive", "private-memory.db")
    _collect_prohibited_name(violations, "PYZ", "tests.test_phase1")

    with pytest.raises(RuntimeError) as exc_info:
        _raise_archive_violations(violations)

    message = str(exc_info.value)
    assert "private-memory.db" in message
    assert "tests.test_phase1" in message


@pytest.mark.parametrize(
    "payload",
    (
        b"set the environment variable VOYAGE_API_KEY=<API-KEY>",
        b"VOYAGE_API_KEY=${VOYAGE_KEY}",
        b"GEMINI_API_KEY=your-key-here",
        b"OTHER_API_KEY=''",
        b'CUSTOM_TOKEN=""',
    ),
)
def test_secret_scan_ignores_placeholders_and_help_text(payload: bytes) -> None:
    # Label must denote our own artifact: tier 2 is scoped to code we author.
    _scan_bytes(payload, "Python archive entry 'amg.config'")


@pytest.mark.parametrize(
    "payload",
    (
        b"GEMINI_API_KEY=AQ.AbCdEf123456",
        b"PREVIOUSLY_UNKNOWN_API_KEY=AQ.ZyXwVu987654",
    ),
)
def test_secret_scan_remains_a_hard_failure_for_genuine_assignment(
    payload: bytes,
) -> None:
    with pytest.raises(RuntimeError, match="SECRET SCAN FAILED"):
        _scan_bytes(payload, "Python archive entry 'amg.config'")


def test_exact_value_scan_is_hard_failure_without_echoing_secret() -> None:
    fake_secret = "owner-fake-secret-1234567890"
    with pytest.raises(RuntimeError) as exc_info:
        _scan_bytes(
            b"prefix:" + fake_secret.encode("utf-8") + b":suffix",
            "synthetic entry",
            (("OTHER_API_KEY", fake_secret),),
        )

    message = str(exc_info.value)
    assert "SECRET SCAN FAILED" in message
    assert "OTHER_API_KEY" in message
    assert fake_secret not in message


def test_exact_value_scan_detects_distinctive_middle_fragment() -> None:
    fake_secret = "prefix00-owner-middle-secret-suffix99"
    middle_fragment = fake_secret[8:24]

    with pytest.raises(RuntimeError) as exc_info:
        _scan_bytes(
            middle_fragment.encode("utf-8"),
            "synthetic entry",
            (("OTHER_TOKEN", fake_secret),),
        )

    message = str(exc_info.value)
    assert "OTHER_TOKEN" in message
    assert fake_secret not in message
    assert middle_fragment not in message


def test_exact_value_loader_combines_environment_and_dotenv(tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "GEMINI_API_KEY='dotenv-gemini-secret'\n"
        "SECONDARY_TOKEN=dotenv-token-secret # local token\n"
        "UNRELATED_PASSWORD=not-scanned\n",
        encoding="utf-8",
    )

    secrets = _load_secret_values(
        environ={
            "VOYAGE_API_KEY": "environment-voyage-secret",
            "CUSTOM_API_KEY": "environment-custom-secret",
            "EMPTY_TOKEN": "",
            "UNRELATED_PASSWORD": "not-scanned",
        },
        dotenv_path=dotenv_path,
    )

    assert secrets == [
        ("GEMINI_API_KEY", "dotenv-gemini-secret"),
        ("SECONDARY_TOKEN", "dotenv-token-secret"),
        ("VOYAGE_API_KEY", "environment-voyage-secret"),
        ("CUSTOM_API_KEY", "environment-custom-secret"),
    ]


def test_exact_value_scan_warns_when_no_keys_are_loadable(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    secrets = _load_secret_values(environ={}, dotenv_path=tmp_path / ".env")

    captured = capsys.readouterr()
    assert secrets == []
    assert "WARNING: exact-value secret scan could not run" in captured.err
    assert "only the heuristic tier applied" in captured.err


def test_spec_has_a_closed_secret_safe_data_allowlist() -> None:
    """The spec may bundle only web templates and static assets."""

    keywords = _analysis_keywords()
    datas = keywords.get("datas")
    assert isinstance(datas, ast.List), "spec datas must remain a literal inspectable list"
    assert len(datas.elts) == 2
    sources: list[str] = []
    destinations: set[str] = set()
    for item in datas.elts:
        assert isinstance(item, ast.Tuple) and len(item.elts) == 2
        sources.append(ast.unparse(item.elts[0]).casefold())
        destination = ast.literal_eval(item.elts[1])
        assert isinstance(destination, str)
        destinations.add(destination.replace("\\", "/").casefold())

    assert destinations == {"amg/web/templates", "amg/web/static"}
    assert all(
        source.endswith("'web' / 'templates')")
        or source.endswith("'web' / 'static')")
        for source in sources
    )
    prohibited = (
        ".env",
        ".env.keys-backup",
        ".amg_cache",
        ".amg_usage.json",
        ".git",
        "tests",
        ".db",
        ".sqlite",
    )
    assert not any(marker in source for marker in prohibited for source in sources)

    excludes = keywords.get("excludes")
    assert isinstance(excludes, ast.List)
    excluded_names = {ast.literal_eval(item) for item in excludes.elts}
    assert {"pytest", "_pytest", "tests"} <= excluded_names


def test_user_data_dir_uses_source_root_and_frozen_local_app_data(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert user_data_dir() == config_module.REPO_ROOT

    local_app_data = tmp_path / "LocalAppData"
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert user_data_dir() == local_app_data / "AIMemoryGovernance"
    assert user_data_dir().is_dir()


def test_settings_round_trip_changes_resolved_providers_and_clear_is_offline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "settings.json"
    monkeypatch.setattr(config_module, "settings_file_path", lambda: path)
    # Simulate the packaged default (no env override); the socket guard remains active.
    monkeypatch.delenv("AMG_OFFLINE", raising=False)
    monkeypatch.setenv("AMG_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("AMG_EMBED_PROVIDER", "voyage")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)

    save_provider_settings(
        path,
        gemini_api_key="recipient-gemini-test-key",
        voyage_api_key="recipient-voyage-test-key",
        gemini_model="gemini-3.5-flash",
    )
    get_settings.cache_clear()
    configured = get_settings()
    assert configured.offline is False
    assert configured.resolved_llm_provider() == "gemini"
    assert configured.resolved_embed_provider() == "voyage"

    clear_provider_settings(path)
    get_settings.cache_clear()
    reset_provider_state(clear_working_model=True)
    cleared = get_settings()
    assert cleared.offline is True
    assert cleared.resolved_llm_provider() == "stub"
    assert cleared.resolved_embed_provider() == "local"


def test_empty_settings_post_stays_offline_and_responses_do_not_echo_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "settings.json"
    monkeypatch.setattr(config_module, "settings_file_path", lambda: path)
    # No provider method is called; the suite's socket guard remains active.
    monkeypatch.delenv("AMG_OFFLINE", raising=False)
    monkeypatch.setenv("AMG_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("AMG_EMBED_PROVIDER", "voyage")
    get_settings.cache_clear()
    reset_provider_state(clear_working_model=True)

    with TestClient(create_app(tmp_path / "phase8.db")) as client:
        empty = client.post(
            "/api/settings",
            json={
                "gemini_api_key": "",
                "voyage_api_key": "",
                "gemini_model": "gemini-3.5-flash",
            },
        )
        assert empty.status_code == 200
        assert empty.json()["offline"] is True
        assert empty.json()["gemini"]["resolved_provider"] == "stub"
        assert empty.json()["voyage"]["resolved_provider"] == "local"

        gemini_key = "recipient-gemini-secret-123456"
        voyage_key = "recipient-voyage-secret-654321"
        saved = client.post(
            "/api/settings",
            json={
                "gemini_api_key": gemini_key,
                "voyage_api_key": voyage_key,
                "gemini_model": "gemini-3.5-flash",
            },
        )
        assert saved.status_code == 200
        response_text = json.dumps(saved.json(), sort_keys=True)
        assert gemini_key not in response_text
        assert voyage_key not in response_text
        read_back = json.dumps(client.get("/api/settings").json(), sort_keys=True)
        assert gemini_key not in read_back
        assert voyage_key not in read_back


def test_built_executable_contains_no_nonempty_key_assignment() -> None:
    if not EXE_PATH.is_file():
        pytest.skip(
            "dist/AIMemoryGovernance.exe is absent; artifact byte scan runs after a build."
        )
    exact_secrets = _load_secret_values()
    executable = EXE_PATH.read_bytes()
    _scan_bytes(executable, EXE_PATH.name, exact_secrets)

    try:
        from PyInstaller.archive.readers import CArchiveReader, PKG_ITEM_PYZ
    except ImportError:
        pytest.fail(
            "A built executable exists but PyInstaller is unavailable for archive inspection."
        )
    archive = CArchiveReader(str(EXE_PATH))
    prohibited_segments = {".git", ".amg_cache", "tests"}
    for name, toc_entry in archive.toc.items():
        normalized = str(name).replace("\\", "/").casefold()
        parts = set(part for part in normalized.split("/") if part)
        module_parts = normalized.replace("/", ".").split(".")
        basename = normalized.rsplit("/", 1)[-1]
        assert parts.isdisjoint(prohibited_segments), name
        assert "tests" not in module_parts, name
        assert basename != ".amg_usage.json", name
        assert basename != ".env", name
        assert not (
            basename.startswith(".env.") and basename != ".env.example"
        ), name
        assert not basename.endswith(".db"), name
        assert ".sqlite" not in basename, name
        payload = archive.extract(name)
        if isinstance(payload, bytes):
            _scan_bytes(payload, str(name), exact_secrets)
        if toc_entry[-1] == PKG_ITEM_PYZ:
            pyz_archive = archive.open_embedded_archive(name)
            for module_name in pyz_archive.toc:
                assert not _is_prohibited_module_name(str(module_name)), module_name
                module_payload = pyz_archive.extract(module_name, raw=True)
                if isinstance(module_payload, bytes):
                    _scan_bytes(module_payload, str(module_name), exact_secrets)
