from __future__ import annotations

import zipfile

import pytest

from app.core.errors import DocumentError, IntegrityError, UnsafeArchiveError
from app.db.connection import connect
from app.db.migrate import migrate
from app.documents.safety import ZipLimits, safe_extract_zip, sanitize_filename
from app.documents.vault import DocumentVault
from app.security.audit import AuditService
from app.services.clients import ClientService


def setup(tmp_path):
    db = connect(tmp_path / "docs.sqlite3")
    migrate(db)
    master = bytes(range(32))
    audit = AuditService(db, bytes(reversed(range(32))))
    clients = ClientService(db, master, audit)
    client = clients.create({"name": "Document Test Client"})
    vault = DocumentVault(db, tmp_path / "vault", master, audit)
    return db, vault, client


def test_encrypted_document_ingestion_search_and_round_trip(tmp_path):
    db, vault, client = setup(tmp_path)
    original = b"Confidential creditor claim reference ABC-123 and amount INR 1000."
    source = tmp_path / "claim.txt"
    source.write_bytes(original)
    document_id = vault.ingest(source, client_id=client, category="Claim", tags=["creditor"])
    row = db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
    encrypted = (tmp_path / "vault" / row["encrypted_path"]).read_bytes()
    assert original not in encrypted
    assert vault.read(document_id) == original
    results = db.execute("SELECT entity_id FROM search_index WHERE search_index MATCH ?", ("creditor",)).fetchall()
    assert any(int(row[0]) == document_id for row in results)
    # Same content/association deduplicates.
    assert vault.ingest(source, client_id=client) == document_id


def test_tampered_vault_ciphertext_rejected(tmp_path):
    db, vault, client = setup(tmp_path)
    source = tmp_path / "secret.txt"
    source.write_text("Highly confidential", encoding="utf-8")
    document_id = vault.ingest(source, client_id=client)
    row = db.execute("SELECT encrypted_path FROM documents WHERE id=?", (document_id,)).fetchone()
    stored = tmp_path / "vault" / row[0]
    changed = bytearray(stored.read_bytes())
    changed[-1] ^= 1
    stored.write_bytes(changed)
    with pytest.raises(IntegrityError):
        vault.read(document_id)


def test_zip_slip_zip_bomb_and_symlink_are_blocked(tmp_path):
    slip = tmp_path / "slip.zip"
    with zipfile.ZipFile(slip, "w") as archive:
        archive.writestr("../../outside.txt", "bad")
    with pytest.raises(UnsafeArchiveError):
        safe_extract_zip(slip, tmp_path / "out")
    assert not (tmp_path / "outside.txt").exists()

    bomb = tmp_path / "bomb.zip"
    with zipfile.ZipFile(bomb, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("huge.txt", "0" * 200_000)
    with pytest.raises(UnsafeArchiveError):
        safe_extract_zip(bomb, tmp_path / "bomb-out", ZipLimits(max_ratio=2))

    link = tmp_path / "link.zip"
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = 0o120777 << 16
    with zipfile.ZipFile(link, "w") as archive:
        archive.writestr(info, "target")
    with pytest.raises(UnsafeArchiveError):
        safe_extract_zip(link, tmp_path / "link-out")


def test_signature_validation_and_malicious_filename(tmp_path):
    fake = tmp_path / "fake.pdf"
    fake.write_text("not a pdf", encoding="utf-8")
    db, vault, client = setup(tmp_path / "work")
    with pytest.raises(DocumentError):
        vault.ingest(fake, client_id=client)
    assert sanitize_filename("../../CON:<bad>?.txt").startswith("_CON")


def test_document_metadata_search_update_and_zip_duplicate_feedback(tmp_path):
    db, vault, client = setup(tmp_path)
    source = tmp_path / "proof of claim.txt"
    source.write_text("Operational creditor invoice proof amount 25000", encoding="utf-8")
    document_id = vault.ingest(source, client_id=client, category="Claim", tags=["creditor", "proof"])

    metadata = vault.metadata(document_id)
    assert metadata["safe_filename"] == "proof of claim.txt"
    assert metadata["client_name"] == "Document Test Client"
    assert "Operational creditor" in metadata["extracted_text"]
    assert metadata["tags"] == ["creditor", "proof"]

    results = vault.list_documents(query="invoice", client_id=client)
    assert [item["id"] for item in results] == [document_id]

    vault.update_metadata(document_id, category="Verified Claim", tags="claim, accepted", review_status="ACCEPTED")
    changed = vault.metadata(document_id)
    assert changed["category"] == "Verified Claim"
    assert changed["tags"] == ["claim", "accepted"]
    assert changed["review_status"] == "ACCEPTED"

    archive = tmp_path / "docs.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr("proof of claim.txt", "Operational creditor invoice proof amount 25000")
        zip_file.writestr("new note.txt", "Another local searchable document")
    result = vault.import_zip(archive, client_id=client, category="Claim")
    assert len(result["duplicate_document_ids"]) == 1
    assert len(result["imported_document_ids"]) == 1
    assert result["rejected"] == []
