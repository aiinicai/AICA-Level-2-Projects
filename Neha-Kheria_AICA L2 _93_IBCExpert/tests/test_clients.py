import pytest

from app.core.errors import StorageError, ValidationError
from app.db.connection import connect
from app.db.migrate import migrate
from app.security.audit import AuditService
from app.services.clients import ClientService


def service(tmp_path):
    db = connect(tmp_path / "clients.sqlite3")
    migrate(db)
    master = bytes(range(32))
    return db, ClientService(db, master, AuditService(db, bytes(reversed(range(32)))))


def test_full_client_lifecycle_persistence_history_and_encrypted_pan(tmp_path):
    db, clients = service(tmp_path)
    client_id = clients.create({
        "name": "Acme Resolution Private Limited",
        "cin": "U12345DL2020PTC000001",
        "pan": "ABCDE1234F",
        "primary_email": "office@example.invalid",
        "custom_fields": {"source": "professional referral"},
    })
    stored = db.execute("SELECT pan_encrypted FROM clients WHERE id=?", (client_id,)).fetchone()[0]
    assert b"ABCDE1234F" not in stored
    loaded = clients.get(client_id)
    assert loaded["pan"] == "ABCDE1234F"
    assert loaded["custom_fields"]["source"] == "professional referral"

    new_version = clients.update(client_id, {"industry": "Manufacturing", "pan": "ZZZZZ9999Z"}, loaded["row_version"])
    assert new_version == 2
    assert clients.get(client_id)["industry"] == "Manufacturing"
    history = clients.history(client_id)
    assert {item["field_name"] for item in history} >= {"__created__", "industry", "pan"}
    pan_history = next(item for item in history if item["field_name"] == "pan")
    assert "ABCDE1234F" not in (pan_history["previous_value"] or "")

    with pytest.raises(StorageError):
        clients.update(client_id, {"industry": "Stale write"}, expected_version=1)
    assert clients.search("Acme")[0]["id"] == client_id
    clients.archive(client_id)
    assert clients.search(status="ARCHIVED")[0]["id"] == client_id
    clients.restore(client_id)
    clients.soft_delete(client_id)
    with pytest.raises(ValidationError):
        clients.get(client_id)
    assert clients.get(client_id, include_deleted=True)["status"] == "DELETED"

    db.close()
    reopened = connect(tmp_path / "clients.sqlite3")
    persisted = ClientService(reopened, bytes(range(32)), AuditService(reopened, bytes(reversed(range(32)))))
    assert persisted.get(client_id, include_deleted=True)["name"].startswith("Acme")
    persisted.permanent_delete(client_id, "Acme Resolution Private Limited")
    with pytest.raises(ValidationError):
        persisted.get(client_id, include_deleted=True)


def test_sql_injection_is_data_not_code(tmp_path):
    db, clients = service(tmp_path)
    hostile = "Robert'); DROP TABLE clients;--"
    client_id = clients.create({"name": hostile})
    assert clients.get(client_id)["name"] == hostile
    assert db.execute("SELECT name FROM sqlite_master WHERE name='clients'").fetchone()
