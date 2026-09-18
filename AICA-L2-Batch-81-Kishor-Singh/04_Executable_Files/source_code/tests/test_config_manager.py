"""Tests for utils.config_manager, especially the legacy-app-data migration
that carries settings/database/logs forward across a rebrand (e.g. the
original "PDFOfficeUtility" folder name -> "CADocuFlowAI")."""
from __future__ import annotations

import json

from utils import config_manager
from utils.config_manager import ConfigManager, _migrate_legacy_app_data, get_app_data_dir


# --------------------------------------------------------- _migrate_legacy_app_data

def test_migration_noop_when_no_legacy_folder_exists(tmp_path):
    app_dir = tmp_path / "CADocuFlowAI"
    app_dir.mkdir()
    _migrate_legacy_app_data(tmp_path, app_dir)
    assert not (app_dir / "settings.json").exists()


def test_migration_copies_settings_database_and_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(config_manager, "_LEGACY_APP_SHORT_NAMES", ["PDFOfficeUtility"])

    legacy_dir = tmp_path / "PDFOfficeUtility"
    legacy_dir.mkdir()
    (legacy_dir / "settings.json").write_text(json.dumps({"operator_name": "CA Kishor Singh"}), encoding="utf-8")
    (legacy_dir / "app_data.db").write_bytes(b"fake-sqlite-bytes")
    (legacy_dir / "logs").mkdir()
    (legacy_dir / "logs" / "pdf_office_utility.log").write_text("old log line\n", encoding="utf-8")

    app_dir = tmp_path / "CADocuFlowAI"
    app_dir.mkdir()

    _migrate_legacy_app_data(tmp_path, app_dir)

    assert json.loads((app_dir / "settings.json").read_text(encoding="utf-8"))["operator_name"] == "CA Kishor Singh"
    assert (app_dir / "app_data.db").read_bytes() == b"fake-sqlite-bytes"
    assert (app_dir / "logs" / "pdf_office_utility.log").read_text(encoding="utf-8") == "old log line\n"


def test_migration_never_overwrites_existing_new_folder_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(config_manager, "_LEGACY_APP_SHORT_NAMES", ["PDFOfficeUtility"])

    legacy_dir = tmp_path / "PDFOfficeUtility"
    legacy_dir.mkdir()
    (legacy_dir / "settings.json").write_text(json.dumps({"operator_name": "Old User"}), encoding="utf-8")

    app_dir = tmp_path / "CADocuFlowAI"
    app_dir.mkdir()
    (app_dir / "settings.json").write_text(json.dumps({"operator_name": "Already Configured"}), encoding="utf-8")

    _migrate_legacy_app_data(tmp_path, app_dir)

    assert json.loads((app_dir / "settings.json").read_text(encoding="utf-8"))["operator_name"] == "Already Configured"


def test_migration_does_not_overwrite_individual_new_files_already_present(tmp_path, monkeypatch):
    """Even mid-migration (settings.json missing but app_data.db somehow
    already present), an existing new-folder file is never clobbered."""
    monkeypatch.setattr(config_manager, "_LEGACY_APP_SHORT_NAMES", ["PDFOfficeUtility"])

    legacy_dir = tmp_path / "PDFOfficeUtility"
    legacy_dir.mkdir()
    (legacy_dir / "settings.json").write_text("{}", encoding="utf-8")
    (legacy_dir / "app_data.db").write_bytes(b"legacy-db")

    app_dir = tmp_path / "CADocuFlowAI"
    app_dir.mkdir()
    (app_dir / "app_data.db").write_bytes(b"new-db-already-here")

    _migrate_legacy_app_data(tmp_path, app_dir)

    assert (app_dir / "app_data.db").read_bytes() == b"new-db-already-here"
    assert (app_dir / "settings.json").exists()  # still migrated from legacy


def test_migration_leaves_legacy_folder_untouched(tmp_path, monkeypatch):
    monkeypatch.setattr(config_manager, "_LEGACY_APP_SHORT_NAMES", ["PDFOfficeUtility"])

    legacy_dir = tmp_path / "PDFOfficeUtility"
    legacy_dir.mkdir()
    (legacy_dir / "settings.json").write_text(json.dumps({"operator_name": "CA Kishor Singh"}), encoding="utf-8")

    app_dir = tmp_path / "CADocuFlowAI"
    app_dir.mkdir()

    _migrate_legacy_app_data(tmp_path, app_dir)

    # Legacy copy is a copy, not a move -- original must still be intact.
    assert json.loads((legacy_dir / "settings.json").read_text(encoding="utf-8"))["operator_name"] == "CA Kishor Singh"


# --------------------------------------------------------------- get_app_data_dir

def test_get_app_data_dir_migrates_on_first_real_call(tmp_path, monkeypatch):
    monkeypatch.setattr(config_manager, "APP_SHORT_NAME", "CADocuFlowAI")
    monkeypatch.setattr(config_manager, "_LEGACY_APP_SHORT_NAMES", ["PDFOfficeUtility"])
    monkeypatch.setenv("APPDATA", str(tmp_path))

    legacy_dir = tmp_path / "PDFOfficeUtility"
    legacy_dir.mkdir()
    (legacy_dir / "settings.json").write_text(json.dumps({"operator_name": "CA Kishor Singh"}), encoding="utf-8")

    app_dir = get_app_data_dir()

    assert app_dir == tmp_path / "CADocuFlowAI"
    assert json.loads((app_dir / "settings.json").read_text(encoding="utf-8"))["operator_name"] == "CA Kishor Singh"


def test_config_manager_loads_migrated_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(config_manager, "_LEGACY_APP_SHORT_NAMES", ["PDFOfficeUtility"])

    legacy_dir = tmp_path / "PDFOfficeUtility"
    legacy_dir.mkdir()
    (legacy_dir / "settings.json").write_text(json.dumps({"operator_name": "CA Kishor Singh"}), encoding="utf-8")

    app_dir = tmp_path / "CADocuFlowAI"
    app_dir.mkdir()
    _migrate_legacy_app_data(tmp_path, app_dir)

    manager = ConfigManager(app_data_dir=app_dir)
    assert manager.settings.operator_name == "CA Kishor Singh"
