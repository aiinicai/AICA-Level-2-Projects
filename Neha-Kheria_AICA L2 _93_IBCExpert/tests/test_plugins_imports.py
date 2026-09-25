from pathlib import Path

import pytest

from app.core.errors import ValidationError
from app.db.connection import connect
from app.db.migrate import migrate
from app.documents.vault import DocumentVault
from app.plugins.manager import EventBus, PluginManager, PluginManifest
from app.plugins.sample import SAMPLE_PLUGIN
from app.security.audit import AuditService
from app.services.imports import LocalImportService


def setup(tmp_path: Path):
    db = connect(tmp_path / "ibc.sqlite3")
    migrate(db)
    master = bytes(range(32))
    vault = DocumentVault(db, tmp_path / "vault", master, AuditService(db, bytes(reversed(range(32)))))
    events = EventBus(db)
    return db, vault, events


def test_sample_plugin_disabled_by_default_and_permission_gated(tmp_path):
    db, _, _ = setup(tmp_path)
    manager = PluginManager(db)
    manager.register(SAMPLE_PLUGIN)
    plugin = manager.list_plugins()[0]
    assert plugin["enabled"] == 0
    with pytest.raises(ValidationError):
        manager.require_permission(SAMPLE_PLUGIN.key, "events.read")
    manager.set_enabled(SAMPLE_PLUGIN.key, True)
    manager.require_permission(SAMPLE_PLUGIN.key, "events.read")


def test_future_network_permission_cannot_be_registered(tmp_path):
    db, _, _ = setup(tmp_path)
    manager = PluginManager(db)
    with pytest.raises(ValidationError):
        manager.register(PluginManifest("online-updater", "Online updater", "0", ("future.network_update",)))


def test_explicit_local_import_persists_history_and_event(tmp_path):
    db, vault, events = setup(tmp_path)
    source = tmp_path / "local.txt"
    source.write_text("User selected local legal material", encoding="utf-8")
    service = LocalImportService(db, vault, events)
    result = service.import_file(source, category="Manual import")
    assert result["document_id"] > 0
    row = db.execute("SELECT status,source_name,imported_items FROM imports WHERE id=?", (result["import_id"],)).fetchone()
    assert tuple(row) == ("COMPLETE", "local.txt", 1)
    event = db.execute("SELECT event_type FROM event_outbox ORDER BY id DESC LIMIT 1").fetchone()
    assert event[0] == "local_import.completed"
