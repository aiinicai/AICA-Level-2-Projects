import pytest

from app.core.errors import IntegrityError
from app.db.connection import connect
from app.db.migrate import migrate
from app.security.audit import AuditService


def test_audit_chain_detects_content_modification_and_deletion(tmp_path):
    db = connect(tmp_path / "audit.sqlite3")
    migrate(db)
    service = AuditService(db, bytes(range(32)))
    first = service.append("CLIENT_CREATED", "Created client", entity_type="client", entity_id=1)
    second = service.append("CLIENT_UPDATED", "Updated client", entity_type="client", entity_id=1)
    assert service.verify() == (True, None)

    db.execute("UPDATE audit_entries SET summary='forged' WHERE id=?", (first,))
    assert service.verify() == (False, first)
    with pytest.raises(IntegrityError):
        service.assert_valid()

    db.execute("DELETE FROM audit_entries")
    first = service.append("ONE", "one")
    second = service.append("TWO", "two")
    db.execute("DELETE FROM audit_entries WHERE id=?", (first,))
    assert service.verify() == (False, second)
