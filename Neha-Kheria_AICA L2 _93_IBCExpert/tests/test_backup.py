from pathlib import Path

import pytest

from app.core.errors import BackupError, IntegrityError
from app.db.connection import connect
from app.db.migrate import migrate
from app.documents.vault import DocumentVault
from app.security.audit import AuditService
from app.security.encrypted_stream import decrypt_file, encrypt_file
from app.services.backup import BackupService
from app.services.clients import ClientService


def test_encrypted_stream_round_trip_and_truncation(tmp_path):
    source = tmp_path / "large.bin"
    source.write_bytes(bytes(range(256)) * 10000)
    encrypted = tmp_path / "large.enc"
    restored = tmp_path / "restored.bin"
    key = bytes(range(32))
    encrypt_file(source, encrypted, key, b"test")
    decrypt_file(encrypted, restored, key, b"test")
    assert restored.read_bytes() == source.read_bytes()
    truncated = tmp_path / "truncated.enc"
    truncated.write_bytes(encrypted.read_bytes()[:-20])
    with pytest.raises(IntegrityError):
        decrypt_file(truncated, tmp_path / "bad.bin", key, b"test")


def test_create_modify_restore_returns_database_and_document(tmp_path):
    db_path = tmp_path / "app.sqlite3"
    vault_path = tmp_path / "vault"
    db = connect(db_path)
    migrate(db)
    master = bytes(range(32))
    audit = AuditService(db, bytes(reversed(range(32))))
    clients = ClientService(db, master, audit)
    client_id = clients.create({"name": "Backup Original Client"})
    source = tmp_path / "claim.txt"
    source.write_text("Original claim evidence", encoding="utf-8")
    vault = DocumentVault(db, vault_path, master, audit)
    document_id = vault.ingest(source, client_id=client_id)
    backup_service = BackupService(db, db_path, vault_path, tmp_path / "backups", master, audit)
    backup = backup_service.create()
    assert backup_service.verify(backup)["valid"]

    clients.update(client_id, {"name": "Modified Client"}, expected_version=1)
    stored = db.execute("SELECT encrypted_path FROM documents WHERE id=?", (document_id,)).fetchone()[0]
    (vault_path / stored).unlink()
    backup_service.restore(backup)

    restored_clients = ClientService(db, master, AuditService(db, bytes(reversed(range(32)))))
    assert restored_clients.get(client_id)["name"] == "Backup Original Client"
    restored_vault = DocumentVault(db, vault_path, master, AuditService(db, bytes(reversed(range(32)))))
    assert restored_vault.read(document_id) == b"Original claim evidence"


def test_tampered_backup_rejected_before_restore(tmp_path):
    db_path = tmp_path / "app.sqlite3"
    db = connect(db_path); migrate(db)
    master = bytes(range(32)); audit = AuditService(db, bytes(reversed(range(32))))
    service = BackupService(db, db_path, tmp_path / "vault", tmp_path / "backups", master, audit)
    backup = service.create()
    changed = bytearray(backup.read_bytes()); changed[-5] ^= 1; backup.write_bytes(changed)
    with pytest.raises((BackupError, IntegrityError)):
        service.verify(backup)
