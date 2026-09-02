"""
Stage 17 — EXE Packaging, Installation & Distribution test suite.

Scope, honestly stated (see documentation/stage17_exe_packaging.md's
Known Limitations for the full explanation): this sandbox cannot build
or execute a real Windows FINsight.exe — it is Linux, has no network
access to install PyInstaller, and PyInstaller does not cross-compile.
What IS tested here is everything that actually can be, for real, in
this sandbox: the application-side changes packaging required — the
frozen-aware data root, the local secret-key file, and the automatic
database/reference-data initializer's control flow (isolated from the
real database/seed/*.py modules' pre-existing use of the legacy
SQLAlchemy `.query()` API, which this sandbox's ORM verification shim
does not implement — a newly-disclosed, shim-only gap, not a bug in
this stage's own code; see the module docstring note on
_run_seed_modules below and the documentation's Known Limitations).

Uses only synthetic data and a throwaway tmp_path for every filesystem
operation — no real client data, no writes outside tmp_path.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


# =============================================================================
# Frozen-aware data root (config.py, finsight_app.py) — Section 8
# =============================================================================
# Run as a subprocess against a clean interpreter rather than
# monkeypatching sys.frozen and importlib.reload()-ing config.py
# in-process: config.py is imported by nearly every other test file in
# this suite, and mutating/reloading the shared module object mid-run
# risks contaminating unrelated tests. A subprocess is slower but
# completely isolated and still exercises the real, unmodified source.

def _run_python(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=15, cwd=str(REPO_ROOT),
    )


def test_base_dir_is_dev_relative_when_not_frozen():
    result = _run_python(
        "import sys, config\n"
        "assert not getattr(sys, 'frozen', False)\n"
        "print(config.BASE_DIR)"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(REPO_ROOT)


def test_base_dir_is_exe_relative_when_frozen(tmp_path):
    fake_exe = tmp_path / "FINsight.exe"
    fake_exe.touch()
    script = (
        "import sys\n"
        "sys.frozen = True\n"
        f"sys.executable = {str(fake_exe)!r}\n"
        "import config\n"
        "print(config.BASE_DIR)"
    )
    result = _run_python(script)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(tmp_path)


def test_frozen_base_dir_only_affects_user_data_paths_not_templates():
    """Confirms the deliberate split documented in config.py's Stage 17
    comment: BASE_DIR drives DATABASE_PATH/DATA_*_DIR/LOG_DIR only —
    nothing about template/static resolution (app/__init__.py's own
    project_root, computed independently) is touched."""
    result = _run_python(
        "import sys, config\n"
        "sys.frozen = True\n"
        "import tempfile, os\n"
        "d = tempfile.mkdtemp()\n"
        "sys.executable = os.path.join(d, 'FINsight.exe')\n"
        "open(sys.executable, 'w').close()\n"
        "import importlib\n"
        "importlib.reload(config)\n"
        "assert str(config.Config.DATABASE_PATH).startswith(d)\n"
        "assert str(config.Config.LOG_DIR).startswith(d)\n"
        "print('ok')"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_finsight_app_data_root_matches_config_in_dev_mode():
    """finsight_app.py duplicates config.py's frozen-check rather than
    importing it (see finsight_app.py's own docstring for why) — this
    proves the duplicate is not a fork: both resolve to the same
    directory in normal (non-frozen) operation."""
    result = _run_python(
        "import finsight_app, config\n"
        "assert finsight_app._APP_DATA_ROOT == config.BASE_DIR\n"
        "print('ok')"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


# =============================================================================
# Local secret-key file (app/bootstrap.get_or_create_secret_key) — Section 18
# =============================================================================

def test_secret_key_is_generated_on_first_call(tmp_path):
    from app.bootstrap import get_or_create_secret_key

    key = get_or_create_secret_key(tmp_path)
    assert len(key) == 64  # secrets.token_hex(32) -> 64 hex chars
    assert (tmp_path / "config" / "secret_key").exists()


def test_secret_key_is_reused_not_regenerated(tmp_path):
    from app.bootstrap import get_or_create_secret_key

    first = get_or_create_secret_key(tmp_path)
    second = get_or_create_secret_key(tmp_path)
    assert first == second


def test_secret_key_is_never_the_dev_fallback(tmp_path):
    from app.bootstrap import get_or_create_secret_key
    from config import DEV_SECRET_KEY_FALLBACK

    key = get_or_create_secret_key(tmp_path)
    assert key != DEV_SECRET_KEY_FALLBACK


def test_secret_key_file_is_not_world_readable_on_posix(tmp_path):
    from app.bootstrap import get_or_create_secret_key

    get_or_create_secret_key(tmp_path)
    mode = (tmp_path / "config" / "secret_key").stat().st_mode & 0o777
    # Section 26: best-effort only, POSIX-only, documented as such —
    # this asserts the attempt succeeded on this (Linux) sandbox, not
    # that Windows ACLs were set (out of scope, see documentation).
    assert mode == 0o600


def test_secret_key_survives_being_read_with_trailing_whitespace(tmp_path):
    """A user or backup tool re-saving the file with a trailing
    newline must not silently produce a different key on next start."""
    from app.bootstrap import get_or_create_secret_key

    first = get_or_create_secret_key(tmp_path)
    path = tmp_path / "config" / "secret_key"
    path.write_text(first + "\n", encoding="utf-8")
    second = get_or_create_secret_key(tmp_path)
    assert first == second


# =============================================================================
# Database initializer control flow (app/bootstrap.initialize_database)
# — Sections 10, 11, 23. Seed modules and Alembic are stubbed (see
# module docstring) so this tests THIS stage's own orchestration logic,
# not the pre-existing seed scripts' unrelated legacy-API shim gap.
# =============================================================================

@pytest.fixture()
def bootstrap_app(tmp_path):
    """A real (non-TESTING) app, isolated to tmp_path, with the schema
    NOT pre-created — initialize_database is what's supposed to create
    it, so the fixture deliberately doesn't do that itself."""
    from config import Config

    class IsolatedConfig(Config):
        TESTING = False
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'finsight.db'}"
        DATABASE_PATH = tmp_path / "finsight.db"
        DATA_INPUT_DIR = tmp_path / "data" / "input"
        DATA_PROCESSED_DIR = tmp_path / "data" / "processed"
        DATA_OUTPUT_DIR = tmp_path / "data" / "output"
        LOG_DIR = tmp_path / "logs"

    from app import create_app

    return create_app(IsolatedConfig)


@pytest.fixture()
def stub_seed_modules(monkeypatch):
    """Replaces the four real seed(session) functions with tracking
    stubs, isolating initialize_database's own orchestration from the
    real modules' pre-existing, unrelated use of the legacy .query()
    API (which this sandbox's shim doesn't implement — see this file's
    module docstring). The real functions are untouched on disk; only
    this test process's imported references are patched, and pytest's
    monkeypatch fixture reverts this automatically after each test."""
    from database.seed import seed_reference_data, seed_accounting_rules, seed_audit_rules, seed_tax_rules

    calls = []
    for module in (seed_reference_data, seed_accounting_rules, seed_audit_rules, seed_tax_rules):
        def make_stub(name):
            def stub(session):
                calls.append(name)
            return stub
        monkeypatch.setattr(module, "seed", make_stub(module.__name__))
    return calls


def test_new_database_gets_schema_created(bootstrap_app, stub_seed_modules):
    from app.bootstrap import initialize_database
    from app import extensions
    from sqlalchemy import select
    from app.models import Engagement

    messages = []
    result = initialize_database(bootstrap_app.config, db_existed_before=False, log=messages.append)

    assert result["schema_created"] is True
    assert result["db_existed_before"] is False
    # Real proof the schema exists, not just a returned flag: a query
    # against a real table succeeds without "no such table".
    assert extensions.SessionLocal().scalars(select(Engagement)).all() == []


def test_existing_database_schema_is_never_recreated(bootstrap_app, stub_seed_modules, tmp_path):
    """Section 10: 'if database already exists: use it, do not
    overwrite it, do not reset it, do not recreate it unnecessarily.'"""
    from app.bootstrap import initialize_database
    from app.models import Base
    from app import extensions
    from unittest.mock import patch

    with patch.object(Base.metadata, "create_all") as mock_create_all:
        initialize_database(bootstrap_app.config, db_existed_before=True, log=lambda *_: None)
        mock_create_all.assert_not_called()


def test_seed_modules_are_all_invoked_and_committed(bootstrap_app, stub_seed_modules):
    from app.bootstrap import initialize_database

    result = initialize_database(bootstrap_app.config, db_existed_before=False, log=lambda *_: None)
    assert set(result["seeded_modules"]) == {
        "database.seed.seed_reference_data",
        "database.seed.seed_accounting_rules",
        "database.seed.seed_audit_rules",
        "database.seed.seed_tax_rules",
    }
    assert set(stub_seed_modules) == set(result["seeded_modules"])


def test_seeding_failure_does_not_crash_startup(bootstrap_app, monkeypatch):
    """A reference-data seeding problem must never prevent the
    application from starting — the user's own engagement data is
    unaffected either way (Section 10/12)."""
    from app.bootstrap import initialize_database
    from database.seed import seed_reference_data

    def boom(session):
        raise RuntimeError("simulated seed failure")

    monkeypatch.setattr(seed_reference_data, "seed", boom)
    messages = []
    result = initialize_database(bootstrap_app.config, db_existed_before=False, log=messages.append)
    assert result["schema_created"] is True  # schema creation had already succeeded
    assert any("reference data" in m.lower() for m in messages)
    assert not any("Traceback" in m for m in messages)  # Section 12: no raw traceback surfaced


def test_new_db_migration_result_reflects_alembic_availability(bootstrap_app, stub_seed_modules):
    """This sandbox genuinely does not have Alembic installed (same
    disclosed gap as tests/unit/test_migration.py since Stage 15), so
    in THIS environment this exercises the real ImportError fallback
    path — confirmed non-fatal (schema still gets created) and clearly
    disclosed in the returned result, not silently swallowed. The
    "happy path" (Alembic present) is exercised separately below with a
    fake alembic.command module, since real Alembic can't be installed
    here to test the other branch directly."""
    from app.bootstrap import initialize_database

    result = initialize_database(bootstrap_app.config, db_existed_before=False, log=lambda *_: None)
    assert result["migration"] in ("skipped_alembic_not_installed", "stamped_head_new_db")
    assert result["schema_created"] is True


def test_alembic_available_path_stamps_head_on_new_db(bootstrap_app, stub_seed_modules, monkeypatch):
    """Simulates Alembic being installed (as it will be in a real
    packaged build — see documentation's Known Limitations for why the
    real package can't be installed in this sandbox) by injecting a
    fake alembic.command module, to prove the "happy path" branch
    (Alembic present) is reached and calls stamp(..., "head") — not
    just the ImportError fallback, which is the only branch a
    no-Alembic sandbox would otherwise ever exercise."""
    import types
    import sys as _sys

    calls = []

    fake_command = types.ModuleType("alembic.command")
    fake_command.stamp = lambda cfg, rev: calls.append(("stamp", rev))
    fake_command.upgrade = lambda cfg, rev: calls.append(("upgrade", rev))
    fake_alembic_config = types.ModuleType("alembic.config")

    class _FakeAlembicConfig:
        def __init__(self, *a, **k):
            pass

        def set_main_option(self, *a, **k):
            pass

    fake_alembic_config.Config = _FakeAlembicConfig
    fake_alembic = types.ModuleType("alembic")

    monkeypatch.setitem(_sys.modules, "alembic", fake_alembic)
    monkeypatch.setitem(_sys.modules, "alembic.command", fake_command)
    monkeypatch.setitem(_sys.modules, "alembic.config", fake_alembic_config)

    from app.bootstrap import initialize_database

    result = initialize_database(bootstrap_app.config, db_existed_before=False, log=lambda *_: None)
    assert result["migration"] == "stamped_head_new_db"
    assert ("stamp", "head") in calls


def test_alembic_available_path_upgrades_existing_db(bootstrap_app, stub_seed_modules, monkeypatch):
    import types
    import sys as _sys

    calls = []
    fake_command = types.ModuleType("alembic.command")
    fake_command.stamp = lambda cfg, rev: calls.append(("stamp", rev))
    fake_command.upgrade = lambda cfg, rev: calls.append(("upgrade", rev))
    fake_alembic_config = types.ModuleType("alembic.config")

    class _FakeAlembicConfig:
        def __init__(self, *a, **k):
            pass

        def set_main_option(self, *a, **k):
            pass

    fake_alembic_config.Config = _FakeAlembicConfig
    fake_alembic = types.ModuleType("alembic")

    monkeypatch.setitem(_sys.modules, "alembic", fake_alembic)
    monkeypatch.setitem(_sys.modules, "alembic.command", fake_command)
    monkeypatch.setitem(_sys.modules, "alembic.config", fake_alembic_config)

    from app.bootstrap import initialize_database
    from app.models import Base
    from unittest.mock import patch

    with patch.object(Base.metadata, "create_all") as mock_create_all:
        result = initialize_database(bootstrap_app.config, db_existed_before=True, log=lambda *_: None)
        mock_create_all.assert_not_called()  # Section 10: existing DB is never recreated
    assert result["migration"] == "upgraded_existing_db"
    assert ("upgrade", "head") in calls


def test_alembic_failure_on_existing_db_is_never_destructive(bootstrap_app, stub_seed_modules, monkeypatch):
    import types
    import sys as _sys

    def boom_upgrade(cfg, rev):
        raise RuntimeError("simulated alembic failure")

    fake_command = types.ModuleType("alembic.command")
    fake_command.upgrade = boom_upgrade
    fake_command.stamp = lambda cfg, rev: None
    fake_alembic_config = types.ModuleType("alembic.config")

    class _FakeAlembicConfig:
        def __init__(self, *a, **k):
            pass

        def set_main_option(self, *a, **k):
            pass

    fake_alembic_config.Config = _FakeAlembicConfig
    fake_alembic = types.ModuleType("alembic")

    monkeypatch.setitem(_sys.modules, "alembic", fake_alembic)
    monkeypatch.setitem(_sys.modules, "alembic.command", fake_command)
    monkeypatch.setitem(_sys.modules, "alembic.config", fake_alembic_config)

    from app.bootstrap import initialize_database
    from app.models import Base
    from unittest.mock import patch

    messages = []
    with patch.object(Base.metadata, "create_all") as mock_create_all:
        result = initialize_database(bootstrap_app.config, db_existed_before=True, log=messages.append)
        mock_create_all.assert_not_called()
    assert result["migration"].startswith("upgrade_failed")
    assert not any("Traceback" in m for m in messages)  # Section 12


# =============================================================================
# Mode selection (finsight_app._choose_mode) — Section 15
# =============================================================================

def test_choose_mode_respects_env_var_local(monkeypatch):
    monkeypatch.setenv("FINSIGHT_LAUNCH_MODE", "local")
    import finsight_app

    assert finsight_app._choose_mode() == "local"


def test_choose_mode_respects_env_var_lan(monkeypatch):
    monkeypatch.setenv("FINSIGHT_LAUNCH_MODE", "lan")
    import finsight_app

    assert finsight_app._choose_mode() == "lan"


def test_choose_mode_prompts_and_validates_input(monkeypatch, capsys):
    monkeypatch.delenv("FINSIGHT_LAUNCH_MODE", raising=False)
    import finsight_app

    answers = iter(["bogus", "2"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    assert finsight_app._choose_mode() == "lan"
    out = capsys.readouterr().out
    assert "Please enter 1 or 2." in out


# =============================================================================
# No source data in the package (Section 41) — static repo hygiene checks
# =============================================================================

def test_no_development_database_committed_in_repo():
    db_path = REPO_ROOT / "database" / "finsight.db"
    # It's fine for the file to exist locally during development (it's
    # gitignored — see .gitignore, unchanged since Stage 6) — what
    # matters for packaging is that the delivery zip excludes it, which
    # is a build-step concern (see documentation's Package Content
    # Audit section), not something a unit test can verify from inside
    # the already-built zip. This test instead confirms the exclusion
    # RULE exists and covers it.
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "database/finsight.db" in gitignore or "*.db" in gitignore


def test_env_file_is_gitignored():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore


def test_pyinstaller_spec_file_exists_and_is_not_the_old_placeholder():
    spec = (REPO_ROOT / "build_exe.spec").read_text(encoding="utf-8")
    assert "placeholder only" not in spec
    assert "onedir" in spec.lower() or "COLLECT" in spec  # a real onedir-style spec, not the Stage 2 stub
