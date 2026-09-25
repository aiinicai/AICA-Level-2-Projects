from pathlib import Path

from app.db.connection import connect
from app.db.migrate import migrate
from app.documents.vault import DocumentVault
from app.legal.service import LegalService
from app.plugins.manager import EventBus
from app.security.audit import AuditService
from app.services.clients import ClientService
from app.services.review_imports import StructuredImportService


def setup(tmp_path: Path):
    db = connect(tmp_path / "review.sqlite3")
    assert migrate(db) == 3
    master = bytes(range(32))
    audit = AuditService(db, bytes(reversed(range(32))))
    vault = DocumentVault(db, tmp_path / "vault", master, audit)
    service = StructuredImportService(
        db, vault, EventBus(db), ClientService(db, master, audit), LegalService(db, audit)
    )
    return db, service


def test_csv_client_rows_are_staged_then_explicitly_created(tmp_path):
    db, service = setup(tmp_path)
    source = tmp_path / "clients.csv"
    source.write_text("Client Name,CIN,Email\nAlpha Ltd,U12345,alpha@example.com\n", encoding="utf-8")

    result = service.stage_structured(source, target_type="CLIENT", profile_name="Client CSV")
    assert result["review_items"] == 1
    assert db.execute("SELECT COUNT(*) FROM clients").fetchone()[0] == 0
    item = service.list_review()[0]
    assert item["status"] == "PENDING"
    assert service.get_review(item["id"])["payload"]["name"] == "Alpha Ltd"

    resolved = service.resolve(item["id"], note="Reviewed locally")
    assert resolved["created_entity_type"] == "client"
    row = db.execute("SELECT name,cin,primary_email FROM clients WHERE id=?", (resolved["created_entity_id"],)).fetchone()
    assert tuple(row) == ("Alpha Ltd", "U12345", "alpha@example.com")
    assert db.execute("SELECT status FROM imports WHERE id=?", (result["import_id"],)).fetchone()[0] == "COMPLETE"
    assert service.profiles()[0]["name"] == "Client CSV"


def test_legal_judgment_stays_review_required_after_approval(tmp_path):
    db, service = setup(tmp_path)
    source = tmp_path / "judgments.json"
    source.write_text(
        '[{"title":"Example v Example","court":"NCLT","text_content":"Locally supplied judgment text"}]',
        encoding="utf-8",
    )
    result = service.stage_structured(source, target_type="LEGAL_JUDGMENT")
    item = service.list_review()[0]
    resolved = service.resolve(item["id"])
    row = db.execute("SELECT verification_status,text_content FROM judgments WHERE id=?", (resolved["created_entity_id"],)).fetchone()
    assert tuple(row) == ("REVIEW_REQUIRED", "Locally supplied judgment text")
    assert db.execute("SELECT status FROM imports WHERE id=?", (result["import_id"],)).fetchone()[0] == "COMPLETE"


def test_local_legal_source_document_is_vaulted_and_sent_to_review(tmp_path):
    db, service = setup(tmp_path)
    source = tmp_path / "regulation.txt"
    source.write_text("User-selected local regulation source text", encoding="utf-8")

    result = service.stage_legal_source_document(source)
    item = service.get_review(service.list_review()[0]["id"])
    assert item["document_id"] == result["document_id"]
    assert item["target_type"] == "LEGAL_SOURCE_DOCUMENT"
    assert "regulation source text" in (item["source_excerpt"] or "")
    assert db.execute("SELECT review_status FROM documents WHERE id=?", (result["document_id"],)).fetchone()[0] == "REVIEW_REQUIRED"

    resolved = service.resolve(item["id"], note="Source retained for classification")
    assert resolved["created_entity_type"] == "document"
    assert resolved["created_entity_id"] == result["document_id"]


def test_rejecting_staged_row_does_not_create_record(tmp_path):
    db, service = setup(tmp_path)
    source = tmp_path / "clients.csv"
    source.write_text("Client Name\nDo Not Import Ltd\n", encoding="utf-8")
    result = service.stage_structured(source, target_type="CLIENT")
    item = service.list_review()[0]
    service.reject(item["id"], note="Not applicable")
    assert db.execute("SELECT COUNT(*) FROM clients").fetchone()[0] == 0
    assert db.execute("SELECT status,rejected_items FROM imports WHERE id=?", (result["import_id"],)).fetchone()[:] == ("PARTIAL", 1)
